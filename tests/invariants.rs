use proptest::prelude::*;
use ryni::{
    ProjectContext, SourceFile,
    document::Document,
    filesystem::{FileKind, FileSystem},
    settings::Settings,
};
use std::{fs, io, path::Path};

struct Missing;
impl FileSystem for Missing {
    fn kind(&self, _: &Path) -> io::Result<Option<FileKind>> {
        Ok(None)
    }
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(256))]
    #[test]
    fn arbitrary_sources_keep_ranges_valid_and_render_without_panics(text in "(?s).{0,2048}", skill in any::<bool>()) {
        let settings = Settings::default();
        let context = ProjectContext { root: Path::new("."), settings: &settings, filesystem: &Missing };
        let path = if skill { "demo/SKILL.md" } else { "README.md" };
        for source in [text.clone(), format!("---\n{text}\n---\n[Link](%FF)\n")] {
            let document = Document::parse(SourceFile::new(path, source));
            let first = ryni::analyze(&document, &context);
            let second = ryni::analyze(&document, &context);
            prop_assert_eq!(&first.diagnostics, &second.diagnostics);
            for diagnostic in first.diagnostics {
                if let Some(range) = &diagnostic.span {
                    prop_assert!(diagnostic.source.valid_range(range));
                    prop_assert!(diagnostic.location().is_some());
                }
                let rendered = ryni::output::render(&diagnostic, false);
                prop_assert!(!rendered.is_empty());
            }
        }
    }

    #[test]
    fn unicode_prefixes_use_scalar_columns(prefix in "[é界😀a]{0,100}") {
        let text = format!("{prefix} [Link](missing.md)\r\n");
        let document = Document::parse(SourceFile::new("README.md", text));
        let settings = Settings::default();
        let result = ryni::analyze(&document, &ProjectContext { root: Path::new("."), settings: &settings, filesystem: &Missing });
        prop_assert_eq!(result.diagnostics[0].location(), Some((1, prefix.chars().count() + 2)));
        prop_assert_eq!(result.diagnostics[0].span.as_ref().unwrap().start, prefix.len() + 1);
    }
}

#[test]
fn cache_and_threads_preserve_results_and_targets_are_rechecked_between_runs() {
    let root = tempfile::tempdir().unwrap();
    for name in ["a.md", "b.md", "c.md"] {
        fs::write(
            root.path().join(name),
            "[Target](target.txt) [Again](target.txt)\n",
        )
        .unwrap();
    }
    let settings = Settings::default();
    let scan = |threads, cache_targets| {
        ryni::check_with_options(
            root.path(),
            &settings,
            ryni::ExecutionOptions {
                threads,
                cache_targets,
            },
        )
        .unwrap()
    };
    for exists in [false, true, false] {
        let target = root.path().join("target.txt");
        if exists {
            fs::write(&target, "target").unwrap();
        } else if target.exists() {
            fs::remove_file(target).unwrap();
        }
        let expected = scan(1, false);
        assert_eq!(expected.diagnostics.len(), if exists { 0 } else { 6 });
        for (threads, cache) in [(1, true), (4, false), (4, true)] {
            assert_eq!(scan(threads, cache).json(), expected.json());
        }
        let cached = scan(1, true);
        assert_eq!(cached.timings.target_lookups, 1);
        assert_eq!(cached.timings.target_cache_hits, 5);
    }
}

#[test]
fn target_io_errors_do_not_discard_other_findings_in_the_same_document() {
    struct Partial;
    impl FileSystem for Partial {
        fn kind(&self, path: &Path) -> io::Result<Option<FileKind>> {
            if path.ends_with("denied") {
                Err(io::Error::new(io::ErrorKind::PermissionDenied, "denied"))
            } else {
                Ok(None)
            }
        }
    }
    let document = Document::parse(SourceFile::new("README.md", "[A](denied) [B](missing)"));
    let settings = Settings::default();
    let result = ryni::analyze(
        &document,
        &ProjectContext {
            root: Path::new("."),
            settings: &settings,
            filesystem: &Partial,
        },
    );
    assert_eq!(result.errors.len(), 1);
    assert_eq!(result.diagnostics.len(), 1);
}
