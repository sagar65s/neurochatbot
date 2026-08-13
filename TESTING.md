# NeuroChat — Test Checklist

Run through these before considering a change "done."

## Auth
1. **Signup** — new email/password account → lands on `/chat`, `users/{uid}` doc created in Firestore.
2. **Login** — existing account → lands on `/chat`.
3. **Logout** — clears session, redirects to `/login`; visiting `/chat` afterward redirects back to `/login`.
4. **Google login** — popup flow completes, `users/{uid}` doc created/merged.

## Core chat
5. **New chat** — sidebar entry appears, titled from first message.
6. **Send message** — user bubble appears instantly, assistant streams in progressively.
7. **Receive Gemini response** — real reply with `● gemini` badge.
8. **Conversation memory** — "My name is Alex" → "What is my name?" → correctly answers "Alex" in the same conversation.

## Persistence
9. **Firestore message storage** — check Firebase Console, `conversations/{id}/messages` populated after sending.
10. **Load old chat** — refresh page, previously active conversation and its messages reload correctly.
11. **Rename chat** — sidebar title updates, persists across refresh.
12. **Delete chat** — removed from sidebar and Firestore (including its `messages` subcollection).

## Provider fallback
13. **Gemini rate limit / unavailable** — invalid key or network break → falls back to next configured provider, `provider_used` reflects it.
14. **OpenRouter fallback** — break Gemini only, confirm OpenRouter serves the reply.
15. **Groq fallback** — break Gemini + OpenRouter, confirm Groq serves the reply.
16. **All providers unavailable** — break all three → clean `503` message in the UI, no stack trace, no hang.
17. **Provider order respected** — set `AI_PROVIDER_ORDER=groq,gemini,openrouter` → first successful reply comes from Groq.

## Authorization
18. **Unauthorized conversation access** — call `/api/conversations/{other_user_id}/messages` with your own token → `403`.

## Input validation
19. **Empty message** — blank input can't be sent (button disabled; backend also rejects via Pydantic `min_length=1`).
20. **Very long message** — over 8000 chars rejected with `400`; over `MAX_REQUEST_BODY_BYTES` rejected with `413`.

## Resilience
21. **Backend restart** — stop/start `uvicorn` mid-session → next message shows "Can't reach the server," never a silent hang.
22. **Frontend restart** — refresh mid-conversation → conversation and messages reload from Firestore intact.

## Rate limiting
23. Send 21+ messages within 60s → 21st is blocked with a 429 and friendly message; resets after the window.

## Streaming
24. Response text appears progressively, not all at once.
25. Break the active provider mid-stream (artificial test) → partial content is preserved and saved, marked as interrupted.

## Web Search Grounding (Tavily)
26. **Normal question** ("Explain recursion") → no grounding, no citations, no "grounded" badge.
27. **Current-info question** ("What's the latest AI news today?" / "Who is the current Chief Minister of Tamil Nadu?") → "grounded" badge appears regardless of which provider answers, Sources list renders with clickable links.
28. **Citations persist** — refresh the page after a grounded reply → sources still show (confirms Firestore storage, not just the live SSE event).
29. **Works across all 3 providers** — break Gemini only, ask a current-info question → OpenRouter answers WITH grounding (not previously possible). Break Gemini + OpenRouter → Groq answers WITH grounding too.
30. **Master toggle** — set `ENABLE_SEARCH_GROUNDING=false`, restart → grounding never triggers regardless of keywords.
31. **Keyword tuning** — remove a keyword (e.g. "weather") from `GROUNDING_KEYWORDS`, restart → that category of question no longer triggers grounding.
32. **No Tavily key configured** — leave `TAVILY_API_KEY` blank → grounded-style questions still get answered normally, just without citations (graceful degradation, not a crash).

## Voice messages
33. Tap the mic icon → button turns red and pulses, placeholder changes to "Listening...".
34. Speak a short sentence → text appears in the input box as you talk.
35. Tap the mic again (or stop speaking) → message sends automatically, same as typing + Enter.
36. On a browser without Web Speech API support → mic button doesn't render at all (no broken button).

## Timestamps
37. Every message (user and assistant) shows a time like "10:45 AM" next to Copy/Regenerate.
38. Reloading an old conversation shows the original send time, not the current time.

## Auth reliability
39. **Signup works on the first click** — no need to click twice; account creation and redirect to `/chat` happen in one attempt.
40. **Google sign-in error clarity** — if Google sign-in isn't enabled in Firebase Console, the UI shows the exact fix needed instead of a generic error.

## Responsive / UI
32. Resize below 768px → sidebar collapses into a hamburger-triggered overlay drawer; overlay closes on selection or backdrop click.
33. Toggle dark/light mode → persists across refresh.
34. Long code blocks and long unbroken text don't overflow the message column on mobile widths.
35. Copy button works for both full messages and individual code blocks.
36. Regenerate replaces only the targeted assistant message, not the whole conversation.
