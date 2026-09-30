use std::{
    fs,
    path::Path,
    process::{Command, Output},
};
use tempfile::TempDir;

const VALID: &str =
    "---\nname: demo-skill\ndescription: Checks demo inputs. Use for demonstration.\n---\n# Demo\n";

fn project() -> TempDir {
    let project = tempfile::tempdir().unwrap();
    fs::create_dir_all(project.path().join("skills/demo-skill")).unwrap();
    fs::write(project.path().join("skills/demo-skill/SKILL.md"), VALID).unwrap();
    project
}
fn run(path: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_ryni"))
        .arg("check")
        .arg(path)
        .output()
        .unwrap()
}

#[test]
fn valid_skill_passes_without_configuration() {
    let project = project();
    let output = Command::new(env!("CARGO_BIN_EXE_ryni"))
        .arg("check")
        .current_dir(project.path())
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "All checks passed!\n"
    );
}

#[test]
fn all_semantic_checks_run_and_legacy_config_is_ignored() {
    let project = project();
    fs::write(project.path().join("ryni.toml"), "This is not valid TOML").unwrap();
    fs::write(
        project.path().join("skills/demo-skill/SKILL.md"),
        "---\nname: Different\ndescription: ''\nlicense: 123\n---\n",
    )
    .unwrap();
    let output = run(project.path());
    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8(output.stdout).unwrap();
    for rule in [
        "skill-name",
        "skill-directory-name",
        "skill-description",
        "skill-optional-fields",
    ] {
        assert!(
            stdout.contains(&format!("skills/demo-skill/SKILL.md: {rule} ")),
            "{stdout}"
        );
    }
    assert!(stdout.ends_with("Found 4 violation(s).\n"));
}

#[test]
fn malformed_frontmatter_reports_one_finding() {
    let project = project();
    fs::write(project.path().join("skills/demo-skill/SKILL.md"), "bad").unwrap();
    let output = run(project.path());
    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("skill-frontmatter"));
    assert!(stdout.ends_with("Found 1 violation(s).\n"));
}

#[test]
fn discovers_hidden_and_nested_directories_in_stable_order() {
    let project = project();
    for directory in ["z/nested", ".agents/skills/example"] {
        let path = project.path().join(directory);
        fs::create_dir_all(&path).unwrap();
        fs::write(path.join("SKILL.md"), "bad").unwrap();
    }
    fs::write(project.path().join("README.md"), "not a skill").unwrap();
    let output = run(project.path());
    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(
        stdout.find(".agents/skills/example/SKILL.md").unwrap()
            < stdout.find("z/nested/SKILL.md").unwrap()
    );
    assert!(stdout.ends_with("Found 2 violation(s).\n"));
}

#[test]
fn a_single_skill_directory_can_be_checked() {
    let project = project();
    assert_eq!(
        run(&project.path().join("skills/demo-skill")).status.code(),
        Some(0)
    );
}

#[test]
fn empty_scan_is_explicit_and_successful() {
    let project = tempfile::tempdir().unwrap();
    fs::write(project.path().join("README.txt"), "# Project").unwrap();
    let output = run(project.path());
    assert_eq!(output.status.code(), Some(0));
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "No supported files found.\n"
    );
}

#[test]
fn missing_directory_file_argument_and_unreadable_skill_are_errors() {
    let project = project();
    for path in [
        project.path().join("missing"),
        project.path().join("skills/demo-skill/SKILL.md"),
    ] {
        let output = run(&path);
        assert_eq!(output.status.code(), Some(2));
        assert!(output.stdout.is_empty());
    }
    fs::write(project.path().join("skills/demo-skill/SKILL.md"), [0xff]).unwrap();
    assert_eq!(run(project.path()).status.code(), Some(2));
}

#[cfg(unix)]
#[test]
fn nested_symlinks_are_not_followed() {
    let project = project();
    std::os::unix::fs::symlink(
        project.path().join("skills"),
        project.path().join("skills/loop"),
    )
    .unwrap();
    assert_eq!(run(project.path()).status.code(), Some(0));
}

#[test]
fn help_and_version_are_available() {
    for argument in ["--help", "--version"] {
        assert!(
            Command::new(env!("CARGO_BIN_EXE_ryni"))
                .arg(argument)
                .output()
                .unwrap()
                .status
                .success()
        );
    }
}

#[test]
fn ordinary_markdown_files_are_checked_without_skill_metadata_rules() {
    let project = tempfile::tempdir().unwrap();
    for name in ["README.md", "GUIDE.MD", "notes.markdown"] {
        fs::write(project.path().join(name), "[Missing](missing.txt)\n").unwrap();
    }
    let output = run(project.path());
    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(!stdout.contains("skill-frontmatter"));
    assert!(
        stdout.contains("README.md:1:1: markdown-local-link Target \"missing.txt\" does not exist")
    );
    assert!(stdout.ends_with("Found 3 violation(s).\n"));
    fs::write(project.path().join("missing.txt"), "target").unwrap();
    assert_eq!(run(project.path()).status.code(), Some(0));
}

#[test]
fn skill_files_also_receive_the_markdown_link_check() {
    let project = project();
    fs::write(
        project.path().join("skills/demo-skill/SKILL.md"),
        format!("{VALID}\n[Link](missing.md)\n"),
    )
    .unwrap();
    let output = run(project.path());
    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("markdown-local-link"));
    assert!(stdout.ends_with("Found 1 violation(s).\n"));
}
