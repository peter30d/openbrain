from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import httpx


@dataclass
class ExternalResult:
    source_namespace: str
    source_label: str
    title: str
    summary: str
    excerpt: str
    confidence: float
    retrieval_reason: str
    provenance: dict
    uri: str | None = None


class BrianConnectorBase:
    def search(self, query: str, k: int = 5) -> list[ExternalResult]:
        raise NotImplementedError

    def status(self) -> dict:
        raise NotImplementedError


class BrianRepoConnector(BrianConnectorBase):
    def __init__(self, repo_dir: str):
        self.repo_dir = Path(repo_dir)

    def _iter_files(self):
        if not self.repo_dir.exists():
            return []
        return list(self.repo_dir.rglob("*.md"))

    def search(self, query: str, k: int = 5) -> list[ExternalResult]:
        terms = [t.lower() for t in query.split() if t.strip()]
        results: list[ExternalResult] = []

        for file in self._iter_files():
            text = file.read_text(encoding="utf-8", errors="ignore")
            low = text.lower()
            score = sum(1 for t in terms if t in low)
            if score == 0:
                continue

            title = file.stem.replace("-", " ").replace("_", " ").title()
            excerpt = text[:800].strip()
            results.append(
                ExternalResult(
                    source_namespace="external.brianmadden",
                    source_label="Brian Madden Repo",
                    title=title,
                    summary=excerpt[:250],
                    excerpt=excerpt,
                    confidence=min(0.95, 0.5 + score * 0.1),
                    retrieval_reason="keyword match in mirrored Brian repo",
                    provenance={"path": str(file)},
                    uri=None,
                )
            )

        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:k]

    def status(self) -> dict:
        return {
            "connector": "brian_repo",
            "enabled": True,
            "available": self.repo_dir.exists(),
            "path": str(self.repo_dir),
        }


class BrianMCPConnector(BrianConnectorBase):
    """
    Transport slot for direct Brian MCP integration.

    We isolate it here because the public site clearly advertises the MCP URL,
    but the wire contract is not publicly documented in detail. This class is
    the seam where a verified transport can be dropped in later.
    """

    def __init__(self, mcp_url: str, timeout_seconds: int = 20):
        self.mcp_url = mcp_url
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, k: int = 5) -> list[ExternalResult]:
        raise RuntimeError(
            "Direct Brian MCP transport is not enabled yet. "
            "Use the repo/site fallback or add a verified MCP transport implementation."
        )

    def status(self) -> dict:
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                r = client.get(self.mcp_url, headers={"Accept": "text/event-stream"})
            return {
                "connector": "brian_mcp",
                "enabled": True,
                "available": r.status_code in (200, 406),
                "status_code": r.status_code,
                "url": self.mcp_url,
            }
        except Exception as e:
            return {
                "connector": "brian_mcp",
                "enabled": True,
                "available": False,
                "url": self.mcp_url,
                "error": str(e),
            }

