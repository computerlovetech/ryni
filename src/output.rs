use annotate_snippets::{AnnotationKind, Level, Renderer, Snippet};
use ryni::Diagnostic;

pub fn render(diagnostic: &Diagnostic, color: bool) -> String {
    let renderer = if color {
        Renderer::styled()
    } else {
        Renderer::plain()
    };
    let path = diagnostic
        .source
        .path()
        .to_string_lossy()
        .replace('\\', "/");
    let title = Level::ERROR
        .with_name(diagnostic.rule.id())
        .primary_title(&diagnostic.message);
    let snippet = if let Some(span) = &diagnostic.span {
        Snippet::source(diagnostic.source.text())
            .path(&path)
            .fold(true)
            .annotation(AnnotationKind::Primary.span(span.clone()))
    } else {
        // Metadata rules report against the whole document, not a guessed field
        // position. Show a bounded preview without an inaccurate underline.
        let end = diagnostic
            .source
            .text()
            .match_indices('\n')
            .nth(7)
            .map_or(diagnostic.source.text().len(), |(offset, _)| offset);
        Snippet::source(&diagnostic.source.text()[..end])
            .path(&path)
            .fold(false)
    };
    let mut rendered = renderer.render(&[title.element(snippet)]).to_string();
    if let Some(fix) = &diagnostic.fix {
        rendered.push_str(&format!("\n help: {} [{:?}]", fix.title, fix.applicability));
    }
    rendered
}
