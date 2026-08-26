# Talent Signal

AI-powered candidate intelligence MVP for the supplied `Dummy Candidate Database 1000 expanded.xlsx` workbook.

## Run locally

The seed workbook is intentionally not committed. Place the supplied file at `data/Dummy Candidate Database 1000 expanded.xlsx`, then run:

```bash
docker compose up -d postgres
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python3 -m app.scripts.import_candidates
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend local API target is configured in `frontend/.env.local` as `http://127.0.0.1:8000`. Restart `npm run dev` after changing frontend environment variables.

Open `http://localhost:3000`. Set `NEXT_PUBLIC_API_URL` when the API is hosted elsewhere.

Node.js `20.9+` is required by Next.js 16. From the repository root, run `nvm use`, `npm install:frontend`, and `npm run dev`; these proxy to the frontend directory. Running npm commands directly in `frontend/` is also supported. The API defaults to PostgreSQL from `.env`; for an isolated no-Postgres smoke test, set `DATABASE_URL=sqlite:///./candidate_intelligence.db`.

## Use Supabase Postgres

Supabase works as the runtime database because the backend uses standard PostgreSQL through SQLAlchemy and Alembic. The project URL and publishable key are not database credentials and are not sufficient for migrations. In the Supabase Dashboard, open **Connect**, copy the direct or session-pooler PostgreSQL connection string, and put it in `backend/.env` as `DATABASE_URL`. Keep the password only in `.env`; do not commit it.

```dotenv
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:YOUR_DATABASE_PASSWORD@YOUR_SUPABASE_HOST:5432/postgres
SUPABASE_URL=https://lzzyyaddldmwzgvcrteh.supabase.co
SUPABASE_PUBLISHABLE_KEY=your_publishable_key
```

Then run migrations and import the master workbook:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python3 -m app.scripts.import_candidates
uvicorn app.main:app --reload --port 8000
```

The frontend should continue calling FastAPI. It does not read Supabase directly, which keeps database credentials and candidate access on the backend.

For production CV storage, create a private Supabase Storage bucket named `candidate-cvs` in Storage > New bucket, then set these backend-only Vercel variables:

```dotenv
STORAGE_BACKEND=supabase
STORAGE_BUCKET=candidate-cvs
SUPABASE_SERVICE_ROLE_KEY=your_server_only_service_role_key
```

The service-role key is required for server-side Storage uploads and must not be configured as a `NEXT_PUBLIC_*` variable. Uploaded CVs are stored in Supabase Storage; extraction downloads them only to a temporary file and removes that file afterward. Local development continues to use `STORAGE_BACKEND=local` and `UPLOAD_DIR=../data/uploads`.

For Vercel, browser requests use the same-domain `/svc/api/...` route. The root `vercel.json` service transform presents those requests to FastAPI as its existing `/api/...` paths. Local development continues to use `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`.

## Current MVP slice

- Idempotent Excel import with stable `CAND-*` IDs and original-row provenance.
- Normalized candidates, skills, education, documents, notes, tenants, users, import batches, and audit logs.
- Hard-filtered candidate search with pagination and deterministic explainable suitability scoring.
- Natural-language demo query parsing for skills, experience, location, salary, and notice period.
- Async upload boundary returning `202`; PDF/DOCX/TXT validation is ready for the document worker phase.
- Responsive recruiter dashboard with metrics, ranked results, and score reasons/gaps.

The production architecture is documented in [docs/architecture.md](docs/architecture.md). The current upload endpoint is deliberately a worker boundary, not a claim that OCR/LLM infrastructure has been deployed.

## Ingestion diagnostics

The master import reads only the `Candidates` worksheet and prints rows read, valid, inserted, updated, skipped, and errors. It uses `SEED_FILE` from `.env` or `../data/Dummy Candidate Database 1000 expanded.xlsx` and never makes the workbook part of runtime queries.

CVs are stored under `data/uploads/` and document metadata is stored in PostgreSQL. PDF extraction uses PyMuPDF text extraction first, then positioned text blocks, then Tesseract OCR when quality is insufficient. Use the development diagnostic endpoint to inspect a LaTeX or other PDF without invoking structured extraction:

```bash
curl -F "file=@resume.pdf" http://localhost:8000/api/dev/extract-diagnostic
```

It returns page count, method, character/word counts, quality, and a 500-character preview. The current repository did not include the supplied workbook or resume, so their actual row count and PDF quality cannot be reported until those files are placed in the workspace.
