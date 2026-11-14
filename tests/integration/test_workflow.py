from io import BytesIO
from datetime import datetime,timedelta,timezone
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import select
from fastapi.testclient import TestClient
from backend.app.storage.models import AuditEvent,User,AuthSession
from tests.conftest import sign_up,confirmation


def test_full_real_ocr_confirmation_history_and_report(signed_client,capture):
    assert capture['is_demo'] is True
    fields={f['code']:f['value'] for f in capture['fields']}
    assert fields=={'systolic':120,'diastolic':80,'pulse':72}
    assert signed_client.get('/api/measurements').json()['items']==[]
    response=signed_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation())
    assert response.status_code==201,response.text
    result=response.json()
    assert result['measured_at'] is None
    assert result['assessment']['diagnosis'] is None
    assert result['assessment']['treatment'] is None
    assert len(signed_client.get('/api/measurements').json()['items'])==1
    pdf=signed_client.get(f'/api/measurements/{result["id"]}/report.pdf')
    assert pdf.status_code==200
    assert pdf.headers['content-type']=='application/pdf'
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert 'ASTRO-01' in text and 'FICTICIOS' in text and '120' in text
    assert 'hora desconocida' in text


def test_other_user_cannot_read_evidence_history_or_report(application,signed_client,capture):
    result=signed_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation()).json()
    with TestClient(application) as other:
        sign_up(other,'othercrew')
        assert other.get(capture['image_url']).status_code==404
        assert other.get('/api/measurements').json()['items']==[]
        assert other.get(f'/api/measurements/{result["id"]}/report.pdf').status_code==404
        assert other.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation()).status_code==404


def test_double_confirmation_is_rejected(signed_client,capture):
    endpoint=f'/api/captures/{capture["id"]}/confirm'
    assert signed_client.post(endpoint,json=confirmation()).status_code==201
    assert signed_client.post(endpoint,json=confirmation()).status_code==409


def test_review_checkbox_is_mandatory(signed_client,capture):
    assert signed_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation(reviewed=False)).status_code==422


def test_wrong_unit_and_duplicate_fields_are_rejected(signed_client,capture):
    body=confirmation();body['readings'][0]['unit']='°C'
    assert signed_client.post(f'/api/captures/{capture["id"]}/confirm',json=body).status_code==422
    body=confirmation();body['readings'].append(body['readings'][0])
    assert signed_client.post(f'/api/captures/{capture["id"]}/confirm',json=body).status_code==422


def test_future_measurement_time_is_rejected(signed_client,capture):
    body=confirmation(measured_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    assert signed_client.post(f'/api/captures/{capture["id"]}/confirm',json=body).status_code==422


def test_correction_preserves_ocr_and_audit(signed_client,capture,application):
    body=confirmation();body['readings'][0]['value']=125
    response=signed_client.post(f'/api/captures/{capture["id"]}/confirm',json=body)
    assert response.status_code==201
    assert response.json()['readings'][0]['provenance']=='user_reviewed'
    with application.state.db_session() as db:
        audit=db.scalar(select(AuditEvent).where(AuditEvent.capture_id==capture['id']))
        assert next(r for r in audit.detail['candidates'] if r['code']=='systolic')['value']==120
        assert audit.detail['confirmed'][0]['value']==125


def test_valid_anomalous_values_are_not_normalized(signed_client,capture):
    body=confirmation();body['readings'][0]['value']=75
    result=signed_client.post(f'/api/captures/{capture["id"]}/confirm',json=body).json()
    assert result['readings'][0]['value']==75
    assert any('relación' in text for text in result['assessment']['findings'])


def test_invalid_and_oversized_pixel_images_rejected(signed_client):
    assert signed_client.post('/api/captures',files={'file':('x.png',b'not an image','image/png')}).status_code==422
    image=Image.new('RGB',(4000,4000),'white');buf=BytesIO();image.save(buf,format='PNG')
    assert signed_client.post('/api/captures',files={'file':('x.png',buf.getvalue(),'image/png')}).status_code==422


def test_cookie_password_and_token_storage(signed_client,application):
    me=signed_client.get('/api/auth/me');assert me.status_code==200
    with application.state.db_session() as db:
        user=db.scalar(select(User));auth=db.scalar(select(AuthSession))
        assert user.password_hash.startswith('$argon2')
        assert signed_client.cookies['aura_session']!=auth.token_hash
    result=signed_client.post('/api/auth/logout')
    assert result.status_code==204
    assert signed_client.get('/api/auth/me').status_code==401


def test_csrf_and_cross_origin_protection(signed_client):
    assert signed_client.post('/api/auth/logout',headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert signed_client.post('/api/auth/logout',headers={'Origin':'https://evil.invalid'}).status_code==403


def test_private_routes_require_authentication(client):
    assert client.get('/api/measurements').status_code==401
    assert client.post('/api/captures/demo').status_code==401
    assert client.get('/api/captures/missing/image').status_code==401


def test_sources_and_capabilities_are_truthful(client):
    assert len(client.get('/api/knowledge').json()['sources'])==5
    assert client.get('/api/knowledge').json()['protocols']==[]
    assert client.get('/api/devices').json()['exact_models']==[]
    assert client.get('/api/devices').json()['dataset_status']=='not_integrated'
    assert client.get('/api/missing').status_code==404
