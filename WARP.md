# AZ-104 Exam Simulator - Progress Tracker

## Current Status: WORKING ✅
Dashboard loads, exam sessions run, and study mode is available.

## Quick start (clean, stable ports)

### Using Scripts (Recommended) ✨
```bash
cd /Users/aimewill/Projects/Az104app

# Start both servers
./start.sh

# Check status
./status.sh

# Stop both servers
./stop.sh
```

### Manual Start (Alternative)
```bash
# 0) Kill any previous dev servers (optional)
pkill -9 -f "uvicorn|vite|node" 2>/dev/null || true

# 1) Backend (Terminal 1)
cd /Users/aimewill/Projects/Az104app
uvicorn backend.app.main:app --host ********* --port 8000

# 2) Frontend (Terminal 2)
cd /Users/aimewill/Projects/Az104app/frontend
npm run dev -- --strictPort --host ********* --port 5173
```

Open http://*********:5173

Health checks
```bash
# Backend
curl -s http://127.0.0.1:8000/api/import/status | jq .
curl -s http://127.0.0.1:8000/api/dashboard     | jq .
```

## Question counts (667 total)
- **Total Questions: 667**
  - **Exam Questions: 446** (single, multi, truefalse) - used in Random/Unseen/Weak/Review modes
  - **Study Questions: 221** (DRAG DROP/HOTSPOT) - only in Study Mode
- Questions with Images: 218 (exhibits + table images)
- Questions in Series: 37 (grouped into 11 series)
- Question numbering: Uses Q# format (Q1, Q2, Q94, etc.)

## Recent fixes and changes (Feb 15, 2026 - Latest)

### 🎯 NEW: Random Mode = Unseen Only ✅
- **Feature**: Random mode now only picks questions you haven't seen yet
- **How it works**:
  - Clicking "Random" gives you 60 NEW unseen questions (times_shown == 0)
  - Once all 446 exam questions are seen, falls back to least-seen questions
  - Dashboard shows progress: "342 Unseen" with "104 seen" below
  - Progress bar shows "104 of 446 exam questions seen (23%)"
  - Shows "6 more sessions to see all exam questions"
- **Goal**: Work through all 446 questions without repetition, then review wrong ones
- **Files touched**:
  - `backend/app/services/session_service.py` — `_select_random()` filters by times_shown
  - `backend/app/routers/dashboard.py` — Added unseen_questions, seen_questions, exam_questions
  - `frontend/src/pages/Dashboard.jsx` — Progress bar and unseen count display

### 🔐 NEW: User Authentication ✅
- **Feature**: User login/registration system for tracking individual progress
- **How it works**:
  - JWT-based authentication (stateless, Railway-ready)
  - Register with email/password, optional display name
  - Login persists via localStorage token
  - **Login required to start exams** (enforced on frontend and backend)
  - Sessions and history are tracked per-user
  - Dashboard shows user-specific stats
- **Endpoints**:
  - `POST /api/auth/register` - Create account
  - `POST /api/auth/login` - Get access token
  - `GET /api/auth/me` - Get current user info
- **Files touched**:
  - `backend/app/models.py` — Added `User` model, `user_id` FK on `ExamSession`
  - `backend/app/auth.py` — JWT token utilities, password hashing
  - `backend/app/routers/auth.py` — Auth API endpoints
  - `backend/app/routers/session.py` — Associate sessions with users
  - `backend/app/routers/dashboard.py` — Filter stats by user
  - `backend/app/config.py` — JWT_SECRET_KEY config
  - `backend/requirements.txt` — Added auth dependencies
  - `frontend/src/context/AuthContext.jsx` — Auth state management
  - `frontend/src/pages/Login.jsx` — Login page
  - `frontend/src/pages/Register.jsx` — Registration page
  - `frontend/src/api/client.js` — Auth API + token handling
  - `frontend/src/App.jsx` — Auth integration, header user info
  - `frontend/src/index.css` — Auth page styles

### 🎨 Modern Design Refresh ✅
- **Feature**: Polished, modern UI inspired by Warp docs design
- **Design changes**:
  - New color palette with purple/indigo accents
  - Inter font for better typography
  - Subtle borders and refined shadows
  - Improved button hover effects with transforms
  - Sticky header with backdrop blur
  - Cleaner stat cards and tables
  - Gradient accents on progress bars and Study Mode button
- **Files touched**:
  - `frontend/index.html` — Inter font from Google Fonts
  - `frontend/src/index.css` — Complete styling overhaul
  - `frontend/src/pages/Dashboard.jsx` — Updated inline styles

### 🌙 NEW: Dark Mode ✅
- **Feature**: Toggle between light and dark themes
- **How it works**:
  - Click sun/moon icon in header to toggle
  - Preference saved to localStorage
  - Auto-detects system preference on first load
  - Smooth CSS transitions between themes

