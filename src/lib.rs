mod rules;

use ignore::{WalkBuilder, overrides::OverrideBuilder};
use std::{
    fs,
    ops::Range,
    path::{Path, PathBuf},
    sync::Arc,
};

#[derive(Debug, PartialEq, Eq)]
pub struct Diagnostic {
    pub path: PathBuf,
    pub rule: String,
    pub location: Option<(usize, usize)>,
    pub message: String,
    /// Original source and byte range, retained for diagnostic rendering.
    pub source: Arc<str>,
    pub span: Option<Range<usize>>,
}

#[derive(Debug)]
pub struct CheckReport {
    pub files_checked: usize,
    pub diagnostics: Vec<Diagnostic>,
}

#[derive(Debug, Default)]
pub struct CheckOptions {
    pub no_ignore: bool,
    pub exclude: Vec<String>,
}

/// Discover supported files and run all applicable built-in rules.
/// I/O errors are separate from lint violations; an empty scan is explicit.
pub fn check(project: &Path) -> Result<CheckReport, String> {
    check_with_options(project, &CheckOptions::default())
}

pub fn check_with_options(project: &Path, options: &CheckOptions) -> Result<CheckReport, String> {
    let project = fs::canonicalize(project)
        .map_err(|error| format!("cannot open project {}: {error}", project.display()))?;
    if !project.is_dir() {
        return Err(format!("expected a directory: {}", project.display()));
    }
    let mut exclusions = OverrideBuilder::new(&project);
    for pattern in &options.exclude {
        exclusions
            .add(&format!("!{pattern}"))
            .map_err(|error| format!("invalid exclusion {pattern:?}: {error}"))?;
    }
    let mut walker = WalkBuilder::new(&project);
    walker
        .standard_filters(!options.no_ignore)
        .hidden(false)
        .follow_links(false)
        .overrides(exclusions.build().map_err(|error| error.to_string())?);
    let mut paths = Vec::new();
    for entry in walker.build() {
        let entry = entry.map_err(|error| format!("cannot discover Markdown files: {error}"))?;
        if let Some(error) = entry.error() {
            return Err(format!(
                "cannot read ignore rules for {}: {error}",
                entry.path().display()
            ));
        }
        if entry.file_type().is_some_and(|kind| kind.is_file())
            && entry.path().extension().is_some_and(|extension| {
                extension.eq_ignore_ascii_case("md") || extension.eq_ignore_ascii_case("markdown")
            })
        {
            paths.push(entry.into_path());
        }
    }
    paths.sort();
    let mut report = CheckReport {
        files_checked: paths.len(),
        diagnostics: Vec::new(),
    };
    for path in paths {
        let source = fs::read_to_string(&path)
            .map_err(|error| format!("cannot read {}: {error}", path.display()))?;
        let relative = path.strip_prefix(&project).unwrap_or(&path);
        let mut diagnostics = if path.file_name().is_some_and(|name| name == "SKILL.md") {
            rules::check(&path, &source)
        } else {
            Vec::new()
        };
        diagnostics.extend(rules::markdown::check(&path, &source)?);
        let source: Arc<str> = source.into();
        report
            .diagnostics
            .extend(diagnostics.into_iter().map(|mut diagnostic| {
                diagnostic.path = relative.to_path_buf();
                diagnostic.source = Arc::clone(&source);
                diagnostic
            }));
    }
    Ok(report)
}
