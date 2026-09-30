mod rules;

use std::{
    fs,
    path::{Path, PathBuf},
};
use walkdir::WalkDir;

#[derive(Debug, PartialEq, Eq)]
pub struct Diagnostic {
    pub path: PathBuf,
    pub rule: String,
    pub message: String,
}

#[derive(Debug)]
pub struct CheckReport {
    pub files_checked: usize,
    pub diagnostics: Vec<Diagnostic>,
}

/// Discover supported files and run all applicable built-in rules.
/// I/O errors are separate from lint violations; an empty scan is explicit.
pub fn check(project: &Path) -> Result<CheckReport, String> {
    let project = fs::canonicalize(project)
        .map_err(|error| format!("cannot open project {}: {error}", project.display()))?;
    if !project.is_dir() {
        return Err(format!("expected a directory: {}", project.display()));
    }
    let mut paths = Vec::new();
    for entry in WalkDir::new(&project).follow_links(false) {
        let entry = entry.map_err(|error| format!("cannot discover skills: {error}"))?;
        if entry.file_type().is_file() && entry.file_name() == "SKILL.md" {
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
        report
            .diagnostics
            .extend(
                rules::check(&path, &source)
                    .into_iter()
                    .map(|mut diagnostic| {
                        diagnostic.path = relative.to_path_buf();
                        diagnostic
                    }),
            );
    }
    Ok(report)
}
