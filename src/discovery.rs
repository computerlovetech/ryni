use std::path::{Path, PathBuf};
use walkdir::WalkDir;

pub(crate) fn discover(project: &Path) -> Result<Vec<PathBuf>, String> {
    let mut paths = Vec::new();
    for entry in WalkDir::new(project).follow_links(false) {
        let entry = entry.map_err(|error| format!("cannot discover Markdown files: {error}"))?;
        if entry.file_type().is_file()
            && entry.path().extension().is_some_and(|extension| {
                extension.eq_ignore_ascii_case("md") || extension.eq_ignore_ascii_case("markdown")
            })
        {
            paths.push(entry.into_path());
        }
    }
    paths.sort();
    Ok(paths)
}
