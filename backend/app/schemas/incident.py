import uuid

from pydantic import BaseModel


class IncidentListItem(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    difficulty: str
    category: str
    priority: str
    summary: str
    is_free_tier: bool
    xp_reward: int

    model_config = {"from_attributes": True}


class IncidentPublic(BaseModel):
    """
    What a student is allowed to see about an incident. Deliberately omits
    `answer_key` and the fault-bearing parts of `initial_state` (interface
    configs remain visible — that's what CLI `show` commands reveal — but
    this schema is the topology + narrative only; live device state is
    served exclusively through the CLI endpoint, one command at a time).
    """

    id: uuid.UUID
    slug: str
    title: str
    difficulty: str
    category: str
    priority: str
    summary: str
    impact: str
    symptoms: list[str]
    learning_objectives: list[str]
    topology: dict
    xp_reward: int

    model_config = {"from_attributes": True}


class AttemptStart(BaseModel):
    incident_id: uuid.UUID


class AttemptPublic(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    status: str
    hints_used: int
    failed_attempts: int
    unnecessary_commands: int
    root_cause_identified: bool
    remediation_applied: bool
    verification_passed: bool
    methodology_progress: dict
    score_diagnosis: float | None = None
    score_methodology: float | None = None
    score_efficiency: float | None = None
    score_remediation: float | None = None
    score_verification: float | None = None
    score_overall: float | None = None

    model_config = {"from_attributes": True}


class CliCommandRequest(BaseModel):
    device: str
    command: str


class CliCommandResponse(BaseModel):
    device: str
    command: str
    output: str
    was_useful: bool


class DiagnosisSubmit(BaseModel):
    root_cause_statement: str


class RemediationSubmit(BaseModel):
    device: str
    commands: list[str]


class VerifySubmit(BaseModel):
    device: str
    command: str


class ResolutionSummary(BaseModel):
    attempt: AttemptPublic
    root_cause: str
    correct_remediation: str
    verification_procedure: str
    explanation: str
