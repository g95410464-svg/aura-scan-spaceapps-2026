from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.core.settings import Settings
from tests.conftest import open_workspace


def test_railway_https_origin_is_allowed_behind_http_proxy(tmp_path, monkeypatch):
    domain = 'aura-scan-spaceapps-2026-production.up.railway.app'
    monkeypatch.setenv('RAILWAY_PUBLIC_DOMAIN', domain)
    monkeypatch.delenv('PUBLIC_ORIGIN', raising=False)
    config = Settings(database_url=f'sqlite:///{tmp_path / "proxy.sqlite3"}', storage_dir=tmp_path/'captures', secure_cookies=False)
    assert config.public_origin == f'https://{domain}'
    with TestClient(create_app(config), base_url=f'http://{domain}') as client:
        open_workspace(client)
        upload = {'file': ('invalid.png', b'not an image', 'image/png')}
        accepted = client.post('/api/captures', files=upload, headers={'Origin':f'https://{domain}'})
        assert accepted.status_code == 422  # Reached image validation, past origin and CSRF.
        for origin in [f'https://{domain}.evil.test', 'null', f'http://{domain}:8080', 'https://evil.test']:
            assert client.post('/api/captures', files=upload, headers={'Origin':origin}).status_code == 403
        assert client.post('/api/captures', files=upload, headers={'Origin':f'https://{domain}:443'}).status_code == 422


def test_explicit_public_origin_takes_precedence(monkeypatch):
    monkeypatch.setenv('RAILWAY_PUBLIC_DOMAIN', 'generated.up.railway.app')
    monkeypatch.setenv('PUBLIC_ORIGIN', 'https://custom.example')
    assert Settings().public_origin == 'https://custom.example'
