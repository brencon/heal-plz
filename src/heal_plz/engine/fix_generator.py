import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from heal_plz.config import settings
from heal_plz.db.models.root_cause import RootCause
from heal_plz.engine.code_context import CodeContext
from heal_plz.integrations.llm.prompts import FIX_GENERATION_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    path: str
    content: str


@dataclass
class FixResult:
    success: bool
    changes: list[FileChange] = field(default_factory=list)
    description: str = ""
    attempt: int = 1
    model: str = ""
    tokens_used: int = 0
    error: Optional[str] = None


class FixGenerator:
    def __init__(self, max_attempts: int = 3) -> None:
        self.max_attempts = max_attempts

    async def generate(
        self,
        root_cause: RootCause,
        code_context: CodeContext,
    ) -> FixResult:
        feedback_lines: list[str] = []

        for attempt in range(1, self.max_attempts + 1):
            logger.info(
                "Generating fix attempt %d/%d for %s",
                attempt,
                self.max_attempts,
                root_cause.file_path,
            )

            feedback_section = ""
            if feedback_lines:
                feedback_section = (
                    "\n## Previous Attempt Feedback\n"
                    + "\n".join(feedback_lines)
                )

            line_range = "unknown"
            if root_cause.line_range_start:
                line_range = f"{root_cause.line_range_start}"
                if root_cause.line_range_end:
                    line_range += f"-{root_cause.line_range_end}"

            prompt = FIX_GENERATION_PROMPT.format(
                root_cause_category=root_cause.category.value,
                root_cause_description=root_cause.description,
                file_path=root_cause.file_path or "unknown",
                line_range=line_range,
                code_context=code_context.to_prompt_context(),
                feedback_section=feedback_section,
            )

            try:
                import anthropic

                client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                response = await client.messages.create(
                    model=settings.PRIMARY_LLM_MODEL,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )

                text = response.content[0].text
                tokens = (response.usage.input_tokens or 0) + (
                    response.usage.output_tokens or 0
                )

                changes = self._parse_file_changes(text)

                if not changes:
                    feedback_lines.append(
                        f"Attempt {attempt}: Could not parse file changes from response"
                    )
                    continue

                return FixResult(
                    success=True,
                    changes=changes,
                    description=self._extract_description(text),
                    attempt=attempt,
                    model=settings.PRIMARY_LLM_MODEL,
                    tokens_used=tokens,
                )

            except Exception as e:
                logger.exception("Fix generation attempt %d failed", attempt)
                feedback_lines.append(f"Attempt {attempt}: Error — {e}")

        return FixResult(
            success=False,
            attempt=self.max_attempts,
            error="All fix attempts failed",
        )

    def _parse_file_changes(self, text: str) -> list[FileChange]:
        changes = []
        pattern = re.compile(
            r"###\s*FILE:\s*(.+?)\s*\n```\w*\n(.*?)```",
            re.DOTALL,
        )
        for match in pattern.finditer(text):
            path = match.group(1).strip()
            content = match.group(2)
            changes.append(FileChange(path=path, content=content))

        return changes

    def _extract_description(self, text: str) -> str:
        lines = text.split("\n")
        desc_lines = []
        for line in lines:
            if line.startswith("### FILE:"):
                break
            if line.strip():
                desc_lines.append(line.strip())
        return " ".join(desc_lines[:3]) if desc_lines else "Auto-generated fix"
