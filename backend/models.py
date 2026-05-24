from typing import Optional

from pydantic import BaseModel


class PolicyResponse(BaseModel):
    id: str
    title: str
    country: str
    department: str
    departmentLabel: str
    level: str
    date: str
    summary: str
    fullTextUrl: str
    relatedTechnologies: list[str] = []
    relatedIndustries: list[str] = []
    marketReactionDays: Optional[int] = None


class PolicyListResponse(BaseModel):
    policies: list[PolicyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SimilarPolicy(BaseModel):
    policy: PolicyResponse
    score: float
