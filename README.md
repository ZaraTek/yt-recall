# YouTube Recall

Turn any YouTube video into an AI-generated summary and active-recall practice
so educational content actually sticks. Paste a link, get a summary, key points,
and a mix of flashcards, multiple-choice, and open-ended questions. Save
everything (plus your own notes) to a personal, Google-authenticated library.

## Features

- Paste a YouTube link to generate a summary + recall questions.
- Mixed practice: flashcards (self-graded), multiple-choice (auto-graded), and
  open-ended (reveal + self-grade), with an end-of-session score.
- Personal library of watched videos with summaries, questions, and notes.
- Manual note-taking with autosave.
- Google sign-in; each user's library is private to them.

## Tech stack

- Frontend: React + Vite + TypeScript, React Router, TanStack Query,
  `@react-oauth/google`.
- Backend: Python FastAPI, `youtube-transcript-api`, Gemini 2.0 Flash
  (`google-genai`), MongoDB via `motor`, Google ID token verification via
  `google-auth`.
- Hosting: Vercel (SPA static build + Python serverless function under `/api`).

## Project layout

```
.
├── api/                 # FastAPI backend
│   ├── index.py         # App entry (ASGI `app`)
│   ├── config.py        # Settings / env
│   ├── db.py            # MongoDB (motor) connection + indexes
│   ├── auth.py          # Google ID token verification dependency
│   ├── models.py        # Pydantic models
│   ├── routers/videos.py
│   ├── services/transcript.py
│   ├── services/gemini.py
│   └── requirements.txt
├── frontend/            # Vite React app
│   └── src/
├── vercel.json
└── .env.example
```

## Prerequisites

- A Google OAuth 2.0 Client ID (type: Web application). Add your dev origin
  (`http://localhost:5173`) and your production domain to the allowed
  JavaScript origins.
- A Gemini API key from https://aistudio.google.com/apikey.
- A MongoDB Atlas cluster and connection string.

## Local development

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

The backend reads `.env` from the repo root (or `api/`), and the frontend reads
`VITE_*` variables from `frontend/.env` (or via your shell). See `.env.example`
for all keys.

### Backend

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Run from the api/ directory so absolute imports resolve:
uvicorn index:app --reload --port 8000
```

The API will be available at `http://localhost:8000` (docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
# Create frontend/.env with:
#   VITE_GOOGLE_CLIENT_ID=...
#   VITE_API_BASE=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`.

## Environment variables

| Variable | Where | Purpose |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` | backend | Verifies incoming Google ID tokens |
| `GEMINI_API_KEY` | backend | Gemini 2.0 Flash access |
| `MONGODB_URI` | backend | MongoDB Atlas connection string |
| `MONGODB_DB` | backend | Database name (default `yt_recall`) |
| `CORS_ORIGINS` | backend | Comma-separated allowed origins |
| `VITE_GOOGLE_CLIENT_ID` | frontend | Google sign-in button |
| `VITE_API_BASE` | frontend | API base URL (leave empty in prod) |

## Deployment (Vercel)

1. Import the repository into Vercel.
2. Add the backend env vars (`GOOGLE_CLIENT_ID`, `GEMINI_API_KEY`,
   `MONGODB_URI`, `MONGODB_DB`, `CORS_ORIGINS`) and the frontend build var
   `VITE_GOOGLE_CLIENT_ID`. Leave `VITE_API_BASE` empty so the SPA calls the
   same-origin `/api`.
3. `vercel.json` routes `/api/*` to the FastAPI Python function and serves the
   Vite build for everything else.

## Known limitations

- `youtube-transcript-api` is sometimes IP-blocked on cloud hosts (including
  Vercel). If transcript fetching fails in production, a rotating proxy or a
  Gemini video-URL fallback would be the next step. Videos without captions
  are reported to the user with a clear message.
