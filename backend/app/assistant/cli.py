from __future__ import annotations

from app.assistant.chat import answer_message
from app.db.session import create_session_factory


def main() -> None:
    session_factory = create_session_factory()
    session_id: str | None = None
    print("Jordan - CourtVision NBA Intelligence Assistant")
    print("Grounded in stored data. Type 'exit' to quit.")
    while True:
        try:
            message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return
        if message.lower() in {"exit", "quit"}:
            print("Goodbye.")
            return
        if not message:
            continue
        with session_factory() as session:
            try:
                response = answer_message(session, message, session_id)
            except ValueError as exc:
                print(f"Jordan: I could not complete that request: {exc}")
                continue
        session_id = str(response["session_id"])
        print(f"Jordan: {response['message']}")


if __name__ == "__main__":
    main()
