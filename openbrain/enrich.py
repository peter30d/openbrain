from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter
import re
from typing import Iterable

from slugify import slugify


STOPWORDS = {
    "about", "after", "again", "also", "always", "and", "any", "are", "because",
    "been", "before", "being", "between", "both", "but", "call", "could", "days",
    "each", "even", "every", "from", "have", "here", "into", "just", "kind",
    "know", "last", "like", "made", "make", "maybe", "more", "most", "much",
    "must", "need", "next", "note", "notes", "only", "other", "over", "really",
    "same", "should", "since", "some", "such", "than", "that", "them", "then",
    "there", "these", "they", "this", "those", "through", "today", "told",
    "tomorrow", "want", "week", "what", "when", "where", "which", "while",
    "with", "work", "would", "your", "yesterday", "system", "architecture",
    "project", "memory", "openbrain", "openclaw",
}

MEMORY_TYPE_PATTERNS: dict[str, list[str]] = {
    "decision": [
        r"\bdecided\b",
        r"\bdecision\b",
        r"\bwe chose\b",
        r"\bI chose\b",
        r"\bapproved\b",
        r"\bsettled on\b",
    ],
    "preference": [
        r"\bprefer\b",
        r"\bI like\b",
        r"\bI don't like\b",
        r"\bmy preference\b",
        r"\bI'd rather\b",
        r"\bI want\b",
    ],
    "meeting": [
        r"\bmeeting\b",
        r"\bcall\b",
        r"\bstandup\b",
        r"\b1:1\b",
        r"\bdiscussion\b",
        r"\bspoke with\b",
        r"\btalked with\b",
    ],
    "task": [
        r"\btodo\b",
        r"\bto do\b",
        r"\bneed to\b",
        r"\bmust\b",
        r"\bshould\b",
        r"\baction item\b",
        r"\bfollow up\b",
        r"\bnext step\b",
        r"\bremember to\b",
    ],
    "project": [
        r"\bproject\b",
        r"\bmilestone\b",
        r"\broadmap\b",
        r"\bdeliverable\b",
        r"\bimplementation\b",
        r"\brelease plan\b",
    ],
    "insight": [
        r"\binsight\b",
        r"\bI realized\b",
        r"\blearned that\b",
        r"\bpattern\b",
        r"\bkey takeaway\b",
    ],
    "reference": [
        r"\barticle\b",
        r"\bblog\b",
        r"\bvideo\b",
        r"\bpaper\b",
        r"\bpodcast\b",
        r"\btranscript\b",
        r"https?://",
    ],
    "person": [
        r"\bmet with\b",
        r"\btalked to\b",
        r"\bspoke to\b",
        r"\bSarah\b",  # harmless; people extraction still drives most cases
    ],
}

HIGH_SENSITIVITY_PATTERNS = [
    r"\bpassword\b",
    r"\bsecret\b",
    r"\bapi key\b",
    r"\bprivate key\b",
    r"\bcredential\b",
    r"\btoken\b",
    r"\bbank\b",
    r"\btax\b",
    r"\bpassport\b",
    r"\bmedical\b",
    r"\bssn\b",
]

ELEVATED_SENSITIVITY_PATTERNS = [
    r"\bclient\b",
    r"\bcustomer\b",
    r"\bconfidential\b",
    r"\bnda\b",
    r"\binternal\b",
    r"\bpersonal\b",
    r"\bsalary\b",
]

TITLE_PREFIX = {
    "decision": "Decision",
    "preference": "Preference",
    "meeting": "Meeting note",
    "task": "Task",
    "project": "Project note",
    "insight": "Insight",
    "reference": "Reference",
    "person": "People note",
    "note": "Note",
}


@dataclass
class EnrichmentResult:
    title: str
    summary: str
    memory_type: str
    project: str | None = None
    people: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    importance: int = 3
    sensitivity: str = "normal"


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = item.strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text.replace("\n", " ").strip())
    return [c.strip() for c in chunks if c.strip()]


