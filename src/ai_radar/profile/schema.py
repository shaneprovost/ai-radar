"""Pydantic models for user profile."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class DetectedEnvironment(BaseModel):
    os: str = ""
    shell: str = ""
    package_managers: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    editors: list[str] = Field(default_factory=list)
    frameworks_detected: list[str] = Field(default_factory=list)
    git_repos_sampled: list[str] = Field(default_factory=list)


class AITooling(BaseModel):
    claude_code_detected: bool = False
    claude_code_version: Optional[str] = None
    mcp_servers: list[str] = Field(default_factory=list)
    api_keys_present: list[str] = Field(default_factory=list)
    other_ai_tools: list[str] = Field(default_factory=list)


class WorkflowPattern(BaseModel):
    description: str
    commands_or_steps: list[str] = Field(default_factory=list)
    frequency: str = "unknown"
    pain_level: str = "minor annoyance"  # "minor annoyance" | "real friction" | "major time sink"
    source: str = "user"  # "detected" | "user"


class UserProvided(BaseModel):
    name: str = ""
    role: str = ""
    primary_focus: str = ""
    daily_tools: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    adoption_style: Literal["early adopter", "pragmatic", "cautious"] = "pragmatic"
    recently_adopted: list[str] = Field(default_factory=list)
    ignore_topics: list[str] = Field(default_factory=list)
    workflow_patterns: list[WorkflowPattern] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    biggest_time_sink: str = ""


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "anthropic/claude-sonnet-4-6"
    max_tokens_per_digest: int = 8000


class DeliveryPreferences(BaseModel):
    slack_webhook_url: Optional[str] = None
    digest_dir: str = "~/ai-radar/digests"
    max_items_per_digest: int = 10
    cron_schedule: str = "0 8 * * 1"


class Profile(BaseModel):
    version: str = "1"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    detected: DetectedEnvironment = Field(default_factory=DetectedEnvironment)
    ai_tooling: AITooling = Field(default_factory=AITooling)
    user: UserProvided = Field(default_factory=UserProvided)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    delivery: DeliveryPreferences = Field(default_factory=DeliveryPreferences)
