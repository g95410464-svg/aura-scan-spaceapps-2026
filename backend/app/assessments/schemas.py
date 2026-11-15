from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContextInput(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    subject_alias: str = Field(min_length=1, max_length=80)
    is_demo: bool = False
    environment: Literal['unknown','station','spacecraft','moon','mars','earth'] = 'unknown'
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    mood: Literal['unknown','steady','strained','low'] = 'unknown'
    symptoms: str = Field(default='', max_length=2000)
    medical_notes: str = Field(default='', max_length=2000)
    red_flags: list[Literal['chest_pain','breathing','consciousness']] = Field(default_factory=list, max_length=3)

    @field_validator('subject_alias')
    @classmethod
    def alias_not_blank(cls, value):
        if not value.strip():
            raise ValueError('Introduce un alias para reunir el historial.')
        return value.strip()
