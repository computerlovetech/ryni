from ryni.skill_repository import (
    IgnoreStatus,
    InstallationStatus,
    RepositoryRoot,
    SkillLayout,
    SkillSource,
)


class InMemorySkillRepository:
    def __init__(
        self,
        layout: SkillLayout = SkillLayout(),
        ignores: tuple[IgnoreStatus, ...] = (),
        installations: dict[SkillSource, InstallationStatus] | None = None,
    ) -> None:
        self.snapshot = layout
        self.ignore_statuses = ignores
        self.installations = installations if installations is not None else {}

    def layout(self, root: RepositoryRoot) -> SkillLayout:
        return self.snapshot

    def ignores(self, root: RepositoryRoot, layout: SkillLayout) -> tuple[IgnoreStatus, ...]:
        return self.ignore_statuses

    def installation(self, source: SkillSource) -> InstallationStatus:
        return self.installations[source]
