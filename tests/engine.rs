use serde_json::Value;
use std::{
    fs,
    path::Path,
    process::{Command, Output},
};

fn run(root: &Path, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_ryni"))
        .current_dir(root)
        .args(args)
        .output()
        .unwrap()
}
fn json(root: &Path, args: &[&str]) -> (i32, Value) {
    let mut arguments = vec!["check", "--output-format", "json"];
    arguments.extend(args);
    let output = run(root, &arguments);
    (
        output.status.code().unwrap(),
        serde_json::from_slice(&output.stdout).unwrap(),
    )
}

#[test]
fn json_preserves_findings_when_another_file_cannot_be_read() {
    let root = tempfile::tempdir().unwrap();
    fs::write(root.path().join("a.md"), [0xff]).unwrap();
    fs::write(root.path().join("b.md"), "é [missing](absent.md)\r\n").unwrap();
    let (code, result) = json(root.path(), &[]);
    assert_eq!(code, 2);
    assert_eq!(result["schema_version"], 1);
    assert_eq!(result["complete"], false);
    assert_eq!(result["files_discovered"], 2);
    assert_eq!(result["files_checked"], 1);
    assert_eq!(result["errors"][0]["operation"], "read");
    assert_eq!(result["errors"][0]["path"], "a.md");
    let finding = &result["diagnostics"][0];
    assert_eq!(finding["path"], "b.md");
    assert_eq!(finding["range"]["start"], 3);
    assert_eq!(finding["location"]["column"], 3);
    assert_eq!(finding["severity"], "error");
}

#[test]
fn bad_configuration_is_structured_and_isolation_bypasses_it() {
    let root = tempfile::tempdir().unwrap();
    fs::write(
        root.path().join("ryni.toml"),
        "schema-version = 1\n[lint]\nselect = ['typo']",
    )
    .unwrap();
    let (code, result) = json(root.path(), &[]);
    assert_eq!(code, 2);
    assert_eq!(result["errors"][0]["operation"], "configure");
    assert_eq!(json(root.path(), &["--isolated"]).0, 0);
}

#[test]
fn discovery_keeps_hidden_skills_and_applies_explicit_exclusions_to_files() {
    let root = tempfile::tempdir().unwrap();
    fs::create_dir_all(root.path().join(".agents/skills/demo")).unwrap();
    fs::create_dir(root.path().join("vendor")).unwrap();
    fs::write(root.path().join(".agents/skills/demo/SKILL.md"), "bad").unwrap();
    fs::write(root.path().join("vendor/README.md"), "[broken](missing)").unwrap();
    fs::write(root.path().join(".gitignore"), "vendor/\n").unwrap();
    assert_eq!(json(root.path(), &[]).1["files_checked"], 2);
    let result = json(root.path(), &["--respect-ignore"]).1;
    assert_eq!(result["files_checked"], 1);
    assert_eq!(
        result["diagnostics"][0]["path"],
        ".agents/skills/demo/SKILL.md"
    );
    assert_eq!(
        json(root.path(), &["--exclude", "vendor"]).1["files_checked"],
        1
    );
    assert_eq!(
        json(root.path(), &["vendor/README.md", "--exclude", "README.md"]).1["files_checked"],
        0
    );
    assert_eq!(json(root.path(), &["vendor/README.md"]).0, 1);
}

#[test]
fn packs_drive_document_and_repository_rules() {
    let root = tempfile::tempdir().unwrap();
    fs::write(root.path().join("team.toml"), r#"
schema-version = 1
name = "team"
version = "1.0.0"
requires-ryni = ">=0.2, <1"
[lint]
preview = true
select = ["skill-required-metadata", "markdown-required-sections", "project-required-files", "skill-duplicate-name"]
required-metadata = ["owner"]
required-sections = ["Usage"]
required-files = ["AGENTS.md"]
"#).unwrap();
    fs::write(
        root.path().join("ryni.toml"),
        "schema-version = 1\npacks = [{path = 'team.toml', version = '1.0.0'}]",
    )
    .unwrap();
    for directory in ["a", "b"] {
        fs::create_dir(root.path().join(directory)).unwrap();
        fs::write(
            root.path().join(directory).join("SKILL.md"),
            "---\nname: shared\nowner: Team\n---\n# **Usage**\n",
        )
        .unwrap();
    }
    let (code, result) = json(root.path(), &[]);
    assert_eq!(code, 1);
    let diagnostics = result["diagnostics"].as_array().unwrap();
    assert_eq!(diagnostics.len(), 3);
    assert_eq!(
        diagnostics
            .iter()
            .filter(|d| d["rule"] == "skill-duplicate-name")
            .count(),
        2
    );
    assert_eq!(
        diagnostics
            .iter()
            .filter(|d| d["rule"] == "project-required-files")
            .count(),
        1
    );
    let settings: Value = serde_json::from_slice(&run(root.path(), &["settings"]).stdout).unwrap();
    assert_eq!(settings["packs"][0]["version"], "1.0.0");
}

#[test]
fn parsing_prerequisite_is_reported_even_when_only_a_dependent_rule_is_selected() {
    let root = tempfile::tempdir().unwrap();
    fs::write(root.path().join("SKILL.md"), "invalid").unwrap();
    let result = json(root.path(), &["--select", "skill-name"]).1;
    assert_eq!(result["diagnostics"].as_array().unwrap().len(), 1);
    assert_eq!(result["diagnostics"][0]["rule"], "skill-frontmatter");
    assert_eq!(json(root.path(), &["--select", "markdown-local-link"]).0, 0);
}

#[test]
fn missing_project_requirements_fail_even_with_no_markdown() {
    let root = tempfile::tempdir().unwrap();
    fs::write(root.path().join("ryni.toml"), "schema-version = 1\n[lint]\npreview = true\nselect = ['project-required-files']\nrequired-files = ['AGENTS.md']").unwrap();
    assert_eq!(json(root.path(), &[]).0, 1);
    fs::create_dir(root.path().join("AGENTS.md")).unwrap();
    assert_eq!(json(root.path(), &[]).0, 1);
    let output = run(root.path(), &["check"]);
    assert!(!String::from_utf8_lossy(&output.stdout).contains("No supported files"));
}

#[test]
fn rule_help_is_backed_by_registry() {
    let root = tempfile::tempdir().unwrap();
    assert!(
        run(root.path(), &["rule", "markdown-local-link"])
            .status
            .success()
    );
    assert_eq!(run(root.path(), &["rule", "typo"]).status.code(), Some(2));
}
