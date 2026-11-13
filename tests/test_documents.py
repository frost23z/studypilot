from pathlib import Path

from fastapi.testclient import TestClient

PDF = b"%PDF-1.4 fake"


def test_pdf_is_shown_in_the_browser(client: TestClient, documents: Path) -> None:
    (documents / "AI Agents.pdf").write_bytes(PDF)

    response = client.get("/documents/AI%20Agents.pdf")

    assert response.status_code == 200
    assert response.content == PDF
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")


def test_markdown_is_shown_as_text(client: TestClient, documents: Path) -> None:
    (documents / "overview.md").write_text("# Courses\n", encoding="utf-8")

    response = client.get("/documents/overview.md")

    assert response.status_code == 200
    assert response.text == "# Courses\n"
    assert response.headers["content-type"].startswith("text/plain")


def test_unknown_file_is_not_found(client: TestClient) -> None:
    assert client.get("/documents/nothing.pdf").status_code == 404


def test_other_file_types_are_not_served(client: TestClient, documents: Path) -> None:
    (documents / "secret.txt").write_text("no", encoding="utf-8")

    assert client.get("/documents/secret.txt").status_code == 404


def test_cannot_leave_the_documents_folder(
    client: TestClient, documents: Path, tmp_path: Path
) -> None:
    (tmp_path / "secret.pdf").write_bytes(PDF)  # next to the folder, not in it
    (documents / "link.pdf").symlink_to(tmp_path / "secret.pdf")

    for path in [
        "/documents/..%2Fsecret.pdf",
        "/documents/%2e%2e%2fsecret.pdf",
        "/documents/..",
        "/documents/%2Fetc%2Fpasswd",
        "/documents/secret%00.pdf",
        "/documents/link.pdf",  # a link that points outside
    ]:
        assert client.get(path).status_code == 404, path


def test_answer_lists_the_files_it_cites(client: TestClient, documents: Path, graph) -> None:
    (documents / "Technical Best Practice.pdf").write_bytes(PDF)
    graph.reply = "Use small commits [Technical Best Practice.pdf, page 12] [Made Up.pdf, page 1]."

    body = {"thread_id": "t1", "user_id": "sam", "message": "How should I commit?"}
    answer = client.post("/chat", json=body).json()

    assert answer["sources"] == [{"file": "Technical Best Practice.pdf", "page": 12}]


def test_saved_chat_shows_the_sources_of_old_answers_again(
    client: TestClient, documents: Path, graph
) -> None:
    (documents / "overview.md").write_text("# Courses\n", encoding="utf-8")
    graph.reply = "Start here [overview.md]."
    body = {"thread_id": "t1", "user_id": "sam", "message": "Where do I start?"}
    client.post("/chat", json=body)

    messages = client.get("/chat/t1").json()["messages"]

    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["sources"] == []
    assert messages[1]["sources"] == [{"file": "overview.md", "page": None}]
