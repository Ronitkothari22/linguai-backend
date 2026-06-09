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
- [x] Create .env.example with these 4 keys: DATABASE_URL, AUTH_JWT_SECRET, GEMINI_API_KEY, ENVIRONMENT
- [x] Create app/config.py using pydantic-settings, reads all env vars, raises clear error if any missing
- [x] Create app/database.py with async SQLAlchemy engine using DATABASE_URL and async session factory
- [ ] Create SQLAlchemy model: users (id, email, name, password_hash, language, level, goal, created_at)
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

- [x] Create app/services/sm2_engine.py
- [x] Implement update_sm2(quality, ease_factor, interval, repetition) -> dict
- [x] quality < 3: reset repetition to 0, interval to 1
- [x] quality >= 3, repetition 0: interval = 1
- [x] quality >= 3, repetition 1: interval = 6
- [x] quality >= 3, repetition > 1: interval = round(interval * ease_factor)
- [x] quality >= 3: repetition += 1
- [x] ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
- [x] ease_factor floor: max(1.3, new_ef)
- [x] next_review_date = date.today() + timedelta(days=new_interval)
- [x] Return dict with ease_factor, interval, repetition, next_review_date
- [x] Create tests/test_sm2.py
- [x] Test quality=5: ease_factor increases, interval grows beyond 6 on 3rd repetition
- [x] Test quality=3: ease_factor stays close to starting value
- [x] Test quality=2: repetition resets to 0, interval resets to 1
- [x] Test quality=0: full reset
- [x] Test repetition=0: interval must equal 1
- [x] Test repetition=1: interval must equal 6
- [x] Test ease_factor never drops below 1.3 even with repeated quality=0
- [x] Test next_review_date is always >= today
- [x] Test return dict has all 4 required keys
- [x] pytest tests/test_sm2.py -v — all tests pass, paste output into task.md test log
- [ ] Commit: feat: SM-2 spaced repetition engine

---

## Phase 3 — AI Evaluation Engine

- [x] Create app/services/ai_evaluator.py
- [x] Import and configure Gemini client using GEMINI_API_KEY from config, model gemini-1.5-flash
- [x] Create Pydantic model: EvaluationError (type, description, correction)
- [x] Create Pydantic model: EvaluationResult (errors list, topics_affected list, overall_quality_score int, feedback_message str)
- [x] Implement async evaluate_answer(user_answer, expected_answer, exercise_type, language) -> EvaluationResult
- [x] System prompt instructs Gemini to return JSON only, no markdown, no preamble
- [x] Parse Gemini response text as JSON and validate with EvaluationResult Pydantic model
- [x] On JSON parse failure: retry once with same inputs
- [x] On second failure: return fallback EvaluationResult with quality_score=0 and generic message
- [x] Function never raises an exception — always returns EvaluationResult
- [x] Create tests/test_ai_evaluator.py with unittest.mock patching Gemini client
- [x] Test: correct answer mock returns quality_score=5 and empty errors list
- [x] Test: wrong tense mock returns error with type="grammar" and topic "Past Tense" in topics_affected
- [x] Test: missing article mock returns grammar error
- [x] Test: malformed Gemini response triggers retry and then returns fallback
- [x] Test: fallback response has quality_score=0 and non-empty feedback_message
- [x] pytest tests/test_ai_evaluator.py -v — all tests pass, paste output into task.md test log
- [x] Commit: feat: AI evaluation engine

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
- [ ] POST /auth/register: validate input + hash password + insert users row + return user_id + access_token
- [ ] POST /auth/login: verify password + return access_token + user profile
- [ ] POST /auth/logout: clear client session contract + return success
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
- [ ] Implement get_current_user dependency using PyJWT to decode custom backend JWT
- [ ] Use AUTH_JWT_SECRET from config
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
============================= test session starts ==============================
platform linux -- Python 3.13.3, pytest-8.4.1, pluggy-1.6.0 -- /home/ronit/.pyenv/versions/3.13.3/bin/python3.13
cachedir: .pytest_cache
rootdir: /home/ronit/Documents/Projects/lingiai/linguai-backend
plugins: anyio-4.13.0, langsmith-0.8.5
collecting ... collected 9 items

tests/test_sm2.py::test_quality_5_increases_ease_factor_and_grows_interval_beyond_six_on_third_review PASSED [ 11%]
tests/test_sm2.py::test_quality_3_keeps_ease_factor_close_to_starting_value PASSED [ 22%]
tests/test_sm2.py::test_quality_2_resets_repetition_and_interval PASSED  [ 33%]
tests/test_sm2.py::test_quality_0_full_reset PASSED                      [ 44%]
tests/test_sm2.py::test_repetition_zero_sets_interval_to_one PASSED      [ 55%]
tests/test_sm2.py::test_repetition_one_sets_interval_to_six PASSED       [ 66%]
tests/test_sm2.py::test_ease_factor_never_drops_below_one_point_three PASSED [ 77%]
tests/test_sm2.py::test_next_review_date_is_always_today_or_later PASSED [ 88%]
tests/test_sm2.py::test_return_dict_has_all_required_keys PASSED         [100%]

============================== 9 passed in 0.06s ===============================
```

### Phase 3 — AI Evaluator
```
============================= test session starts ==============================
platform linux -- Python 3.13.3, pytest-9.0.3, pluggy-1.6.0 -- /home/ronit/Documents/Projects/lingiai/linguai-backend/venv/bin/python
cachedir: .pytest_cache
rootdir: /home/ronit/Documents/Projects/lingiai/linguai-backend
plugins: asyncio-1.4.0, anyio-4.13.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 5 items

tests/test_ai_evaluator.py::test_correct_answer_mock_returns_quality_five_and_empty_errors_list PASSED [ 20%]
tests/test_ai_evaluator.py::test_wrong_tense_mock_returns_grammar_error_and_past_tense_topic PASSED [ 40%]
tests/test_ai_evaluator.py::test_missing_article_mock_returns_grammar_error PASSED [ 60%]
tests/test_ai_evaluator.py::test_malformed_gemini_response_triggers_retry_and_then_returns_fallback PASSED [ 80%]
tests/test_ai_evaluator.py::test_fallback_response_has_quality_zero_and_non_empty_feedback_message PASSED [100%]

=============================== warnings summary ===============================
app/services/ai_evaluator.py:6
  /home/ronit/Documents/Projects/lingiai/linguai-backend/app/services/ai_evaluator.py:6: FutureWarning:

  All support for the `google.generativeai` package has ended. It will no longer be receiving
  updates or bug fixes. Please switch to the `google.genai` package as soon as possible.
  See README for more details:

  https://github.com/google-gemini/deprecated-generative-ai-python/blob/main/README.md

    import google.generativeai as genai

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 5 passed, 1 warning in 1.62s =========================
```

### Phase 4 — Lesson Generator
```
paste pytest -v output here
```

### Phase 7 — Integration
```
paste pytest -v output here
```
