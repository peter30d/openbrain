from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from openbrain.db import SessionLocal
from openbrain.models import MemoryRecord, ExternalPromotion, GatewayAuditLog
from openbrain.embeddings import EmbeddingProvider
from openbrain.archive import write_archive
from openbrain.connectors import BrianRepoConnector, BrianMCPConnector, ExternalResult
from openbrain.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryGatewayService:
    def __init__(self):
        self.embedder = EmbeddingProvider(settings.embed_model)
        self.brian_repo = BrianRepoConnector(settings.brian_repo_dir) if settings.enable_brian_repo else None
        self.brian_mcp = BrianMCPConnector(settings.brian_mcp_url, settings.brian_timeout_seconds) if settings.enable_brian_mcp else None

    def _audit(self, event_type: str, payload: dict) -> None:
        with SessionLocal() as db:
            db.add(GatewayAuditLog(event_type=event_type, payload=payload))
            db.commit()

    def capture_memory(
        self,
        text_value: str,
        memory_type: str = "note",
        source_surface: str = "telegram_openclaw",
        source_session_id: str | None = None,
        project: str | None = None,
        tags: list[str] | None = None,
        topics: list[str] | None = None,
        people: list[str] | None = None,
    ) -> dict[str, Any]:
        cleaned = " ".join(text_value.split()).strip()
        summary = cleaned[:280]
        title = summary[:80] if len(summary) > 80 else summary
        record_id = uuid.uuid4()
        captured_at = utcnow()
        embedding = self.embedder.embed(cleaned)

        draft = {
            "id": record_id,
            "title": title or "Memory",
            "raw_text": text_value,
            "cleaned_text": cleaned,
            "summary": summary,
            "memory_type": memory_type,
            "source_surface": source_surface,
            "source_session_id": source_session_id,
            "project": project,
            "people": people or [],
            "topics": topics or [],
            "tags": tags or [],
            "action_items": [],
            "importance": 3,
            "sensitivity": "normal",
            "provenance_type": "local",
            "provenance_ref": None,
            "captured_at": captured_at,
        }

        archive_path = write_archive(settings.archive_dir, draft)

        with SessionLocal() as db:
            rec = MemoryRecord(
                id=record_id,
                title=draft["title"],
                raw_text=draft["raw_text"],
                cleaned_text=draft["cleaned_text"],
                summary=draft["summary"],
                memory_type=draft["memory_type"],
                source_surface=draft["source_surface"],
                source_session_id=draft["source_session_id"],
                project=draft["project"],
                people=draft["people"],
                topics=draft["topics"],
                tags=draft["tags"],
                action_items=draft["action_items"],
                importance=draft["importance"],
                sensitivity=draft["sensitivity"],
                provenance_type=draft["provenance_type"],
                provenance_ref=draft["provenance_ref"],
                archive_path=archive_path,
                captured_at=captured_at,
                created_at=captured_at,
                updated_at=captured_at,
                embedding=embedding,
            )
            db.add(rec)
            db.commit()

        self._audit("capture_memory", {"id": str(record_id), "source_surface": source_surface})
        return {"id": str(record_id), "title": draft["title"], "summary": summary, "archive_path": archive_path}

    def search_local_memory(self, query: str, k: int = 5) -> list[dict]:
        query_vec = self.embedder.embed(query)

        sql = text(
            """
            SELECT
                id,
                title,
                summary,
                cleaned_text,
                archive_path,
                provenance_type,
                captured_at,
                1 - (embedding <=> CAST(:query_vec AS vector)) AS score
            FROM memory_records
            WHERE status = 'active'
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :k
            """
        )

        with SessionLocal() as db:
            rows = db.execute(sql, {"query_vec": str(query_vec), "k": k}).mappings().all()

        return [
            {
                "source_namespace": "local",
                "source_label": "Local Canonical Memory",
                "title": row["title"],
                "summary": row["summary"],
                "excerpt": row["cleaned_text"][:500],
                "confidence": float(row["score"] or 0.0),
                "retrieval_reason": "semantic vector match",
                "provenance": {
                    "id": str(row["id"]),
                    "archive_path": row["archive_path"],
                    "captured_at": row["captured_at"].isoformat() if row["captured_at"] else None,
                },
            }
            for row in rows
        ]

    def search_brian(self, query: str, k: int = 5) -> list[dict]:
        results: list[ExternalResult] = []
        if self.brian_repo:
            results.extend(self.brian_repo.search(query, k=k))
        if self.brian_mcp:
            try:
                results.extend(self.brian_mcp.search(query, k=k))
            except Exception:
                pass

        results.sort(key=lambda r: r.confidence, reverse=True)
        return [r.__dict__ for r in results[:k]]

    def federated_search(self, query: str, k: int = 5) -> dict:
        local = self.search_local_memory(query, k=k)
        brian = self.search_brian(query, k=k)

        combined = sorted(
            local + brian,
            key=lambda r: float(r.get("confidence", 0.0)),
            reverse=True,
        )[:k]

        self._audit("federated_search", {"query": query, "k": k})
        return {"query": query, "local": local, "brian": brian, "combined": combined}

    def promote_external_result(
        self,
        source_namespace: str,
        title: str,
        excerpt: str,
        uri: str | None = None,
        promotion_note: str | None = None,
    ) -> dict:
        merged_text = excerpt if not promotion_note else f"{excerpt}\n\nMy note:\n{promotion_note}"
        created = self.capture_memory(
            text_value=merged_text,
            memory_type="reference",
            source_surface="promoted_external",
            tags=["promoted-external"],
            topics=[],
            people=[],
        )

        with SessionLocal() as db:
            db.add(
                ExternalPromotion(
                    local_memory_id=uuid.UUID(created["id"]),
                    external_source=source_namespace,
                    external_title=title,
                    external_uri=uri,
                    external_excerpt=excerpt,
                    promotion_note=promotion_note,
                )
            )
            db.commit()

        self._audit("promote_external_result", {"local_memory_id": created["id"], "source_namespace": source_namespace})
        return created

    def health(self) -> dict:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"ok": True, "service": "openbrain-gateway"}

    def source_status(self) -> dict:
        return {
            "local": {"ok": True, "database": settings.database_url.split("@")[-1]},
            "brian_repo": self.brian_repo.status() if self.brian_repo else {"enabled": False},
            "brian_mcp": self.brian_mcp.status() if self.brian_mcp else {"enabled": False},
        }

