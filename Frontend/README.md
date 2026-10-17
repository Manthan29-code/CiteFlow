# CiteFlow Frontend (Part A & Part B Complete)

An editorial-tech research document explorer and automated LaTeX citation generator built with **React 18 + TypeScript + Vite**, styled using **Tailwind CSS**, animated via **Framer Motion**, and state-managed with **Redux Toolkit**.

---

## 1. Getting Started

### 1.1 Install Dependencies
Dependencies are listed in `package.json`. Run:
```bash
npm install
```

### 1.2 Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings:
- `VITE_API_BASE_URL`: Base API path (`/api/v1` for Vite dev proxy)
- `DEV_PROXY_TARGET`: Backend FastAPI server target (`http://localhost:8000`)
- `VITE_APP_NAME`: Display title (`CiteFlow`)
- `VITE_MAX_UPLOAD_MB`: Pre-check file upload limit (`25`)
- `VITE_ALLOWED_EXTENSIONS`: Permitted file types (`pdf`)
- `VITE_PAGE_SIZE`: Pagination page size (`100`)
- `VITE_UPLOAD_CONCURRENCY`: Simultaneous uploads allowed (`2`)
- `VITE_PASSWORD_MIN_LENGTH`: Minimum password length for registration (`6`)
- `VITE_JOB_POLL_INTERVAL_MS`: Polling initial interval for citation jobs (`2000`)
- `VITE_JOB_POLL_MAX_INTERVAL_MS`: Polling max backoff interval (`10000`)
- `VITE_ENABLE_SSE`: Enable Server-Sent Events real-time streaming (`false`)

### 1.3 Start Development Server
```bash
npm run dev
```
The app runs at `http://localhost:5173`. In development, requests to `/api` are automatically proxied to `DEV_PROXY_TARGET`.

---

## 2. Architecture & Completed Deliverables

### 2.1 Part A: Accounts & File Explorer
- **Cookie Authentication & CSRF**: Operates with the backend's 3-cookie model (`access_token`, `refresh_token`, `csrf_token`), automatically attaching `X-CSRF-Token` on mutating requests (`POST`, `PUT`, `PATCH`, `DELETE`).
- **Single-Flight 401 Refresh**: Intercepts 401s, rotates tokens once via `POST /auth/refresh` (shared among parallel requests), and retries the original request.
- **Nested Folder Tree**: Lazy-loading directory hierarchy in the sidebar with active folder highlighting and keyboard navigation.
- **File & Folder Operations**: Folders sorted first, human-readable file sizes, and created dates. Double-click to open folders or PDFs.
- **Upload Queue Engine**: Drag-and-drop zone and file picker with client-side size/extension pre-checks, XHR percentage progress, concurrency control, cancel, and retry.
- **Secure PDF Viewing**: Synchronously opens new blank tabs on click to bypass popup blockers, then navigates to the signed URL without leaking or caching it.

### 2.2 Part B: Generate .tex Citation Jobs
- **Generate .tex Button (`GenerateButton.tsx`)**:
  - Available for all PDF rows with output mode choice: **Full Document** (`standalone`) or **Bibliography Block** (`fragment`).
  - Idempotent: Handles both `202 Accepted` and `200 OK` (existing active job) seamlessly.
  - Double-click prevention: Immediately disables upon click.
- **Status Badges (`StatusBadge.tsx`)**:
  - Accessible badges for each state: `queued`, `running` (spinner), `needs_title_confirmation` & `needs_review` (amber attention badge), `succeeded` (green check), `unresolved`, `failed`, `canceled`, `expired`.
- **Title Confirmation Dialog (`TitleConfirmDialog.tsx`)**:
  - Triggered on `needs_title_confirmation`.
  - Radio list of candidate titles with match confidence indicators (`high`, `medium`, `low` or percentage score).
  - Manual title entry mode with validation (1 to 300 characters, no control characters).
  - Actions: Confirm title (`action: "select"` or `action: "custom"`), or Skip (`action: "skip"`).
- **Metadata Review Form (`ReviewFormDialog.tsx`)**:
  - Triggered on `needs_review`.
  - Displays all bibliographic fields: Title, Authors, Year, Journal, Journal Abbreviation, DOI URL, Volume, Issue, First Page, Article Number.
  - Interactive Authors editor: Add, remove, and reorder authors with explanatory citation rules.
  - Source conflict resolution: Highlights discrepancies with "Use this" action buttons.
  - Partial updates: Submits **only** the fields that were modified by the user.
- **Result & TeX Preview Dialog (`TexPreviewDialog.tsx`)**:
  - Read-only monospace block displaying plain text `.tex` document fetched from `GET /jobs/{id}/tex`.
  - **Copy to Clipboard** with visual feedback.
  - **Download .tex** using client-side Blob and temporary object URL with auto-revocation.
  - Contextual hints for LaTeX packages (`hyperref` or `thebibliography`).
- **Job Drawer / Panel (`JobPanel.tsx`)**:
  - Slide-over drawer detailing active job status, contextual actions, and historical runs for the file.
- **Needs Attention Indicator in Navigation**:
  - Top bar badge dynamically counts jobs requiring user confirmation or review; clicking immediately opens the matching dialog.

---

## 3. Design System: Editorial 'Premium Fluidity'
- **Palette**: Warm Cream (`#fcfbf9`), Rich Charcoal (`#171717`), and Vibrant Indigo (`#4338ca`).
- **Typography**: Display headings in *Playfair Display* (italic emphasis), body in *Inter*, functional labels in *JetBrains Mono* with `0.3em` tracking.
- **Tactile Feedback**: Framer Motion micro-interactions on button clicks, card hovers, modal reveals, and upload drawer animations.
