
import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.delenv('RENDER', raising=False)
    monkeypatch.delenv('VERCEL', raising=False)
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def test_security_headers_present(client):
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert 'camera=()' in (response.headers.get('Permissions-Policy') or '')
    assert response.headers.get('Cross-Origin-Opener-Policy') == 'same-origin'
    assert response.headers.get('Cross-Origin-Resource-Policy') == 'same-origin'


def test_csp_header_present(client):
    response = client.get('/healthz')
    csp = response.headers.get('Content-Security-Policy', '')
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'self'" in csp
    assert "object-src 'none'" in csp
    assert "script-src 'self' 'nonce-" in csp
    assert "style-src 'self' 'nonce-" in csp
    assert "'unsafe-inline'" not in csp


def test_request_id_header_returned(client):
    response = client.get('/healthz')
    # healthz is in SKIP_LOG_PATHS but finish_request still sets X-Request-ID.
    assert response.headers.get('X-Request-ID')
