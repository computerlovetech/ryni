"""Opinionated agent harness conventions for Rýni."""

from ryni.models import RulePack

from .checks import RULES as CHECKS
from .reviews import RULES as REVIEWS

PACK = RulePack(
    name="tidy-harness",
    description="One source of truth, discoverable docs, and focused instructions.",
    rules=(*CHECKS, *REVIEWS),
)
