from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import httpx


def _clip(text: str, max_len: int) -> str:
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        return str(value)


def _is_method_not_found_error(exc: Exception) -> bool:
    return "method not found" in str(exc).lower()


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
                    summary=_clip(excerpt, 250),
                    excerpt=excerpt,
                    confidence=min(0.90, 0.45 + score * 0.08),
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
    Direct MCP transport for brianmadden.ai/mcp.

    Observed live tool names:
    - get_file
    - list_files
    - search
    - get_framework
    - get_current_thinking
    - get_loading_instructions
    """

    PROTOCOL_CANDIDATES = [
        "2025-03-26",
        "2024-11-05",
    ]

    def __init__(self, mcp_url: str, timeout_seconds: int = 20):
        self.mcp_url = mcp_url
        self.timeout_seconds = timeout_seconds

        self._session_id: str | None = None
        self._initialized = False
        self._negotiated_protocol: str | None = None
        self._server_info: dict[str, Any] | None = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        if self._negotiated_protocol:
            headers["MCP-Protocol-Version"] = self._negotiated_protocol
        return headers

    def _remember_session(self, response: httpx.Response) -> None:
        session_id = response.headers.get("Mcp-Session-Id")
        if session_id:
            self._session_id = session_id

    def _parse_sse_objects(self, text: str) -> list[dict]:
        events: list[dict] = []
        data_lines: list[str] = []

        for line in text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif not line.strip():
                if data_lines:
                    payload = "\n".join(data_lines).strip()
                    try:
                        parsed = json.loads(payload)
                        if isinstance(parsed, dict):
                            events.append(parsed)
                    except Exception:
                        pass
                    data_lines = []

        if data_lines:
            payload = "\n".join(data_lines).strip()
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    events.append(parsed)
            except Exception:
                pass

        return events

    def _parse_rpc_payload(self, response: httpx.Response) -> dict:
        body = response.text.strip()
        if not body:
            return {}

        content_type = response.headers.get("content-type", "")

        if "text/event-stream" in content_type or body.startswith("event:") or "\ndata:" in body:
            events = self._parse_sse_objects(body)
            for event in reversed(events):
                if "result" in event or "error" in event or "method" in event:
                    return event
            raise RuntimeError("No JSON-RPC payload found in SSE response")

        try:
            parsed = json.loads(body)
        except Exception as e:
            raise RuntimeError(f"Unable to parse MCP response: {e}. Raw body: {body[:500]}") from e

        if not isinstance(parsed, dict):
            raise RuntimeError(f"Unexpected MCP response shape: {type(parsed).__name__}")
        return parsed

    def _rpc(self, method: str, params: dict | None = None, notification: bool = False) -> dict:
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if not notification:
            payload["id"] = self._next_id()
        if params is not None:
            payload["params"] = params

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = client.post(
                self.mcp_url,
                headers=self._headers(),
                json=payload,
            )

        self._remember_session(response)

        if notification:
            return {}

        parsed = self._parse_rpc_payload(response)

        if "error" in parsed:
            err = parsed["error"]
            message = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            raise RuntimeError(f"MCP method {method} failed: {message}")

        return parsed.get("result", {})

    def _initialize(self) -> None:
        if self._initialized:
            return

        last_error: Exception | None = None

        for version in self.PROTOCOL_CANDIDATES:
            self._session_id = None
            self._negotiated_protocol = None

            try:
                result = self._rpc(
                    "initialize",
                    {
                        "protocolVersion": version,
                        "capabilities": {},
                        "clientInfo": {
                            "name": "openbrain-gateway",
                            "version": "0.4.0",
                        },
                    },
                )

                self._negotiated_protocol = result.get("protocolVersion", version)
                server_info = result.get("serverInfo", {})
                self._server_info = server_info if isinstance(server_info, dict) else {}

                try:
                    self._rpc("notifications/initialized", {}, notification=True)
                except Exception:
                    pass

                self._initialized = True
                return
            except Exception as e:
                last_error = e

        if last_error:
            raise last_error
        raise RuntimeError("Failed to initialize Brian MCP connector")

    def _list_tools(self) -> list[dict]:
        self._initialize()
        try:
            result = self._rpc("tools/list")
        except Exception as e:
            if _is_method_not_found_error(e):
                return []
            raise

        if isinstance(result, dict) and isinstance(result.get("tools"), list):
            return result["tools"]
        if isinstance(result, list):
            return result
        return []

    def _list_resources(self) -> list[dict]:
        self._initialize()
        try:
            result = self._rpc("resources/list")
        except Exception as e:
            if _is_method_not_found_error(e):
                return []
            raise

        if isinstance(result, dict) and isinstance(result.get("resources"), list):
            return result["resources"]
        if isinstance(result, list):
            return result
        return []

    def _tool_map(self) -> dict[str, dict]:
        return {
            str(tool.get("name", "")).strip(): tool
            for tool in self._list_tools()
            if isinstance(tool, dict) and tool.get("name")
        }

    def _call_tool(self, name: str, arguments: dict | None = None) -> dict:
        self._initialize()
        args = arguments or {}
        try:
            return self._rpc("tools/call", {"name": name, "arguments": args})
        except Exception:
            return self._rpc("tools/call", {"name": name, "args": args})

    def _read_resource(self, uri: str) -> dict:
        self._initialize()
        return self._rpc("resources/read", {"uri": uri})

    def _extract_content_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, dict):
            for key in ("text", "content", "body", "value"):
                if isinstance(content.get(key), str):
                    return content[key].strip()
            return _safe_json(content)

        if not isinstance(content, list):
            return ""

        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            for key in ("text", "content", "body", "value"):
                if isinstance(block.get(key), str):
                    parts.append(block[key])
                    break

        return "\n\n".join(part.strip() for part in parts if part.strip()).strip()

    def _structured_items(self, structured: Any) -> list[Any]:
        if isinstance(structured, list):
            return structured

        if isinstance(structured, dict):
            for key in (
                "results",
                "items",
                "matches",
                "entries",
                "documents",
                "files",
                "frameworks",
            ):
                if isinstance(structured.get(key), list):
                    return structured[key]
            return [structured]

        return []

    def _normalize_structured(
        self,
        structured: Any,
        reason: str,
        default_confidence: float = 0.97,
    ) -> list[ExternalResult]:
        items = self._structured_items(structured)
        results: list[ExternalResult] = []

        for item in items:
            if isinstance(item, dict):
                title = (
                    item.get("title")
                    or item.get("name")
                    or item.get("label")
                    or item.get("file")
                    or item.get("path")
                    or "Brian Madden MCP Result"
                )
                excerpt = (
                    item.get("excerpt")
                    or item.get("summary")
                    or item.get("description")
                    or item.get("snippet")
                    or item.get("text")
                    or item.get("content")
                    or item.get("body")
                    or _safe_json(item)
                )
                uri = (
                    item.get("url")
                    or item.get("uri")
                    or item.get("path")
                    or item.get("file")
                    or item.get("source")
                    or item.get("source_url")
                )
                raw_score = item.get("score") or item.get("confidence") or item.get("relevance")
                confidence = default_confidence
                if isinstance(raw_score, (int, float)) and 0 <= float(raw_score) <= 1:
                    confidence = float(raw_score)
            else:
                title = "Brian Madden MCP Result"
                excerpt = str(item)
                uri = None
                confidence = default_confidence

            excerpt = str(excerpt).strip()
            if not excerpt:
                continue

            results.append(
                ExternalResult(
                    source_namespace="external.brianmadden",
                    source_label="Brian Madden MCP",
                    title=str(title),
                    summary=_clip(excerpt, 250),
                    excerpt=_clip(excerpt, 1600),
                    confidence=confidence,
                    retrieval_reason=reason,
                    provenance={"transport": "mcp"},
                    uri=uri,
                )
            )

        return results

    def _normalize_tool_output(
        self,
        tool_name: str,
        raw: Any,
        default_confidence: float = 0.97,
    ) -> list[ExternalResult]:
        if isinstance(raw, dict) and raw.get("isError"):
            raise RuntimeError(f"MCP tool {tool_name} returned isError=true")

        if isinstance(raw, dict):
            structured = raw.get("structuredContent") or raw.get("structured_content")
            if structured is not None:
                structured_results = self._normalize_structured(
                    structured,
                    reason=f"direct MCP tool call via {tool_name}",
                    default_confidence=default_confidence,
                )
                if structured_results:
                    return structured_results

            for key in ("results", "items", "matches", "entries", "documents", "files", "frameworks"):
                if key in raw:
                    structured_results = self._normalize_structured(
                        raw,
                        reason=f"direct MCP tool call via {tool_name}",
                        default_confidence=default_confidence,
                    )
                    if structured_results:
                        return structured_results

            content = raw.get("content") or raw.get("contents")
            text = self._extract_content_text(content)
            if text:
                return [
                    ExternalResult(
                        source_namespace="external.brianmadden",
                        source_label="Brian Madden MCP",
                        title=f"Brian Madden MCP via {tool_name}",
                        summary=_clip(text, 250),
                        excerpt=_clip(text, 1600),
                        confidence=default_confidence,
                        retrieval_reason=f"direct MCP tool call via {tool_name}",
                        provenance={"transport": "mcp", "tool": tool_name},
                        uri=None,
                    )
                ]

        if isinstance(raw, list):
            structured_results = self._normalize_structured(
                raw,
                reason=f"direct MCP tool call via {tool_name}",
                default_confidence=default_confidence,
            )
            if structured_results:
                return structured_results

        raw_text = _safe_json(raw).strip()
        if raw_text:
            return [
                ExternalResult(
                    source_namespace="external.brianmadden",
                    source_label="Brian Madden MCP",
                    title=f"Brian Madden MCP via {tool_name}",
                    summary=_clip(raw_text, 250),
                    excerpt=_clip(raw_text, 1600),
                    confidence=default_confidence,
                    retrieval_reason=f"direct MCP tool call via {tool_name}",
                    provenance={"transport": "mcp", "tool": tool_name},
                    uri=None,
                )
            ]

        return []

    def _search_with_search_tool(self, query: str, k: int) -> list[ExternalResult]:
        arg_sets = [
            {"query": query, "limit": k},
            {"query": query, "k": k},
            {"query": query},
            {"q": query, "limit": k},
            {"q": query, "k": k},
            {"q": query},
            {"text": query},
            {"prompt": query},
            {"topic": query},
        ]

        errors: list[str] = []
        for args in arg_sets:
            try:
                raw = self._call_tool("search", args)
                results = self._normalize_tool_output("search", raw, default_confidence=0.99)
                if results:
                    return results[:k]
            except Exception as e:
                errors.append(str(e))

        if errors:
            raise RuntimeError("search tool failed: " + " | ".join(errors[:3]))
        return []

    def _search_with_current_thinking(self, query: str, k: int) -> list[ExternalResult]:
        arg_sets = [
            {"query": query},
            {"topic": query},
            {"prompt": query},
            {},
        ]

        for args in arg_sets:
            try:
                raw = self._call_tool("get_current_thinking", args)
                results = self._normalize_tool_output("get_current_thinking", raw, default_confidence=0.96)
                if results:
                    return results[:k]
            except Exception:
                continue
        return []

    def _search_with_framework(self, query: str, k: int) -> list[ExternalResult]:
        arg_sets = [
            {"query": query},
            {"name": query},
            {"framework": query},
            {"topic": query},
        ]

        for args in arg_sets:
            try:
                raw = self._call_tool("get_framework", args)
                results = self._normalize_tool_output("get_framework", raw, default_confidence=0.96)
                if results:
                    return results[:k]
            except Exception:
                continue
        return []

    def _search_via_file_tools(self, query: str, k: int) -> list[ExternalResult]:
        try:
            raw = self._call_tool("list_files", {})
        except Exception:
            return []

        file_entries = self._structured_items(raw.get("structuredContent") if isinstance(raw, dict) else raw)
        if not file_entries:
            file_entries = self._structured_items(raw)

        terms = [t.lower() for t in query.split() if t.strip()]
        scored: list[tuple[int, dict | str]] = []

        for item in file_entries:
            if isinstance(item, dict):
                hay = " ".join(str(item.get(key, "")) for key in ("path", "file", "name", "title", "description")).lower()
            else:
                hay = str(item).lower()

            score = sum(1 for term in terms if term in hay)
            if score > 0:
                scored.append((score, item))

        if not scored:
            return []

        scored.sort(key=lambda x: x[0], reverse=True)
        top_items = [item for _, item in scored[:k]]

        results: list[ExternalResult] = []
        for item in top_items:
            candidate_paths: list[str] = []
            if isinstance(item, dict):
                for key in ("path", "file", "name", "title"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        candidate_paths.append(value.strip())
            else:
                candidate_paths.append(str(item).strip())

            file_raw = None
            for candidate in candidate_paths:
                for args in ({"path": candidate}, {"file": candidate}, {"name": candidate}):
                    try:
                        file_raw = self._call_tool("get_file", args)
                        break
                    except Exception:
                        continue
                if file_raw is not None:
                    break

            if file_raw is None:
                continue

            normalized = self._normalize_tool_output("get_file", file_raw, default_confidence=0.95)
            if normalized:
                results.extend(normalized[:1])

        return results[:k]

    def search(self, query: str, k: int = 5) -> list[ExternalResult]:
        self._initialize()
        tools = self._tool_map()

        # 1. Prefer the explicit search tool if present
        if "search" in tools:
            try:
                results = self._search_with_search_tool(query, k)
                if results:
                    return results[:k]
            except Exception:
                pass

        # 2. Try current thinking for broad/future/current/trend questions
        query_l = query.lower()
        if "get_current_thinking" in tools and any(
            token in query_l for token in ("current", "future", "trend", "thinking", "direction", "knowledge work", "ai")
        ):
            results = self._search_with_current_thinking(query, k)
            if results:
                return results[:k]

        # 3. Try framework lookup for framework-oriented questions
        if "get_framework" in tools and any(
            token in query_l for token in ("framework", "model", "approach", "method")
        ):
            results = self._search_with_framework(query, k)
            if results:
                return results[:k]

        # 4. File-based fallback using list_files + get_file
        if "list_files" in tools and "get_file" in tools:
            results = self._search_via_file_tools(query, k)
            if results:
                return results[:k]

        # 5. Final fallback: resources if any
        try:
            resources = self._list_resources()
        except Exception:
            resources = []

        if resources:
            terms = [t.lower() for t in query.split() if t.strip()]
            scored: list[tuple[int, dict]] = []
            for resource in resources:
                hay = " ".join(
                    str(resource.get(key, ""))
                    for key in ("name", "title", "description", "uri")
                ).lower()
                score = sum(1 for term in terms if term in hay)
                if score > 0:
                    scored.append((score, resource))

            scored.sort(key=lambda x: x[0], reverse=True)
            top_resources = [item for _, item in scored[:k]]

            results: list[ExternalResult] = []
            for resource in top_resources:
                uri = resource.get("uri")
                if not uri:
                    continue
                try:
                    raw = self._read_resource(uri)
                except Exception:
                    continue

                text = self._extract_content_text(raw.get("contents") if isinstance(raw, dict) else raw)
                if not text:
                    text = _safe_json(raw)

                results.append(
                    ExternalResult(
                        source_namespace="external.brianmadden",
                        source_label="Brian Madden MCP",
                        title=resource.get("title") or resource.get("name") or uri,
                        summary=_clip(text, 250),
                        excerpt=_clip(text, 1600),
                        confidence=0.94,
                        retrieval_reason="resource fallback via direct MCP",
                        provenance={"transport": "mcp", "resource_uri": uri},
                        uri=uri,
                    )
                )

            if results:
                return results[:k]

        return []

    def status(self) -> dict:
        try:
            self._initialize()
        except Exception as e:
            return {
                "connector": "brian_mcp",
                "enabled": True,
                "available": False,
                "url": self.mcp_url,
                "error": str(e),
            }

        tools: list[dict] = []
        tool_error: str | None = None
        resources: list[dict] = []
        resource_error: str | None = None

        try:
            tools = self._list_tools()
        except Exception as e:
            tool_error = str(e)

        try:
            resources = self._list_resources()
        except Exception as e:
            if not _is_method_not_found_error(e):
                resource_error = str(e)

        return {
            "connector": "brian_mcp",
            "enabled": True,
            "available": True,
            "url": self.mcp_url,
            "protocol_version": self._negotiated_protocol,
            "server_info": self._server_info or {},
            "tool_names": [t.get("name") for t in tools if isinstance(t, dict)],
            "tool_count": len(tools),
            "tool_error": tool_error,
            "resources_supported": resource_error is None,
            "resource_count": len(resources),
            "resource_error": resource_error,
            "session_id_present": bool(self._session_id),
        }
