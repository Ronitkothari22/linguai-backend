# LinguAI Backend — Task Tracker

> Read this before every session. Mark tasks [x] when done. Never delete tasks.

**Stack:** FastAPI · SQLAlchemy (async) · Supabase PostgreSQL · Gemini API · SM-2 Algorithm
**Agent:** backend-agent
**Status:** 🟡 In Progress

---

## Phase 1 — Project Scaffold

- [x] git init inside linguai-backend/
- [x] python -m venv venv and install all packages from BACKEND_AGENT.md
- [x] pip freeze > requirements.txt
- [x] Create complete folder structure matching BACKEND_AGENT.md exactly
- [x] Create .gitignore (venv/, .env, __pycache__/, *.pyc, .pytest_cache/)
- [x] Create .env.example with all 5 keys: SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET, DATABASE_URL, GEMINI_API_KEY, ENVIRONMENT
- [x] Create app/config.py using pydantic-settings, reads all env vars, raises clear error if any missing
- [x] Create app/database.py with async SQLAlchemy engine using DATABASE_URL and async session factory
- [x] Create SQLAlchemy model: users (id, email, name, language, level, goal, created_at)
- [x] Create SQLAlchemy model: lessons (id, user_id FK, topics ARRAY, content JSONB, score, completed_at, created_at)
- [x] Create SQLAlchemy model: mistakes (id, user_id FK, topic, error_type, frequency, last_seen, created_at, UNIQUE user_id+topic+error_type)
- [x] Create SQLAlchemy model: sm2_cards (id, user_id FK, topic, ease_factor, interval, repetition, next_review DATE, created_at, UNIQUE user_id+topic)
- [x] Create SQLAlchemy model: progress (id, user_id FK, topic, mastery_score, updated_at, UNIQUE user_id+topic)
- [x] Create Pydantic schemas for users (UserCreate, UserResponse, UserProfile)
- [x] Create Pydantic schemas for lessons (Exercise, Lesson, LessonSubmitRequest, LessonSubmitResponse)
- [x] Create Pydantic schemas for mistakes (MistakeCreate, MistakeResponse)
- [x] Create Pydantic schemas for sm2_cards (SM2CardResponse)
- [x] Create Pydantic schemas for progress (ProgressResponse, DashboardResponse, WeakTopicResponse)
- [x] Create app/main.py: FastAPI instance, register all routers, CORS allow all origins for dev
- [x] GET /health returns {"status": "ok", "version": "1.0.0"}
- [ ] Run uvicorn app.main:app --reload and confirm health check returns 200
- [ ] Commit: chore: project scaffold and database models

---

## Phase 2 — SM-2 Engine

- [ ] Create app/services/sm2_engine.py
- [ ] Implement update_sm2(quality, ease_factor, interval, repetition) -> dict
- [ ] quality < 3: reset repetition to 0, interval to 1
- [ ] quality >= 3, repetition 0: interval = 1
- [ ] quality >= 3, repetition 1: interval = 6
- [ ] quality >= 3, repetition > 1: interval = round(interval * ease_factor)
- [ ] quality >= 3: repetition += 1
- [ ] ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
- [ ] ease_factor floor: max(1.3, new_ef)
- [ ] next_review_date = date.today() + timedelta(days=new_interval)
- [ ] Return dict with ease_factor, interval, repetition, next_review_date
- [ ] Create tests/test_sm2.py
- [ ] Test quality=5: ease_factor increases, interval grows beyond 6 on 3rd repetition
- [ ] Test quality=3: ease_factor stays close to starting value
- [ ] Test quality=2: repetition resets to 0, interval resets to 1
- [ ] Test quality=0: full reset
- [ ] Test repetition=0: interval must equal 1
- [ ] Test repetition=1: interval must equal 6
- [ ] Test ease_factor never drops below 1.3 even with repeated quality=0
- [ ] Test next_review_date is always >= today
- [ ] Test return dict has all 4 required keys
- [ ] pytest tests/test_sm2.py -v — all tests pass, paste output into task.md test log
- [ ] Commit: feat: SM-2 spaced repetition engine

---

## Phase 3 — AI Evaluation Engine

