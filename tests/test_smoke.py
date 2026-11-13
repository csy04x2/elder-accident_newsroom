"""기능 구현 전 최소 진입점·경로 설정 확인."""
from fastapi.testclient import TestClient

from api.main import app
from newsroom.paths import ROOT_DIR, processed_data_dir


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_default_data_dir(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert processed_data_dir() == ROOT_DIR / "data" / "processed"