### ⏱️ NEW: Timer & Timed Mode ✅
- **Feature**: Countdown timer for timed exam sessions (simulates real AZ-104)
- **How it works**:
  - Dashboard shows "Practice Mode" vs "Timed Mode" toggle
  - Default 100 minutes (configurable 10-180 min)
  - Timer displays in exam header with MM:SS countdown
  - Yellow warning at ≤10 minutes remaining
  - Red critical warning at ≤2 minutes (with pulse animation)
  - Pause/Resume button to stop the clock
  - Auto-submits exam when time expires
- **Files touched**:
  - `backend/app/models.py` — Added `paused_at`, `total_paused_seconds` fields
  - `backend/app/routers/session.py` — Added `/time`, `/pause`, `/resume` endpoints
  - `frontend/src/pages/Dashboard.jsx` — Timer mode toggle UI
  - `frontend/src/pages/ExamSession.jsx` — Timer component
  - `frontend/src/api/client.js` — Timer API methods
  - `frontend/src/index.css` — Pulse animation

### 🖼️ Exhibit & Table Image Extraction ✅
- **Feature**: Automatically extracts and displays images from PDFs (exhibits + table data)
- **How it works**: 
  - Detects questions referencing "exhibit", "following users", "following resources", etc.
  - Finds the **actual PDF page** containing each question text (question numbers ≠ PDF page numbers)
  - Uses 150-200 character text matching with whitespace normalization
  - Extracts exhibit images AND table images from correct PDF pages using PyMuPDF
  - Table images detected by dimensions (wide, short aspect ratio)
  - Saves images to `backend/app/static/exhibits/` with unique filenames
  - Displays images above question text in exam and results pages
- **Result**: 218 questions now show their correct images
- **Files**: Images served via FastAPI StaticFiles at `/static/exhibits/`
- **Feb 13 Fix**: Complete rewrite of image extraction to match question text to actual PDF pages (fixed 145 mismatches)
- **Feb 15 Fix**: Re-extracted all 210 images with `scripts/reextract_images.py` to fix remaining mismatches (e.g., Q327/Q328 showing wrong VM table)
- **Feb 15 Heuristic Update**: Parser now scores candidate images across previous/current/next pages and prefers table-like images when the question says "following table". Re-extracted all exhibits. Verified Q140 and Q327–Q329 against the PDF.
- **Feb 15 Batch Fix**: Added "following locations" keyword and fixed 16 more missing images (Q46, Q49, Q52, Q54, Q71, Q79, Q95, Q117, Q137, Q177, Q220, Q276, Q302, Q313, Q372, Q16)
- **Data cleanup**: Removed stale `/static/exhibits/q*_img0.jpeg` references and nulled missing paths to prevent 404s.

### 🔗 NEW: Question Series Grouping ✅
- **Feature**: Related questions (same scenario) now appear consecutively
- **Detection**: 
  - Explicit "Note: This question is part of a series" markers
  - Scenario matching (questions with same setup/table are grouped)
- **Grouping**: Questions in same series get identical `series_id` and stay together in ALL exam modes
- **Result**: 37 questions organized into 11 series
- **Examples**:
  - Q38, Q39, Q40, Q304 (same user/role table scenario)
  - Q327, Q328, Q329 (same VM scenario)
  - Q2, Q3, Q4 (same subscription scenario)

### 📖 NEW: Improved Text Readability ✅
- **Paragraph Formatting**: Questions now display with proper line breaks between sections
- **Abbreviation Expansion**: Common abbreviations automatically expanded:
  - `qis` → `question is`
  - `qs` → `questions`
  - `qin` → `question in`
  - `qsets` → `question sets`
- **CSS**: Added `whiteSpace: 'pre-line'` to preserve formatting
- **Result**: Much easier to read multi-paragraph questions

### 📝 NEW: Question Number References ✅
- **Feature**: Questions display their PDF reference number (Q94, Q188, etc.)
- **Storage**: `source_page` field now stores question number instead of PDF page
- **Display**: Shows as "📄 Q94" badge next to domain tags
- **Result**: Easy cross-reference with original PDF

### Database Schema Updates
- Added `exhibit_image` column for image paths
- Added `series_id` column for grouping related questions
- Added `sequence_number` column for maintaining PDF order

### Previous Fixes (Still Active)
- Parser rewrite for truncated choices (normalizes line breaks)
- Study question detection (DRAG DROP/HOTSPOT)
- Duplicate prevention during import
- Frontend IPv4 binding and stable ports

## Files touched
### Backend
- `backend/app/services/parser.py` — Image extraction + series detection + paragraph formatting + abbreviation expansion
- `backend/app/models.py` — Added `exhibit_image`, `series_id`, `sequence_number` fields
- `backend/app/routers/import_router.py` — Save new fields during import
- `backend/app/services/session_service.py` — Group questions by series, keep related questions together
- `backend/app/routers/session.py` — Include new fields in API responses
- `backend/app/main.py` — Static file serving for exhibit images
- `backend/app/static/exhibits/` — Directory for extracted images (218 images)

