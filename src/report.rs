use crate::{Diagnostic, error::ScanError};
use serde::Serialize;

#[derive(Debug, Default)]
pub struct CheckReport {
    pub files_discovered: usize,
    pub files_checked: usize,
    pub diagnostics: Vec<Diagnostic>,
    pub errors: Vec<ScanError>,
}

impl CheckReport {
    pub fn exit_code(&self) -> u8 {
        if !self.errors.is_empty() {
            2
        } else if !self.diagnostics.is_empty() {
            1
        } else {
            0
        }
    }

    pub(crate) fn sort(&mut self) {
        self.diagnostics.sort_by(|a, b| {
            (
                a.source.path(),
                a.span.as_ref().map(|s| s.start),
                a.rule.id(),
                &a.message,
            )
                .cmp(&(
                    b.source.path(),
                    b.span.as_ref().map(|s| s.start),
                    b.rule.id(),
                    &b.message,
                ))
        });
        self.errors
            .sort_by(|a, b| (&a.path, &a.message).cmp(&(&b.path, &b.message)));
    }

    /// Schema 1: positions are one-based Unicode scalar columns; byte ranges are half-open.
    pub fn json(&self) -> serde_json::Value {
        serde_json::json!({
            "schema_version": 1,
            "files_discovered": self.files_discovered,
            "files_checked": self.files_checked,
            "complete": self.errors.is_empty(),
            "diagnostics": self.diagnostics.iter().map(|d| {
                serde_json::json!({
                    "rule": d.rule.id(), "severity": "error", "message": d.message,
                    "path": d.source.path().to_string_lossy().replace('\\', "/"),
                    "range": d.span.as_ref().map(|span| serde_json::json!({"start": span.start, "end": span.end})),
                    "location": d.location().map(Position::from),
                    "end_location": d.span.as_ref().and_then(|span| d.source.location(span.end)).map(Position::from),
                })
            }).collect::<Vec<_>>(),
            "errors": self.errors,
        })
    }
}

#[derive(Serialize)]
struct Position {
    line: usize,
    column: usize,
}
impl From<(usize, usize)> for Position {
    fn from((line, column): (usize, usize)) -> Self {
        Self { line, column }
    }
}
