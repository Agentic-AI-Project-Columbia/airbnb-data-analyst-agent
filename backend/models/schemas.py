from pydantic import BaseModel


class QueryResult(BaseModel):
    columns: list[str]
    row_count: int
    data: list[dict]


class EDAFinding(BaseModel):
    metric: str
    value: str
    interpretation: str


class EDAFindings(BaseModel):
    summary: str
    findings: list[EDAFinding]
    follow_up_questions: list[str]
