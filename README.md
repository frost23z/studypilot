# StudyPilot

A study assistant for course materials. Ask questions about your PDFs and Markdown notes, get
answers with the official docs as backup, save notes, and let it remember facts about you across
chats.

It has three parts that you start separately:

1. **Ingest** reads everything in `documents/` into a Chroma vector store (run once, and again
   when the documents change).
2. **API** (FastAPI) runs the agent, the notes and the long-term memory.
3. **Web app** (Streamlit) is the page you use. It only talks to the API.

## Before you start

- [uv](https://docs.astral.sh/uv/). It installs Python 3.14 for you.
- Java 11 or newer. The PDF loader needs it. Check with `java -version`.
- A [Google AI Studio](https://aistudio.google.com/) API key (chat and embeddings).
- A [Tavily](https://tavily.com/) API key (official docs search).

## Set up

Run every command from the project root. The documents folder and the database files are found
relative to it.

```bash
uv sync
```

Create a `.env` file in the project root:

```env
GOOGLE_API_KEYS=["your-google-key"]
TAVILY_API_KEY=your-tavily-key
```

`GOOGLE_API_KEYS` is a JSON list so you can add more keys to rotate between. If you keep your
secrets in Doppler instead of `.env`, put `doppler run --` in front of the commands below.

## Run it

**1. Ingest the documents** (first time, and after you add, change or remove files in
`documents/`). Unchanged files are skipped, and a run that stopped halfway carries on where it
left off.

```bash
uv run python ingest.py
```

**2. Start the API** in one terminal:

```bash
uv run uvicorn api.main:app --reload
```

It runs at <http://localhost:8000>. Open <http://localhost:8000/docs> to try the endpoints. You do
not need to start the notes server yourself, the API starts it when a note is saved.

**3. Start the web app** in a second terminal:

```bash
uv run streamlit run src/frontend/app.py
```

It opens at <http://localhost:8501>. Type your name in the sidebar to begin. The name keeps your
memory separate from other people's.

## Using the web app

| Page | What it does |
| --- | --- |
| Chat (home) | Ask about your course or about official docs. Ask it to save a note and approve it. |
| Notes | Every saved note, newest first. |
| Memories | The facts it remembers about you. Remove any with the ✕ button. |

On the chat page:

- **Chats.** The sidebar lists your chats, the most recently used first, named after the first
  question. Click one to go back to it. **New chat** starts an empty one. Each name has its own
  list of chats.
- **Sources.** When an answer cites your course materials, for example
  `[Technical Best Practice.pdf, page 12]`, the answer shows a *Sources* line under it. Each link
  opens that file in a new browser tab. A PDF opens at the cited page. A Markdown file opens as
  plain text.

The API is expected at `http://localhost:8000`. If it runs somewhere else, set
`STUDYPILOT_API_URL` before starting Streamlit:

```bash
STUDYPILOT_API_URL=http://localhost:9000 uv run streamlit run src/frontend/app.py
```

Source links are opened by your browser, which may reach the API at a different address than the
Streamlit server does (for example when the two run in containers). Set
`STUDYPILOT_PUBLIC_API_URL` to the address your browser can use. It defaults to
`STUDYPILOT_API_URL`.

## API endpoints

| Method and path | What it does |
| --- | --- |
| `POST /chat` | Send a message. The answer and the files it cites, or a note waiting for approval, come back. |
| `POST /chat/approve` | Save (`true`) or drop (`false`) the note that is waiting. |
| `GET /chat/{thread_id}` | The saved messages of one chat, with the files each answer cites. |
| `GET /notes`, `POST /notes` | List notes, add a note. |
| `GET /notes/{id}`, `PUT /notes/{id}`, `DELETE /notes/{id}` | Read, replace, delete one note. |
| `GET /threads/{user_id}` | The chats of one person, the most recently used first. |
| `GET /memories/{user_id}` | The facts remembered about one person. |
| `DELETE /memories/{user_id}/{fact_id}` | Forget one fact. |
| `GET /documents/{filename}` | A PDF or Markdown file from `documents/`, to show in the browser. |

## Other commands

```bash
uv run langgraph dev   # open the agent in LangGraph Studio to see each step of a run
uv run pytest          # run the tests (the API tests use a fake agent, no keys needed)
uv run pyrefly check   # type check
```

## Where the data lives

These are created in the project root the first time they are needed, and are not committed:

- `chroma_langchain_db/` is the vector store of your documents.
- `notes.sqlite3` holds the saved notes.
- `chat_memory.sqlite3` holds the chats.
- `long_term_memory.sqlite3` holds the remembered facts.
- `threads.sqlite3` holds the list of chats shown in the sidebar.

To start fresh, stop the API and delete the file you want to reset.

Chats from before the chat list existed are not in the list, because only the messages were
saved. Their messages are still in `chat_memory.sqlite3`, and a chat opens if you know its id:
add `&thread=<id>` to the page address.

## Troubleshooting

- **"Could not reach the server"** in the web app: the API is not running, or it is on another
  address. Start it, or set `STUDYPILOT_API_URL`.
- **The API stops at start with "Set GOOGLE_API_KEYS in .env"**: the `.env` file is missing, or
  you ran the command from another folder.
- **A source link says "Document not found"**: the file is not in `documents/` any more, or the
  API was started from another folder. Set `DOCUMENTS_DIR` in `.env` if the files live elsewhere.
- **A source link does not open**: the browser cannot reach the API at the address in the link.
  Set `STUDYPILOT_PUBLIC_API_URL`.
- **Answers say nothing about your course**: run `uv run python ingest.py` first.
- **Ingest fails on a PDF**: check that Java is installed. Failed files are tried again on the
  next run.