### Frontend
- `frontend/src/pages/ExamSession.jsx` — Display exhibit images + preserve paragraph formatting
- `frontend/src/pages/Results.jsx` — Display exhibit images + show Q# references
- CSS — Added `whiteSpace: 'pre-line'` for text readability

## Troubleshooting
- Page keeps “Loading dashboard…” or refuses to connect:
  1) Hard refresh (Cmd/Ctrl+Shift+R).
  2) Ensure only one Vite is running on 5173: `lsof -i :5173`.
  3) Clean restart:
     ```bash
     pkill -9 -f "uvicorn|vite|node"; sleep 1
     uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
     # new terminal
     npm run dev -- --strictPort --host 127.0.0.1 --port 5173
     ```
  4) Verify backend JSON: `curl -s http://127.0.0.1:8000/api/dashboard`.

## Service URLs
- Backend: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:5173

## PDF source
`pdfs/AZ-104 englische Version PDF www.it-pruefungen.ch.pdf`

## ⚠️ Critical Paths (DO NOT CHANGE)
These paths must remain as-is for local development:
- **Database**: `data/az104.db` (NOT exam.db)
- **PDFs**: `pdfs/` at project root (NOT data/pdfs/)
- **Exhibits**: `backend/app/static/exhibits/` (NOT data/exhibits/)

For Railway deployment, use environment variables:
- `DATABASE_URL` - PostgreSQL connection string (auto-set by Railway)
- `JWT_SECRET_KEY` - Secure random string for auth tokens
- `PDFS_DIR` - Path to PDFs on Railway volume
- `EXHIBITS_DIR` - Path to exhibits on Railway volume

## 🚀 Railway Deployment
**Live URL**: https://az104-exam-simulator-production.up.railway.app

### Why only 5 demo questions on fresh deploy?
Railway creates a **fresh database** - it doesn't have your local questions!
To migrate your 667 questions to Railway:
```bash
# 1. Link to Postgres service
railway link  # Select Postgres

# 2. Get the public DATABASE_URL
railway run -- python -c "import os; print(os.environ.get('DATABASE_PUBLIC_URL'))"

# 3. Run migration
python scripts/migrate_to_railway.py "<POSTGRES_URL_FROM_STEP_2>"

# 4. Link back to app and redeploy
railway link  # Select az104-exam-simulator
railway up --detach
```

### ⚠️ After re-extracting images locally
If you re-run `scripts/reextract_images.py` locally, you must ALSO update Railway:
1. Push new image files to git: `git add -A && git commit && git push`
2. Deploy to Railway: `railway up --detach`
3. Update Railway DB image paths:
   ```bash
   python scripts/update_railway_images.py "<POSTGRES_PUBLIC_URL>"
   ```
   (The local SQLite has new paths, but Railway PostgreSQL needs to be synced)

---

## Dev handoff (continue work in a new session)
- Open this file first and run the commands under “Quick start”. Use 127.0.0.1 for both servers to avoid localhost/IPv6 quirks.
- Project layout
  - `backend/app/routers/` — API routes: `import_router.py`, `session.py`, `dashboard.py`
  - `backend/app/services/` — parsing/session logic
  - `backend/app/main.py` — FastAPI app + CORS + health
  - `frontend/src/pages/` — UI pages (`Dashboard.jsx`, `ExamSession.jsx`, `StudySession.jsx`)
  - `frontend/src/api/client.js` — frontend REST client
  - `pdfs/` — source PDFs; `data/az104.db` — SQLite DB

- Useful API calls
  - Status: `GET /api/import/status`
  - Scan PDFs: `POST /api/import/scan`
  - Import from last scan: `POST /api/import/run`
  - Dashboard data: `GET /api/dashboard`
  - Start exam: `POST /api/session/start {"mode":"random"}` (modes: `random|unseen|weak|review_wrong`)
  - Study set: `GET /api/session/study`

- Re-import flow (safe)
  1) `POST /api/import/scan`
  2) `POST /api/import/run`
  (DB is kept; duplicates are skipped with stable_id.)

- Clean restart (one-liners)
```bash
pkill -9 -f "uvicorn|vite|node" 2>/dev/null || true \
&& uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 & \
&& (cd frontend && npm run dev -- --strictPort --host 127.0.0.1 --port 5173 &)
```

## Future Improvements

See **[ROADMAP.md](ROADMAP.md)** for detailed feature plans and implementation priorities.

### Quick Summary:
- 📈 Performance Analytics Dashboard (progress tracking)
- 📊 Smart Review After Submission (review missed questions)
- 💡 Study Mode (show explanations during exam)
- 📝 Bookmarking & Notes
- 🔍 Question Search & Filter
- And more...

### Completed:
- ✅ User Authentication (Feb 15, 2026) - JWT-based login/register for Railway deployment
- ✅ Modern Design Refresh (Feb 13, 2026) - Warp-inspired UI
- ✅ Timer & Timed Mode (Feb 13, 2026)
- ✅ Dark Mode (Feb 13, 2026)
- ✅ Question readability improvements (Feb 13, 2026)
