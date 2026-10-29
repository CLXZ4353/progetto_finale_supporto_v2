# -*- coding: utf-8 -*-
"""RAG leggero sul corpus di policy.

Dieci documenti Markdown, chunking per sezione e retrieval BM25 in Python.
Niente embedding: per un corpus così piccolo il retrieval lessicale è
sufficiente, azzera le dipendenze e rende il progetto riproducibile (la
stessa scelta è documentata nel Laboratorio 8).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi

from .config import CORPUS_DIR, Settings, get_settings

# Espansioni lessicali per le domande frequenti in italiano.
_SYNONYMS = {
    "traccio": ["tracking", "tracciamento", "spedizione"],
    "tracciare": ["tracking", "tracciamento"],
    "traccia": ["tracking", "tracciamento"],
    "tracking": ["tracciamento", "spedizione"],
    "rimborso": ["rimborsare", "restituzione"],
    "rimborsare": ["rimborso", "restituzione"],
    "reso": ["restituzione", "restituire"],
    "resi": ["restituzione", "restituire"],
    "restituire": ["reso", "restituzione"],
    "annullamento": ["annullare", "annullato", "rimborso"],
    "annullare": ["annullamento", "annullato", "rimborso"],
    "annullato": ["annullamento", "annullare", "rimborso"],
    "cancellare": ["annullare", "annullamento"],
    "disdire": ["annullare", "annullamento"],
    "restituirlo": ["reso", "restituzione", "restituire"],
    "restituirla": ["reso", "restituzione", "restituire"],
    "personalizzato": ["personalizzati", "personalizzata", "personalizzate"],
    "personalizzata": ["personalizzato", "personalizzati", "personalizzate"],
    "personalizzati": ["personalizzato", "personalizzata", "personalizzate"],
    "difettoso": ["difetto", "difettosa", "difettosi"],
    "difettosa": ["difetto", "difettoso", "difettosi"],
    "spedizione": ["consegna", "corriere", "spedizioni"],
    "spedizioni": ["spedizione", "consegna", "corriere"],
    "consegna": ["spedizione", "corriere"],
    "garanzia": ["difetto", "difettoso"],
    "pagamento": ["carta", "paypal"],
}


def _title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def load_corpus(corpus_dir: Path | None = None) -> list[Document]:
    folder = Path(corpus_dir or CORPUS_DIR)
    docs: list[Document] = []
    for path in sorted(folder.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append(
            Document(
                page_content=text,
                metadata={"source": path.name, "title": _title(text) or path.stem},
            )
        )
    if not docs:
        raise FileNotFoundError(f"Nessun documento .md in {folder}")
    return docs


def split_documents(
    documents: Iterable[Document],
    chunk_size: int = 650,
    chunk_overlap: int = 50,
) -> list[Document]:
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "titolo"), ("##", "sezione"), ("###", "sottosezione")],
        strip_headers=False,
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks: list[Document] = []
    for doc in documents:
        sections = header_splitter.split_text(doc.page_content)
        if not sections:
            sections = [Document(page_content=doc.page_content, metadata={})]
        source = doc.metadata.get("source", "documento")
        index = 0
        for section in sections:
            meta = {
                **doc.metadata,
                **{k: v for k, v in section.metadata.items() if v},
                "source": source,
            }
            section_doc = Document(page_content=section.page_content, metadata=meta)
            for piece in text_splitter.split_documents([section_doc]):
                index += 1
                piece.metadata["chunk_id"] = f"{source}#{index}"
                piece.metadata["source"] = source
                chunks.append(piece)
    return chunks


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-zàèéìòù0-9]+", text.lower())
    return [word for word in words if len(word) > 1]


def _query_tokens(query: str) -> list[str]:
    tokens = _tokens(query)
    for token in list(tokens):
        tokens.extend(_SYNONYMS.get(token, []))
    return tokens


def _index(settings: Settings) -> tuple[BM25Okapi, list[Document]]:
    chunks = split_documents(
        load_corpus(), settings.chunk_size, settings.chunk_overlap
    )
    return BM25Okapi([_tokens(doc.page_content) for doc in chunks]), chunks


def retrieve(
    query: str,
    *,
    k: int | None = None,
    settings: Settings | None = None,
) -> list[Document]:
    settings = settings or get_settings()
    index, chunks = _index(settings)
    scores = index.get_scores(_query_tokens(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    limit = k or settings.top_k
    return [chunks[i] for i in ranked[:limit] if scores[i] > 0]


def format_context(documents: list[Document]) -> str:
    lines: list[str] = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "?")
        section = doc.metadata.get("sezione", "")
        header = f"[S{i}] {source}" + (f" - {section}" if section else "")
        lines.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n".join(lines)


def source_payload(documents: list[Document]) -> list[dict]:
    payload = []
    for i, doc in enumerate(documents, start=1):
        payload.append(
            {
                "id": f"S{i}",
                "source": doc.metadata.get("source", "?"),
                "chunk_id": doc.metadata.get("chunk_id", ""),
                "section": doc.metadata.get("sezione", ""),
                "snippet": re.sub(r"\s+", " ", doc.page_content).strip()[:280],
            }
        )
    return payload


def corpus_stats() -> dict:
    docs = load_corpus()
    chunks = split_documents(docs)
    lengths = [len(chunk.page_content) for chunk in chunks]
    return {
        "documenti": len(docs),
        "chunk": len(chunks),
        "caratteri_totali": sum(len(doc.page_content) for doc in docs),
        "chunk_min": min(lengths) if lengths else 0,
        "chunk_max": max(lengths) if lengths else 0,
        "chunk_media": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
    }
