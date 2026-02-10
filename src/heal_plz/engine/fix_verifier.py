import logging
from dataclasses import dataclass, field
from typing import Optional

from heal_plz.db.models.verification import VerificationResult, VerificationType

logger = logging.getLogger(__name__)


@dataclass
class VerificationCheck:
    check_type: VerificationType
    result: VerificationResult
    output: str = ""
    duration_seconds: float = 0.0


@dataclass
class VerificationSuite:
    checks: list[VerificationCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(
            c.result == VerificationResult.PASS for c in self.checks
        )

    @property
    def summary(self) -> str:
        parts = []
        for c in self.checks:
            parts.append(f"{c.check_type.value}: {c.result.value}")
        return ", ".join(parts)


class FixVerifier:
    async def verify_syntax(self, file_path: str, content: str) -> VerificationCheck:
        if file_path.endswith(".py"):
            try:
                compile(content, file_path, "exec")
                return VerificationCheck(
                    check_type=VerificationType.LINT,
                    result=VerificationResult.PASS,
                    output="Python syntax valid",
                )
            except SyntaxError as e:
                return VerificationCheck(
                    check_type=VerificationType.LINT,
                    result=VerificationResult.FAIL,
                    output=f"SyntaxError: {e}",
                )

        return VerificationCheck(
            check_type=VerificationType.LINT,
            result=VerificationResult.PASS,
            output="Syntax check skipped (non-Python file)",
        )

    async def verify_changes(
        self, changes: list[dict],
    ) -> VerificationSuite:
        suite = VerificationSuite()

        for change in changes:
            path = change.get("path", "")
            content = change.get("content", "")

            check = await self.verify_syntax(path, content)
            suite.checks.append(check)

        return suite
