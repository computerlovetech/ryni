use crate::{
    error::{Operation, ScanError},
    settings::Settings,
};
use std::{
    fs,
    path::{Path, PathBuf},
};

pub(crate) struct Input {
    pub path: PathBuf,
    pub root: PathBuf,
}
impl Input {
    pub fn open(path: &Path) -> Result<Self, ScanError> {
        let absolute =
            fs::canonicalize(path).map_err(|e| ScanError::new(Operation::OpenProject, path, e))?;
        let root = if absolute.is_dir() {
            absolute.clone()
        } else if absolute.is_file() && supported(&absolute) {
            absolute.parent().unwrap_or(Path::new(".")).to_path_buf()
        } else {
            return Err(ScanError::new(
                Operation::OpenProject,
                path,
                "expected a directory or Markdown file",
            ));
        };
        Ok(Self {
            path: absolute,
            root,
        })
    }
}
fn supported(path: &Path) -> bool {
    path.extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("md") || ext.eq_ignore_ascii_case("markdown"))
}

/// Discovery records recoverable errors rather than abandoning unrelated files.
pub(crate) fn discover(input: &Input, settings: &Settings) -> (Vec<PathBuf>, Vec<ScanError>) {
    let mut paths = Vec::new();
    let mut errors = Vec::new();
    if settings.excluded_path(
        input.path.strip_prefix(&input.root).unwrap_or(&input.path),
        input.path.is_dir(),
    ) {
        return (paths, errors);
    }
    let mut builder = ignore::WalkBuilder::new(&input.path);
    builder
        .standard_filters(settings.discovery.respect_ignore)
        .hidden(false)
        .follow_links(false);
    let root = input.root.clone();
    let settings = settings.clone();
    builder.filter_entry(move |entry| {
        !settings.excluded_path(
            entry.path().strip_prefix(&root).unwrap_or(entry.path()),
            entry.file_type().is_some_and(|kind| kind.is_dir()),
        )
    });
    for entry in builder.build() {
        match entry {
            Ok(entry) => {
                if let Some(error) = entry.error() {
                    errors.push(ScanError::new(
                        Operation::Discover,
                        entry
                            .path()
                            .strip_prefix(&input.root)
                            .unwrap_or(entry.path()),
                        error,
                    ));
                }
                if entry.file_type().is_some_and(|kind| kind.is_file()) && supported(entry.path()) {
                    paths.push(entry.into_path());
                }
            }
            Err(error) => errors.push(ScanError::new(Operation::Discover, &input.root, error)),
        }
    }
    paths.sort();
    (paths, errors)
}
