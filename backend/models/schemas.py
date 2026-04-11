from typing import Any

from pydantic import BaseModel, Field


class ArtifactRef(BaseModel):
    filename: str
    path: str


class ErrorResult(BaseModel):
    error: str


class QueryResult(BaseModel):
    columns: list[str]
    row_count: int
    returned_row_count: int
    truncated: bool = False
    data: list[dict[str, Any]]


class CodeExecutionResult(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int
    artifacts: list[ArtifactRef] = Field(default_factory=list)


class EDAFinding(BaseModel):
    metric: str
    value: str
    interpretation: str


class EDAFindings(BaseModel):
    summary: str
    findings: list[EDAFinding]
    follow_up_questions: list[str]
