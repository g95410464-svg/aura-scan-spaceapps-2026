from io import BytesIO
from datetime import datetime,timedelta,timezone
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import select, inspect
from fastapi.testclient import TestClient
from backend.app.storage.models import AuditEvent,Workspace,BrowserSession
from tests.conftest import open_workspace,confirmation


def test_full_real_ocr_confirmation_history_and_report(visitor_client,capture):
    assert capture['is_demo'] is True
    fields={f['code']:f['value'] for f in capture['fields']}
    assert fields=={'systolic':120,'diastolic':80,'pulse':72}
    assert visitor_client.get('/api/measurements').json()['items']==[]
    response=visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation())
    assert response.status_code==201,response.text
    result=response.json()
    assert result['measured_at'] is None
    assert result['assessment']['diagnosis'] is None
    assert result['assessment']['treatment'] is None
    assert len(visitor_client.get('/api/measurements').json()['items'])==1
    pdf=visitor_client.get(f'/api/measurements/{result["id"]}/report.pdf')
    assert pdf.status_code==200
    assert pdf.headers['content-type']=='application/pdf'
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert 'ASTRO-01' in text and 'FICTICIOS' in text and '120' in text
    assert 'hora desconocida' in text


def test_another_browser_cannot_read_evidence_history_or_report(application,visitor_client,capture):
    result=visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation()).json()
    with TestClient(application) as other:
        open_workspace(other)
        assert other.get(capture['image_url']).status_code==404
        assert other.get('/api/measurements').json()['items']==[]
        assert other.get(f'/api/measurements/{result["id"]}/report.pdf').status_code==404
        assert other.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation()).status_code==404


def test_double_confirmation_is_rejected(visitor_client,capture):
    endpoint=f'/api/captures/{capture["id"]}/confirm'
    assert visitor_client.post(endpoint,json=confirmation()).status_code==201
    assert visitor_client.post(endpoint,json=confirmation()).status_code==409


def test_review_checkbox_is_mandatory(visitor_client,capture):
    assert visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation(reviewed=False)).status_code==422


def test_wrong_unit_and_duplicate_fields_are_rejected(visitor_client,capture):
    body=confirmation();body['readings'][0]['unit']='°C'
    assert visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=body).status_code==422
    body=confirmation();body['readings'].append(body['readings'][0])
    assert visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=body).status_code==422


def test_future_measurement_time_is_rejected(visitor_client,capture):
    body=confirmation(measured_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    assert visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=body).status_code==422


def test_correction_preserves_ocr_and_audit(visitor_client,capture,application):
    body=confirmation();body['readings'][0]['value']=125
    response=visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=body)
    assert response.status_code==201
    assert response.json()['readings'][0]['provenance']=='user_reviewed'
    with application.state.db_session() as db:
        audit=db.scalar(select(AuditEvent).where(AuditEvent.capture_id==capture['id']))
        assert next(r for r in audit.detail['candidates'] if r['code']=='systolic')['value']==120
        assert audit.detail['confirmed'][0]['value']==125


def test_valid_anomalous_values_are_not_normalized(visitor_client,capture):
    body=confirmation();body['readings'][0]['value']=75
    result=visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=body).json()
    assert result['readings'][0]['value']==75
    assert any('relación' in text for text in result['assessment']['findings'])


def test_invalid_and_oversized_pixel_images_rejected(visitor_client):
    assert visitor_client.post('/api/captures',files={'file':('x.png',b'not an image','image/png')}).status_code==422
    image=Image.new('RGB',(4000,4000),'white');buf=BytesIO();image.save(buf,format='PNG')
    assert visitor_client.post('/api/captures',files={'file':('x.png',buf.getvalue(),'image/png')}).status_code==422


def test_anonymous_cookie_and_workspace_are_reused(visitor_client,application):
    again=visitor_client.get('/api/session')
    assert again.status_code==200
    assert set(again.json())=={'csrf','expires_at'}
    with application.state.db_session() as db:
        workspaces=db.scalars(select(Workspace)).all()
        sessions=db.scalars(select(BrowserSession)).all()
        assert len(workspaces)==1 and len(sessions)==1
        assert visitor_client.cookies['aura_browser']!=sessions[0].token_hash
        assert 'users' not in inspect(db.bind).get_table_names()
        assert 'auth_sessions' not in inspect(db.bind).get_table_names()


def test_no_accounts_or_login_endpoints(client):
    response=client.get('/api/session')
    assert response.status_code==200
    cookie=response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    assert client.post('/api/auth/register',json={}).status_code in {404,405}
    assert client.post('/api/auth/login',json={}).status_code in {404,405}
    assert client.get('/api/auth/me').status_code==404
    assert not any('/api/auth/' in path for path in client.get('/openapi.json').json()['paths'])


def test_expired_browser_cannot_recover_previous_history(visitor_client,capture,application):
    visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation())
    with application.state.db_session() as db:
        browser=db.scalar(select(BrowserSession))
        browser.expires_at=0
        db.commit()
    assert visitor_client.get('/api/measurements').status_code==401
    open_workspace(visitor_client)
    assert visitor_client.get('/api/measurements').json()['items']==[]
    assert visitor_client.get(capture['image_url']).status_code==404


def test_csrf_and_cross_origin_protection(visitor_client):
    assert visitor_client.post('/api/captures/demo',headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert visitor_client.post('/api/captures/demo',headers={'Origin':'https://evil.invalid'}).status_code==403


def test_records_require_browser_workspace_but_no_account(client):
    assert client.get('/api/measurements').status_code==401
    assert client.post('/api/captures/demo').status_code==401
    assert client.get('/api/captures/missing/image').status_code==401


def test_sources_and_capabilities_are_truthful(client):
    assert len(client.get('/api/knowledge').json()['sources'])==5
    assert client.get('/api/knowledge').json()['protocols']==[]
    assert client.get('/api/devices').json()['exact_models']==[]
    assert client.get('/api/devices').json()['dataset_status']=='not_integrated'
    assert client.get('/api/missing').status_code==404
