use crate::{
    CheckReport, Diagnostic, SourceFile,
    document::Document,
    error::{Operation, ScanError},
};
use serde::Serialize;
use std::{
    collections::BTreeMap,
    fs,
    io::Write,
    ops::Range,
    path::{Component, Path},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum Applicability {
    Safe,
    Unsafe,
    DisplayOnly,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Edit {
    pub range: Range<usize>,
    pub replacement: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Fix {
    pub title: String,
    pub applicability: Applicability,
    pub edits: Vec<Edit>,
}

#[derive(Debug, Default)]
pub struct FixResult {
    pub files_changed: usize,
    pub errors: Vec<ScanError>,
}

/// Apply each file's edits as one validated replacement. Never mutate an incomplete scan.
/// The caller must recheck changed files; this function never edits diagnostic snapshots.
pub fn apply(root: &Path, report: &CheckReport, unsafe_fixes: bool) -> FixResult {
    let mut result = FixResult::default();
    if !report.errors.is_empty() {
        return result;
    }
    let mut files: BTreeMap<&Path, Vec<&Diagnostic>> = BTreeMap::new();
    for diagnostic in &report.diagnostics {
        if let Some(fix) = &diagnostic.fix
            && (fix.applicability == Applicability::Safe
                || unsafe_fixes && fix.applicability == Applicability::Unsafe)
        {
            files
                .entry(diagnostic.source.path())
                .or_default()
                .push(diagnostic);
        }
    }
    for (relative, diagnostics) in files {
        let apply = || -> Result<bool, ScanError> {
            let fail = |error: String| ScanError::new(Operation::ApplyFix, relative, error);
            if relative
                .components()
                .any(|c| !matches!(c, Component::Normal(_)))
            {
                return Err(fail("fix paths must be project-relative".into()));
            }
            let path = root.join(relative);
            let metadata = fs::symlink_metadata(&path).map_err(|e| fail(e.to_string()))?;
            if !metadata.is_file() {
                return Err(fail("refusing to replace a symlink or non-file".into()));
            }
            let original = fs::read_to_string(&path).map_err(|e| fail(e.to_string()))?;
            if diagnostics.iter().any(|d| d.source.text() != original) {
                return Err(fail(
                    "source changed since analysis; re-run the check".into(),
                ));
            }
            let edits: Vec<_> = diagnostics
                .iter()
                .filter_map(|d| d.fix.as_ref())
                .flat_map(|f| f.edits.iter())
                .collect();
            let transformed = apply_edits(&original, &edits).map_err(fail)?;
            if transformed == original {
                return Ok(false);
            }
            let parsed = Document::parse(SourceFile::new(relative, transformed.clone()));
            if parsed.metadata.as_ref().is_some_and(Result::is_err) {
                return Err(fail(
                    "proposed edits produce invalid skill frontmatter".into(),
                ));
            }
            let parent = path
                .parent()
                .ok_or_else(|| fail("file has no parent".into()))?;
            let mut temporary =
                tempfile::NamedTempFile::new_in(parent).map_err(|e| fail(e.to_string()))?;
            temporary
                .as_file()
                .set_permissions(metadata.permissions())
                .map_err(|e| fail(e.to_string()))?;
            temporary
                .write_all(transformed.as_bytes())
                .map_err(|e| fail(e.to_string()))?;
            temporary
                .as_file()
                .sync_all()
                .map_err(|e| fail(e.to_string()))?;
            // Recheck immediately before replacement, after preparing the new contents.
            if fs::read_to_string(&path).map_err(|e| fail(e.to_string()))? != original {
                return Err(fail("source changed while preparing fixes".into()));
            }
            temporary.persist(&path).map_err(|e| fail(e.to_string()))?;
            Ok(true)
        };
        match apply() {
            Ok(true) => result.files_changed += 1,
            Ok(false) => {}
            Err(error) => result.errors.push(error),
        }
    }
    result
}

fn apply_edits(original: &str, edits: &[&Edit]) -> Result<String, String> {
    let mut edits = edits.to_vec();
    edits.sort_by_key(|edit| (edit.range.start, edit.range.end));
    let mut previous: Option<&Edit> = None;
    for edit in &edits {
        if edit.range.start > edit.range.end || original.get(edit.range.clone()).is_none() {
            return Err("edit has an invalid UTF-8 range".into());
        }
        if previous.is_some_and(|previous| {
            previous.range.end > edit.range.start || previous.range.start == edit.range.start
        }) {
            return Err("fixes overlap; no edits applied to this file".into());
        }
        previous = Some(edit);
    }
    let mut result = original.to_owned();
    for edit in edits.into_iter().rev() {
        result.replace_range(edit.range.clone(), &edit.replacement);
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_overlaps_and_invalid_unicode_ranges() {
        let a = Edit {
            range: 0..2,
            replacement: "a".into(),
        };
        let b = Edit {
            range: 0..0,
            replacement: "b".into(),
        };
        assert!(apply_edits("é", &[&a, &b]).is_err());
        assert!(
            apply_edits(
                "é",
                &[&Edit {
                    range: 1..2,
                    replacement: "".into()
                }]
            )
            .is_err()
        );
        assert_eq!(apply_edits("é", &[&a]).unwrap(), "a");
    }
}
