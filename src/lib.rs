pub mod diagnostic;
mod discovery;
pub mod document;
pub mod error;
pub mod filesystem;
pub mod fix;
pub mod output;
pub mod registry;
pub mod report;
mod rules;
pub mod settings;
pub mod source;

pub use diagnostic::Diagnostic;
use document::Document;
use error::{Operation, ScanError};
use filesystem::{FileSystem, OsFileSystem};
use registry::Rule;
pub use report::CheckReport;
use settings::{Overrides, Settings};
pub use source::SourceFile;
use std::{
    fs,
    path::{Path, PathBuf},
};

pub struct ProjectContext<'a> {
    pub root: &'a Path,
    pub settings: &'a Settings,
    pub filesystem: &'a dyn FileSystem,
}

#[derive(Debug, Default)]
pub struct Analysis {
    pub diagnostics: Vec<Diagnostic>,
    pub errors: Vec<ScanError>,
}

/// Analyze a supplied snapshot; reading the source is the caller's responsibility.
pub fn analyze(document: &Document, context: &ProjectContext<'_>) -> Analysis {
    let path = context.root.join(document.source.path());
    let mut result = Analysis::default();
    if context.settings.enabled.iter().any(|rule| {
        matches!(rule.metadata().scope, registry::Scope::Skill) || *rule == Rule::DuplicateSkillName
    }) {
        result
            .diagnostics
            .extend(rules::skill::check(document, &path, context.settings));
    }
    if context.settings.enabled(Rule::MarkdownLocalLink) {
        let links = rules::markdown::check(document, &path, context.filesystem);
        result.diagnostics.extend(links.diagnostics);
        result.errors.extend(links.errors);
    }
    if context.settings.enabled(Rule::RequiredSections) {
        for required in &context.settings.required_sections {
            if !document.headings.contains(required) {
                result.diagnostics.push(Diagnostic::new(
                    Rule::RequiredSections,
                    &document.source,
                    None,
                    format!("Required heading {required:?} is missing"),
                ));
            }
        }
    }
    result
}

pub fn project_root(project: &Path) -> Result<PathBuf, ScanError> {
    Ok(discovery::Input::open(project)?.root)
}

/// Discover configuration at the input directory (or a file's parent) and check it.
pub fn check(project: &Path) -> Result<CheckReport, ScanError> {
    let root = project_root(project)?;
    let settings = Settings::resolve(&root, None, false, Overrides::default())?;
    check_with_settings(project, &settings)
}

#[derive(Debug, Clone, Copy)]
pub struct ExecutionOptions {
    pub threads: usize,
    pub cache_targets: bool,
}
impl Default for ExecutionOptions {
    fn default() -> Self {
        Self {
            threads: 1,
            cache_targets: true,
        }
    }
}

pub fn check_with_settings(project: &Path, settings: &Settings) -> Result<CheckReport, ScanError> {
    check_with_options(project, settings, ExecutionOptions::default())
}

pub fn check_with_options(
    project: &Path,
    settings: &Settings,
    options: ExecutionOptions,
) -> Result<CheckReport, ScanError> {
    use rayon::prelude::*;
    use std::time::Instant;
    if !(1..=256).contains(&options.threads) {
        return Err(ScanError::new(
            Operation::Configure,
            project,
            "threads must be between 1 and 256",
        ));
    }
    let input = discovery::Input::open(project)?;
    let started = Instant::now();
    let (paths, errors) = discovery::discover(&input, settings);
    let mut report = CheckReport {
        files_discovered: paths.len(),
        errors,
        ..Default::default()
    };
    report.timings.discovery_ms = started.elapsed().as_secs_f64() * 1000.0;
    let filesystem = filesystem::CachedFileSystem::new(&OsFileSystem, options.cache_targets);
    let context = ProjectContext {
        root: &input.root,
        settings,
        filesystem: &filesystem,
    };
    let check_file = |path: &PathBuf| {
        let mut result = CheckReport::default();
        let mut index = rules::project::ProjectIndex::default();
        let relative = path.strip_prefix(&input.root).unwrap_or(path);
        let started = Instant::now();
        let source = fs::read_to_string(path);
        result.timings.read_ms = started.elapsed().as_secs_f64() * 1000.0;
        match source {
            Err(error) => result
                .errors
                .push(ScanError::new(Operation::Read, relative, error)),
            Ok(source) => {
                let started = Instant::now();
                let document = Document::parse(SourceFile::new(relative, source));
                result.timings.parse_ms = started.elapsed().as_secs_f64() * 1000.0;
                let started = Instant::now();
                let analysis = analyze(&document, &context);
                result.timings.rules_ms = started.elapsed().as_secs_f64() * 1000.0;
                result.files_checked = 1;
                result.diagnostics = analysis.diagnostics;
                result.errors = analysis.errors;
                if settings.enabled(Rule::DuplicateSkillName) {
                    index.insert(&document);
                }
            }
        }
        (result, index)
    };
    let results: Vec<_> = if options.threads == 1 {
        paths.iter().map(check_file).collect()
    } else {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(options.threads)
            .build()
            .map_err(|e| ScanError::new(Operation::Configure, project, e))?;
        pool.install(|| paths.par_iter().map(check_file).collect())
    };
    let mut index = rules::project::ProjectIndex::default();
    for (result, file_index) in results {
        report.files_checked += result.files_checked;
        report.diagnostics.extend(result.diagnostics);
        report.errors.extend(result.errors);
        report.timings.read_ms += result.timings.read_ms;
        report.timings.parse_ms += result.timings.parse_ms;
        report.timings.rules_ms += result.timings.rules_ms;
        index.merge(file_index);
    }
    let started = Instant::now();
    let project_analysis = index.check(&context);
    report.timings.project_ms = started.elapsed().as_secs_f64() * 1000.0;
    (
        report.timings.target_lookups,
        report.timings.target_cache_hits,
    ) = filesystem.statistics();
    report.diagnostics.extend(project_analysis.diagnostics);
    report.errors.extend(project_analysis.errors);
    report.sort();
    Ok(report)
}
