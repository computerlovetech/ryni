use std::{
    fs,
    path::Path,
    process::{Command, Output},
};

fn run(path: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_ryni"))
        .arg("check")
        .arg(path)
        .output()
        .unwrap()
}

fn write_file(root: &Path, name: &str, content: &str) {
    let path = root.join(name);
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, content).unwrap();
}

#[test]
fn invalid_link_paths_do_not_abort_remaining_links_or_files() {
    let project = tempfile::tempdir().unwrap();
    let root = project.path();
    write_file(
        root,
        "a.md",
        &format!("[Too long]({})\n[Missing](missing.txt)\n", "a".repeat(300)),
    );
    write_file(root, "z.md", "[Later](missing.txt)\n");
    let output = run(root);
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert_eq!(output.status.code(), Some(1), "{output:?}");
    assert!(output.stderr.is_empty());
    assert!(stdout.contains("z.md:1:1"), "{stdout}");
    assert!(stdout.ends_with("Found 3 errors.\n"), "{stdout}");
}

#[test]
fn nbsp_reference_destination_does_not_abort_scan() {
    let project = tempfile::tempdir().unwrap();
    let root = project.path();
    write_file(
        root,
        "a.md",
        "See [#1].\n\n[#1]:\u{a0}https://example.com/pull/1\n",
    );
    write_file(root, "z.md", "[Later](missing.txt)\n");
    let output = run(root);
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert_eq!(output.status.code(), Some(1), "{output:?}");
    assert!(output.stderr.is_empty());
    assert!(stdout.contains("z.md:1:1"), "{stdout}");
    assert!(stdout.ends_with("Found 2 errors.\n"), "{stdout}");
}

#[test]
fn invalid_paths_have_identical_findings_with_cache_and_parallel_checks() {
    let project = tempfile::tempdir().unwrap();
    let target = "a".repeat(300);
    for name in ["a.md", "b.md"] {
        write_file(
            project.path(),
            name,
            &format!("[A]({target}) [B]({target})"),
        );
    }
    let mut expected = None;
    for args in [vec!["--no-cache"], vec![], vec!["--threads", "4"]] {
        let output = Command::new(env!("CARGO_BIN_EXE_ryni"))
            .arg("check")
            .arg(project.path())
            .args(["--output-format", "json"])
            .args(args)
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(1), "{output:?}");
        let report: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(report["complete"], true);
        assert_eq!(report["diagnostics"].as_array().unwrap().len(), 4);
        if let Some(expected) = &expected {
            assert_eq!(&report, expected);
        } else {
            expected = Some(report);
        }
    }
}
