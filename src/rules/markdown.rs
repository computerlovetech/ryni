use crate::Diagnostic;
use percent_encoding::percent_decode_str;
use pulldown_cmark::{Event, LinkType, Options, Parser, Tag};
use std::{fs, io, path::Path};

/// Check explicit Markdown links and images against the local filesystem.
/// URL schemes, rooted URLs, and same-document links are outside this rule.
pub(crate) fn check(path: &Path, source: &str) -> Result<Vec<Diagnostic>, String> {
    let mut diagnostics = Vec::new();
    let line_starts: Vec<usize> = std::iter::once(0)
        .chain(source.match_indices('\n').map(|(index, _)| index + 1))
        .collect();
    let options = Options::ENABLE_TABLES
        | Options::ENABLE_FOOTNOTES
        | Options::ENABLE_STRIKETHROUGH
        | Options::ENABLE_YAML_STYLE_METADATA_BLOCKS
        | Options::ENABLE_PLUSES_DELIMITED_METADATA_BLOCKS;
    for (event, range) in Parser::new_ext(source, options).into_offset_iter() {
        let destination = match event {
            Event::Start(Tag::Link {
                link_type: LinkType::Email,
                ..
            }) => continue,
            Event::Start(Tag::Link { dest_url, .. } | Tag::Image { dest_url, .. }) => dest_url,
            _ => continue,
        };
        if destination.starts_with('/') || destination.starts_with('\\') || has_scheme(&destination)
        {
            continue;
        }
        // Strip URL components before decoding: %23 and %3F are filename characters.
        let raw_path = destination.split(['#', '?']).next().unwrap_or_default();
        if raw_path.is_empty() {
            continue;
        }
        let target = percent_decode_str(raw_path).decode_utf8();
        let message = match target {
            Err(_) => Some(format!("Target {raw_path:?} is not a valid UTF-8 path")),
            Ok(target) => {
                // Encoded rooted paths are not relative filesystem links either.
                if target.starts_with('/')
                    || target.starts_with('\\')
                    || Path::new(target.as_ref()).is_absolute()
                {
                    continue;
                }
                if target.contains('\0') {
                    Some(format!("Target {raw_path:?} contains a null character"))
                } else {
                    let resolved = path
                        .parent()
                        .unwrap_or(Path::new("."))
                        .join(target.as_ref());
                    match fs::metadata(&resolved) {
                        Ok(_) => None,
                        Err(error)
                            if matches!(
                                error.kind(),
                                io::ErrorKind::NotFound | io::ErrorKind::NotADirectory
                            ) =>
                        {
                            Some(format!("Target {raw_path:?} does not exist"))
                        }
                        Err(error) => {
                            return Err(format!(
                                "cannot inspect link target {} from {}: {error}",
                                resolved.display(),
                                path.display()
                            ));
                        }
                    }
                }
            }
        };
        if let Some(message) = message {
            let line = line_starts.partition_point(|start| *start <= range.start);
            let column = source[line_starts[line - 1]..range.start].chars().count() + 1;
            diagnostics.push(Diagnostic {
                path: path.to_path_buf(),
                location: Some((line, column)),
                source: Default::default(),
                span: Some(range),
                rule: "markdown-local-link".into(),
                message,
            });
        }
    }
    Ok(diagnostics)
}