- [ ] Create app/services/ai_evaluator.py
- [ ] Import and configure Gemini client using GEMINI_API_KEY from config, model gemini-1.5-flash
- [ ] Create Pydantic model: EvaluationError (type, description, correction)
- [ ] Create Pydantic model: EvaluationResult (errors list, topics_affected list, overall_quality_score int, feedback_message str)
- [ ] Implement async evaluate_answer(user_answer, expected_answer, exercise_type, language) -> EvaluationResult
- [ ] System prompt instructs Gemini to return JSON only, no markdown, no preamble
- [ ] Parse Gemini response text as JSON and validate with EvaluationResult Pydantic model
- [ ] On JSON parse failure: retry once with same inputs
- [ ] On second failure: return fallback EvaluationResult with quality_score=0 and generic message
- [ ] Function never raises an exception — always returns EvaluationResult
- [ ] Create tests/test_ai_evaluator.py with unittest.mock patching Gemini client
- [ ] Test: correct answer mock returns quality_score=5 and empty errors list
- [ ] Test: wrong tense mock returns error with type="grammar" and topic "Past Tense" in topics_affected
- [ ] Test: missing article mock returns grammar error
- [ ] Test: malformed Gemini response triggers retry and then returns fallback
- [ ] Test: fallback response has quality_score=0 and non-empty feedback_message
- [ ] pytest tests/test_ai_evaluator.py -v — all tests pass, paste output into task.md test log
- [ ] Commit: feat: AI evaluation engine

---

## Phase 4 — Lesson Generator and Recommendation Engine

- [ ] Create app/services/recommendation.py
- [ ] Define STARTER_TOPICS dict: beginner (5 topics), intermediate (5 topics), advanced (5 topics) — use values from BACKEND_AGENT.md
- [ ] Implement async get_due_topics(user_id, db, level) -> list[str]
- [ ] Query sm2_cards WHERE user_id = user_id AND next_review <= today
- [ ] Order by next_review ASC
- [ ] Take top 5 results
- [ ] If empty result: return STARTER_TOPICS[level]
- [ ] Create app/services/lesson_generator.py
- [ ] Implement async generate_lesson(user_id, topics, language, level, goal) -> dict
- [ ] Build Gemini prompt specifying: language, level, goal, topics, exact exercise distribution (2 fill_blank, 1 sentence_correction, 1 translation, 1 vocabulary_match)
- [ ] Prompt instructs Gemini to return JSON array only, no markdown
- [ ] Parse response into list of exercise dicts
- [ ] Add UUID id to each exercise
- [ ] Build and return full lesson dict: lesson_id (new UUID), topics, exercises
- [ ] Save lesson to lessons table in DB
- [ ] Create tests/test_lesson_generator.py with mocked Gemini
- [ ] Test: result always contains exactly 5 exercises
- [ ] Test: each exercise has id, type, prompt, answer, hint, topic keys
- [ ] Test: exercise types match expected distribution
- [ ] Test: lesson is saved to DB (mock DB session)
- [ ] pytest tests/test_lesson_generator.py -v — all tests pass, paste output into task.md test log
- [ ] Commit: feat: lesson generator and recommendation engine

---

## Phase 5 — API Endpoints

> Add each endpoint to postman_collection.json immediately after building it.

- [ ] Create app/routers/auth.py
- [ ] POST /auth/register: Supabase sign_up + insert users row + return user_id + access_token
- [ ] POST /auth/login: Supabase sign_in + fetch user row + return access_token + user profile
- [ ] POST /auth/logout: Supabase sign_out + return success
- [ ] Add all 3 auth endpoints to postman_collection.json with examples and test scripts
- [ ] Login test script saves access_token as {{auth_token}} environment variable

- [ ] Create app/routers/onboarding.py
- [ ] POST /onboarding/setup: update users row + create 5 sm2_cards + create 5 progress rows + return user_profile and starter_topics
- [ ] Add to postman_collection.json

- [ ] Create app/routers/lessons.py
- [ ] GET /lessons/today: check for existing today's lesson → if exists return it → if not generate new one via recommendation + lesson_generator
- [ ] POST /lessons/submit: evaluate answer → upsert mistakes → update sm2_cards → update progress → return evaluation + topics_updated + mastery_snapshot
- [ ] GET /lessons/history: paginated query of lessons table, query params limit and offset
- [ ] Add all 3 lesson endpoints to postman_collection.json

