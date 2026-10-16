# CiteFlow Backend (FastAPI + PostgreSQL + ImageKit)

CiteFlow Backend is a high-performance, asynchronous REST API service built with FastAPI, PostgreSQL (SQLAlchemy 2.0 + psycopg 3), and ImageKit for secure document handling.

---

## 1. Architecture Overview (Server Part A)

- **Authentication & Security**:
  - Argon2id password hashing via `argon2-cffi`.
  - JWT access tokens (15-minute expiry) in `httpOnly` secure cookies.
  - Opaque refresh tokens stored as SHA-256 hashes in PostgreSQL with family rotation and automatic reuse/theft revocation.
  - Double-submit CSRF protection with `X-CSRF-Token` header.
  - Strict ownership enforcement across all endpoints (unauthorized access returns 404 to avoid leaking resource existence).
  - Rate limiting on login and registration endpoints.
- **Nested Folder System**:
  - Root folder automatically provisioned at user registration.
  - Arbitrary nested hierarchy up to `MAX_FOLDER_DEPTH`.
  - Unicode NFC normalization and case-insensitive unique naming within parents.
  - Breadcrumb computation and paginated file/folder listings.
- **File Upload & Storage**:
  - Pure ASGI early upload-size enforcement middleware.
  - Handler registry architecture with `PdfHandler` validating real binary structure (%PDF header, PyMuPDF encryption/corruption checks, page checks).
  - Private file upload to ImageKit with server-generated UUID names (user-supplied names are never exposed or sent to ImageKit).
  - Short-lived signed URLs for PDF viewing (`GET /api/v1/files/{id}/url`).
  - Compensation pattern: if database record creation fails after an ImageKit upload, the file is deleted from ImageKit or queued in `storage_deletions`.
- **Safe Outbox Deletion**:
  - Recursive folder and file deletion atomically queues all descendant ImageKit IDs into `storage_deletions`.
  - Background `StorageCleanerWorker` drains the queue using `FOR UPDATE SKIP LOCKED`.

---

## 2. Environment Configuration

The backend loads configuration from the repository's root `.env` file. Copy the variables from `.env.example` into `.env`:

```bash
# App settings
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
CORS_ALLOW_ORIGINS=http://localhost:5173

# Database (psycopg3 async / Neon PostgreSQL)
# You can paste your Neon connection string directly:
DATABASE_URL=postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
DB_POOL_SIZE=5

# Auth & Tokens
JWT_SECRET=your-32-character-random-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
COOKIE_SECURE=false

# ImageKit Configuration
IMAGEKIT_PRIVATE_KEY=your_private_key
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_id
IMAGEKIT_BASE_FOLDER=/citegen
SIGNED_URL_EXPIRES_SECONDS=300
```

---

## 3. Quick Start

### 1. Database Configuration (Neon PostgreSQL)
Set `DATABASE_URL` in your `.env` to your Neon connection string. The server automatically ensures tables on startup via `create_all`.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### Launch the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive OpenAPI documentation is available at: `http://localhost:8000/docs` or `http://localhost:8000/openapi.json`.
Liveness and readiness probes are available at:
- `GET /health`
- `GET /health/ready`
