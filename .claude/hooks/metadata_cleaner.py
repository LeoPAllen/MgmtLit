#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from bib_validator import extract_fields, split_entries
from metadata_validator import (
    VALIDATED_FIELDS,
    load_json_index,
    normalize_doi,
    normalize_pages,
    normalize_text,
)


def _is_verified(field: str, value: str, index: dict[str, set[str]]) -> bool:
    if field in {"journal", "booktitle"}:
        return normalize_text(value) in index["journal"]
    if field == "volume":
        return value in index["volume"]
    if field == "number":
        return value in index["number"]
    if field == "pages":
        return normalize_pages(value) in index["pages"]
    if field == "publisher":
        return normalize_text(value) in index["publisher"]
    if field == "year":
        return value in index["year"]
    if field == "doi":
        return normalize_doi(value) in index["doi"]
    return True


def _render_field(name: str, value: str) -> str:
    return f"  {name} = {{{value}}},"


def clean_bib_file(bib_file: Path, json_dir: Path) -> dict[str, Any]:
    content = bib_file.read_text(encoding="utf-8")
    index = load_json_index(json_dir)

    cleaned_entries: list[str] = []
    removed_by_key: dict[str, list[str]] = {}
    output: list[str] = []
    for entry in split_entries(content):
        fields = extract_fields(entry.body)
        kept: dict[str, str] = {}
        removed: list[str] = []
        for name, value in fields.items():
            value = value.strip()
            if name not in VALIDATED_FIELDS:
                kept[name] = value
                continue
            if _is_verified(name, value, index):
                kept[name] = value
            else:
                removed.append(name)

        entry_type = entry.entry_type
        if entry_type in {"article", "incollection", "inproceedings", "book"}:
            required = {
                "article": ["journal"],
                "incollection": ["booktitle"],
                "inproceedings": ["booktitle"],
                "book": ["publisher"],
            }[entry_type]
            if any(req not in kept for req in required):
                entry_type = "misc"
                kept.pop("journal", None)
                kept.pop("booktitle", None)
                kept.pop("publisher", None)
                if "howpublished" not in kept and "url" not in kept:
                    kept["howpublished"] = "Metadata-cleaned source"
                if "type_downgrade" not in removed:
                    removed.append("type_downgrade")

        if removed:
            keywords = kept.get("keywords", "")
            if "METADATA_CLEANED" not in keywords:
                kept["keywords"] = (keywords + ", METADATA_CLEANED").strip(", ").strip()
            cleaned_entries.append(entry.key)
            removed_by_key[entry.key] = removed

        preferred_order = [
            "author",
            "title",
            "journal",
            "booktitle",
            "publisher",
            "year",
            "volume",
            "number",
            "pages",
            "doi",
            "url",
            "howpublished",
            "abstract",
            "keywords",
            "note",
        ]
        ordered = [k for k in preferred_order if k in kept] + [k for k in kept if k not in preferred_order]
        output.append(f"@{entry_type}{{{entry.key},")
        output.extend(_render_field(name, kept[name]) for name in ordered)
        output.append("}")
        output.append("")

    if cleaned_entries:
        bib_file.write_text("\n".join(output).strip() + "\n", encoding="utf-8")
    return {
        "cleaned": bool(cleaned_entries),
        "entries_cleaned": len(cleaned_entries),
        "total_fields_removed": sum(len(v) for v in removed_by_key.values()),
        "cleaned_entries": removed_by_key,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            json.dumps(
                {"cleaned": False, "error": "usage: metadata_cleaner.py <bib_file> <json_dir>"}
            )
        )
        return 2
    try:
        result = clean_bib_file(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as exc:
        print(json.dumps({"cleaned": False, "error": str(exc)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
