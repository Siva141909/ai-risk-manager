"""Phase 4K — policy corpus loading and section-level chunking.

Chunks are aligned to markdown `##` section headings, not arbitrary
fixed-length splits — matches the design doc's Section 17 rationale
(policy documents have meaningful structural boundaries). Every chunk
carries `applies_to_pattern` metadata parsed from an
`applies_to_pattern: <value>` line directly under the heading, so
retrieval can be pattern-filtered as well as similarity-ranked.

Every document in docs/policy_documents/ is DEMO/SYNTHETIC content
authored for this project — never a real Razorpay policy. This module
does not change that content, only parses it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SECTION_RE = re.compile(r"^## Section (\d+): (.+)$", re.MULTILINE)
_APPLIES_TO_RE = re.compile(r"^applies_to_pattern:\s*(\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class PolicyChunkRecord:
    doc_id: str
    section_id: str
    title: str
    text: str
    applies_to_pattern: str


def _doc_id_from_filename(path: Path) -> str:
    # "02_shared_infrastructure_handling.md" -> "shared-infrastructure-handling"
    stem = path.stem
    parts = stem.split("_")[1:] if stem[0].isdigit() else stem.split("_")
    return "-".join(parts)


def load_policy_corpus(policy_dir: Path) -> list[PolicyChunkRecord]:
    chunks: list[PolicyChunkRecord] = []
    for path in sorted(policy_dir.glob("*.md")):
        text = path.read_text()
        doc_id = _doc_id_from_filename(path)

        headings = list(_SECTION_RE.finditer(text))
        for i, match in enumerate(headings):
            section_num, title = match.group(1), match.group(2)
            start = match.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[start:end].strip()

            applies_match = _APPLIES_TO_RE.search(body)
            applies_to = applies_match.group(1) if applies_match else "general"
            body_clean = _APPLIES_TO_RE.sub("", body).strip()

            chunks.append(
                PolicyChunkRecord(
                    doc_id=doc_id,
                    section_id=f"{section_num}",
                    title=title,
                    text=body_clean,
                    applies_to_pattern=applies_to,
                )
            )
    return chunks
