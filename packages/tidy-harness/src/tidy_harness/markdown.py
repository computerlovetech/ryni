"""CommonMark links and GitHub-style heading fragments."""

import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

PARSER = MarkdownIt("commonmark")


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.ids.update(
            value
            for key, value in attrs
            if value and (key == "id" or (tag == "a" and key == "name"))
        )


def parse(text: str, *, include_images: bool = True) -> tuple[list[tuple[str, int]], set[str]]:
    tokens = PARSER.parse(text)
    links, anchors = [], set()
    used = set()
    html = Anchors()
    for i, token in enumerate(tokens):
        if token.type == "html_block":
            html.feed(token.content)
        if token.type != "inline":
            continue
        children = token.children or []
        for child in children:
            if child.type == "link_open" or (include_images and child.type == "image"):
                links.append(
                    (
                        child.attrGet("href" if child.type == "link_open" else "src"),
                        token.map[0] + 1,
                    )
                )
            if child.type == "html_inline":
                html.feed(child.content)
        if i and tokens[i - 1].type == "heading_open":
            title = "".join(c.content for c in children if c.type in ("text", "code_inline"))
            explicit = re.search(r"\s*\{#([^\s}]+)\}\s*$", title)
            if explicit:
                anchors.add(explicit[1])
                title = title[: explicit.start()]
            slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
            candidate, number = slug, 0
            while candidate in used:
                number += 1
                candidate = f"{slug}-{number}"
            used.add(candidate)
            anchors.add(candidate)
    return links, anchors | html.ids


def local(href: str):
    url = urlsplit(href)
    if url.scheme or url.netloc or url.path.startswith("/"):
        return None
    return unquote(url.path), unquote(url.fragment)
