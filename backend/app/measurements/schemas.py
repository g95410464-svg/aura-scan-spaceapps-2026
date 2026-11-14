import re
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from backend.app.devices.catalog import DEVICES, FIELDS


class Credentials(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username: str = Field(min_length=3,max_length=40,pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=10,max_length=128)


class Reading(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    code: str
    value: float = Field(ge=-1000,le=10000)
    unit: str

    @model_validator(mode='after')
    def correct_unit(self):
        if self.code not in FIELDS or self.unit not in FIELDS[self.code]['units']:
            raise ValueError('Indicador o unidad no admitidos.')
        return self


class Confirmation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    subject_alias: str = Field(min_length=1,max_length=80)
    device_type: str
    measured_at: datetime | None = None
    symptoms: str = Field(default='',max_length=2000)
    readings: list[Reading] = Field(min_length=1,max_length=6)
    reviewed: bool

    @field_validator('subject_alias')
    @classmethod
    def subject_not_blank(cls,value):
        if not value.strip():
            raise ValueError('Introduce un alias para el astronauta.')
        return value.strip()

    @model_validator(mode='after')
    def validate_confirmation(self):
        if not self.reviewed:
            raise ValueError('Confirma que revisaste los valores y sus unidades.')
        if self.device_type not in DEVICES:
            raise ValueError('Selecciona una categoría admitida.')
        spec=DEVICES[self.device_type]
        codes=[r.code for r in self.readings]
        if len(set(codes))!=len(codes):
            raise ValueError('Un indicador no puede aparecer dos veces.')
        if not set(spec['required']).issubset(codes) or not set(codes).issubset(spec['fields']):
            raise ValueError('Los campos no corresponden a la categoría seleccionada.')
        if self.measured_at:
            if self.measured_at.tzinfo is None:
                raise ValueError('La hora debe incluir zona horaria.')
            if self.measured_at>datetime.now(timezone.utc):
                raise ValueError('La medición no puede tener una fecha futura.')
        return self
