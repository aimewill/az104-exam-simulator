# AZ-104 Exam Simulator

A local, offline exam simulator for Microsoft Azure Administrator (AZ-104) certification preparation. Parses practice questions from PDFs, tracks your progress, and identifies weak areas.

**Current Status**: ✅ Fully operational with 667 questions imported, including 208 with exhibit/table images (99.5% accuracy) and 37 grouped in 11 related series.

## Features

### Core Functionality
- **PDF Import**: Automatically extracts questions from AZ-104 practice exam PDFs
- **60-Question Sessions**: Simulates real exam conditions
- **Multiple Exam Modes**:
  - Random: Randomly selected questions
  - Unseen First: Prioritizes questions you haven't seen
  - Weak Areas: Focuses on domains where you score lowest
  - Review Wrong: Only previously missed questions
- **Score Tracking**: Percent score and scaled score (0-1000, passing at 700)
- **Domain Classification**: Auto-classifies questions into AZ-104 domains
- **Progress Dashboard**: Score trends, weak areas, session history
- **Keyboard Shortcuts**: 1-9 for choices, F to flag, N/P for navigation
- **Offline**: Runs entirely on your Mac, no external APIs needed

### Advanced Features 🆕
- **🔐 User Authentication**: Register/login to track your personal progress (required to start exams)
- **🌙 Dark Mode**: Toggle between light and dark themes (persists in localStorage, respects system preference)
- **🖼️ Exhibit Images**: Automatically extracts and displays 208 diagram/screenshot/table images from PDFs (correctly matched to questions)
- **🔗 Question Series**: Related questions (same scenario) stay together for context (37 questions in 11 series)
- **📝 Question References**: Each question shows its PDF reference number (Q1, Q94, Q188, etc.)
- **📖 Enhanced Readability**: 
  - Proper paragraph formatting with line breaks
  - Automatic abbreviation expansion (qis → question is, qs → questions)
  - Clean, professional text presentation

## Project Structure

```
Az104app/
├── backend/           # Python FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py     # Database models (with exhibit_image, series_id, sequence_number)
│   │   ├── database.py
│   │   ├── config.py
│   │   ├── routers/
│   │   ├── services/     # parser.py (image extraction + series detection)
│   │   └── static/
│   │       └── exhibits/ # Extracted exhibit images (208 images)
│   ├── tests/
│   └── requirements.txt
├── frontend/          # React + Vite frontend
│   ├── src/
│   │   ├── pages/        # ExamSession.jsx, Results.jsx (with image display)
│   │   ├── api/
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── pdfs/              # Place your PDF files here
├── data/              # SQLite database (auto-created, 667 questions)
├── config/
│   └── domains.json   # Domain keyword mappings
├── start.sh           # Start both servers
├── stop.sh            # Stop both servers
├── status.sh          # Check server status
├── SCRIPTS.md         # Script documentation
├── ROADMAP.md         # Future features and improvements
├── WARP.md            # Development notes and progress tracker
└── README.md
```

## Requirements

- macOS
- Python 3.11+
- Node.js 18+
- npm

## Setup

### 1. Backend Setup

```bash
# Navigate to project directory
cd ~/Projects/Az104app

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd ~/Projects/Az104app/frontend

# Install dependencies
npm install
```

### 3. Add PDF Files

Place your AZ-104 practice exam PDF files in the `pdfs/` directory:

```bash
# Your PDFs should be here
~/Projects/Az104app/pdfs/
```

## Running the Application

### Quick Start (Recommended)

Use the provided scripts to start and stop the application:

```bash
cd ~/Projects/Az104app

# Start both backend and frontend
./start.sh

# Check if servers are running
./status.sh

# Stop both servers
./stop.sh
```

The app will be available at **http://127.0.0.1:5173**

### Manual Start (Alternative)

#### Start Backend Server

```bash
# From project root, activate venv if not already active
cd ~/Projects/Az104app
source venv/bin/activate

# Start FastAPI server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The backend will be available at `http://127.0.0.1:8000`

#### Start Frontend (in a new terminal)

