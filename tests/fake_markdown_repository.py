from ryni.markdown_repository import MarkdownSnapshot
from ryni.skill_repository import RepositoryRoot


class InMemoryMarkdownRepository:
    def __init__(self, snapshot: MarkdownSnapshot) -> None:
        self.snapshot = snapshot

    def inspect(self, root: RepositoryRoot) -> MarkdownSnapshot:
        return self.snapshot
