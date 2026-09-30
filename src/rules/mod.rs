pub(crate) mod markdown;

use crate::Diagnostic;
use serde_yaml_ng::{Mapping, Value};
use std::path::Path;

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub(crate) enum Rule {
    Frontmatter,
    Name,
    DirectoryName,
    Description,
    OptionalFields,
}

impl Rule {
    pub(crate) fn id(self) -> &'static str {
        match self {
            Self::Frontmatter => "skill-frontmatter",
            Self::Name => "skill-name",
            Self::DirectoryName => "skill-directory-name",
            Self::Description => "skill-description",
            Self::OptionalFields => "skill-optional-fields",
        }
    }
}

pub(crate) fn check(path: &Path, source: &str) -> Vec<Diagnostic> {
    let mut diagnostics = Vec::new();
    let mut report = |rule: Rule, message: String| {
        diagnostics.push(Diagnostic {
            path: path.to_path_buf(),
            location: None,
            rule: rule.id().into(),
            message,
        });
    };
    // All metadata rules depend on parsing. Report one prerequisite failure,
    // rather than misleading missing-field errors for each dependent rule.
    let metadata = match frontmatter(source) {
        Ok(metadata) => metadata,
        Err(message) => {
            report(Rule::Frontmatter, message);
            return diagnostics;
        }
    };
    for rule in &[
        Rule::Name,
        Rule::DirectoryName,
        Rule::Description,
        Rule::OptionalFields,
    ] {
        match rule {
            Rule::Frontmatter => {}
            Rule::Name => {
                match text(&metadata, "name") {
                    None => report(
                        *rule,
                        "Field 'name' is required and must be a string".into(),
                    ),
                    Some(name) => {
                        if !(1..=64).contains(&name.chars().count()) {
                            report(*rule, "Field 'name' must contain 1–64 characters".into());
                        }
                        if name != name.to_lowercase()
                            || !name.chars().all(|c| c.is_alphanumeric() || c == '-')
                        {
                            report(*rule, "Field 'name' must use lowercase letters, numbers, and hyphens only".into());
                        }
                        if name.starts_with('-') || name.ends_with('-') || name.contains("--") {
                            report(*rule, "Field 'name' must not have leading, trailing, or consecutive hyphens".into());
                        }
                    }
                }
            }
            Rule::DirectoryName => {
                if let Some(name) = text(&metadata, "name") {
                    let directory = path.parent().and_then(Path::file_name);
                    if directory != Some(std::ffi::OsStr::new(name)) {
                        report(
                            *rule,
                            format!("Field 'name' ({name:?}) must match the containing directory"),
                        );
                    }
                } else {
                    report(
                        *rule,
                        "Cannot match directory: field 'name' must be a string".into(),
                    );
                }
            }
            Rule::Description => {
                if !text(&metadata, "description")
                    .is_some_and(|s| !s.trim().is_empty() && s.chars().count() <= 1024)
                {
                    report(
                        *rule,
                        "Field 'description' must be a nonempty string of at most 1024 characters"
                            .into(),
                    );
                }
            }
            Rule::OptionalFields => {
                for field in ["license", "allowed-tools"] {
                    if metadata.contains_key(Value::from(field)) && text(&metadata, field).is_none()
                    {
                        report(*rule, format!("Optional field '{field}' must be a string"));
                    }
                }
                if metadata.contains_key(Value::from("compatibility"))
                    && !text(&metadata, "compatibility")
                        .is_some_and(|s| !s.trim().is_empty() && s.chars().count() <= 500)
                {
                    report(*rule, "Optional field 'compatibility' must be a nonempty string of at most 500 characters".into());
                }
                if let Some(value) = metadata.get(Value::from("metadata"))
                    && !value.as_mapping().is_some_and(|mapping| {
                        mapping.iter().all(|(k, v)| k.is_string() && v.is_string())
                    })
                {
                    report(
                        *rule,
                        "Optional field 'metadata' must map string keys to string values".into(),
                    );
                }
            }
        }
    }
    diagnostics
}

fn text<'a>(metadata: &'a Mapping, field: &str) -> Option<&'a str> {
    metadata.get(Value::from(field)).and_then(Value::as_str)
}

