from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.main import create_app


def test_assistant_capabilities_and_chat_are_grounded(db_session: Session) -> None:
    app = create_app()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)

    capabilities = client.get("/api/assistant/capabilities")
    assert capabilities.status_code == 200
    assert "Project NBA awards" in capabilities.json()["capabilities"][3]

    response = client.post(
        "/api/assistant/chat",
        json={"message": "What can you do?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "local-tools"
    assert body["sources"] == [{"tool": "list_capabilities", "arguments": {}}]
    assert "search stored players and teams" in body["message"].lower()
    assert body["session_id"]
