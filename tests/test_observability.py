import re

from fastapi.testclient import TestClient

from service.app import app


def test_health_response_has_request_id_and_security_headers():
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
