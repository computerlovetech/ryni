use ryni::{
    ProjectContext, SourceFile,
    document::Document,
    filesystem::{FileKind, FileSystem},
    settings::{LintOptions, Overrides, Settings},
};
use serde::Deserialize;
use std::{io, path::Path};

#[derive(Deserialize)]
struct Cases {
    case: Vec<Case>,
}
#[derive(Deserialize)]
struct Case {
    name: String,
    path: String,
    source: String,
    select: Vec<String>,
    expected: Vec<String>,
    #[serde(default)]
    required_metadata: Vec<String>,
    #[serde(default)]
    required_sections: Vec<String>,
}
struct Missing;
impl FileSystem for Missing {
    fn kind(&self, _: &Path) -> io::Result<Option<FileKind>> {
        Ok(None)
    }
}

#[test]
fn rule_fixtures() {
    let cases: Cases = toml::from_str(include_str!("fixtures/rules.toml")).unwrap();
    for case in cases.case {
        let settings = Settings::resolve(
            Path::new("."),
            None,
            true,
            Overrides {
                lint: LintOptions {
                    select: Some(case.select),
                    preview: Some(true),
                    required_metadata: Some(case.required_metadata),
                    required_sections: Some(case.required_sections),
                    ..Default::default()
                },
                ..Default::default()
            },
        )
        .unwrap();
        let document = Document::parse(SourceFile::new(case.path, case.source));
        let result = ryni::analyze(
            &document,
            &ProjectContext {
                root: Path::new("."),
                settings: &settings,
                filesystem: &Missing,
            },
        );
        assert!(result.errors.is_empty(), "{}", case.name);
        let mut actual: Vec<_> = result
            .diagnostics
            .iter()
            .map(|d| d.rule.id().to_string())
            .collect();
        actual.sort();
        let mut expected = case.expected;
        expected.sort();
        assert_eq!(actual, expected, "{}", case.name);
    }
}

#[test]
fn plain_diagnostic_snapshot() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("README.md"),
        "# Guide\r\n\r\né [Testing](docs/testing.md)\r\n",
    )
    .unwrap();
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_ryni"))
        .args(["check", "--isolated"])
        .arg(root.path())
        .env("NO_COLOR", "1")
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert_eq!(
        String::from_utf8(output.stdout)
            .unwrap()
            .replace("\r\n", "\n"),
        include_str!("snapshots/local-link.txt").replace("\r\n", "\n")
    );
}
