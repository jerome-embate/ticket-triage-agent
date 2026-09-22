# Ticket Triage Agent

A support-ticket triage agent built on [`pydantic-ai`](https://ai.pydantic.dev/). Given an incoming support ticket, an LLM agent uses tools — knowledge-base search, account lookup, and known-issues check — to classify the ticket and draft a response, returning a structured `TicketResolution`. Exposed via a single FastAPI endpoint.

## How it works

1. A ticket (`ticket_id`, `customer_id`, `subject`, `body`) comes in through `POST /triage_ticket`.
2. A `pydantic_ai.Agent` (model: `anthropic:claude-sonnet-4-5`) receives the ticket and decides which tools to call:
   - **`search_kb`** — semantic search over an in-memory knowledge base.
   - **`check_account_status`** — looks up the customer's plan, account status, and ticket history.
   - **`check_known_issues`** — checks for active incidents matching keywords from the ticket.
3. The agent is instructed to ground its triage decision and suggested response only in tool output — not invented information.
4. The agent returns a structured `TicketResolution`: category, urgency, confidence, reasoning, a suggested response, whether to escalate to a human, and any relevant KB articles.

All "backend" data (customers, known issues, KB articles) is fake, in-memory seed data — there's no real database or ticketing system behind this.

## Architecture

```
api.py → agent.py:triage_ticket → pydantic_ai.Agent → TicketResolution
```

| File | Responsibility |
|---|---|
| `models.py` | Pydantic schemas: `IncomingTicket` (API input), `TriageResult` (category/urgency/confidence/reasoning), `TicketResolution` (final agent output). `TicketCategory` and `UrgencyLevel` are the fixed enums the LLM must choose from. |
| `agent.py` | Defines the `pydantic_ai.Agent`, its system prompt, and its three `@agent.tool` functions. `TicketDeps` is the dependency bag (`kb`, `customers`, `known_issues`) injected into every tool call via `RunContext`. |
| `knowledge_base.py` | A minimal in-memory RAG store. `SentenceTransformer("all-MiniLM-L6-v2")` embeds naive sentence-count chunks (`chunk_text_with_overlap`), and `search()` does brute-force cosine similarity over a numpy matrix — no vector DB, no persistence. |
| `seed_data.py` | Fake in-memory data: `fake_customers`, `known_issues`, `kb_articles` (fed into the `KnowledgeBase` at startup), and `golden_tickets` (a hand-labeled eval set, not currently wired into any automated eval). |
| `api.py` | Wires everything together at import time — builds the module-level `KnowledgeBase` and `TicketDeps` once from `seed_data`, and exposes `POST /triage_ticket`. |

There's no request-scoped state: all dependencies are process-global singletons built once at startup. This means **adding or changing seed data / KB articles requires a process restart** to take effect — there's no reload/reindex endpoint.

## Requirements

- Python >= 3.12 (see `.python-version`)
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- An Anthropic API key

## Setup

Install dependencies (creates/updates `.venv` from `uv.lock`):

```bash
uv sync
```

Create a `.env` file in the project root with your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

`agent.py` loads this via `python-dotenv` at import time.

## Running

Start the API server (Uvicorn, with auto-reload):

```bash
uv run uvicorn ticket_triage_agent.api:app --reload
```

The server listens on `http://127.0.0.1:8000` by default. Interactive docs are available at `/docs`.

### Sanity-checking the knowledge base

To check knowledge-base retrieval in isolation, without going through the API or the agent:

```bash
uv run python -m ticket_triage_agent.run_knowledge
```

## API

### `POST /triage_ticket`

**Request body** (`IncomingTicket`):

```json
{
  "ticket_id": "T-2001",
  "customer_id": "cust_4471",
  "subject": "Can't access my dashboard",
  "body": "I keep getting a 500 error when I try to log in to my dashboard."
}
```

**Response** (`TicketResolution`):

```json
{
  "ticket_id": "T-2001",
  "triage": {
    "category": "technical",
    "urgency": "high",
    "can_auto_resolve": false,
    "confidence": 0.85,
    "reasoning": "Customer is on the pro plan and reports a dashboard 500 error, which matches an active known issue (INC-201)."
  },
  "suggested_response": "Thanks for reaching out — we're aware of an active issue causing dashboard 500 errors for pro-tier users and our team is investigating...",
  "escalate_to_human": true,
  "relevant_kb_articles": [
    "If you're experiencing a 500 error on the dashboard, this is often caused by a temporary server issue..."
  ]
}
```

Example request with `curl`:

```bash
curl -X POST http://127.0.0.1:8000/triage_ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "T-2001",
    "customer_id": "cust_4471",
    "subject": "Can'\''t access my dashboard",
    "body": "I keep getting a 500 error when I try to log in to my dashboard."
  }'
```

Sample customer IDs seeded in `seed_data.py`: `cust_4471` (pro, active), `cust_5502` (free, active), `cust_6103` (enterprise, suspended).

A tool or agent failure returns `500` with the error detail.

## Docker

Build and run the API in a container:

```bash
docker build -t ticket-triage-agent .
docker run -e ANTHROPIC_API_KEY=sk-ant-... -p 8000:8000 ticket-triage-agent
```

The image is a two-stage build: dependencies and the `all-MiniLM-L6-v2` embedding model are resolved and pre-fetched at build time (via `uv` and `HF_HOME`), so the runtime container starts with `HF_HUB_OFFLINE=1` and no network access needed to load the embedding model. `ANTHROPIC_API_KEY` must still be supplied at runtime.

The builder stage also copies in a `version.txt` file, so one must exist in the build context — even an empty file works for a local build. In CI this file is generated automatically (see below); it isn't required to be committed.

## CI/CD

`.github/workflows/build.yaml` runs on every push to `main` and publishes a versioned Docker image to Amazon ECR:

1. **Checkout** the repo.
2. **Authenticate to AWS via OIDC** (`aws-actions/configure-aws-credentials`) — no long-lived AWS keys in GitHub, just a trust relationship between the repo and an IAM role.
3. **Log in to ECR** (`aws-actions/amazon-ecr-login`).
4. **Bump the version and tag the commit** — runs `scripts/git_update.sh -v patch`, which reads the latest tag (`git describe --tags`, defaulting to `v0.1.0` if none exists yet), increments the requested part following semver (`vMAJOR.MINOR.PATCH`), then `git tag`s and pushes the new tag to `origin`. If the current commit is already tagged, it skips retagging instead of creating a duplicate. The bump type is hardcoded to `patch` in the workflow — change the `-v` flag in `build.yaml` to `minor` or `major` when you need one of those instead; there's no automatic detection from commit messages or PR labels.
5. **Write `version.txt`** with the new tag, so it lands in the build context before the image is built.
6. **Build and push the Docker image**, tagged with the new version, to `$ECR_REGISTRY/$ECR_REPOSITORY` (`ECR_REPOSITORY` is `${{ github.repository }}`, i.e. `owner/repo`).

### Required repo secrets

| Secret | Purpose |
|---|---|
| `AWS_REGION` | AWS region used for OIDC auth and ECR |
| `AWS_IAM_ROLE` | IAM role ARN the workflow assumes via OIDC |

### Bumping versions manually

`scripts/git_update.sh` can be run outside CI too:

```bash
./scripts/git_update.sh -v patch   # or minor / major
```

This creates and pushes a real git tag to `origin` — it's not a dry run, so only run it when you actually intend to cut a release.

## Testing

There are no tests, linter, or formatter configured in this repo (no pytest/ruff/mypy in `pyproject.toml`, no test files). `seed_data.golden_tickets` is a small hand-labeled set of expected category/urgency pairs intended as the reference set for adding evaluation, but it isn't wired into any automated eval yet.

## Project structure

```
.
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── .python-version
└── src/
    └── ticket_triage_agent/
        ├── __init__.py
        ├── agent.py          # Agent, tools, TicketDeps, triage_ticket()
        ├── api.py             # FastAPI app and /triage_ticket endpoint
        ├── knowledge_base.py  # In-memory embedding-based RAG store
        ├── models.py          # Pydantic schemas and enums
        ├── run_knowledge.py   # Ad-hoc KB retrieval sanity check
        └── seed_data.py       # Fake customers, known issues, KB articles, golden set
```
