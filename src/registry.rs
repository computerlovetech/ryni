/// Stable identities shared by execution, configuration, documentation and output.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Rule {
    Frontmatter,
    Name,
    DirectoryName,
    Description,
    OptionalFields,
    MarkdownLocalLink,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Scope {
    Skill,
    Markdown,
    Project,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stability {
    Stable,
    Preview,
}

pub struct RuleMetadata {
    pub id: &'static str,
    pub scope: Scope,
    pub stability: Stability,
    pub default_enabled: bool,
    pub explanation: &'static str,
}

impl Rule {
    pub const ALL: &[Self] = &[
        Self::Frontmatter,
        Self::Name,
        Self::DirectoryName,
        Self::Description,
        Self::OptionalFields,
        Self::MarkdownLocalLink,
    ];

    pub fn metadata(self) -> RuleMetadata {
        let (id, explanation) = match self {
            Self::Frontmatter => (
                "skill-frontmatter",
                "SKILL.md must start with delimited YAML containing a mapping with unique string keys.",
            ),
            Self::Name => (
                "skill-name",
                "The name must contain 1–64 lowercase Unicode letters, numbers or hyphens, without leading, trailing or consecutive hyphens.",
            ),
            Self::DirectoryName => (
                "skill-directory-name",
                "The skill name must exactly match its containing directory.",
            ),
            Self::Description => (
                "skill-description",
                "The description must be a nonblank string of at most 1,024 Unicode characters.",
            ),
            Self::OptionalFields => (
                "skill-optional-fields",
                "Validate license, allowed-tools, compatibility and metadata against the Agent Skills field requirements.",
            ),
            Self::MarkdownLocalLink => (
                "markdown-local-link",
                "Relative Markdown links and images must point to existing files or directories. URL schemes and document anchors are skipped.",
            ),
        };
        RuleMetadata {
            id,
            explanation,
            scope: if self == Self::MarkdownLocalLink {
                Scope::Markdown
            } else {
                Scope::Skill
            },
            stability: Stability::Stable,
            default_enabled: true,
        }
    }

    pub fn id(self) -> &'static str {
        self.metadata().id
    }
    pub fn from_id(id: &str) -> Option<Self> {
        Self::ALL.iter().copied().find(|rule| rule.id() == id)
    }
}

impl std::fmt::Display for Rule {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.id())
    }
}

impl PartialEq<&str> for Rule {
    fn eq(&self, other: &&str) -> bool {
        self.id() == *other
    }
}
