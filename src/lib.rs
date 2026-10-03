pub mod diagnostic;
mod discovery;
pub mod document;
pub mod error;
pub mod filesystem;
pub mod fix;
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

pub fn check_with_settings(project: &Path, settings: &Settings) -> Result<CheckReport, ScanError> {
    let input = discovery::Input::open(project)?;
    let (paths, errors) = discovery::discover(&input, settings);
    let mut report = CheckReport {
        files_discovered: paths.len(),
        errors,
        ..Default::default()
    };
    let context = ProjectContext {
        root: &input.root,
        settings,
        filesystem: &OsFileSystem,
    };
    let mut index = rules::project::ProjectIndex::default();
    for path in paths {
        let relative = path.strip_prefix(&input.root).unwrap_or(&path);
        let source = match fs::read_to_string(&path) {
            Ok(source) => source,
            Err(error) => {
                report
                    .errors
                    .push(ScanError::new(Operation::Read, relative, error));
                continue;
            }
        };
        let document = Document::parse(SourceFile::new(relative, source));
        let analysis = analyze(&document, &context);
        report.files_checked += 1;
        report.diagnostics.extend(analysis.diagnostics);
        report.errors.extend(analysis.errors);
        if settings.enabled(Rule::DuplicateSkillName) {
            index.insert(&document);
        }
    }
    let project_analysis = index.check(&context);
    report.diagnostics.extend(project_analysis.diagnostics);
    report.errors.extend(project_analysis.errors);
    report.sort();
    Ok(report)
}