- [ ] Create app/routers/progress.py
- [ ] GET /progress/dashboard: calculate streak + fetch all progress rows + count weak topics + return DashboardResponse
- [ ] GET /progress/weak-topics: query progress where mastery_score < 0.6, join sm2_cards for next_review, join mistakes for frequency
- [ ] Add both progress endpoints to postman_collection.json

- [ ] Confirm all 10 endpoints exist: /health, /auth/register, /auth/login, /auth/logout, /onboarding/setup, /lessons/today, /lessons/submit, /lessons/history, /progress/dashboard, /progress/weak-topics
- [ ] Commit: feat: all API endpoints

---

## Phase 6 — JWT Middleware

- [ ] Create app/utils/jwt_middleware.py
- [ ] Implement get_current_user dependency using PyJWT to decode Supabase JWT
- [ ] Use SUPABASE_JWT_SECRET from config
- [ ] Extract sub field as user_id
- [ ] Raise HTTPException 401 on expired token
- [ ] Raise HTTPException 401 on invalid token
- [ ] Raise HTTPException 401 if sub is missing
- [ ] Apply dependency to onboarding, lessons, and progress routers
- [ ] Do NOT apply to auth router or health endpoint
- [ ] Manual test: request to GET /lessons/today without token returns 401
- [ ] Manual test: request with valid token returns 200
- [ ] Commit: feat: JWT auth middleware

---

## Phase 7 — Integration Tests

- [ ] Create tests/test_integration.py
- [ ] Test full happy path: register → login → onboard → get today's lesson → submit one answer → get progress dashboard
- [ ] Assert: after register, user exists in users table
- [ ] Assert: after onboard, 5 sm2_cards exist for user
- [ ] Assert: after submit with wrong answer, mistake row exists or frequency incremented
- [ ] Assert: after submit, sm2_card for affected topic was updated
- [ ] Assert: after submit, progress mastery_score was updated
- [ ] Assert: GET /progress/dashboard returns streak >= 1 after first lesson submission
- [ ] Edge case test: GET /lessons/today for brand new user returns starter lesson (not empty)
- [ ] Edge case test: submit same answer twice for same exercise does not duplicate mistake rows
- [ ] pytest tests/ -v — all tests across all files pass, paste output into task.md test log
- [ ] Commit: test: integration test suite

---

## API Endpoint Status

| Method | Path | Built | Postman | Tested |
|--------|------|-------|---------|--------|
| GET | /health | [ ] | [ ] | [ ] |
| POST | /auth/register | [ ] | [ ] | [ ] |
| POST | /auth/login | [ ] | [ ] | [ ] |
| POST | /auth/logout | [ ] | [ ] | [ ] |
| POST | /onboarding/setup | [ ] | [ ] | [ ] |
| GET | /lessons/today | [ ] | [ ] | [ ] |
| POST | /lessons/submit | [ ] | [ ] | [ ] |
| GET | /lessons/history | [ ] | [ ] | [ ] |
| GET | /progress/dashboard | [ ] | [ ] | [ ] |
| GET | /progress/weak-topics | [ ] | [ ] | [ ] |

---

## Database Table Status

| Table | Model | Schema | In DB | Tested |
|-------|-------|--------|-------|--------|
| users | [ ] | [ ] | [ ] | [ ] |
| lessons | [ ] | [ ] | [ ] | [ ] |
| mistakes | [ ] | [ ] | [ ] | [ ] |
| sm2_cards | [ ] | [ ] | [ ] | [ ] |
| progress | [ ] | [ ] | [ ] | [ ] |

---

## Blockers

> Add blockers here. Mark resolved ones [resolved]. Never delete.

- Uvicorn could not bind to `127.0.0.1:8000` or `127.0.0.1:8001` in this sandbox, so `/health` was verified with an in-process ASGI request instead. [pending]

---

## Test Results Log

### Phase 2 — SM-2 Engine
```
paste pytest -v output here
```

### Phase 3 — AI Evaluator
```
paste pytest -v output here
```

### Phase 4 — Lesson Generator
```
paste pytest -v output here
```

### Phase 7 — Integration
```
paste pytest -v output here
```
