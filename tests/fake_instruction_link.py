from ryni.instruction_link import InstructionLink
from ryni.models import Finding


class InMemoryInstructionLinkRepair:
    def __init__(self, findings: list[Finding]) -> None:
        self.findings = findings
        self.repaired: list[InstructionLink] = []

    def repair(self, link: InstructionLink) -> None:
        self.repaired.append(link)
        self.findings.clear()
