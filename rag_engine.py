"""Small, auditable RAG layer built on Chroma."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "knowledge.jsonl"


def _load_records() -> list[dict[str, Any]]:
    records = []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _build_collection():
    # In-memory client keeps deployment simple. The corpus is tiny and rebuilt on startup.
    client = chromadb.Client()
    collection = client.get_or_create_collection(name="autosage_knowledge")
    if collection.count() == 0:
        records = _load_records()
        collection.add(
            ids=[r["id"] for r in records],
            documents=[r["text"] for r in records],
            metadatas=[{
                "vehicle_type": r["vehicle_type"],
                "topic": r["topic"],
                "title": r["title"],
                "source_name": r["source_name"],
                "source_url": r["source_url"],
            } for r in records],
        )
    return collection


def retrieve(query: str, vehicle_type: str, n_results: int = 5) -> list[dict[str, Any]]:
    collection = _build_collection()
    where = {"$or": [{"vehicle_type": vehicle_type}, {"vehicle_type": "both"}]}
    result = collection.query(
        query_texts=[query],
        n_results=min(n_results, max(1, collection.count())),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    docs: list[dict[str, Any]] = []
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    for document, metadata, distance in zip(documents, metadatas, distances):
        docs.append({
            "text": document,
            "metadata": metadata or {},
            "distance": float(distance),
        })
    return docs
