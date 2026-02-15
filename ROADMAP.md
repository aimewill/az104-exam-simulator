# AZ-104 Exam Simulator - Roadmap

## Current Status ✅
- 667 questions imported with full text
- 131 questions with exhibit images
- 24 questions grouped in related series
- Question references (Q# format)
- Paragraph formatting and abbreviation expansion

---

## Planned Improvements

### Priority 1: High-Impact Features 🎯

#### 1. Timer & Timed Mode ⏱️
**Status**: ✅ Completed (Feb 13, 2026)
**Impact**: High | **Effort**: Medium

Implemented features:
- ✅ Countdown timer in exam sessions (default 100 minutes)
- ✅ Configurable time limit (10-180 minutes)
- ✅ Yellow warning at ≤10 minutes remaining
- ✅ Red critical warning at ≤2 minutes (with pulse animation)
- ✅ "Timed Mode" vs "Practice Mode" toggle on Dashboard
- ✅ Pause/Resume functionality
- ✅ Auto-submit when time expires

**Files modified**:
- `backend/app/models.py` - Added `paused_at`, `total_paused_seconds` fields
- `backend/app/routers/session.py` - Added `/time`, `/pause`, `/resume` endpoints
- `frontend/src/pages/Dashboard.jsx` - Timer mode toggle UI
- `frontend/src/pages/ExamSession.jsx` - Timer component
- `frontend/src/api/client.js` - Timer API methods

---

#### 2. Performance Analytics Dashboard 📈
**Status**: Planned
**Impact**: High | **Effort**: Medium

Track progress over time:
- Score trend graph (last 10 sessions)
- Average score by domain with visual charts
- "Weak areas" heat map
- Time-to-complete trends
- Best/worst question types (single/multi)
- Session history with drill-down details
- Export analytics to CSV

**Files to modify**:
- `frontend/src/pages/Dashboard.jsx` - Add analytics charts
- `backend/app/routers/dashboard.py` - Analytics endpoints
- Add charting library (recharts or chart.js)

---

#### 3. Smart Review After Submission 📊
**Status**: Planned
**Impact**: High | **Effort**: Low

Focused review after exam:
- After submitting, show review options:
  - Only incorrect answers
  - Questions you flagged
  - Questions you skipped (no answer)
- One-click "Review Missed Questions" button
- Filter toggle on results page
- Quick navigation between wrong answers

**Files to modify**:
- `frontend/src/pages/Results.jsx` - Add filter buttons
- Add "Review Mode" that highlights only specific questions

---

### Priority 2: Quality-of-Life Improvements ✨

#### 4. Explanation Display During Exam 💡
**Status**: Planned
**Impact**: Medium | **Effort**: Low

Learning mode vs pure test mode:
- Toggle to show/hide explanations immediately after answering
- "Study Mode" vs "Exam Mode" setting
- Show explanation with green/red feedback without ending session
- Optional: reveal answer immediately after selection
- Configurable in session settings

**Files to modify**:
- `frontend/src/pages/ExamSession.jsx` - Add explanation reveal
- `backend/app/routers/session.py` - Mode parameter

---

#### 5. Dark Mode 🌙
**Status**: Planned
**Impact**: Medium | **Effort**: Low

Eye strain relief:
- Toggle dark/light theme
- Persist preference in localStorage
- Better contrast for late-night studying
- Dark-friendly exhibit images (border adjustments)
- Theme toggle in header/settings

**Files to modify**:
- `frontend/src/index.css` - Add dark theme variables
- `frontend/src/App.jsx` - Theme context/toggle
- All component styles - Support CSS variables

---

#### 6. Question Bookmarking & Notes 📝
**Status**: Planned
**Impact**: Medium | **Effort**: Medium

Personal study aids:
- Bookmark specific questions
- Add personal notes to questions
- "My Bookmarks" page
- Filter exams to only bookmarked questions
- Tag questions with custom labels
- Export bookmarks with notes

**Files to modify**:
- `backend/app/models.py` - Add UserBookmark model
- `backend/app/routers/` - Bookmark endpoints
- `frontend/src/pages/Bookmarks.jsx` - New page

---

#### 7. Question Search & Filter 🔍
**Status**: Planned
**Impact**: Medium | **Effort**: Medium

Find specific topics:
- Search questions by keyword (full-text search)
- Filter by domain, question type
- Filter by status (never seen, got wrong, mastered)
- "Questions I got wrong 3+ times"
- Advanced filters (has exhibit, in series, etc.)

**Files to modify**:
- `backend/app/routers/dashboard.py` - Search endpoint
- `frontend/src/pages/Dashboard.jsx` - Search UI
- Add search index to database

---

#### 8. Export Results to PDF 📄
**Status**: Planned
**Impact**: Low | **Effort**: Low

Offline study materials:
- Export session results as PDF
- Include questions, answers, explanations
- Printable format for offline study
- Include exhibit images in PDF
- Optional: export all bookmarked questions

**Files to modify**:
- `backend/app/routers/session.py` - PDF generation endpoint
- Add PDF library (reportlab or weasyprint)

---

### Priority 3: Advanced Features 🚀

#### 9. Mobile Responsive Design 📱
**Status**: Planned
**Impact**: Medium | **Effort**: High

Study on any device:
- Responsive layout for tablets/phones
- Touch-friendly navigation
- Optimized image loading for mobile
- PWA support for offline use
- Install as app on iOS/Android

**Files to modify**:
- All frontend components - Add responsive CSS
- `frontend/public/manifest.json` - PWA config
- Add service worker for offline support

---

#### 10. AI-Powered Question Difficulty 🤖
**Status**: Future
**Impact**: Medium | **Effort**: Medium

Adaptive learning:
- Calculate difficulty based on global pass rate
- "Easy/Medium/Hard" badges on questions
- Adaptive mode: harder questions when you're doing well
- Personalized difficulty based on your history
- Recommend review schedule based on difficulty

**Files to modify**:
- `backend/app/models.py` - Add difficulty field
- `backend/app/services/` - Difficulty calculation service
- Requires aggregate statistics across sessions

---

#### 11. Flashcard Mode 🃏
**Status**: Future
**Impact**: Medium | **Effort**: Medium

Quick concept review:
- Convert questions to flashcards
- Spaced repetition algorithm (SM-2)
- "Daily review" of weak topics
- Flip cards for answers
- Separate flashcard session mode

**Files to modify**:
- `frontend/src/pages/FlashcardSession.jsx` - New page
- `backend/app/services/flashcard_service.py` - Spaced repetition logic

---

#### 12. Multi-User Support 👥
**Status**: Future
**Impact**: Low | **Effort**: High

Study with partners (optional):
- User profiles with separate progress
- Optional leaderboard
- Share bookmarks/notes between users
- Requires authentication system

**Files to modify**:
- Add authentication (JWT or sessions)
- `backend/app/models.py` - User model
- All routers - Add user context
- Significant architectural change

---

## User Feedback & Requests 📣

### Question Readability Improvements
**Status**: ✅ Completed (Feb 13, 2026)
**Requested by**: User

Implemented improvements:
- ✅ Proper paragraph formatting with line breaks
- ✅ Abbreviation expansion (qis → question is, qs → questions, qin → question in, qsets → question sets)
- ✅ Enhanced text spacing and word separation
- ✅ Added `whiteSpace: 'pre-line'` CSS for proper rendering

Further potential improvements:
- Better handling of bullet points and numbered lists
- Auto-detect and format code snippets (PowerShell, CLI commands)
- Highlight Azure service names in questions
- Add tooltips for Azure terminology

---

## Implementation Priority

### Phase 1 (Quick Wins - Next Session)
1. Smart Review After Submission (2-3 hours)
2. Dark Mode (2-3 hours)
3. Explanation Display During Exam (1-2 hours)

### Phase 2 (High Value - Next Week)
1. ~~Timer & Timed Mode~~ ✅ Completed
2. Performance Analytics Dashboard (6-8 hours)

### Phase 3 (Medium Term - Next Month)
1. Question Bookmarking & Notes
2. Question Search & Filter
3. Export Results to PDF

### Phase 4 (Long Term - Future)
1. Mobile Responsive Design
2. AI-Powered Difficulty
3. Flashcard Mode
4. Multi-User Support (if needed)

---

## Technical Debt & Maintenance

### Code Quality
- Add unit tests for parser functions
- Add integration tests for API endpoints
- Type hints for all Python functions
- ESLint/Prettier for frontend consistency

### Performance
- Add pagination to results page (for large sessions)
- Optimize image loading (lazy loading, compression)
- Add database indices for frequently queried fields
- Cache domain statistics

### Documentation
- API documentation (OpenAPI/Swagger)
- Component documentation (Storybook)
- Deployment guide for production
- Backup/restore procedures

---

## Contributing

To suggest new features or report issues:
1. Check this roadmap first
2. Add suggestions to the "User Feedback & Requests" section
3. Mark priority (High/Medium/Low) and estimated effort

Last updated: Feb 13, 2026
