use ryni::{
    registry::{Rule, Stability},
    settings::{LintOptions, Overrides, Settings},
};
use std::{fs, path::Path};

fn resolve(root: &Path) -> Result<Settings, ryni::error::ScanError> {
    Settings::resolve(root, None, false, Overrides::default())
}

#[test]
fn defaults_and_registry_are_complete() {
    let root = tempfile::tempdir().unwrap();
    let settings = resolve(root.path()).unwrap();
    assert_eq!(settings.enabled.len(), 6);
    let mut ids = std::collections::BTreeSet::new();
    for rule in Rule::ALL {
        assert!(ids.insert(rule.id()));
        assert_eq!(Rule::from_id(rule.id()), Some(*rule));
        assert!(!rule.metadata().explanation.is_empty());
        assert!(!settings.enabled(*rule) || rule.metadata().stability == Stability::Stable);
    }
}

#[test]
fn packs_repository_and_cli_have_explicit_precedence() {
    let root = tempfile::tempdir().unwrap();
    fs::create_dir(root.path().join("config")).unwrap();
    fs::write(
        root.path().join("config/team.toml"),
        r#"
schema-version = 1
name = "example/team"
version = "1.2.0"
requires-ryni = ">=0.2, <1"
[lint]
select = ["skill-name"]
required-metadata = ["owner"]
"#,
    )
    .unwrap();
    fs::write(
        root.path().join("config/ryni.toml"),
        r#"
schema-version = 1
packs = [{ path = "team.toml", version = "1.2.0" }]
[lint]
select = ["skill-description"]
[discovery]
exclude = ["vendor", "**/generated/**"]
"#,
    )
    .unwrap();
    let path = root.path().join("config/ryni.toml");
    let repository =
        Settings::resolve(root.path(), Some(&path), false, Overrides::default()).unwrap();
    assert!(repository.enabled(Rule::Description));
    assert!(!repository.enabled(Rule::Name));
    assert_eq!(repository.required_metadata, ["owner"]);
    assert!(repository.excluded(Path::new("vendor/docs/README.md")));
    let cli = Settings::resolve(
        root.path(),
        Some(&path),
        false,
        Overrides {
            lint: LintOptions {
                select: Some(vec!["markdown-local-link".into()]),
                ..Default::default()
            },
            ..Default::default()
        },
    )
    .unwrap();
    assert_eq!(
        cli.enabled.into_iter().collect::<Vec<_>>(),
        [Rule::MarkdownLocalLink]
    );
    assert_eq!(cli.packs[0].name, "example/team");
}

#[test]
fn rejects_typos_incompatible_packs_and_unpinned_versions() {
    let root = tempfile::tempdir().unwrap();
    for config in [
        "schema-version = 2",
        "schema-version = 1\n[lint]\nrequired-files = ['docs/./guide.md']",
        "schema-version = 1\n[discovery]\nexclude = ['']",
        "schema-version = 1\nunknown = true",
        "schema-version = 1\n[lint]\nselect = ['typo']",
        "schema-version = 1\n[lint]\nselect = ['skill-duplicate-name']",
        "schema-version = 1\n[lint]\nrequired-files = ['../outside']",
        "schema-version = 1\n[lint]\nrequired-sections = ['']",
        "schema-version = 1\n[discovery]\nexclude = ['[']",
    ] {
        fs::write(root.path().join("ryni.toml"), config).unwrap();
        assert!(resolve(root.path()).is_err(), "{config}");
    }
    for (pin, requirement) in [("2.0.0", ">=0.2"), ("^1", ">=0.2"), ("1.0.0", ">=999")] {
        fs::write(
            root.path().join("ryni.toml"),
            format!("schema-version = 1\npacks = [{{ path = 'team.toml', version = '{pin}' }}]"),
        )
        .unwrap();
        fs::write(root.path().join("team.toml"), format!("schema-version = 1\nname = 'team'\nversion = '1.0.0'\nrequires-ryni = '{requirement}'")).unwrap();
        assert!(resolve(root.path()).is_err());
    }
}

#[test]
fn preview_and_isolation_are_explicit() {
    let root = tempfile::tempdir().unwrap();
    fs::write(
        root.path().join("ryni.toml"),
        "schema-version = 1\n[lint]\npreview = true\nselect = ['all']\nignore = ['skill-name']",
    )
    .unwrap();
    let settings = resolve(root.path()).unwrap();
    assert!(settings.enabled(Rule::DuplicateSkillName));
    assert!(!settings.enabled(Rule::Name));
    fs::write(root.path().join("ryni.toml"), "invalid TOML").unwrap();
    assert!(resolve(root.path()).is_err());
    assert_eq!(
        Settings::resolve(root.path(), None, true, Overrides::default())
            .unwrap()
            .enabled
            .len(),
        6
    );
}
