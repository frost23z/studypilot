from fastapi.testclient import TestClient

from threads.store import TITLE_LENGTH, make_title


def send(client: TestClient, thread_id: str, user_id: str, message: str) -> None:
    body = {"thread_id": thread_id, "user_id": user_id, "message": message}
    assert client.post("/chat", json=body).status_code == 200


def test_new_person_has_no_chats(client: TestClient) -> None:
    assert client.get("/threads/sam").json() == []


def test_chat_is_listed_with_its_first_question_as_title(client: TestClient) -> None:
    send(client, "t1", "sam", "What is a Django model?")
    send(client, "t1", "sam", "And a view?")

    threads = client.get("/threads/sam").json()

    assert [(t["thread_id"], t["title"]) for t in threads] == [("t1", "What is a Django model?")]


def test_most_recently_used_chat_comes_first(client: TestClient) -> None:
    send(client, "t1", "sam", "first")
    send(client, "t2", "sam", "second")
    assert [t["thread_id"] for t in client.get("/threads/sam").json()] == ["t2", "t1"]

    send(client, "t1", "sam", "back to the first")

    assert [t["thread_id"] for t in client.get("/threads/sam").json()] == ["t1", "t2"]


def test_chats_are_kept_per_person(client: TestClient) -> None:
    send(client, "t1", "sam", "mine")
    send(client, "t2", "alex", "theirs")

    assert [t["thread_id"] for t in client.get("/threads/sam").json()] == ["t1"]
    assert [t["thread_id"] for t in client.get("/threads/alex").json()] == ["t2"]


def test_a_chat_cannot_be_taken_over_by_another_person(client: TestClient) -> None:
    send(client, "t1", "sam", "mine")
    send(client, "t1", "alex", "I use sam's thread id")

    assert client.get("/threads/alex").json() == []
    assert [t["title"] for t in client.get("/threads/sam").json()] == ["mine"]


def test_long_title_is_cut_on_one_line() -> None:
    title = make_title("word " * 50 + "\n second line")

    assert len(title) == TITLE_LENGTH
    assert title.endswith("…")
    assert "\n" not in title