fn has_scheme(destination: &str) -> bool {
    let Some((scheme, _)) = destination.split_once(':') else {
        return false;
    };
    scheme.starts_with(|c: char| c.is_ascii_alphabetic())
        && scheme
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'+' | b'-' | b'.'))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn project() -> TempDir {
        let root = tempfile::tempdir().unwrap();
        fs::create_dir(root.path().join("docs")).unwrap();
        fs::write(root.path().join("docs/guide.md"), "# Guide\n").unwrap();
        root
    }

    #[test]
    fn resolves_relative_paths_directories_anchors_and_queries() {
        let root = project();
        fs::write(root.path().join("README.md"), "").unwrap();
        let source = "[Guide](guide.md#missing-heading) [Parent](../README.md) [Dir](.) [Query](guide.md?raw=1#section)";
        assert!(
            check(&root.path().join("docs/index.md"), source)
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn reports_links_and_images_with_unicode_line_and_column() {
        let root = project();
        let source = "# Title\r\n\r\né [Missing](missing.md)\r\n![Image](image.png)";
        let diagnostics = check(&root.path().join("docs/index.md"), source).unwrap();
        assert_eq!(diagnostics.len(), 2);
        assert_eq!(diagnostics[0].location, Some((3, 3)));
        assert_eq!(diagnostics[1].location, Some((4, 1)));
        assert_eq!(
            diagnostics[0].message,
            "Target \"missing.md\" does not exist"
        );
    }

    #[test]
    fn supports_full_collapsed_shortcut_and_image_references() {
        let root = project();
        let source =
            "[Guide][ref]\n\n[ref][]\n\n[ref]\n\n![Image][ref]\n\n[ref]: missing.md \"Title\"\n";
        let diagnostics = check(&root.path().join("docs/index.md"), source).unwrap();
        assert_eq!(diagnostics.len(), 4);
        assert_eq!(diagnostics[0].location, Some((1, 1)));
    }

    #[test]
    fn decodes_paths_after_removing_url_components() {
        let root = project();
        for name in [
            "my guide.md",
            "café.md",
            "hash#file.md",
            "100%.md",
            "a+b.md",
            "a&b.md",
        ] {
            fs::write(root.path().join("docs").join(name), "").unwrap();
        }
        let query_link = if cfg!(windows) {
            ""
        } else {
            fs::write(root.path().join("docs/query?file.md"), "").unwrap();
            "[D](query%3Ffile.md?raw=1)"
        };
        let source = "[A](my%20guide.md#section) [B](caf%C3%A9.md) [C](hash%23file.md) {query_link} [E](100%25.md) [F](a+b.md) [G](a&amp;b.md) [H](<my guide.md>)";
        let source = source.replace("{query_link}", query_link);
        assert!(
            check(&root.path().join("docs/index.md"), &source)
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn skips_nonlocal_urls_and_same_document_links() {
        let root = project();
        let source = "[A](https://example.com/missing) [B](mailto:test@example.com) [C](custom+app://anything) [D](/docs/route) [E](//example.com/file) [F](#missing) [G](?query) [H]() [I](data:text/plain,hello) <https://example.com> <test@example.com>";
        assert!(
            check(&root.path().join("docs/index.md"), source)
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn skips_code_html_comments_frontmatter_and_plain_prose() {
        let root = project();
        let source = "---\nexample: '[Link](missing.md)'\n---\n\n`[Link](missing.md)`\n\n```md\n[Link](missing.md)\n```\n\n    [Link](missing.md)\n\n<!-- [Link](missing.md) -->\n\n<a href=\"missing.md\">Link</a>\n\nmissing.md\n\n[undefined-reference]\n";
        assert!(
            check(&root.path().join("docs/index.md"), source)
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn checks_markdown_in_tables_and_footnotes() {
        let root = project();
        let source =
            "| Guide |\n| --- |\n| [Link](missing.md) |\n\nText[^1]\n\n[^1]: [Link](missing.md)\n";
        assert_eq!(
            check(&root.path().join("docs/index.md"), source)
                .unwrap()
                .len(),
            2
        );
    }

    #[test]
    fn does_not_guess_extensions_and_reports_invalid_targets() {
        let root = project();
        let source = "[Route](guide) [Invalid](%FF) [Null](%00) [NotDir](guide.md/child)";
        let diagnostics = check(&root.path().join("docs/index.md"), source).unwrap();
        assert_eq!(diagnostics.len(), 4);
    }

    #[cfg(unix)]
    #[test]
    fn linked_symlinks_resolve_and_broken_symlinks_fail() {
        use std::os::unix::fs::symlink;
        let root = project();
        symlink("guide.md", root.path().join("docs/link.md")).unwrap();
        symlink("missing.md", root.path().join("docs/broken.md")).unwrap();
        let diagnostics = check(
            &root.path().join("docs/index.md"),
            "[Good](link.md) [Bad](broken.md)",
        )
        .unwrap();
        assert_eq!(diagnostics.len(), 1);
        assert!(diagnostics[0].message.contains("broken.md"));
    }
}
