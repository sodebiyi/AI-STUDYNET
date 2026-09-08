# NetMentor AI

**Learn. Troubleshoot. Think Like a Network Engineer.**

NetMentor AI is a troubleshooting-first learning platform for aspiring and junior Network Engineers. Instead of
teaching networking as a wall of theory, it puts you in front of realistic NOC-style incidents, a simulated Cisco
CLI, and an AI coach that asks Socratic questions instead of handing you the answer — because the goal isn't
"knows what OSPF is," it's "can actually find and fix a broken OSPF adjacency at 2am."

This repository is the **MVP** described in the product spec: registration/login, a dashboard, the "Follow the
Packet" visualiser, 5 troubleshooting incidents, a simulated CLI, an AI troubleshooting coach, a troubleshooting
score, progress tracking, and a basic "Am I Job Ready?" readiness report. It is real, running, tested code — not a
static prototype — built so the rest of the product spec (more incidents, BGP/MPLS/VPN content, the interview
simulator, admin dashboard, Stripe billing, multi-vendor CLI) can be layered on without re-architecting anything.

## How it works, end to end

1. Register / log in (JWT auth).
2. Land on a dashboard showing your level, skill breakdown, streak, and a recommended next incident.
3. Step through **Follow the Packet** to see exactly what happens, layer by layer, when you ping a host, resolve a
   DNS name, or open an HTTPS site.
4. Open **Incidents**, pick a realistic ticket, and investigate it using a simulated Cisco CLI (`show ip interface
   brief`, `show vlan brief`, `show ip route`, `configure terminal`, etc.) against a live simulated network — not
   canned text, an actual small routing/switching engine that evaluates your commands against real device state.
5. Talk to the **AI Coach** in the right-hand panel. It won't tell you the root cause — it asks what you've
   verified, nudges you toward the layer you haven't checked yet, and only reveals the answer through a graduated
   hint system (or full reveal on hint 3) so guessing is never faster than investigating.
6. Submit a diagnosis, apply the fix via the CLI, and verify it. On success you get a full breakdown: diagnosis,
   methodology, efficiency, remediation, and verification scores, plus XP and an update to your per-skill
   readiness profile.

## Architecture

```
netmentor-ai/
├── backend/            FastAPI + SQLAlchemy + Alembic (Python)
│   ├── app/
│   │   ├── api/         auth, incidents, dashboard routers
│   │   ├── core/        config, db session, JWT/password hashing, auth deps, rate limiting
│   │   ├── models/      SQLAlchemy models (User, Incident, IncidentAttempt, CommandLog, HintLog, SkillProfile)
│   │   ├── schemas/     Pydantic request/response models (never leak answer keys to the client)
│   │   ├── simulation/  the network simulation engine, CLI parser, and the 5 incident definitions
│   │   ├── services/    AI coach engine, scoring engine, readiness/skill-profile engine
│   │   └── tests/       pytest suite (engine, CLI, scoring, full incident walkthroughs via the real API)
│   └── alembic/         migrations
└── frontend/            Next.js 14 (App Router) + TypeScript + Tailwind
    ├── app/              pages: landing, login/register, dashboard, packet-visualiser, incidents, incidents/[id], readiness
    ├── components/       TopologyDiagram (SVG), CliTerminal, CoachPanel, AuthGuard, Nav
    ├── data/             static "Follow the Packet" scenario/header data
    └── lib/              typed API client, auth context
```

### The network simulation engine (`backend/app/simulation/`)

This is the core of the product, so it's worth understanding:

- **`engine.py`** represents devices/interfaces/links/VLANs/routes/OSPF as plain JSON state and *evaluates outcomes*
  — does a ping succeed, what does a route table look like, is an OSPF adjacency up — by walking that state (L1
  admin/line status → L2 VLAN/trunk membership → L3 subnet/routing-table/OSPF-adjacency logic). It is not a
  packet-accurate emulator; it's deliberately a controlled simulation, exactly as the product spec calls for, with
  the explicit design goal that a real emulator (EVE-NG/GNS3/container networking) could sit behind the same
  `attempt_ping` / `run_show_command` call shape later without touching the API layer.
