from pathlib import Path
from datetime import datetime
import frontmatter
from slugify import slugify


def write_archive(base_dir: str, record: dict) -> str:
    captured: datetime = record["captured_at"]
    title_slug = slugify(record["title"])[:80] or "memory"
    day_dir = Path(base_dir) / f"{captured:%Y}" / f"{captured:%m}" / f"{captured:%d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / f"{title_slug}-{record['id']}.md"

    post = frontmatter.Post(
        content=record["cleaned_text"],
        **{
            "id": str(record["id"]),
            "title": record["title"],
            "summary": record["summary"],
            "memory_type": record["memory_type"],
            "source_surface": record["source_surface"],
            "source_session_id": record.get("source_session_id"),
            "project": record.get("project"),
            "people": record.get("people", []),
            "topics": record.get("topics", []),
            "tags": record.get("tags", []),
            "action_items": record.get("action_items", []),
            "importance": record.get("importance", 3),
            "sensitivity": record.get("sensitivity", "normal"),
            "provenance_type": record.get("provenance_type", "local"),
            "provenance_ref": record.get("provenance_ref"),
            "captured_at": captured.isoformat(),
        },
    )

    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return str(path)

