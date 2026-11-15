import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from fastapi.testclient import TestClient
from backend.app.vision.demo import demo_image
from backend.app.vision.reader import analyze_bytes
from tests.conftest import open_workspace, confirmation


def setup_live(client, monkeypatch, real_ocr=False):
    clock=[time.time()]
    monkeypatch.setattr('backend.app.main.time.time',lambda:clock[0])
    if not real_ocr:
        ocr_result=analyze_bytes(demo_image(),'auto')
        monkeypatch.setattr('backend.app.main.analyze_bytes',lambda *_:ocr_result)
    result=client.post('/api/live/sessions',json={'subject_alias':'ASTRO-LIVE','device_type':'auto','is_demo':True})
    assert result.status_code==201,result.text
    return result.json()['id'],clock


def send(client,sid,sequence,clock):
    clock[0]+=2
    return client.post(f'/api/live/{sid}/frames',files={'file':('frame.png',demo_image(),'image/png')},data={'sequence':sequence})


def test_continuous_ocr_auto_saves_without_confirming_or_duplicate(visitor_client,monkeypatch):
    sid,clock=setup_live(visitor_client,monkeypatch,real_ocr=True)
    for seq in range(1,4):
        response=send(visitor_client,sid,seq,clock)
        assert response.status_code==200,response.text
        assert bool(response.json()['recording'])==(seq==3)
    automatic=response.json()['recording']
    assert automatic['status']=='pending'
    assert all(r['provenance']=='live_ocr_unreviewed' for r in automatic['readings'])
    assert visitor_client.get('/api/measurements').json()['items']==[]
    repeat=send(visitor_client,sid,3,clock)
    assert repeat.json()['recording']['id']==automatic['id']  # Idempotent retry.
    assert send(visitor_client,sid,4,clock).json()['status']=='unchanged'
    assert len(visitor_client.get('/api/live/readings').json()['items'])==1
    assistant=visitor_client.get('/api/assistant',params={'subject_alias':'ASTRO-LIVE','is_demo':True}).json()
    assert assistant['record_count']==0 and len(assistant['automatic_readings'])==1
    assert assistant['metrics']==[] and assistant['diagnosis'] is None
    evidence=visitor_client.get(f'/api/captures/{automatic["capture_id"]}')
    assert evidence.json()['subject_alias']=='ASTRO-LIVE'
    saved=visitor_client.post(f'/api/captures/{automatic["capture_id"]}/confirm',json=confirmation(subject_alias='ASTRO-LIVE'))
    assert saved.status_code==201,saved.text
    assert visitor_client.get('/api/live/readings').json()['items']==[]
    assert len(visitor_client.get('/api/measurements').json()['items'])==1


def test_stopping_prevents_late_frames_and_browser_spaces_stay_private(visitor_client,application,monkeypatch):
    sid,clock=setup_live(visitor_client,monkeypatch)
    for seq in range(1,4):response=send(visitor_client,sid,seq,clock)
    capture_id=response.json()['recording']['capture_id']
    with TestClient(application) as other:
        open_workspace(other)
        assert send(other,sid,4,clock).status_code==404
        assert other.post(f'/api/live/{sid}/stop').status_code==404
        assert other.get(f'/api/captures/{capture_id}').status_code==404
        assert other.get('/api/live/readings').json()['items']==[]
    assert visitor_client.post(f'/api/live/{sid}/stop').status_code==200
    assert visitor_client.post(f'/api/live/{sid}/stop').status_code==200
    assert send(visitor_client,sid,4,clock).status_code==409


def test_live_validation_csrf_expiry_and_sequence(visitor_client,monkeypatch):
    for body in [{'subject_alias':' '},{'subject_alias':'X','device_type':'unknown'},{'subject_alias':'X','extra':1}]:
        assert visitor_client.post('/api/live/sessions',json=body).status_code==422
    assert visitor_client.post('/api/live/sessions',json={'subject_alias':'X'},headers={'X-CSRF-Token':'wrong'}).status_code==403
    sid,clock=setup_live(visitor_client,monkeypatch)
    assert send(visitor_client,sid,1,clock).status_code==200
    assert send(visitor_client,sid,0,clock).status_code==422
    assert send(visitor_client,sid,2,clock).status_code==200
    assert send(visitor_client,sid,1,clock).status_code==409
    clock[0]+=7201
    assert send(visitor_client,sid,3,clock).status_code==409


def test_simultaneous_frame_retries_cannot_create_two_records(visitor_client,monkeypatch):
    sid,clock=setup_live(visitor_client,monkeypatch)
    assert send(visitor_client,sid,1,clock).status_code==200
    assert send(visitor_client,sid,2,clock).status_code==200
    clock[0]+=2
    result=analyze_bytes(demo_image())
    barrier=Barrier(2)
    def simultaneous_ocr(*_):
        barrier.wait(timeout=10)
        return result
    monkeypatch.setattr('backend.app.main.analyze_bytes',simultaneous_ocr)
    def post():
        return visitor_client.post(f'/api/live/{sid}/frames',files={'file':('frame.png',demo_image(),'image/png')},data={'sequence':3})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:post(),range(2)))
    assert sorted(r.status_code for r in responses)==[200,409]
    assert len(visitor_client.get('/api/live/readings').json()['items'])==1
