pub mod diagnostic;
mod discovery;
pub mod document;
pub mod error;
pub mod filesystem;
pub mod registry;
mod rules;
pub mod settings;
pub mod source;

pub use diagnostic::Diagnostic;
pub use source::SourceFile;
use std::{fs, path::Path};

#[derive(Debug)]
pub struct CheckReport {
    pub files_checked: usize,
    pub diagnostics: Vec<Diagnostic>,
}

/// Analyze a source snapshot without reading it from disk.
pub fn analyze(
    document: &document::Document,
    path: &Path,
    filesystem: &dyn filesystem::FileSystem,
) -> Result<Vec<Diagnostic>, String> {
    let mut diagnostics = rules::skill::check(document, path);
    diagnostics.extend(rules::markdown::check(document, path, filesystem)?);
    Ok(diagnostics)
}

/// Discover supported files and run all applicable built-in rules.
/// I/O errors are separate from lint violations; an empty scan is explicit.
pub fn check(project: &Path) -> Result<CheckReport, String> {
    let project = fs::canonicalize(project)
        .map_err(|error| format!("cannot open project {}: {error}", project.display()))?;
    if !project.is_dir() {
        return Err(format!("expected a directory: {}", project.display()));
    }
    let paths = discovery::discover(&project)?;
    let mut report = CheckReport {
        files_checked: paths.len(),
        diagnostics: Vec::new(),
    };
    for path in paths {
        let source = fs::read_to_string(&path)
            .map_err(|error| format!("cannot read {}: {error}", path.display()))?;
        let relative = path.strip_prefix(&project).unwrap_or(&path);
        let document = document::Document::parse(SourceFile::new(relative, source));
        report
            .diagnostics
            .extend(analyze(&document, &path, &filesystem::OsFileSystem)?);
    }
    Ok(report)
}
