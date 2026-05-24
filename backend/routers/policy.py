import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from data import get_policies
from models import PolicyListResponse, PolicyResponse, SimilarPolicy
from similarity import derive_innovation_stage, find_similar

router = APIRouter()


def _filter_policies(
    items: list,
    *,
    department: Optional[str] = None,
    country: Optional[str] = None,
    level: Optional[str] = None,
    innovation_stage: Optional[str] = None,
    tech_id: Optional[str] = None,
    industry_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list:
    result = items
    if department and department != "all":
        result = [p for p in result if p.get("department") == department]
    if country and country != "all":
        result = [p for p in result if p.get("country") == country]
    if level and level != "all":
        result = [p for p in result if p.get("level") == level]
    if innovation_stage and innovation_stage != "all":
        result = [p for p in result if derive_innovation_stage(p) == innovation_stage]
    if tech_id:
        result = [p for p in result if tech_id in p.get("relatedTechnologies", [])]
    if industry_id:
        result = [p for p in result if industry_id in p.get("relatedIndustries", [])]
    if date_from:
        result = [p for p in result if p.get("date", "") >= date_from]
    if date_to:
        result = [p for p in result if p.get("date", "") <= date_to]
    return result


@router.get("/policies", response_model=PolicyListResponse)
def list_policies(
    department: Optional[str] = None,
    country: Optional[str] = None,
    level: Optional[str] = None,
    innovation_stage: Optional[str] = None,
    tech_id: Optional[str] = None,
    industry_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort_by: str = "date",
    sort_order: str = "desc",
) -> dict:
    items = _filter_policies(
        get_policies(),
        department=department,
        country=country,
        level=level,
        innovation_stage=innovation_stage,
        tech_id=tech_id,
        industry_id=industry_id,
        date_from=date_from,
        date_to=date_to,
    )

    reverse = sort_order == "desc"
    items.sort(key=lambda p: p.get(sort_by, ""), reverse=reverse)

    total = len(items)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    page_items = items[start : start + page_size]

    return {
        "policies": [PolicyResponse(**p) for p in page_items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(policy_id: str) -> dict:
    for p in get_policies():
        if p.get("id") == policy_id:
            return PolicyResponse(**p)
    raise HTTPException(status_code=404, detail="policy not found")


@router.get("/policies/{policy_id}/similar", response_model=list[SimilarPolicy])
def similar_policies(
    policy_id: str,
    top_n: int = Query(default=5, ge=1, le=20),
    min_score: float = Query(default=0.1, ge=0.0, le=1.0),
) -> list:
    target = None
    all_policies = get_policies()
    for p in all_policies:
        if p.get("id") == policy_id:
            target = p
            break
    if target is None:
        raise HTTPException(status_code=404, detail="policy not found")

    results = find_similar(target, all_policies, top_n=top_n, min_score=min_score)
    return [
        {"policy": PolicyResponse(**p), "score": s}
        for p, s in results
    ]
