import json
import typer
import httpx

from openbrain.config import settings

app = typer.Typer(help="CLI bridge for OpenClaw -> OpenBrain Gateway")


def base_url() -> str:
    return f"http://{settings.host}:{settings.port}"


@app.command()
def capture(
    text: str,
    memory_type: str = "note",
    source_surface: str = "telegram_openclaw",
    source_session_id: str = "",
    project: str = "",
):
    payload = {
        "text": text,
        "memory_type": memory_type,
        "source_surface": source_surface,
        "source_session_id": source_session_id or None,
        "project": project or None,
        "tags": [],
        "topics": [],
        "people": [],
    }
    r = httpx.post(f"{base_url()}/memories/capture", json=payload, timeout=30)
    r.raise_for_status()
    typer.echo(r.text)


@app.command()
def search(query: str, k: int = 5):
    r = httpx.post(f"{base_url()}/search/local", json={"query": query, "k": k}, timeout=30)
    r.raise_for_status()
    typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def brian(query: str, k: int = 5):
    r = httpx.post(f"{base_url()}/search/brian", json={"query": query, "k": k}, timeout=30)
    r.raise_for_status()
    typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def federated(query: str, k: int = 5):
    r = httpx.post(f"{base_url()}/search/federated", json={"query": query, "k": k}, timeout=30)
    r.raise_for_status()
    typer.echo(json.dumps(r.json(), indent=2))


@app.command()
def promote(
    source_namespace: str,
    title: str,
    excerpt: str,
    uri: str = "",
    promotion_note: str = "",
):
    payload = {
        "source_namespace": source_namespace,
        "title": title,
        "excerpt": excerpt,
        "uri": uri or None,
        "promotion_note": promotion_note or None,
    }
    r = httpx.post(f"{base_url()}/external/promote", json=payload, timeout=30)
    r.raise_for_status()
    typer.echo(r.text)