- **`cli.py`** parses a Cisco-style command line against a device's state (with real config-mode tracking —
  `configure terminal` → `interface X` → `switchport access vlan 10` works as a sequence of calls, exactly like a
  real terminal) and either returns realistic `show` output or mutates state.
- **`incidents.py`** defines the 5 MVP incidents (topology, the injected fault, the answer key). The answer key
  (root cause, correct remediation, verification, scoring hints) **never** reaches the frontend — only
  `IncidentPublic` (topology + narrative) does. `POST /incidents` seeds this table.

### AI Coach (`backend/app/services/coach.py`)

The coach is a **deterministic, rule-based Socratic dialogue engine** — no external LLM API key required to run
this project. It reasons over *observable investigation state* (which `show` commands the student has actually run,
categorised by OSI layer, in what order) rather than free-text understanding. That's a deliberate product decision:
a student can't talk their way to the answer without doing the investigative work, and the whole engine runs
locally with zero inference cost.

`AI_COACH_PROVIDER` in `backend/app/core/config.py` documents the seam for swapping in a real LLM later: set it to
`"llm"`, supply `LLM_API_KEY`, and implement the branch in `coach_reply()` — the caller (`app/api/incidents.py`)
doesn't need to change at all. **Never** expose an LLM API key to the frontend; it stays server-side, read from an
environment variable, exactly like `JWT_SECRET_KEY`.

### Scoring (`backend/app/services/scoring.py`)

Grades engineering *behaviour*, not just "did you eventually get there": diagnosis accuracy, troubleshooting
methodology (did you check L1 → L2 → L3 → hypothesis → fix → verify, in order), efficiency (hints used, failed
attempts, unnecessary/invalid commands), remediation correctness, and verification. See the `NETWORK ENGINEER
SCORE` breakdown on the incident-resolved screen.

## Running it

### Quickest path: Docker Compose

```bash
cp .env.example .env        # edit JWT_SECRET_KEY at minimum
docker compose up -d --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (interactive docs at `/docs`)
- Postgres: localhost:5432

On first boot the backend container runs `alembic upgrade head` then seeds the 5 incidents automatically (see
`backend/Dockerfile`'s `CMD`). Re-running `docker compose up` is idempotent — the seed script upserts by slug.

> **Note:** `NEXT_PUBLIC_API_URL` is inlined into the frontend bundle at **build** time (a Next.js constraint, not
> a bug). If you change it, run `docker compose build frontend` rather than just restarting the container.

### Local development (no Docker)

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://netmentor:netmentor@localhost:5432/netmentor"
export JWT_SECRET_KEY="dev-secret"
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local
npm run dev
```

You'll need a local Postgres with a `netmentor` database/user (or point `DATABASE_URL` at any Postgres instance).

### Running the tests

```bash
cd backend
export DATABASE_URL="postgresql+psycopg2://netmentor:netmentor@localhost:5432/netmentor_test"
export JWT_SECRET_KEY="test-secret"
python -m pytest app/tests -v
```

