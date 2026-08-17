"""Foundation smoke tests: app boots, health check reports DB connectivity."""


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "MeritMatrix Pro 2.0"
    assert body["status"] == "running"


def test_health_endpoint_reports_ok_and_db_connected(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["app"] == "MeritMatrix Pro 2.0"


def test_openapi_docs_available(client):
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "MeritMatrix Pro 2.0"


def test_404_returns_clean_error_shape(client):
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
