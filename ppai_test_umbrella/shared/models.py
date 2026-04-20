# from __future__ import annotations

# from typing import List, Optional, Dict, Any
# from pydantic import BaseModel, Field


# class Requirement(BaseModel):
#     requirement_id: str
#     title: str
#     description: str
#     module: str = "general"
#     actors: List[str] = Field(default_factory=list)
#     business_rules: List[str] = Field(default_factory=list)
#     acceptance_criteria: List[str] = Field(default_factory=list)
#     source_path: Optional[str] = None


# class Scenario(BaseModel):
#     scenario_id: str
#     requirement_id: str
#     title: str
#     objective: str
#     scenario_type: str
#     priority: str
#     tags: List[str] = Field(default_factory=list)


# class TestCase(BaseModel):
#     testcase_id: str
#     scenario_id: str
#     title: str
#     preconditions: List[str] = Field(default_factory=list)
#     steps: List[str] = Field(default_factory=list)
#     expected_results: List[str] = Field(default_factory=list)
#     automation_candidate: bool = True
#     automation_type: Optional[str] = None


# class AutomationCandidate(BaseModel):
#     testcase_id: str
#     recommended_framework: str
#     rationale: str
#     starter_code_path: Optional[str] = None


# class RetrievalHit(BaseModel):
#     source_id: str
#     score: float
#     preview: str
#     metadata: Dict[str, Any] = Field(default_factory=dict)


# class LocatorHealingRequest(BaseModel):
#     page_name: str
#     locator_name: str
#     failed_selector: str
#     dom_hints: List[str] = Field(default_factory=list)


# class LocatorHealingResponse(BaseModel):
#     resolved: bool
#     candidates: List[str] = Field(default_factory=list)
#     reason: str


# class StepHealingRequest(BaseModel):
#     flow_name: str
#     current_steps: List[str]
#     failure_note: Optional[str] = None


# class StepHealingResponse(BaseModel):
#     updated_steps: List[str] = Field(default_factory=list)
#     reasons: List[str] = Field(default_factory=list)

from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Requirement(BaseModel):
    requirement_id: str
    title: str
    description: str
    module: str = "general"
    actors: List[str] = Field(default_factory=list)
    business_rules: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    source_path: Optional[str] = None


class Scenario(BaseModel):
    scenario_id: str
    requirement_id: str
    title: str
    objective: str
    scenario_type: str
    priority: str
    tags: List[str] = Field(default_factory=list)


class ActionStep(BaseModel):
    action: str
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    key: Optional[str] = None
    expected: Optional[str] = None
    timeout_ms: int = 10000
    description: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TestCase(BaseModel):
    testcase_id: str
    scenario_id: str
    title: str
    preconditions: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    expected_results: List[str] = Field(default_factory=list)
    automation_candidate: bool = True
    automation_type: Optional[str] = None
    action_steps: List[ActionStep] = Field(default_factory=list)


class AutomationCandidate(BaseModel):
    testcase_id: str
    recommended_framework: str
    rationale: str
    starter_code_path: Optional[str] = None


class RetrievalHit(BaseModel):
    source_id: str
    score: float
    preview: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LocatorHealingRequest(BaseModel):
    page_name: str
    locator_name: str
    failed_selector: str
    dom_hints: List[str] = Field(default_factory=list)


class LocatorHealingResponse(BaseModel):
    resolved: bool
    candidates: List[str] = Field(default_factory=list)
    reason: str


class StepHealingRequest(BaseModel):
    flow_name: str
    current_steps: List[str]
    failure_note: Optional[str] = None


class StepHealingResponse(BaseModel):
    updated_steps: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)