# CareAuth AI — AI-Powered Prior Authorization & Documentation Assistant

> **⚠️ This is a demonstration prototype with synthetic data and no production security controls. It must not be used with real patient health information (PHI).**

## What It Does

CareAuth AI is a workflow assistant for hospital authorization staff. It checks a prior authorization request against insurance policy rules, verifies that every required document is attached, explains blockers with policy citations, and blocks incomplete submissions. When a payer rejects a request, it classifies the reason and produces a resubmission checklist.

**What it is not:** a chatbot, a clinical tool, a coverage authority, a production system, or a HIPAA-compliant application.

## Quick Start

### Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY

# Run the backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:3000 (frontend) and http://localhost:8000 (API).

### Demo Reset

```bash
curl -X POST http://localhost:8000/api/v1/admin/reset
```

## Architecture

- **Backend:** Python 3.11+ / FastAPI / SQLModel / SQLite
- **Frontend:** Next.js 15 / TypeScript / Tailwind CSS / shadcn/ui
- **AI Agents:** Coverage Agent (RAG + policy citation), Documentation Agent (gap detection), Communication Agent (packet generation + rejection analysis)
- **Orchestrator:** Pure Python, parallel agent execution via asyncio.gather

## Project Structure

```
app/
├── api/          # FastAPI routers
├── models/       # SQLModel entities
├── schemas/      # Pydantic request/response schemas
├── services/     # Business logic (state machine, etc.)
├── agents/       # AI agents (coverage/, documentation/, communication/, rag/)
├── mock_payer/   # Scripted + manual payer simulation
├── seed/         # Reference data + policy documents
└── storage/      # Local file storage

contracts/        # Frozen API contracts (Python + TypeScript)
frontend/         # Next.js 15 App Router application
```

## Safety Boundary

*CareAuth AI determines whether an administrative request is complete and consistent with the stated policy. It does not determine whether care is appropriate. That judgment belongs to the physician, and the coverage decision belongs to the payer.*
