#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

from bib_validator import extract_fields, split_entries

VALIDATED_FIELDS = {"journal", "booktitle", "volume", "number", "pages", "publisher", "year", "doi"}


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def normalize_doi(value: str) -> str:
    doi = normalize_text(value)
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:", "doi.org/"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi


def normalize_pages(value: str) -> str:
    return re.sub(r"\s*[-–—]+\s*", "-", value.strip())


def load_json_index(json_dir: Path) -> dict[str, set[str]]:
    index = {
        "journal": set(),
        "booktitle": set(),
        "volume": set(),
        "number": set(),
        "pages": set(),
        "publisher": set(),
        "year": set(),
        "doi": set(),
    }

    def ingest_dict(obj: dict[str, Any]) -> None:
        for key in ("journal", "booktitle", "container_title", "venue"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                index["journal"].add(normalize_text(val))
        source = obj.get("source")
        if isinstance(source, dict):
            source_name = source.get("name")
            if isinstance(source_name, str) and source_name.strip():
                index["journal"].add(normalize_text(source_name))
        volume = obj.get("volume")
        if volume is not None:
            index["volume"].add(str(volume).strip())
        issue = obj.get("issue", obj.get("number"))
        if issue is not None:
            index["number"].add(str(issue).strip())
        pages = obj.get("pages", obj.get("page"))
        if isinstance(pages, str) and pages.strip():
            index["pages"].add(normalize_pages(pages))
        publisher = obj.get("publisher")
        if isinstance(publisher, str) and publisher.strip():
            index["publisher"].add(normalize_text(publisher))
        year = obj.get("year", obj.get("publication_year"))
        if year is not None:
            index["year"].add(str(year).strip())
        doi = obj.get("doi")
        if isinstance(doi, str) and doi.strip():
            index["doi"].add(normalize_doi(doi))

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            ingest_dict(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for file in sorted(json_dir.glob("*.json")):
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            continue
        walk(payload)
    index["booktitle"] = set(index["journal"])
    return index


def validate_bib_file(bib_file: Path, json_dir: Path) -> dict[str, object]:
    try:
        content = bib_file.read_text(encoding="utf-8")
    except Exception as exc:
        return {"valid": False, "errors": [f"cannot read {bib_file}: {exc}"]}

    index = load_json_index(json_dir)
    errors: list[str] = []
    for entry in split_entries(content):
        fields = extract_fields(entry.body)
        for field, raw_value in fields.items():
            if field not in VALIDATED_FIELDS:
                continue
            if not raw_value:
                continue
            value = raw_value.strip()
            match field:
                case "journal" | "booktitle":
                    ok = normalize_text(value) in index["journal"]
                case "volume":
                    ok = value in index["volume"]
                case "number":
                    ok = value in index["number"]
                case "pages":
                    ok = normalize_pages(value) in index["pages"]
                case "publisher":
                    ok = normalize_text(value) in index["publisher"]
                case "year":
                    ok = value in index["year"]
                case "doi":
                    ok = normalize_doi(value) in index["doi"]
                case _:
                    ok = True
            if not ok:
                errors.append(f"{entry.key}: field '{field}' not found in JSON evidence")
    return {"valid": not errors, "errors": errors}


def main() -> int:
    if len(sys.argv) != 3:
        print(
            json.dumps(
                {"valid": False, "errors": ["usage: metadata_validator.py <bib_file> <json_dir>"]}
            )
        )
        return 2
    result = validate_bib_file(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
