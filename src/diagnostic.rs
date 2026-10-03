use crate::{registry::Rule, source::SourceFile};
use std::{ops::Range, sync::Arc};

#[derive(Debug, PartialEq, Eq)]
pub struct Diagnostic {
    pub rule: Rule,
    pub message: String,
    pub source: Arc<SourceFile>,
    pub span: Option<Range<usize>>,
    pub fix: Option<crate::fix::Fix>,
}

impl Diagnostic {
    pub(crate) fn new(
        rule: Rule,
        source: &Arc<SourceFile>,
        span: Option<Range<usize>>,
        message: impl Into<String>,
    ) -> Self {
        debug_assert!(span.as_ref().is_none_or(|span| source.valid_range(span)));
        Self {
            rule,
            message: message.into(),
            source: Arc::clone(source),
            span,
            fix: None,
        }
    }

    pub fn location(&self) -> Option<(usize, usize)> {
        self.span
            .as_ref()
            .and_then(|span| self.source.location(span.start))
    }
}
