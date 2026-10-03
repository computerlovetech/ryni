use crate::source::SourceFile;
use pulldown_cmark::{Event, LinkType, Options, Parser, Tag, TagEnd};
use serde_yaml_ng::{Mapping, Value};
use std::{ops::Range, sync::Arc};

#[derive(Debug)]
pub struct Link {
    pub destination: String,
    pub span: Range<usize>,
}

#[derive(Debug)]
pub struct ParseIssue {
    pub message: String,
    pub span: Option<Range<usize>>,
}

#[derive(Debug)]
pub struct Frontmatter {
    pub fields: Mapping,
    pub span: Range<usize>,
}

/// Shared facts extracted once from the original, unmodified source snapshot.
#[derive(Debug)]
pub struct Document {
    pub source: Arc<SourceFile>,
    pub metadata: Option<Result<Frontmatter, ParseIssue>>,
    pub links: Vec<Link>,
    pub headings: Vec<String>,
}

impl Document {
    pub fn parse(source: SourceFile) -> Self {
        let metadata = source
            .path()
            .file_name()
            .filter(|name| *name == "SKILL.md")
            .map(|_| frontmatter(source.text()));
        let options = Options::ENABLE_TABLES
            | Options::ENABLE_FOOTNOTES
            | Options::ENABLE_STRIKETHROUGH
            | Options::ENABLE_YAML_STYLE_METADATA_BLOCKS
            | Options::ENABLE_PLUSES_DELIMITED_METADATA_BLOCKS;
        let mut links = Vec::new();
        let mut headings = Vec::new();
        let mut heading = None::<String>;
        for (event, span) in Parser::new_ext(source.text(), options).into_offset_iter() {
            match event {
                Event::Start(Tag::Link {
                    link_type: LinkType::Email,
                    ..
                }) => {}
                Event::Start(Tag::Link { dest_url, .. } | Tag::Image { dest_url, .. }) => {
                    links.push(Link {
                        destination: dest_url.into_string(),
                        span,
                    });
                }
                Event::Start(Tag::Heading { .. }) => heading = Some(String::new()),
                Event::Text(text) | Event::Code(text) => {
                    if let Some(heading) = &mut heading {
                        heading.push_str(&text);
                    }
                }
                Event::SoftBreak | Event::HardBreak => {
                    if let Some(heading) = &mut heading {
                        heading.push(' ');
                    }
                }
                Event::End(TagEnd::Heading(_)) => {
                    if let Some(heading) = heading.take() {
                        headings.push(heading);
                    }
                }
                _ => {}
            }
        }
        Self {
            source: Arc::new(source),
            metadata,
            links,
            headings,
        }
    }
}

fn frontmatter(source: &str) -> Result<Frontmatter, ParseIssue> {
    let missing = |message: &str| ParseIssue {
        message: message.into(),
        span: None,
    };
    let bom = usize::from(source.starts_with('\u{feff}')) * '\u{feff}'.len_utf8();
    let mut lines = source[bom..].split_inclusive('\n');
    let first = lines.next().unwrap_or_default();
    if first.trim_end_matches(['\r', '\n']) != "---" {
        return Err(missing(
            "SKILL.md must start with YAML frontmatter delimited by '---'",
        ));
    }
    let start = bom + first.len();
    let mut end = start;
    let mut closed = false;
    for line in lines {
        if line.trim_end_matches(['\r', '\n']) == "---" {
            closed = true;
            break;
        }
        end += line.len();
    }
    if !closed {
        return Err(missing(
            "YAML frontmatter is missing its closing '---' delimiter",
        ));
    }
    let value: Value = serde_yaml_ng::from_str(&source[start..end]).map_err(|error| {
        // serde_yaml's index is measured in bytes within the original YAML slice.
        let span = error.location().and_then(|location| {
            let offset = start + location.index();
            (offset <= end && source.is_char_boundary(offset)).then_some(offset..offset)
        });
        ParseIssue {
            message: format!("Invalid YAML frontmatter: {error}"),
            span,
        }
    })?;
    match value {
        Value::Mapping(fields) if fields.keys().all(Value::is_string) => Ok(Frontmatter {
            fields,
            span: start..end,
        }),
        _ => Err(missing(
            "YAML frontmatter must be a mapping with string keys",
        )),
    }
}
