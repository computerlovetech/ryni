use crate::{
    error::{Operation, ScanError},
    registry::{Rule, Stability},
};
use ignore::overrides::{Override, OverrideBuilder};
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeSet,
    fs,
    path::{Component, Path, PathBuf},
};

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields, rename_all = "kebab-case")]
pub struct LintOptions {
    pub select: Option<Vec<String>>,
    pub ignore: Option<Vec<String>>,
    pub preview: Option<bool>,
    pub required_metadata: Option<Vec<String>>,
    pub required_sections: Option<Vec<String>>,
    pub required_files: Option<Vec<String>>,
}

impl LintOptions {
    fn overlay(&mut self, other: Self) {
        if other.select.is_some() {
            self.select = other.select;
        }
        if other.ignore.is_some() {
            self.ignore = other.ignore;
        }
        if other.preview.is_some() {
            self.preview = other.preview;
        }
        if other.required_metadata.is_some() {
            self.required_metadata = other.required_metadata;
        }
        if other.required_sections.is_some() {
            self.required_sections = other.required_sections;
        }
        if other.required_files.is_some() {
            self.required_files = other.required_files;
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(default, deny_unknown_fields, rename_all = "kebab-case")]
pub struct DiscoveryOptions {
    pub exclude: Vec<String>,
    pub respect_ignore: bool,
}

impl Default for DiscoveryOptions {
    fn default() -> Self {
        Self {
            exclude: Vec::new(),
            respect_ignore: true,
        }
    }
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "kebab-case")]
struct Configuration {
    schema_version: u32,
    #[serde(default)]
    packs: Vec<PackReference>,
    #[serde(default)]
    lint: LintOptions,
    #[serde(default)]
    discovery: DiscoveryOptions,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PackReference {
    path: PathBuf,
    version: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "kebab-case")]
struct Pack {
    schema_version: u32,
    name: String,
    version: String,
    requires_ryni: String,
    #[serde(default)]
    lint: LintOptions,
}

#[derive(Debug, Clone, Serialize)]
pub struct ResolvedPack {
    pub name: String,
    pub version: String,
    #[serde(serialize_with = "crate::error::serialize_path")]
    pub path: PathBuf,
}

/// CLI overrides are applied after packs and repository options.
#[derive(Debug, Default)]
pub struct Overrides {
    pub lint: LintOptions,
    pub exclude: Option<Vec<String>>,
    pub respect_ignore: Option<bool>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Settings {
    pub enabled: BTreeSet<Rule>,
    pub preview: bool,
    pub required_metadata: Vec<String>,
    pub required_sections: Vec<String>,
    pub required_files: Vec<String>,
    pub discovery: DiscoveryOptions,
    pub packs: Vec<ResolvedPack>,
    #[serde(skip)]
    exclusions: Override,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            enabled: Rule::ALL
                .iter()
                .copied()
                .filter(|r| r.metadata().default_enabled)
                .collect(),
            preview: false,
            required_metadata: vec![],
            required_sections: vec![],
            required_files: vec![],
            discovery: DiscoveryOptions::default(),
            packs: vec![],
            exclusions: Override::empty(),
        }
    }
}

impl Settings {
    pub fn enabled(&self, rule: Rule) -> bool {
        self.enabled.contains(&rule)
    }

    /// Exclusions apply to explicit inputs too. Patterns match root-relative paths or ancestors.
    pub fn excluded(&self, relative: &Path) -> bool {
        self.excluded_path(relative, false)
    }

    pub(crate) fn excluded_path(&self, relative: &Path, is_dir: bool) -> bool {
        relative.ancestors().enumerate().any(|(index, path)| {
            self.exclusions
                .matched(path, is_dir || index > 0)
                .is_ignore()
        })
    }

