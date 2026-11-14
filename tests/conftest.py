import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.core.settings import Settings
from backend.app.core.security import _attempts


@pytest.fixture
def application(tmp_path):
    _attempts.clear()
    return create_app(Settings(database_url=f'sqlite:///{tmp_path / "test.sqlite3"}',storage_dir=tmp_path/'captures'))


@pytest.fixture
def client(application):
    with TestClient(application) as client:
        yield client


def sign_up(client,username='testcrew'):
    response=client.post('/api/auth/register',json={'username':username,'password':'Testing-only-password-42'})
    assert response.status_code==201,response.text
    client.headers['X-CSRF-Token']=response.json()['csrf']
    return response


@pytest.fixture
def signed_client(client):
    sign_up(client)
    return client


@pytest.fixture
def capture(signed_client):
    response=signed_client.post('/api/captures/demo')
    assert response.status_code==201,response.text
    assert response.json()['recognition']=='visible_labels'
    return response.json()


def confirmation(**overrides):
    return {'subject_alias':'ASTRO-01','device_type':'blood_pressure','measured_at':None,'symptoms':'Contexto ficticio para pruebas.',
            'readings':[{'code':'systolic','value':120,'unit':'mmHg'},{'code':'diastolic','value':80,'unit':'mmHg'},{'code':'pulse','value':72,'unit':'lpm'}],
            'reviewed':True,**overrides}
