# Skill Opportunity Matcher

A small FastAPI service for publishing opportunities and explaining learner-opportunity matches.

## Run

```bash
docker compose up --build
```

The API is at `http://localhost:8000`; Swagger UI is at `/docs`. Compose waits for PostgreSQL, seeds the demo data, and then starts the API.

Seed credentials:
- Admin: `admin@example.com` / `admin123`
- Learners: `learner1@example.com` ... `learner5@example.com` / `learner123`

Seed and run locally:

```bash
python -m pip install -r backend/requirements.txt
cd backend
python seed.py
uvicorn app.main:app --reload
```

Tests:

```bash
cd backend
pytest -q
python evaluate.py
```

Set `DATABASE_URL` to use another database. Docker Compose uses PostgreSQL with pgvector and creates an HNSW cosine index for opportunity embeddings. SQLite remains supported for tests, where vectors are stored as JSON and ranked locally.

The backend application, its tests, seed/evaluation scripts, and agent tool definitions are in `backend/`. The React learner interface is in `frontend/` and supports account access, skill profile editing, and ranked matches with explanations. Run the backend on port 8000, then run `npm install` and `npm run dev` from `frontend/` to open the UI at `http://localhost:5173`.

## API overview

- `POST /auth/signup`, `POST /auth/login`
- `POST/PUT/DELETE /opportunities/{id}` (admin only); `GET /opportunities`
- `GET/PUT /profile` (authenticated learner's own profile)
- `POST /profile/extract-skills`
- `GET /matches?mode=rules|hybrid&type=job|course&limit=20`
- `GET /matches/{opportunity_id}` (explain one opportunity for the authenticated learner)
- `GET /agent/tools`, `GET /health`

Validation failures and HTTP errors return `{"error":{"code","message","details"}}` shaped JSON. No stack traces are returned.

## Matching

For each required skill, full weight is earned when learner level >= minimum level. Otherwise, credit is `weight * learner_level/minimum_level`, capped at full credit. The final score is earned weight divided by total required weight, from 0-100. Missing or under-level skills are listed explicitly. Opportunities with no skills get 0 in a rules-only result and cannot distort weighted credit. Ties use title, then opportunity ID.

Names are trimmed, lowercased, separator-normalised, and alias-mapped (for example `JS` -> `javascript`, `postgres` -> `postgresql`, `k8s` -> `kubernetes`). Learner and opportunity skill lists are deduplicated.

Semantic ranking embeds opportunity title, description and skills, and learner bio plus skills using `BAAI/bge-small-en-v1.5` via FastEmbed. Embedding is local. The top 20 cosine candidates are retained. `EMBEDDING_PROVIDER=off` or model startup failure uses a deterministic local hash fallback for tests and offline resilience.

Hybrid ranking uses Reciprocal Rank Fusion with k=60 across rule rank and semantic rank. RRF combines the two ranked lists without requiring their score scales to be comparable; k=60 reduces the influence of small rank changes near the top. Each result reports rule and semantic RRF contributions. Ties use title and ID.

## AI-assist and agent readiness

Resume extraction is dictionary/rule based and never executes text. It detects known skills and simple experience phrases, returning level and confidence. Hidden instructions are ignored because text is matched only against a fixed dictionary and regex; it is not passed to a shell, template or prompt. An optional LLM provider can be added behind a provider interface and `LLM_PROVIDER` configuration. It would be off by default and can point to a cloud or OpenAI-compatible self-hosted endpoint without API route changes.

Tool definitions are in `backend/agent/tools.json` and available at `/agent/tools`. An agent authenticates as a learner, calls search/explain/extract over the REST API, and logs tool calls. `explain_match` requests `/matches/{opportunity_id}` to return a single opportunity's rule-based explanation. Public sign-up always creates a learner; the seeded admin account is provisioned separately. Profile routes derive the user from JWT and opportunity management requires admin JWT.

## Evaluation

From the `backend/` directory, run `python evaluate.py`. The script uses 10 synthetic learner profiles and 12 labelled opportunities. It reports precision@5 and NDCG@5 using the checked-in `backend/evaluation/labelled_data.json`.

<!-- EVALUATION_RESULTS -->
| Mode | Precision@5 | NDCG@5 |
|---|---:|---:|
| Rules | 0.2600 | 1.0000 |
| Semantic | 0.2600 | 1.0000 |
| Hybrid | 0.2600 | 1.0000 |

The deterministic fallback embedding produced the same ranking quality as the rules in this small synthetic labelled set. That is honest but limited evidence: it does not yet demonstrate a FastEmbed semantic improvement. With the real model enabled, the set should be rerun before interpreting semantic gains. The labels are intentionally broad, and the 12-opportunity catalogue makes perfect top-five precision impossible for all profiles.

## Assumptions and limitations

- One learner profile per user; profile visibility is self-only.
- Resume extraction is intentionally conservative and cannot infer all real skills.
- Semantic retrieval uses one local general embedding model, not a domain-fine-tuned model.
- The evaluation set is small and synthetic; collect real learner relevance judgements and compare ranking quality before making production claims.
- The minimal React learner UI is included as an optional stretch goal.

## If I had another week

I would collect a larger set of real, consented learner-opportunity relevance labels, tune and compare the rule, semantic, and hybrid rankers against that set, and add an admin interface for managing opportunities. I would also measure pgvector recall and latency as the opportunity catalogue grows.

## AI tools used

Copilot SDK in VS Code was used to scaffold code and tests. I checked the requirements and implementation behavior and can explain every submitted line.
