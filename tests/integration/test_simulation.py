from uuid import uuid4
from io import BytesIO
from fastapi.testclient import TestClient
from pypdf import PdfReader
from tests.conftest import open_workspace


def test_guided_simulation_runs_real_ocr_and_builds_isolated_history(visitor_client,application):
    key=str(uuid4())
    response=visitor_client.post('/api/simulation/run',json={'run_key':key})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['is_demo'] and len(result['screens'])==3 and len(result['records'])==3
    assert all(r['is_demo'] for r in result['records'])
    assert all(f['provenance']=='simulation_scripted' for r in result['records'] for f in r['readings'])
    assert visitor_client.post('/api/simulation/run',json={'run_key':key}).json()['id']==result['id']
    assert len(visitor_client.get('/api/measurements').json()['items'])==3
    data=visitor_client.get('/api/assistant',params={'subject_alias':result['subject_alias'],'is_demo':True}).json()
    assert data['record_count']==3
    assert next(m for m in data['metrics'] if m['code']=='systolic')['delta']==6
    assert next(m for m in data['metrics'] if m['code']=='spo2')['value']==98
    assert data['context']['sleep_hours']==6
    assert data['diagnosis'] is None
    real=visitor_client.get('/api/assistant',params={'subject_alias':result['subject_alias'],'is_demo':False}).json()
    assert real['record_count']==0 and real['context'] is None
    pdf=visitor_client.get(f'/api/measurements/{result["report_id"]}/report.pdf')
    assert pdf.status_code==200
    text=' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
    assert 'FICTICIOS' in text and 'Simulación guionada' in text
    with TestClient(application) as other:
        open_workspace(other)
        assert other.get(result['screens'][0]['image_url']).status_code==404
        assert other.get('/api/measurements').json()['items']==[]


def test_simulation_requires_browser_csrf_and_valid_key(visitor_client):
    assert visitor_client.post('/api/simulation/run',json={},headers={'X-CSRF-Token':'bad'}).status_code==403
    assert visitor_client.post('/api/simulation/run',json={'run_key':'invalid'}).status_code==422
