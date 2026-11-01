from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app


def test_unknown_route_uses_shared_error_envelope() -> None:
    response = TestClient(app).get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Resource not found."}
    }


def test_unsupported_method_uses_shared_error_envelope_and_preserves_allow() -> None:
    test_app = FastAPI()
    test_app.add_exception_handler(405, app.exception_handlers[405])

    @test_app.get("/test-only")
    def test_only_route() -> dict[str, bool]:
        return {"ok": True}

    response = TestClient(test_app).patch("/test-only")

    assert response.status_code == 405
    assert response.json() == {
        "error": {"code": "METHOD_NOT_ALLOWED", "message": "Method not allowed."}
    }
    assert "GET" in response.headers["allow"]
