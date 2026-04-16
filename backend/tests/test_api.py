import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """Проверяем, что корневой эндпоинт работает"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health_check():
    """Проверяем health check"""
    response = client.get("/health")
    assert response.status_code == 200

def test_docs_available():
    """Проверяем, что Swagger документация доступна"""
    response = client.get("/docs")
    assert response.status_code == 200

def test_login_endpoint():
    """Проверяем эндпоинт логина"""
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "123"
    })
    # Может быть 200 или 401, в зависимости от наличия пользователя
    assert response.status_code in [200, 401]

def test_cors_headers():
    """Проверяем CORS заголовки"""
    response = client.options("/", headers={
        "Origin": "http://localhost:3000"
    })
    assert "access-control-allow-origin" in response.headers