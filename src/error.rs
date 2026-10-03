use serde::Serialize;
use std::{
    fmt,
    path::{Path, PathBuf},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum Operation {
    OpenProject,
    Configure,
    Discover,
    Read,
    InspectTarget,
    ApplyFix,
}

/// Execution failures are separate from lint findings, including in JSON output.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ScanError {
    pub operation: Operation,
    pub path: PathBuf,
    pub message: String,
}

impl ScanError {
    pub fn new(operation: Operation, path: &Path, error: impl fmt::Display) -> Self {
        Self {
            operation,
            path: path.into(),
            message: error.to_string(),
        }
    }
}

impl fmt::Display for ScanError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{:?} {}: {}",
            self.operation,
            self.path.display(),
            self.message
        )
    }
}
impl std::error::Error for ScanError {}