    /// No parent-directory search: only the chosen project's ryni.toml is implicit.
    pub fn resolve(
        root: &Path,
        config: Option<&Path>,
        isolated: bool,
        overrides: Overrides,
    ) -> Result<Self, ScanError> {
        if isolated && config.is_some() {
            return Err(ScanError::new(
                Operation::Configure,
                root,
                "explicit configuration cannot be combined with isolation",
            ));
        }
        let config_path = config
            .map(Path::to_path_buf)
            .unwrap_or_else(|| root.join("ryni.toml"));
        let fail = |message: String| ScanError::new(Operation::Configure, &config_path, message);
        let mut lint = LintOptions::default();
        let mut discovery = DiscoveryOptions::default();
        let mut packs = Vec::new();
        if !isolated {
            let content = match fs::read_to_string(&config_path) {
                Ok(content) => Some(content),
                Err(error) if config.is_none() && error.kind() == std::io::ErrorKind::NotFound => {
                    None
                }
                Err(error) => return Err(fail(error.to_string())),
            };
            if let Some(content) = content {
                let configuration: Configuration =
                    toml::from_str(&content).map_err(|e| fail(e.to_string()))?;
                schema(configuration.schema_version).map_err(&fail)?;
                let mut names = BTreeSet::new();
                for reference in configuration.packs {
                    let path = config_path.parent().unwrap_or(root).join(reference.path);
                    let pack_fail =
                        |message: String| ScanError::new(Operation::Configure, &path, message);
                    let content =
                        fs::read_to_string(&path).map_err(|e| pack_fail(e.to_string()))?;
                    let pack: Pack =
                        toml::from_str(&content).map_err(|e| pack_fail(e.to_string()))?;
                    schema(pack.schema_version).map_err(&pack_fail)?;
                    let pinned = semver::Version::parse(&reference.version)
                        .map_err(|e| pack_fail(e.to_string()))?;
                    let version = semver::Version::parse(&pack.version)
                        .map_err(|e| pack_fail(e.to_string()))?;
                    if pinned != version {
                        return Err(pack_fail(format!(
                            "expected pack version {pinned}, found {version}"
                        )));
                    }
                    let required = semver::VersionReq::parse(&pack.requires_ryni)
                        .map_err(|e| pack_fail(e.to_string()))?;
                    let current = semver::Version::parse(env!("CARGO_PKG_VERSION"))
                        .map_err(|e| pack_fail(e.to_string()))?;
                    if !required.matches(&current) {
                        return Err(pack_fail(format!(
                            "pack requires ryni {required}, running {current}"
                        )));
                    }
                    if pack.name.trim().is_empty() || !names.insert(pack.name.clone()) {
                        return Err(pack_fail("pack names must be nonblank and unique".into()));
                    }
                    validate_options(&pack.lint).map_err(&pack_fail)?;
                    packs.push(ResolvedPack {
                        name: pack.name,
                        version: pack.version,
                        path,
                    });
                    lint.overlay(pack.lint);
                }
                validate_options(&configuration.lint).map_err(&fail)?;
                lint.overlay(configuration.lint);
                discovery = configuration.discovery;
            }
        }
        validate_options(&overrides.lint).map_err(&fail)?;
        lint.overlay(overrides.lint);
        if let Some(exclude) = overrides.exclude {
            discovery.exclude = exclude;
        }
        if let Some(respect) = overrides.respect_ignore {
            discovery.respect_ignore = respect;
        }
        let preview = lint.preview.unwrap_or(false);
        let mut enabled = match lint.select {
            Some(select) => resolve_rules(&select, preview, true).map_err(&fail)?,
            None => Self::default().enabled,
        };
        for rule in
            resolve_rules(&lint.ignore.unwrap_or_default(), preview, false).map_err(&fail)?
        {
            enabled.remove(&rule);
        }
        let mut builder = OverrideBuilder::new(root);
        for pattern in &discovery.exclude {
            if pattern.trim().is_empty() {
                return Err(fail("exclusion patterns must not be blank".into()));
            }
            builder
                .add(&format!("!{pattern}"))
                .map_err(|e| fail(format!("invalid exclusion {pattern:?}: {e}")))?;
        }
        Ok(Self {
            enabled,
            preview,
            packs,
            discovery,
            required_metadata: lint.required_metadata.unwrap_or_default(),
            required_sections: lint.required_sections.unwrap_or_default(),
            required_files: lint.required_files.unwrap_or_default(),
            exclusions: builder.build().map_err(|e| fail(e.to_string()))?,
        })
    }
}

fn schema(version: u32) -> Result<(), String> {
    if version == 1 {
        Ok(())
    } else {
        Err(format!("unsupported schema-version {version}; expected 1"))
    }
}

fn validate_options(lint: &LintOptions) -> Result<(), String> {
    for list in [&lint.select, &lint.ignore].into_iter().flatten() {
        resolve_rules(list, true, false)?;
    }
    for list in [
        &lint.required_metadata,
        &lint.required_sections,
        &lint.required_files,
    ]
    .into_iter()
    .flatten()
    {
        if list.iter().any(|item| item.trim().is_empty()) {
            return Err("requirements must not be blank".into());
        }
        if list.iter().collect::<BTreeSet<_>>().len() != list.len() {
            return Err("requirements must be unique".into());
        }
    }
    for path in lint.required_files.iter().flatten() {
        if path.split('/').any(|part| matches!(part, "" | "." | ".."))
            || path.contains('\\')
            || path.contains(':')
            || path.contains('\0')
            || Path::new(path)
                .components()
                .any(|c| !matches!(c, Component::Normal(_)))
        {
            return Err(format!(
                "required file {path:?} must be a portable project-relative path without '.' or '..'"
            ));
        }
    }
    Ok(())
}

fn resolve_rules(ids: &[String], preview: bool, selecting: bool) -> Result<BTreeSet<Rule>, String> {
    let mut rules = BTreeSet::new();
    for id in ids {
        if id == "all" {
            rules.extend(
                Rule::ALL.iter().copied().filter(|r| {
                    !selecting || preview || r.metadata().stability == Stability::Stable
                }),
            );
        } else {
            let rule = Rule::from_id(id).ok_or_else(|| format!("unknown rule {id:?}"))?;
            if selecting && !preview && rule.metadata().stability == Stability::Preview {
                return Err(format!("rule {id:?} requires preview = true or --preview"));
            }
            rules.insert(rule);
        }
    }
    Ok(rules)
}
