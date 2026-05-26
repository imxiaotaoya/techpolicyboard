"""Multi-factor weighted similarity for policy recommendation.

Uses only the standard library — no embedding model or vector DB needed.
"""

import re

STAGE_ORDER = ["basic-research", "applied-rd", "pilot", "commercialization"]

RELATED_DEPTS: dict[str, set[str]] = {
    # Chinese departments
    "MoST": {"MIIT", "NDRC"},
    "MIIT": {"MoST", "NDRC"},
    "NDRC": {"MIIT", "MoST"},
    "StateCouncil": {"NDRC", "MoST", "MIIT"},
    # US departments
    "White House": {"OMB", "OSTP", "NIST"},
    "OMB": {"White House", "OSTP"},
    "OSTP": {"White House", "OMB", "NSF", "DOE"},
    "US Congress": {"GAO", "CRS"},
    "DoD": {"DARPA", "US Congress"},
    "DOE": {"OSTP", "NSF", "NIST"},
    "NSF": {"OSTP", "DOE", "NIST"},
    "NIH": {"NSF", "HHS"},
    "NIST": {"White House", "OMB"},
    "SEC": {"FTC", "CFTC"},
    "FTC": {"SEC", "DOJ"},
    "FCC": {"FTC", "NTIA"},
    # EU bodies
    "European Commission": {"European Parliament", "Council of the EU"},
    "European Parliament": {"European Commission", "Council of the EU"},
    "Council of the EU": {"European Commission", "European Parliament"},
    # All external/international
    "International": {"European Commission", "US Congress", "StateCouncil"},
}

WEIGHTS = {
    "tech_overlap": 0.35,
    "industry_overlap": 0.25,
    "department_match": 0.15,
    "level_match": 0.10,
    "country_match": 0.10,
    "stage_proximity": 0.05,
}


def derive_innovation_stage(policy: dict) -> str:
    """Mirrors the frontend deriveInnovationStage() in constants.ts."""
    text = f"{policy.get('title', '')}{policy.get('summary', '')}"
    if re.search(r"(基础|前沿|基础研究|科学问题|原理)", text):
        return "basic-research"
    if re.search(r"(示范|试点|pilot|首台|验证)", text):
        return "pilot"
    if re.search(r"(产业化|量产|商业|市场|落地|商业化|商用)", text):
        return "commercialization"
    dept = policy.get("department", "")
    if dept == "MoST":
        return "basic-research"
    if dept == "MIIT":
        return "applied-rd"
    if dept == "NDRC":
        return "commercialization"
    if dept == "International":
        return "applied-rd"
    return "applied-rd"


def _jaccard(a: list[str], b: list[str]) -> float:
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _department_score(dept_a: str, dept_b: str) -> float:
    if dept_a == dept_b:
        return 1.0
    related = RELATED_DEPTS.get(dept_a, set())
    if dept_b in related:
        return 0.5
    return 0.0


def _stage_proximity(stage_a: str, stage_b: str) -> float:
    if stage_a == stage_b:
        return 1.0
    try:
        idx_a = STAGE_ORDER.index(stage_a)
        idx_b = STAGE_ORDER.index(stage_b)
        if abs(idx_a - idx_b) == 1:
            return 0.5
    except ValueError:
        pass
    return 0.0


def compute_similarity(policy_a: dict, policy_b: dict) -> float:
    tech_jaccard = _jaccard(
        policy_a.get("relatedTechnologies", []),
        policy_b.get("relatedTechnologies", []),
    )
    industry_jaccard = _jaccard(
        policy_a.get("relatedIndustries", []),
        policy_b.get("relatedIndustries", []),
    )
    dept_score = _department_score(
        policy_a.get("department", ""),
        policy_b.get("department", ""),
    )
    level_score = 1.0 if policy_a.get("level") == policy_b.get("level") else 0.0
    country_score = 1.0 if policy_a.get("country") == policy_b.get("country") else 0.0
    stage_score = _stage_proximity(
        derive_innovation_stage(policy_a),
        derive_innovation_stage(policy_b),
    )

    return (
        WEIGHTS["tech_overlap"] * tech_jaccard
        + WEIGHTS["industry_overlap"] * industry_jaccard
        + WEIGHTS["department_match"] * dept_score
        + WEIGHTS["level_match"] * level_score
        + WEIGHTS["country_match"] * country_score
        + WEIGHTS["stage_proximity"] * stage_score
    )


def find_similar(
    target: dict,
    candidates: list[dict],
    top_n: int = 5,
    min_score: float = 0.1,
) -> list[tuple[dict, float]]:
    scored = []
    target_id = target.get("id")
    for c in candidates:
        if c.get("id") == target_id:
            continue
        s = compute_similarity(target, c)
        if s >= min_score:
            scored.append((c, round(s, 4)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]
