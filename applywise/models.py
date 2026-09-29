from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Block(Contract):
    id: str
    section: str
    text: str


class Document(Contract):
    name: str
    kind: str
    blocks: list[Block]
    checks: list[str]
    warnings: list[str]

    @property
    def text(self):
        return "\n".join(b.text for b in self.blocks)


class Evidence(Contract):
    source_id: str
    quote: str


class Requirement(Contract):
    id: str
    label: str
    job_quote: str
    importance: Literal["required", "preferred"]
    hard_gate: bool
    status: Literal["supported", "partial", "not_evidenced", "contradicted"]
    evidence: list[Evidence]
    reason: str


class Question(Contract):
    id: str
    requirement_id: str
    question: str
    why: str


class Analysis(Contract):
    role: str
    summary: str
    requirements: list[Requirement] = Field(min_length=1, max_length=20)
    questions: list[Question] = Field(max_length=6)
    target_block_ids: list[str] = Field(max_length=5)
    restructure: bool
    structure_reason: str


class Answer(Contract):
    id: str
    question: str
    requirement_id: str
    text: str


class Edit(Contract):
    block_id: str
    replacement: str
    reason: str
    evidence: list[Evidence] = Field(min_length=1)


class LayoutSection(Contract):
    heading: str
    block_ids: list[str]


class EditPlan(Contract):
    edits: list[Edit] = Field(max_length=5)
    layout: list[LayoutSection]
    notes: list[str] = Field(max_length=3)


class Usage(Contract):
    stage: str
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0


class Scorecard(Contract):
    score: float
    supported: int
    total: int
    eligibility: str
    recommendation: str
    reason: str
