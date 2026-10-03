use ryni::{
    CheckReport, Diagnostic, SourceFile,
    fix::{self, Applicability, Edit, Fix},
    registry::Rule,
};
use std::{fs, process::Command, sync::Arc};

#[test]
fn directory_name_fix_requires_opt_in_preserves_body_and_is_idempotent() {
    let root = tempfile::tempdir().unwrap();
    let directory = root.path().join("demo");
    fs::create_dir(&directory).unwrap();
    let path = directory.join("SKILL.md");
    let original =
        "\u{feff}---\r\nname: other # comment\r\ndescription: 'Description'\r\n---\r\n# Body\r\n";
    fs::write(&path, original).unwrap();
    let run = |args: &[&str]| {
        Command::new(env!("CARGO_BIN_EXE_ryni"))
            .arg("check")
            .arg(&directory)
            .args(args)
            .output()
            .unwrap()
    };
    assert_eq!(run(&["--fix"]).status.code(), Some(1));
    assert_eq!(fs::read_to_string(&path).unwrap(), original);
    assert!(run(&["--fix", "--unsafe-fixes"]).status.success());
    let fixed = fs::read_to_string(&path).unwrap();
    assert!(fixed.starts_with("\u{feff}---\r\n"));
    assert!(fixed.contains("name: demo\r\n"));
    assert!(fixed.ends_with("---\r\n# Body\r\n"));
    assert!(run(&["--fix", "--unsafe-fixes"]).status.success());
    assert_eq!(fs::read_to_string(&path).unwrap(), fixed);
}

fn report(original: &str, applicability: Applicability) -> CheckReport {
    CheckReport {
        diagnostics: vec![Diagnostic {
            rule: Rule::MarkdownLocalLink,
            message: "fixture".into(),
            span: None,
            source: Arc::new(SourceFile::new("README.md", original)),
            fix: Some(Fix {
                title: "replace".into(),
                applicability,
                edits: vec![Edit {
                    range: 0..original.len(),
                    replacement: "changed".into(),
                }],
            }),
        }],
        ..Default::default()
    }
}

#[test]
fn edits_reject_stale_sources_and_never_apply_display_only_fixes() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("README.md");
    fs::write(&path, "original").unwrap();
    let display = report("original", Applicability::DisplayOnly);
    assert_eq!(fix::apply(root.path(), &display, true).files_changed, 0);
    let safe = report("original", Applicability::Safe);
    fs::write(&path, "user edit").unwrap();
    assert_eq!(fix::apply(root.path(), &safe, false).errors.len(), 1);
    assert_eq!(fs::read_to_string(&path).unwrap(), "user edit");
    fs::write(&path, "original").unwrap();
    assert_eq!(fix::apply(root.path(), &safe, false).files_changed, 1);
    assert_eq!(fs::read_to_string(&path).unwrap(), "changed");
}

#[test]
fn overlapping_fixes_and_incomplete_scans_leave_files_untouched() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("README.md");
    fs::write(&path, "original").unwrap();
    let mut report = report("original", Applicability::Safe);
    report.diagnostics[0]
        .fix
        .as_mut()
        .unwrap()
        .edits
        .push(Edit {
            range: 0..1,
            replacement: "x".into(),
        });
    assert_eq!(fix::apply(root.path(), &report, false).errors.len(), 1);
    report.errors.push(ryni::error::ScanError::new(
        ryni::error::Operation::Read,
        &path,
        "unreadable",
    ));
    assert_eq!(fix::apply(root.path(), &report, true).files_changed, 0);
    assert_eq!(fs::read_to_string(&path).unwrap(), "original");
}
