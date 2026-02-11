import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from heal_plz.engine.stacktrace_parser import ParsedStacktrace, StacktraceParser
from heal_plz.integrations.github.client import GitHubClient

logger = logging.getLogger(__name__)


@dataclass
class FileContext:
    path: str
    content: str
    highlight_lines: list[int] = field(default_factory=list)


@dataclass
class CodeContext:
    files: dict[str, FileContext] = field(default_factory=dict)
    test_files: dict[str, FileContext] = field(default_factory=dict)
    recent_commits: list[dict[str, Any]] = field(default_factory=list)
    parsed_stacktrace: Optional[ParsedStacktrace] = None

    def to_prompt_context(self) -> str:
        sections = []

        if self.parsed_stacktrace and self.parsed_stacktrace.frames:
            sections.append("## Stacktrace Frames")
            for f in self.parsed_stacktrace.frames:
                sections.append(f"- {f.file_path}:{f.line_number} in {f.function_name or '?'}")

        if self.files:
            sections.append("\n## Affected Source Files")
            for path, ctx in self.files.items():
                sections.append(f"\n### {path}")
                sections.append(f"```\n{ctx.content}\n```")

        if self.test_files:
            sections.append("\n## Related Test Files")
            for path, ctx in self.test_files.items():
                sections.append(f"\n### {path}")
                sections.append(f"```\n{ctx.content}\n```")

        if self.recent_commits:
            sections.append("\n## Recent Commits")
            for c in self.recent_commits[:5]:
                sha = c.get("sha", "")[:7]
                msg = c.get("commit", {}).get("message", "").split("\n")[0]
                sections.append(f"- {sha}: {msg}")

        return "\n".join(sections)


class CodeContextBuilder:
    def __init__(self, github_client: GitHubClient) -> None:
        self.github = github_client
        self.parser = StacktraceParser()

    async def build(
        self,
        owner: str,
        repo: str,
        stacktrace: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        commit_sha: Optional[str] = None,
    ) -> CodeContext:
        context = CodeContext()

        if stacktrace:
            context.parsed_stacktrace = self.parser.parse(stacktrace)
            for frame in context.parsed_stacktrace.frames:
                await self._add_file(
                    context, owner, repo, frame.file_path, commit_sha,
                    highlight_lines=[frame.line_number] if frame.line_number else [],
                )

        if file_path and file_path not in context.files:
            await self._add_file(
                context, owner, repo, file_path, commit_sha,
                highlight_lines=[line_number] if line_number else [],
            )

        for path in list(context.files.keys()):
            test_path = self._guess_test_path(path)
            if test_path:
                content = await self.github.get_file_content(
                    owner, repo, test_path, ref=commit_sha
                )
                if content:
                    context.test_files[test_path] = FileContext(
                        path=test_path, content=content
                    )

        affected_paths = list(context.files.keys())
        if affected_paths:
            commits = await self.github.get_commits(
                owner, repo, path=affected_paths[0], sha=commit_sha, per_page=5
            )
            context.recent_commits = commits

        return context

    def _normalize_repo_path(self, path: str, repo: str) -> Optional[str]:
        if not path.startswith("/"):
            return path
        parts = path.split("/")
        for i, part in enumerate(parts):
            if part == repo and i + 1 < len(parts):
                return "/".join(parts[i + 1:])
        return None

    async def _add_file(
        self,
        context: CodeContext,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str],
        highlight_lines: Optional[list[int]] = None,
    ) -> None:
        if ".." in path:
            return
        if path.startswith("/"):
            normalized = self._normalize_repo_path(path, repo)
            if not normalized:
                return
            path = normalized
        if path in context.files:
            return

        content = await self.github.get_file_content(owner, repo, path, ref=ref)
        if content:
            context.files[path] = FileContext(
                path=path,
                content=content,
                highlight_lines=highlight_lines or [],
            )

    def _guess_test_path(self, source_path: str) -> Optional[str]:
        if "test" in source_path:
            return None

        name = source_path.rsplit("/", 1)[-1]
        base, ext = name.rsplit(".", 1) if "." in name else (name, "")

        candidates = [
            source_path.replace(name, f"test_{name}"),
            source_path.replace(name, f"{base}.test.{ext}"),
            source_path.replace(name, f"{base}_test.{ext}"),
            f"tests/{name.replace(f'.{ext}', '')}_test.{ext}",
            f"tests/test_{name}",
        ]
        return candidates[0] if ext else None
