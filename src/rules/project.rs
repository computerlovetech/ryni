use crate::{
    Analysis, Diagnostic, ProjectContext, SourceFile,
    document::Document,
    error::{Operation, ScanError},
    registry::Rule,
};
use std::{collections::BTreeMap, sync::Arc};

/// Retain only facts needed across files, rather than every parsed document.
#[derive(Default)]
pub(crate) struct ProjectIndex {
    names: BTreeMap<String, Vec<Arc<SourceFile>>>,
}

impl ProjectIndex {
    pub fn merge(&mut self, other: Self) {
        for (name, sources) in other.names {
            self.names.entry(name).or_default().extend(sources);
        }
    }
    pub fn insert(&mut self, document: &Document) {
        if let Some(Ok(metadata)) = &document.metadata
            && let Some(name) = super::skill::text(&metadata.fields, "name")
        {
            self.names
                .entry(name.into())
                .or_default()
                .push(Arc::clone(&document.source));
        }
    }

    pub fn check(self, context: &ProjectContext<'_>) -> Analysis {
        let mut result = Analysis::default();
        if context.settings.enabled(Rule::DuplicateSkillName) {
            for (name, sources) in self.names {
                if sources.len() > 1 {
                    for source in &sources {
                        result.diagnostics.push(Diagnostic::new(
                            Rule::DuplicateSkillName,
                            source,
                            None,
                            format!(
                                "Skill name {name:?} is used by {} skills in this scan",
                                sources.len()
                            ),
                        ));
                    }
                }
            }
        }
        if context.settings.enabled(Rule::RequiredFiles) {
            let source = Arc::new(SourceFile::new(".", ""));
            for relative in &context.settings.required_files {
                let path = context.root.join(relative);
                match context.filesystem.is_file(&path) {
                    Ok(true) => {}
                    Ok(false) => result.diagnostics.push(Diagnostic::new(
                        Rule::RequiredFiles,
                        &source,
                        None,
                        format!("Required project file {relative:?} is missing"),
                    )),
                    Err(error) => result.errors.push(ScanError::new(
                        Operation::InspectTarget,
                        std::path::Path::new(relative),
                        error,
                    )),
                }
            }
        }
        result
    }
}
