from typing import Any

from pydantic import BaseModel, Field


class SettingUpdate(BaseModel):
    key: str
    value: Any


class SpamTrigger(BaseModel):
    trigger: str = Field(..., min_length=2)
    score: int = Field(..., gt=0, lt=101)


class SpamTriggerDelete(BaseModel):
    trigger: str


class Chat(BaseModel):
    id: int
    name: str


class PunishmentRule(BaseModel):
    level: int
    action: str
    duration: int