def _clip(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


class MemoryEnricher:
    def enrich(
        self,
        raw_text: str,
        requested_memory_type: str | None = None,
        requested_project: str | None = None,
        requested_tags: list[str] | None = None,
        requested_topics: list[str] | None = None,
        requested_people: list[str] | None = None,
    ) -> EnrichmentResult:
        text = _normalize_text(raw_text)
        cleaned_text = " ".join(line.strip() for line in text.splitlines() if line.strip())

        inferred_type = self._infer_memory_type(cleaned_text)
        memory_type = (
            requested_memory_type
            if requested_memory_type and requested_memory_type != "note"
            else inferred_type
        )

        people = requested_people or self._extract_people(text)
        project = requested_project or self._extract_project(text)
        action_items = self._extract_action_items(text)
        topics = requested_topics or self._extract_topics(cleaned_text, people=people, project=project)
        tags = requested_tags or self._build_tags(memory_type, topics, project, text)
        summary = self._build_summary(cleaned_text, action_items)
        title = self._build_title(cleaned_text, memory_type)
        importance = self._score_importance(memory_type, cleaned_text, action_items)
        sensitivity = self._score_sensitivity(cleaned_text)

        return EnrichmentResult(
            title=title,
            summary=summary,
            memory_type=memory_type,
            project=project,
            people=people,
            topics=topics,
            tags=tags,
            action_items=action_items,
            importance=importance,
            sensitivity=sensitivity,
        )

    def _infer_memory_type(self, text: str) -> str:
        scored: dict[str, int] = {}
        for memory_type, patterns in MEMORY_TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    score += 1
            if score:
                scored[memory_type] = score

        if not scored:
            return "note"

        if "task" in scored and scored["task"] >= 1:
            return "task"
        if "decision" in scored and scored["decision"] >= 1:
            return "decision"
        if "preference" in scored and scored["preference"] >= 1:
            return "preference"

        return sorted(scored.items(), key=lambda x: (-x[1], x[0]))[0][0]

    def _extract_people(self, text: str) -> list[str]:
        people: list[str] = []

        mentions = re.findall(r"@([A-Za-z0-9_.-]+)", text)
        people.extend(mentions)

        relation_patterns = [
            r"(?:with|to|from|about|for|cc|met with|talked to|spoke to|discussed with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
            r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b",
        ]
        for pattern in relation_patterns:
            people.extend(re.findall(pattern, text))

        # filter obvious non-people
        bad = {"OpenBrain", "OpenClaw", "Telegram", "Ubuntu", "Brian Madden"}
        people = [p for p in people if p not in bad]

        return _dedupe(people)[:8]

    def _extract_project(self, text: str) -> str | None:
        patterns = [
            r"\bproject\s+([A-Za-z0-9][A-Za-z0-9 _-]{1,40})",
            r"\bfor\s+([A-Za-z0-9][A-Za-z0-9 _-]{1,40})\s+project\b",
            r"\bon\s+([A-Za-z0-9][A-Za-z0-9 _-]{1,40})\s+project\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip(" .,:;!-")
                value = re.sub(r"\s+", " ", value)
                return value[:60]
        return None

    def _extract_action_items(self, text: str) -> list[str]:
        items: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if re.match(r"^[-*]\s+", stripped):
                items.append(re.sub(r"^[-*]\s+", "", stripped))
                continue

            if re.match(r"^\[\s?[xX ]\]\s+", stripped):
                items.append(re.sub(r"^\[\s?[xX ]\]\s+", "", stripped))
                continue

        for sentence in _sentences(text):
            if re.search(
                r"\b(need to|must|should|follow up|next step|todo|remember to|action item)\b",
                sentence,
                flags=re.IGNORECASE,
            ):
                items.append(sentence)

        return _dedupe(items)[:8]

    def _extract_topics(self, text: str, people: list[str], project: str | None) -> list[str]:
        hashtags = re.findall(r"#([A-Za-z0-9_-]+)", text)
        tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{3,}\b", text.lower())

        excluded = {p.lower() for p in people}
        if project:
            excluded.update(project.lower().split())

        counts = Counter(
            token for token in tokens
            if token not in STOPWORDS and token not in excluded and not token.isdigit()
        )

        keywords = [word for word, _ in counts.most_common(6)]
        topics = hashtags + keywords
        return _dedupe(topics)[:6]

    def _build_tags(self, memory_type: str, topics: list[str], project: str | None, text: str) -> list[str]:
        hashtags = [slugify(h) for h in re.findall(r"#([A-Za-z0-9_-]+)", text)]
        tags = [slugify(memory_type)]
        tags.extend(hashtags)
        tags.extend(slugify(t) for t in topics[:4])
        if project:
            tags.append(f"project-{slugify(project)}")
        return _dedupe(tags)[:8]

    def _build_summary(self, text: str, action_items: list[str]) -> str:
        sents = _sentences(text)
        if not sents:
            return _clip(text, 240)

        summary = " ".join(sents[:2])
        if action_items and "action" not in summary.lower():
            summary = f"{summary} Action items: {action_items[0]}"
        return _clip(summary, 280)

    def _build_title(self, text: str, memory_type: str) -> str:
        first = _sentences(text)[0] if _sentences(text) else text
        prefix = TITLE_PREFIX.get(memory_type, "Note")
        body = _clip(first, 72)
        return f"{prefix}: {body}"

    def _score_importance(self, memory_type: str, text: str, action_items: list[str]) -> int:
        base = {
            "decision": 4,
            "preference": 4,
            "task": 4,
            "project": 4,
            "insight": 4,
            "meeting": 3,
            "person": 3,
            "reference": 2,
            "note": 3,
        }.get(memory_type, 3)

        boosts = 0
        if action_items:
            boosts += 1
        if re.search(r"\b(important|critical|key|must|never forget|remember this)\b", text, flags=re.IGNORECASE):
            boosts += 1

        return max(1, min(5, base + boosts))

    def _score_sensitivity(self, text: str) -> str:
        for pattern in HIGH_SENSITIVITY_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return "high"

        for pattern in ELEVATED_SENSITIVITY_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return "elevated"

        return "normal"

