# NeuroChat

A ChatGPT-style AI chatbot with automatic fallback across Gemini, OpenRouter, and Groq, plus Google Search Grounding for current-events questions — built with Next.js, FastAPI, and Firebase.

## Features

- Email/password + Google authentication (Firebase Auth)
- Multi-conversation chat with persistent history (Firestore)
- Conversation memory with a bounded, token-aware context window
- Automatic AI provider fallback: Gemini → OpenRouter → Groq
- **Live Web Search Grounding (Tavily)** — questions about current events, news, prices, or "latest" anything automatically trigger a web search, and the results are handed to whichever provider answers — works identically for Gemini, OpenRouter, and Groq, not just one of them
- **Voice messages** — tap the mic, speak, and it's transcribed and sent automatically, like a voice note (Web Speech API, Chrome-based browsers)
- **Message timestamps** — every message shows the time it was sent
- Real-time streaming responses (Server-Sent Events)
- Markdown rendering, syntax-highlighted code blocks, copy buttons
- Regenerate response
- Dark / light mode
- Fully responsive, including a mobile drawer sidebar
- Per-user rate limiting and request size limits
- Ownership-checked, token-verified backend — no data leakage between users

## Architecture

```
                 USER
                   ↓
           Next.js Frontend (TypeScript, Tailwind)
                   ↓
          Firebase Authentication (client SDK)
                   ↓
              FastAPI Backend
                   ↓
     should_ground(message)? ──── keyword check
                   ↓
            AI Model Manager
                   ↓
    ┌──────────────┼──────────────┐
    ↓              ↓              ↓
 Gemini        OpenRouter        Groq
 (+ Google         ↓              ↓
  Search if   (no grounding) (no grounding)
  grounded)       ↓              ↓
    └──────────────┼──────────────┘
                   ↓
             Firestore (conversations, messages, citations)
```

## Technology stack

**Frontend:** Next.js, React, TypeScript, Tailwind CSS, react-markdown, react-syntax-highlighter
**Backend:** Python, FastAPI, Pydantic, httpx, google-genai, groq
**Auth & DB:** Firebase Authentication, Cloud Firestore
**AI:** Gemini (primary, with optional Google Search Grounding), OpenRouter (fallback), Groq (fallback)

## Folder structure

```
neurochat/
├── frontend/                 Next.js app
│   ├── app/                   pages: /, /login, /signup, /chat
│   ├── components/            Sidebar, MessageBubble, ChatInput, SourcesList, etc.
│   ├── hooks/                 useAuth, useTheme
│   ├── lib/                   firebase.ts, api.ts, mockChat.ts (makeId helper)
│   └── types/                 auth.ts, chat.ts
├── backend/                   FastAPI app
│   └── app/
│       ├── api/routes/         health, chat, conversations
│       ├── api/dependencies/   auth, rate_limit
│       ├── middleware/         security headers, request size limit
│       ├── providers/          gemini, openrouter, groq + base interface
│       ├── services/           ai_model_manager, conversation_service, grounding
│       ├── firebase/           admin SDK setup
│       ├── config/             settings
│       └── schemas/            chat, conversation Pydantic models
├── firebase/
│   └── firestore.rules
├── TESTING.md
├── README.md
└── .gitignore
```

## Firestore data model

```
users/{userId}
  uid, email, displayName, createdAt

conversations/{conversationId}
  id, userId, title, createdAt, updatedAt

conversations/{conversationId}/messages/{messageId}
  id, conversationId, userId, role, content,
  modelUsed, providerUsed, citations[], createdAt   ← displayed as a timestamp in the UI
```

## Setup