```bash
cd ~/Projects/Az104app/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

The frontend will be available at `http://127.0.0.1:5173`

## First Run

1. The app will detect that the database is empty
2. You'll be redirected to the Import page
3. Click "Scan PDFs" to parse your PDF files
4. Review the scan results (total questions, issues found)
5. Click "Import" to add questions to the database
6. Start practicing!

If no PDFs are found, demo questions will be available for testing.

## Running Tests

```bash
# Activate virtual environment
cd ~/Projects/Az104app
source venv/bin/activate

# Run backend tests
cd backend
pytest -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/import/status` | GET | Check if import is needed |
| `/api/import/scan` | POST | Scan PDFs and extract questions |
| `/api/import/run` | POST | Import scanned questions |
| `/api/session/start` | POST | Start new exam session |
| `/api/session/answer` | POST | Record an answer |
| `/api/session/{id}/submit` | POST | Submit and grade exam |
| `/api/session/{id}/results` | GET | Get detailed results |
| `/api/dashboard` | GET | Dashboard stats |
| `/api/export/missed.csv` | GET | Export missed questions |

## Keyboard Shortcuts

During an exam session:

| Key | Action |
|-----|--------|
| `1-9` | Select answer choice |
| `F` | Flag question for review |
| `N` or `→` | Next question |
| `P` or `←` | Previous question |

## Scoring

- **Scaled Score**: 0-1000 based on `round(1000 * correct / total)`
- **Passing Score**: 700
- **Questions per Session**: 60

## Domain Configuration

Edit `config/domains.json` to customize domain keywords:

```json
{
  "domains": [
    {
      "id": "storage",
      "name": "Implement and manage storage",
      "keywords": ["blob", "storage account", "container", ...]
    }
  ]
}
```

## Troubleshooting

### PDF Parsing Issues

- Ensure PDFs contain selectable text (not scanned images)
- Check the import report for specific issues
- Questions with missing answers or broken choices are skipped

### Exhibit Images Not Showing

- Check that images were extracted: `ls backend/app/static/exhibits/`
- Verify backend is serving static files: `curl http://127.0.0.1:8000/static/exhibits/`
- Images are only extracted for questions referencing "exhibit" keywords
- Clear browser cache if images don't update after re-import

### Exhibit Images Showing Wrong Content

If an exhibit image shows data that doesn't match the question (e.g., Q327 about VM1/VNET1 shows a table with VM3/VM4/VM5):

1. **Re-extract images locally:**
   ```bash
   source venv/bin/activate
   python scripts/reextract_images.py
   ```

2. **Push new images to Git and redeploy:**
   ```bash
   git add -A && git commit -m "Re-extract images" && git push
   railway up --detach
   ```

3. **Update Railway PostgreSQL with new paths:**
   ```bash
   python scripts/update_railway_images.py "<POSTGRES_PUBLIC_URL>"
   ```

This happens because the image extraction must match question text to the correct PDF page, and Railway's PostgreSQL database needs to be synced with the new image paths.

### Question Series Not Grouping

- Series detection looks for "Note: The question is included in a number of questions..."
- Questions must have identical scenario text to be grouped
- Check series_id in database: `sqlite3 data/az104.db "SELECT series_id, COUNT(*) FROM questions WHERE series_id IS NOT NULL GROUP BY series_id;"`

### Database Reset

To start fresh, delete the database:

```bash
rm ~/Projects/Az104app/data/az104.db
```

### Port Conflicts

If ports 8000 or 5173 are in use:

```bash
# Backend: use different port
uvicorn backend.app.main:app --reload --port 8001

# Frontend: edit vite.config.js or use
npm run dev -- --port 5174
```

## Future Development

See **[ROADMAP.md](ROADMAP.md)** for planned features and improvements including:
- Performance Analytics Dashboard  
- Smart Review After Submission
- Question Bookmarking & Notes
- And more...

### Recently Completed
- ✅ Timer & Timed Mode
- ✅ Dark Mode

**User Feedback**: Question readability improvements completed (Feb 13, 2026) - proper paragraphs, abbreviation expansion, enhanced formatting.

---

## License

For personal educational use only.
