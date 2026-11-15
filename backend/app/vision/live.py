"""Temporal OCR agreement for automatic observations, never clinical validation."""
import hashlib
import json
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.devices.catalog import DEVICES, FIELDS

INTERVAL_MS = 1800
MIN_FRAMES = 3
MIN_SPAN = 3.0
MAX_GAP = 15.0
MIN_CONFIDENCE = .90
TOLERANCES = {'pulse':2.0,'spo2':1.0}  # OCR stability heuristic, not clinical normality.


def compatible(first, second):
    if not first or first['device']!=second['device'] or first['demo']!=second['demo']:
        return False
    a={r['code']:r for r in first['readings']};b={r['code']:r for r in second['readings']}
    return a.keys()==b.keys() and all(a[c]['unit']==b[c]['unit'] and abs(a[c]['value']-b[c]['value'])<=TOLERANCES.get(c,0) for c in a)


class LiveStart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    subject_alias: str = Field(min_length=1, max_length=80)
    device_type: str = 'auto'
    is_demo: bool = False

    @field_validator('subject_alias')
    @classmethod
    def alias(cls, value):
        if not value.strip(): raise ValueError('Indica el alias del astronauta antes de iniciar.')
        return value.strip()

    @field_validator('device_type')
    @classmethod
    def category(cls, value):
        if value not in {'auto', *DEVICES}: raise ValueError('Categoría no admitida.')
        return value


def serialize_live(item):
    return {key:getattr(item,key) for key in ['id','session_id','capture_id','subject_alias','device_type','is_demo','created_at','readings','status']}


def advance(state, result, now, is_demo):
    """A bad/missing frame resets agreement; an unchanged screen stays deduplicated."""
    state = dict(state)
    fields = sorted(result.get('fields',[]),key=lambda r:r['code'])
    device = result.get('device_type','unknown')
    quality = result.get('quality',{})
    text = ' '.join(t['text'] for t in result.get('tokens',[]))
    screen_error = re.search(r'\b(ERR(?:OR)?|E[- ]?\d|MEM(?:ORY)?|AVG)\b',text.upper())
    valid = (device in DEVICES and fields and result.get('recognition')=='visible_labels'
             and quality.get('sharpness',0)>=20 and 25<=quality.get('brightness',0)<=245
             and not screen_error)
    if valid:
        codes = {r['code'] for r in fields}
        valid = (set(DEVICES[device]['required']).issubset(codes) and codes.issubset(DEVICES[device]['fields'])
                 and len(codes)==len(fields) and all(r['unit'] in FIELDS[r['code']]['units']
                 and r.get('confidence',0)>=MIN_CONFIDENCE for r in fields))
    if not valid:
        state.update(candidate=None,candidate_reading=None,count=0,first_seen=now,last_seen=now)
        return state, {'status':'searching','count':0,'target':MIN_FRAMES,'fields':fields,
                       'message':'Buscando etiquetas, unidades y valores legibles. Mantén la pantalla quieta, sin reflejos ni modo memoria.'}, False
    readings = [{'code':r['code'],'value':r['value'],'unit':r['unit']} for r in fields]
    current={'device':device,'demo':is_demo,'readings':readings}
    signature = hashlib.sha256(json.dumps([device,is_demo,readings],sort_keys=True).encode()).hexdigest()
    same = compatible(state.get('candidate_reading'),current) and now-state.get('last_seen',0)<=MAX_GAP
    if not same: state['candidate_reading']=current
    state.update(candidate=signature,count=state.get('count',0)+1 if same else 1,
                 first_seen=state.get('first_seen',now) if same else now,last_seen=now)
    stable = state['count']>=MIN_FRAMES and now-state['first_seen']>=MIN_SPAN
    count = min(state['count'],MIN_FRAMES)
    status = 'stabilizing'
    message = 'Lectura detectada. Comprobando consistencia entre varios fotogramas.'
    save = False
    if stable:
        if compatible(state.get('saved_reading'),current):
            status='unchanged';message='Esta lectura ya está guardada. Se registrará otra cuando cambien los valores y vuelvan a estabilizarse.'
        elif now-state.get('saved_at',0)<10:
            status='cooldown';message='Esperando unos segundos antes de guardar otro cambio estable.'
        else:
            status='recorded';message='Lectura estable guardada automáticamente, pendiente de revisión.'
            state.update(last_saved=signature,saved_reading=current,saved_at=now)
            save=True
    return state, {'status':status,'count':count,'target':MIN_FRAMES,'fields':fields,
                   'device_type':device,'message':message}, save
