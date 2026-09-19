"""Boundary for safely repairing an instruction-file link."""

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class InstructionLink(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: Path


class InstructionLinkRepair(Protocol):
    def repair(self, link: InstructionLink) -> None:
        """Repair when safe; leave unsupported cases unchanged; raise on I/O failure."""
        ...