fn frontmatter(source: &str) -> Result<Mapping, String> {
    let mut lines = source.strip_prefix('\u{feff}').unwrap_or(source).lines();
    if lines.next() != Some("---") {
        return Err("SKILL.md must start with YAML frontmatter delimited by '---'".into());
    }
    let mut yaml = String::new();
    let mut closed = false;
    for line in lines {
        if line == "---" {
            closed = true;
            break;
        }
        yaml.push_str(line);
        yaml.push('\n');
    }
    if !closed {
        return Err("YAML frontmatter is missing its closing '---' delimiter".into());
    }
    let value: Value = serde_yaml_ng::from_str(&yaml)
        .map_err(|error| format!("Invalid YAML frontmatter: {error}"))?;
    match value {
        Value::Mapping(mapping) if mapping.keys().all(Value::is_string) => Ok(mapping),
        _ => Err("YAML frontmatter must be a mapping with string keys".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn messages(yaml: &str, rule: Rule) -> Vec<Diagnostic> {
        check(
            Path::new("skills/demo-skill/SKILL.md"),
            &format!("---\n{yaml}\n---\n"),
        )
        .into_iter()
        .filter(|diagnostic| diagnostic.rule == rule.id())
        .collect()
    }

    #[test]
    fn rejects_missing_malformed_nonmapping_and_duplicate_yaml() {
        for source in [
            "",
            "# Skill",
            "---\nname: demo-skill",
            "---\nname: [\n---",
            "---\n- list\n---",
            "---\nname: a\nname: b\n---",
            "---\n1: value\n---",
            "---\n---",
        ] {
            let diagnostics = check(Path::new("demo-skill/SKILL.md"), source);
            assert_eq!(diagnostics.len(), 1, "{source}");
            assert_eq!(diagnostics[0].rule, "skill-frontmatter");
        }
    }

    #[test]
    fn supports_crlf_bom_and_multiline_yaml() {
        let source = "\u{feff}---\r\nname: demo-skill\r\ndescription: >\r\n  First line\r\n  Second line\r\n---\r\nBody\r\n---\r\n";
        assert!(check(Path::new("demo-skill/SKILL.md"), source,).is_empty());
    }

    #[test]
    fn name_format_and_character_limits() {
        for name in ["demo-skill", "a", "café", "技能", &"a".repeat(64)] {
            assert!(
                messages(&format!("name: '{name}'"), Rule::Name).is_empty(),
                "{name}"
            );
        }
        for name in [
            "",
            "Demo",
            "two words",
            "bad_name",
            "-bad",
            "bad-",
            "bad--name",
            &"a".repeat(65),
        ] {
            assert!(
                !messages(&format!("name: '{name}'"), Rule::Name).is_empty(),
                "{name}"
            );
        }
        for yaml in ["{}", "name: 123", "name: null", "name: []"] {
            assert!(!messages(yaml, Rule::Name).is_empty());
        }
    }

    #[test]
    fn directory_name_must_match() {
        assert!(messages("name: demo-skill", Rule::DirectoryName).is_empty());
        for yaml in ["name: other", "{}", "name: 123"] {
            assert_eq!(messages(yaml, Rule::DirectoryName).len(), 1);
        }
    }

    #[test]
    fn description_checks_type_blankness_and_unicode_character_length() {
        assert!(
            messages(
                &format!("description: '{}'", "é".repeat(1024)),
                Rule::Description
            )
            .is_empty()
        );
        for yaml in [
            "{}".into(),
            "description: null".into(),
            "description: 42".into(),
            "description: '   '".into(),
            "description: ''".into(),
            format!("description: '{}'", "é".repeat(1025)),
        ] {
            assert_eq!(messages(&yaml, Rule::Description).len(), 1, "{yaml}");
        }
    }

    #[test]
    fn optional_fields_accept_valid_types_and_limits() {
        for yaml in [
            "{}".into(),
            "license: MIT\nallowed-tools: Bash(git:*) Read\nmetadata:\n  version: '1.0'".into(),
            format!("compatibility: '{}'", "é".repeat(500)),
        ] {
            assert!(messages(&yaml, Rule::OptionalFields).is_empty());
        }
        for yaml in [
            "license: 42".into(),
            "allowed-tools: [Read]".into(),
            "compatibility: null".into(),
            "compatibility: ''".into(),
            "compatibility: '  '".into(),
            format!("compatibility: '{}'", "a".repeat(501)),
            "metadata: []".into(),
            "metadata: null".into(),
            "metadata:\n  version: 1".into(),
            "metadata:\n  1: value".into(),
        ] {
            assert_eq!(messages(&yaml, Rule::OptionalFields).len(), 1, "{yaml}");
        }
    }
}
