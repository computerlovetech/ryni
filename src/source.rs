use std::{
    ops::Range,
    path::{Path, PathBuf},
};

/// An immutable source snapshot. Every range is a half-open UTF-8 byte range.
#[derive(Debug, PartialEq, Eq)]
pub struct SourceFile {
    path: PathBuf,
    text: String,
    line_starts: Vec<usize>,
}

impl SourceFile {
    pub fn new(path: impl Into<PathBuf>, text: impl Into<String>) -> Self {
        let text = text.into();
        let line_starts = std::iter::once(0)
            .chain(text.match_indices('\n').map(|(offset, _)| offset + 1))
            .collect();
        Self {
            path: path.into(),
            text,
            line_starts,
        }
    }

    pub fn path(&self) -> &Path {
        &self.path
    }
    pub fn text(&self) -> &str {
        &self.text
    }

    pub fn valid_range(&self, range: &Range<usize>) -> bool {
        range.start <= range.end && self.text.get(range.clone()).is_some()
    }

    /// One-based line and Unicode scalar column, never byte or display columns.
    pub fn location(&self, offset: usize) -> Option<(usize, usize)> {
        if offset > self.text.len() || !self.text.is_char_boundary(offset) {
            return None;
        }
        let line = self.line_starts.partition_point(|start| *start <= offset);
        Some((
            line,
            self.text[self.line_starts[line - 1]..offset]
                .chars()
                .count()
                + 1,
        ))
    }
}