The suite covers the simulation engine (VLAN mismatch, interface-down, wrong subnet mask, missing default route,
OSPF area mismatch — each incident's fault *and* its fix, verified against the actual engine), the CLI parser
(config-mode sequencing, device-kind gating, realistic error output), the scoring engine, and — most importantly —
full end-to-end incident walkthroughs hitting the real HTTP API: register → list incidents → start attempt →
investigate via CLI → chat with the coach → request a hint → submit diagnosis → apply the fix → verify → confirm
the attempt resolved with a real score and the dashboard/readiness reports updated. It also asserts a free-tier
user is blocked from a Pro incident (402) and that one student can't read another student's attempt (404).

This project was also manually verified end-to-end in a real browser (Playwright) through the full journey —
register → dashboard → Follow the Packet → start an incident → CLI investigation → coach chat → apply the fix via
CLI → verify → resolution screen with the full score card — which is how a real bug (`no shutdown` wasn't
restoring line-protocol status, only admin status) was caught and fixed; there's a regression test for it in
`test_incident_flow.py::test_full_interface_down_incident_walkthrough`.

## Security notes

- Passwords are hashed with bcrypt (passlib); plaintext is never stored or logged.
- JWT auth (`python-jose`), `HS256`, short-lived tokens (default 12h) carrying only user id + role.
- `JWT_SECRET_KEY` **must** be overridden via environment variable outside local dev — the default is intentionally
  an obvious placeholder that you should never actually use.
- Role-based access control scaffolding (`student` / `instructor` / `admin`) is in `app/core/deps.py`
  (`require_role`) — the MVP API surface only needs `student`, but instructor/admin routes (module 15, admin
  dashboard) can hang off the same dependency.
- Rate limiting via `slowapi` — tighter limits on `/auth/register` and `/auth/login` (10/min) than the general API
  default, to blunt credential-stuffing / enumeration attempts.
- Incident answer keys (root cause, correct remediation, scoring rubric) are stored server-side only and are never
  serialized into any response the frontend can see (`IncidentPublic` vs. the internal `Incident` model) — verified
  by `test_full_vlan_incident_walkthrough`'s explicit assertion that `answer_key` and `initial_state` never appear
  in the incident-detail response.
- A student can only read/act on their own attempts (`_get_attempt_or_404` checks `attempt.user_id`), covered by
  `test_cannot_access_another_users_attempt`.
- Minimal audit logging middleware in `app/main.py` (method/path/status per request; deliberately never logs
  request/response bodies, which could contain credentials).
- The JWT is currently stored in `localStorage` on the frontend for MVP simplicity. A production hardening pass
  should move to an httpOnly, `SameSite=strict` refresh-token cookie with short-lived access tokens in memory, to
  reduce XSS blast radius.

## What's genuinely MVP-scoped vs. full spec

Built and working: modules 1 (fundamentals — packet visualiser only for now, standalone lesson content is the next
increment), 2 (Follow the Packet), 3 (AI troubleshooting simulator), 4 (Socratic AI, never gives the answer away),
5 (simulated CLI), 6 (incident engine + data model), 7 (troubleshooting score), 8 (AI coach), 10 (basic readiness
report), 13 (dashboard), 18/19 (security + DB design foundations), 21 (the literal MVP feature list).

Deliberately deferred (see the product spec's own section 21/27 — "don't build everything at once"): the other
20+ fundamentals lessons, BGP/MPLS/VRF/VPN/wireless content, the ticketing/NOC-queue UI (module 9), the interview
simulator (module 11), full learning paths (module 12), gamification beyond XP/streak (badges/leaderboards, module
14), the admin dashboard (module 15), Stripe billing (module 26), and a Juniper/multi-vendor CLI. The architecture
— a data-driven incident table, a decoupled simulation engine, a swappable coach interface — is built so each of
those is additive, not a rewrite.

## Extending it

- **New incident:** add an entry to `INCIDENTS` in `backend/app/simulation/incidents.py` (topology, `initial_state`
  with the fault, `answer_key`), then re-run `python -m app.seed`. Nothing else needs to change — the CLI, engine,
  scoring, and frontend workspace are all incident-agnostic.
- **New CLI command:** add a branch in `backend/app/simulation/cli.py::run_command`. Unrecognised commands already
  return a realistic `% Invalid input` error rather than silently no-op'ing.
- **Real LLM coach:** implement the `AI_COACH_PROVIDER == "llm"` branch in `backend/app/services/coach.py`; the
  investigation-state context it's already given (commands run, hints used, failed attempts) is exactly what
  you'd hand to an LLM as context instead of the rule table.

## Tech stack

Frontend: React 18, Next.js 14 (App Router), TypeScript, Tailwind CSS.
Backend: Python, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, `python-jose` (JWT), `passlib`/`bcrypt`, `slowapi`
(rate limiting).
Database: PostgreSQL 16.
Infra: Docker, Docker Compose.
