AI Conversation Practice — Realtime Voice Tutor

Overview
Add a realtime AI conversation practice feature allowing learners to speak naturally to an AI tutor and receive spoken and text responses. Audio capture and streaming on the client will use Deepgram's realtime API; the backend will orchestrate session setup, authenticate requests, mediate LLM prompts, and optionally transcribe/forward text when needed.

User Flow
- User opens "Conversation" screen and requests a new practice session.
- Frontend requests a conversation session token from backend (`POST /conversations/session`).
- Backend validates JWT, issues a short-lived conversation token and session id, and returns Deepgram connection info (proxy token or relay endpoint details).
- Frontend establishes a direct WebSocket or WebRTC connection to Deepgram (preferred) using the provided token, streams microphone audio to Deepgram, and receives real-time transcripts and/or interim events.
- Backend subscribes to a conversation WebSocket endpoint (or receives webhook events) to get final transcripts from Deepgram, forwards transcripts to the LLM (Gemini) with a conversation system prompt, and sends the LLM's text response back to the client over a protected WebSocket managed by the backend.
- Optionally, backend requests TTS from Deepgram (or another TTS provider) for the LLM's text reply and streams the audio URL or the audio itself back to the client for playback.

High-level Architecture (Backend)
- New router: `app/routers/conversations.py` — manages session creation and a WebSocket endpoint for client-bounded messages.
- New service: `app/services/deepgram_service.py` — issues/refreshes Deepgram tokens (if proxying) and verifies webhook payloads.
- New service: `app/services/conversation_manager.py` — mediates between Deepgram events and the LLM, maintains in-memory session state for active conversations.
- Use existing `ai_evaluator.py` or a new `llm_client.py` wrapper to call Gemini for conversational responses.
- Session state: store ephemeral conversation metadata (session_id, user_id, language, tone, created_at) in an in-memory store (dict) or lightweight cache (Redis) for scale. No persistent conversation storage by default.

API & WebSocket Endpoints
- POST `/conversations/session` — Protected. Creates a new conversation session. Returns `session_id`, `expires_at`, and Deepgram connection info (either a short-lived token or relay endpoint). No conversation content persisted.
- WS `/conversations/ws/{session_id}` — Protected (JWT). Backend WebSocket that clients connect to receive LLM replies, session events, and status. The client streams minimal control messages here (start/stop), but audio will stream to Deepgram directly where possible.
- POST `/conversations/webhook/deepgram` — (If using webhooks) Receives Deepgram final transcript events (server-to-server). Protected by Deepgram signing key. Backend maps transcript -> session_id -> forwards to conversation_manager.

Deepgram Integration Points
- Token handling: either let frontend connect to Deepgram directly with a time-limited token the backend mints, or proxy audio through backend. Prefer direct client→Deepgram with short-lived token for scalability and latency.
- Events: use realtime streaming for interim+final transcripts. Rely on final transcripts for LLM prompts.
- TTS: use Deepgram TTS or return LLM text and let client request TTS. For low-latency, backend can request TTS audio and return an audio URL or base64 chunk via the WS channel.

LLM (Gemini) Interaction Flow
- For each final transcript from Deepgram:
  - Sanitize transcript and assemble a conversation prompt that includes: session language, user proficiency level, short session memory (last N turns kept in-memory), and system instruction to respond as a tutor focusing on conversational feedback (optionally provide pronunciation tips).
  - Call Gemini to produce a text reply and optional inline evaluation flags (e.g., mark pronunciation issues, grammar corrections). Use structured JSON when possible.
  - Return the LLM text to the client via the backend WS and optionally produce TTS audio.

Session Management
- Sessions are ephemeral and kept in-memory with an expiry (e.g., 10 minutes idle, 1 hour total). Use Redis for production to allow horizontal scaling.
- Each session keeps a short conversation history (last 6 user turns + assistant replies) to maintain context while limiting token usage.
- No conversation history is saved to the database by default. If later requested, add opt-in persistence.

Error Handling Strategy
- Network/transcription failure: surface clear codes to client (retryable vs fatal).
- LLM failure: return a friendly fallback reply ("Sorry, I couldn't process that — try again.") and log for monitoring.
- Deepgram auth failure: rotate/refresh tokens and return 401 to client with instruction to re-initiate session.
- Webhook verification: reject events that fail signature checks and log suspicious activity.

Security Considerations
- Always require the user's backend JWT for session creation; issue short-lived Deepgram tokens scoped to a single session.
- Verify Deepgram webhook signatures for server-to-server events.
- Rate-limit session creation and LLM calls per user to prevent abuse and unexpected costs.

Edge Cases
- Client loses network mid-session: keep session alive for a short window (30s–2min) to allow reconnect; if not reconnected, expire session.
- Multiple devices for same user: either allow multiple concurrent sessions or limit to one; prefer allow but track active sessions to surface limits.
- Very long utterances: enforce a maximum transcript length; if exceeded, ask client to split or decline the chunk.
- Sensitive content: sanitize transcripts before sending to LLM; apply content filters for safety.

Future Scalability
- Swap in Redis for session store to scale across backend instances.
- Move audio proxying to a dedicated streaming gateway if backend needs to mediate audio for moderation or recording.
- Add optional persistence for selected sessions (opt-in) to allow teachers or later review.
- Add monitoring and cost controls on LLM and Deepgram usage.

Implementation Plan (next steps)
1. Design: finalize conversation data shapes, WS message schemas, and sample prompts for the LLM (done in this document).
2. Implement backend session creation endpoint and in-memory session manager.
3. Add `app/services/deepgram_service.py` to mint tokens and verify webhooks.
4. Add `app/routers/conversations.py` with `POST /conversations/session` and WebSocket `/conversations/ws/{session_id}`.
5. Integrate LLM calls (reuse `ai_evaluator` patterns) to produce tutor replies.
6. Add unit tests for session creation, webhook verification, and a WebSocket integration test (mock Deepgram events).
7. Ship minimal client contract in API docs and Postman collection. Update `postman_collection.json`.

Testing Strategy
- Unit tests: test token minting, webhook signature verification, session lifecycle, LLM prompt assembly.
- Integration tests (local, mocked): simulate Deepgram final transcript webhook and assert the backend calls Gemini and pushes a message to the WS client.
- Manual E2E: use a browser client or small test HTML page to stream microphone audio to Deepgram and confirm LLM replies arrive via backend WS and play audio.

Files to Add / Modify
- Add `app/routers/conversations.py` (new)
- Add `app/services/deepgram_service.py` (new)
- Add `app/services/conversation_manager.py` (new)
- Update `app/main.py` to register `conversations` router and CORS/WS settings
- Update `postman_collection.json` with `POST /conversations/session`
