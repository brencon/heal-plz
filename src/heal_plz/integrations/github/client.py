import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str) -> None:
        self.token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: Optional[str] = None
    ) -> Optional[str]:
        info = await self.get_file_info(owner, repo, path, ref=ref)
        return info["content"] if info else None

    async def get_file_info(
        self, owner: str, repo: str, path: str, ref: Optional[str] = None
    ) -> Optional[dict[str, str]]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            content = data.get("content", "")
            if data.get("encoding") == "base64":
                import base64
                content = base64.b64decode(content).decode("utf-8")
            return {"content": content, "sha": data.get("sha", "")}

    async def get_commits(
        self,
        owner: str,
        repo: str,
        path: Optional[str] = None,
        sha: Optional[str] = None,
        per_page: int = 5,
    ) -> list[dict[str, Any]]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
        params: dict[str, Any] = {"per_page": per_page}
        if path:
            params["path"] = path
        if sha:
            params["sha"] = sha
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers, params=params)
            if resp.status_code != 200:
                return []
            return resp.json()

    async def create_branch(
        self, owner: str, repo: str, branch_name: str, from_sha: str
    ) -> bool:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=self._headers,
                json={"ref": f"refs/heads/{branch_name}", "sha": from_sha},
            )
            return resp.status_code == 201

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: Optional[str] = None,
    ) -> bool:
        import base64
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        body: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        async with httpx.AsyncClient() as client:
            resp = await client.put(url, headers=self._headers, json=body)
            return resp.status_code in (200, 201)

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> Optional[dict[str, Any]]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=self._headers,
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                },
            )
            if resp.status_code == 201:
                return resp.json()
            logger.error("Failed to create PR: %s %s", resp.status_code, resp.text)
            return None

    async def get_default_branch_sha(
        self, owner: str, repo: str
    ) -> Optional[str]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs/heads/main"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers)
            if resp.status_code == 200:
                return resp.json()["object"]["sha"]
            return None

    async def get_workflow_run_jobs(
        self, owner: str, repo: str, run_id: int
    ) -> list[dict[str, Any]]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers)
            if resp.status_code != 200:
                return []
            return resp.json().get("jobs", [])
