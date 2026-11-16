from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field


class SimulationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    run_key: UUID = Field(default_factory=uuid4)


SCENARIOS = [
    {'title':'Presión de referencia / Baseline','device_type':'blood_pressure','values':[120,80,72],
     'expected':{'systolic':120,'diastolic':80,'pulse':72},'minutes_ago':20},
    {'title':'Segunda lectura / Follow-up','device_type':'blood_pressure','values':[126,82,78],
     'expected':{'systolic':126,'diastolic':82,'pulse':78},'minutes_ago':10},
    {'title':'Oxímetro / Oximeter','device_type':'oximeter','values':[98,75],
     'expected':{'spo2':98,'pulse':75},'minutes_ago':5},
]
