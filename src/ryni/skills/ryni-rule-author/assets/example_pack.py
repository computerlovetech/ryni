"""Example pack: share service.toml analysis across independent file rules."""

from dataclasses import dataclass
from pathlib import Path
import tomllib

from ryni.cache import cached_per_check
from ryni.models import Finding, Rule, RulePack


@dataclass(frozen=True)
class Settings:
    name: str | None = None
    port: int | None = None
    error: str | None = None


@cached_per_check
def read_config(path: Path) -> str:
    # I/O and decoding failures propagate to Rýni as execution errors.
    return path.read_text(encoding="utf-8")


@cached_per_check
def parse_config(text: str) -> Settings:
    # The parser has no target path: identical content can share analysis.
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return Settings(error="Use valid TOML.")
    service = data.get("service")
    if not isinstance(service, dict):
        return Settings(error="Add a [service] table.")
    name, port = service.get("name"), service.get("port")
    # Keep the shared analysis immutable, including invalid input types.
    return Settings(
        name=name if isinstance(name, str) else None,
        port=port if type(port) is int else None,
    )


def structure(path: Path) -> list[Finding]:
    settings = parse_config(read_config(path))
    return [Finding(str(path), 1, "SERVICE001", settings.error)] if settings.error else []


def service_name(path: Path) -> list[Finding]:
    settings = parse_config(read_config(path))
    if settings.error:
        return []  # SERVICE001 owns structural findings.
    if not isinstance(settings.name, str) or not settings.name.strip():
        return [Finding(str(path), 1, "SERVICE002", "Set a non-empty service.name.")]
    return []


def service_port(path: Path) -> list[Finding]:
    settings = parse_config(read_config(path))
    if settings.error:
        return []
    if type(settings.port) is not int or not 1 <= settings.port <= 65535:
        return [Finding(str(path), 1, "SERVICE003", "Set service.port to an integer from 1–65535.")]
    return []


PACK = RulePack(
    name="service-rules",
    description="Validate service settings.",
    rules=(
        Rule("SERVICE001", "structure", "Require service TOML.", "service.toml", structure),
        Rule("SERVICE002", "name", "Require a service name.", "service.toml", service_name),
        Rule("SERVICE003", "port", "Require a valid port.", "service.toml", service_port),
    ),
)