### 1. Firebase project
1. [console.firebase.google.com](https://console.firebase.google.com) → create a project.
2. **Authentication** → enable Email/Password and Google sign-in.
3. **Firestore Database** → create in production mode.
4. Deploy `firebase/firestore.rules` (Firebase CLI: `firebase deploy --only firestore:rules`, or paste into Console → Rules → Publish).
5. **Project Settings** → add a Web app → copy the config into `frontend/.env.local` (copy from `.env.local.example`).
6. **Project Settings → Service accounts** → generate a private key → use its values for `backend/.env` (`FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`). Never commit this file.

### 2. AI providers
- **Gemini** *(required)*: key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey), models at [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models).
- **OpenRouter** *(optional)*: key at [openrouter.ai/keys](https://openrouter.ai/keys), models at [openrouter.ai/models](https://openrouter.ai/models).
- **Groq** *(optional)*: key at [console.groq.com/keys](https://console.groq.com/keys), models at [console.groq.com/docs/models](https://console.groq.com/docs/models) (check the [deprecations page](https://console.groq.com/docs/deprecations)).
- **Tavily** *(optional but recommended)*: free key at [tavily.com](https://tavily.com) — powers live web search grounding for all three providers above (1,000 free searches/month on the free tier).

Set these in `backend/.env` (copy from `.env.example`).

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in Firebase + AI provider values
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in Firebase web config
npm run dev
```

Visit `http://localhost:3000`.

## Environment variables

**`backend/.env`** — Firebase Admin credentials, AI provider keys/models, `AI_PROVIDER_ORDER`, conversation memory limits (`MAX_HISTORY_MESSAGES`, `MAX_CONTEXT_TOKENS`, `SYSTEM_PROMPT`), rate limit settings, grounding settings (`ENABLE_GOOGLE_SEARCH_GROUNDING`, `GROUNDING_KEYWORDS`), `FRONTEND_URL`.

**`frontend/.env.local`** — Firebase web config (public identifiers, safe for the browser), `NEXT_PUBLIC_API_BASE_URL`.

Never put AI provider keys or `FIREBASE_PRIVATE_KEY` in the frontend env file.

## How Web Search Grounding works (Tavily)

1. Every incoming chat message is checked against `GROUNDING_KEYWORDS` (case-insensitive substring match, plus a recent-year check) in `backend/app/services/grounding.py`.
2. If it matches, the backend calls **Tavily** (`backend/app/services/tavily_search.py`) once, before contacting any AI provider.
3. The search results are formatted as plain context and appended to the conversation history as a system-role message.
4. Whichever provider ends up answering — Gemini, OpenRouter, or Groq — sees this context and answers from it. This is different from the earlier approach of relying on Gemini's own built-in search tool, which only worked for Gemini and was inconsistent about returning citations.
5. Citations are known immediately from Tavily's response (not extracted from the AI's reply), stored in Firestore with the message, and rendered as a "Sources" list under the reply with a "grounded" badge.
6. If Tavily has no key configured or the search fails, the app degrades gracefully — the question still gets answered, just without live grounding.

Tune `GROUNDING_KEYWORDS` in `.env` anytime without touching code. Set `ENABLE_SEARCH_GROUNDING=false` to disable the feature entirely.

## Voice messages

Tap the microphone icon next to the send button. While listening, the mic turns red and pulses. Speak your message, then tap the mic again — the transcribed text is sent automatically, the same way a voice note works. Uses the browser's built-in Web Speech API, so no backend changes or API keys are needed; works best in Chrome-based browsers (Safari/Firefox support is more limited). If the browser doesn't support it, the mic button doesn't appear at all.

## API reference

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | none | Liveness check |
| POST | `/api/chat` | required | Send a message, get a full (non-streamed) reply |
| POST | `/api/chat/stream` | required | Send a message, get an SSE token stream + citations |
| GET | `/api/conversations` | required | List the caller's conversations |
| GET | `/api/conversations/{id}` | required | Get one conversation |
| PATCH | `/api/conversations/{id}` | required | Rename a conversation |
| DELETE | `/api/conversations/{id}` | required | Delete a conversation and its messages |
| GET | `/api/conversations/{id}/messages` | required | List messages in a conversation (includes citations) |

All protected routes require `Authorization: Bearer <firebase_id_token>`. Ownership of `conversation_id` is always verified server-side against the token's `uid`.

## Testing

See `TESTING.md` for the full 36-case checklist covering auth, persistence, fallback, authorization, streaming, rate limiting, grounding, and responsive UI.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| CORS error in browser console | `FRONTEND_URL` in backend `.env` doesn't match the frontend's actual origin |
| 401 on every request | Firebase auth state not hydrated yet, or session expired — retry after a moment or re-login |
| `FAILED_PRECONDITION: query requires an index` | Follow the index-creation link in backend logs (needed for the `userId` + `updatedAt` conversation list query) |
| Gemini `ImportError` | Old `google-generativeai` installed instead of `google-genai` — reinstall from `requirements.txt` |
| Groq `model_decommissioned` | `GROQ_MODEL` points at a retired model — check [console.groq.com/docs/models](https://console.groq.com/docs/models) |
| Streaming arrives all at once | A reverse proxy is buffering the response — check proxy config for SSE support |
| 429 "sending too quickly" | Per-user rate limit — adjust `CHAT_RATE_LIMIT_REQUESTS`/`_WINDOW_SECONDS` in `.env` |
| No citations on an obviously current question | Check backend logs for "Tavily returned N result(s)" — if `TAVILY_API_KEY` is missing, grounding silently skips; if present but 0 results, broaden `GROUNDING_KEYWORDS` or the query itself may be too obscure for Tavily to find anything |
| Signup/login needs two clicks | Should be fixed — `useAuth.tsx` now sets user state immediately on success instead of waiting for Firebase's async listener. If you still see this, hard-refresh to clear a stale build |
| "Continue with Google" does nothing / errors | Almost always a Firebase Console setup step, not a code issue — see below |
| Mic button doesn't appear | Browser doesn't support the Web Speech API — use Chrome, or type instead |

### Fixing "Continue with Google"

You do **not** need to manually create or paste a Google OAuth Client ID anywhere in this codebase — Firebase's built-in Google provider handles that automatically once enabled. If the button isn't working:

1. Firebase Console → **Authentication** → **Sign-in method** → click **Google** → toggle **Enable** → set a support email → **Save**.
2. Firebase Console → **Authentication** → **Settings** → **Authorized domains** → confirm `localhost` is listed (for local dev) and your production domain (once deployed).
3. Restart the frontend dev server after any Console change and try again.

If it still fails, the exact reason now shows in the UI itself (e.g. "Google sign-in isn't enabled for this project yet...") instead of a generic error — that message tells you precisely which step above to redo.

## Future improvements

The architecture is already structured for these:

- **RAG:** PDF/doc upload → chunking → embeddings → vector DB (ChromaDB/Pinecone/Weaviate) → retriever feeding into the existing `AIProvider` context pipeline.
- **Image understanding, voice input/output:** extend `ChatMessage` to carry attachments; Gemini and OpenRouter both support multimodal input at the API level already.
- **Web search as a general tool / agents:** the grounding pattern built here (`should_ground` → tool-enabled provider call → citation extraction) generalizes to other tool-calling use cases.
- **Chat export, sharing:** straightforward additions to `conversation_service.py` + a new route.
- **Additional AI providers:** implement `AIProvider`, register in `AIModelManager._registry`, add to `AI_PROVIDER_ORDER` — no other code changes needed.
