use annotate_snippets::{AnnotationKind, Level, Renderer, Snippet};
use ryni::Diagnostic;

pub fn render(diagnostic: &Diagnostic, color: bool) -> String {
    let renderer = if color {
        Renderer::styled()
    } else {
        Renderer::plain()
    };
    let path = diagnostic.path.to_string_lossy().replace('\\', "/");
    let title = Level::ERROR
        .with_name(diagnostic.rule.as_str())
        .primary_title(&diagnostic.message);
    let snippet = if let Some(span) = &diagnostic.span {
        Snippet::source(diagnostic.source.as_ref())
            .path(&path)
            .fold(true)
            .annotation(AnnotationKind::Primary.span(span.clone()))
    } else {
        // Metadata rules report against the whole document, not a guessed field
        // position. Show a bounded preview without an inaccurate underline.
        let end = diagnostic
            .source
            .match_indices('\n')
            .nth(7)
            .map_or(diagnostic.source.len(), |(offset, _)| offset);
        Snippet::source(&diagnostic.source[..end])
            .path(&path)
            .fold(false)
    };
    renderer.render(&[title.element(snippet)]).to_string()
}
