import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

VALID_PASSWORD = "S3curePass!"


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _auth_header(client, username: str) -> dict:
    client.post(
        "/auth/register", json={"username": username, "password": VALID_PASSWORD}
    )
    token = client.post(
        "/auth/login", json={"username": username, "password": VALID_PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").status_code == 200


def test_register_and_login(client):
    r = client.post(
        "/auth/register", json={"username": "alice", "password": VALID_PASSWORD}
    )
    assert r.status_code == 201
    assert "password" not in r.json()  # пароль/хэш не возвращаются

    r = client.post(
        "/auth/login", json={"username": "alice", "password": VALID_PASSWORD}
    )
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    client.post(
        "/auth/register", json={"username": "bob", "password": VALID_PASSWORD}
    )
    r = client.post("/auth/login", json={"username": "bob", "password": "wrong-pass"})
    assert r.status_code == 401


def test_protected_endpoint_requires_token(client):
    assert client.get("/api/data").status_code in (401, 403)


def test_protected_endpoint_with_token(client):
    headers = _auth_header(client, "carol")

    r = client.post(
        "/api/posts",
        json={"title": "Hello", "content": "<script>alert('xss')</script>"},
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert "<script>" not in body["content"]
    assert "&lt;script&gt;" in body["content"]

    r = client.get("/api/data", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_invalid_token_rejected(client):
    headers = {"Authorization": "Bearer not-a-valid-jwt"}
    assert client.get("/api/data", headers=headers).status_code == 401


def test_weak_password_rejected(client):
    r = client.post("/auth/register", json={"username": "dan", "password": "123"})
    assert r.status_code == 422  # не проходит валидацию (min_length=8)
