from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DisciplineProfile:
    name: str
    terms: tuple[str, ...]
    venue_hints: tuple[str, ...]


DISCIPLINE_PROFILES: tuple[DisciplineProfile, ...] = (
    DisciplineProfile(
        name="management",
        terms=(
            "strategic management",
            "organizational behavior",
            "organizational theory",
            "leadership",
            "human resource management",
            "innovation management",
        ),
        venue_hints=(
            "academy of management journal",
            "academy of management review",
            "strategic management journal",
            "organization science",
            "journal of management studies",
        ),
    ),
    DisciplineProfile(
        name="organization_science",
        terms=(
            "organizational routines",
            "institutional theory",
            "sensemaking",
            "practice theory",
            "organizational learning",
        ),
        venue_hints=(
            "organization science",
            "administrative science quarterly",
            "organization studies",
            "research in the sociology of organizations",
        ),
    ),
    DisciplineProfile(
        name="economics",
        terms=(
            "industrial organization",
            "contract theory",
            "labor economics",
            "applied microeconomics",
            "organizational economics",
        ),
        venue_hints=(
            "american economic review",
            "quarterly journal of economics",
            "journal of political economy",
            "review of economic studies",
            "rand journal of economics",
        ),
    ),
    DisciplineProfile(
        name="information_systems",
        terms=(
            "information systems",
            "digital platform",
            "it capability",
            "digital transformation",
            "it governance",
            "analytics capability",
        ),
        venue_hints=(
            "mis quarterly",
            "information systems research",
            "journal of management information systems",
            "european journal of information systems",
        ),
    ),
    DisciplineProfile(
        name="operations_management",
        terms=(
            "operations management",
            "supply chain management",
            "process improvement",
            "service operations",
            "production and operations",
            "queuing",
        ),
        venue_hints=(
            "management science",
            "manufacturing & service operations management",
            "production and operations management",
            "journal of operations management",
        ),
    ),
)


def coverage_anchor_terms(topic: str, description: str, domain_terms: list[str]) -> list[str]:
    merged: list[str] = []
    raw = [topic, description] + domain_terms
    for profile in DISCIPLINE_PROFILES:
        raw.extend(profile.terms)
    for chunk in raw:
        text = chunk.lower().strip()
        if len(text) < 3:
            continue
        if text not in merged:
            merged.append(text)
    return merged[:80]


def query_variants(topic: str, domain_name: str, domain_terms: list[str]) -> list[str]:
    base_terms = [topic, domain_name] + domain_terms[:6]
    variants: list[str] = []
    for profile in DISCIPLINE_PROFILES:
        seed = " ".join(base_terms + list(profile.terms[:2])).strip()
        if seed and seed not in variants:
            variants.append(seed)
    short = " ".join(base_terms).strip()
    if short and short not in variants:
        variants.insert(0, short)
    return variants[:8]


def venue_boost(venue: str | None) -> float:
    if not venue:
        return 0.0
    v = venue.lower()
    for profile in DISCIPLINE_PROFILES:
        for hint in profile.venue_hints:
            if hint in v:
                return 0.6
    return 0.0
