#!/bin/bash
# AZ-104 Exam Simulator - Status Script

PROJECT_DIR="/Users/aimewill/Projects/Az104app"
PID_DIR="$PROJECT_DIR/.pids"

echo "📊 AZ-104 Exam Simulator Status"
echo "================================"
echo ""

# Check Backend
echo "Backend:"
if [ -f "$PID_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$PID_DIR/backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "  ✅ Running (PID: $BACKEND_PID)"
        if curl -s http://127.0.0.1:8000/api/import/status > /dev/null 2>&1; then
            echo "  ✅ API responding"
            # Get question count
            QUESTION_COUNT=$(curl -s http://127.0.0.1:8000/api/import/status | python3 -c "import json, sys; print(json.load(sys.stdin)['questions_in_db'])" 2>/dev/null || echo "unknown")
            echo "  📚 Questions in DB: $QUESTION_COUNT"
        else
            echo "  ⚠️  API not responding"
        fi
    else
        echo "  ❌ Not running (stale PID file)"
    fi
else
    echo "  ❌ Not running"
fi

echo ""

# Check Frontend
echo "Frontend:"
if [ -f "$PID_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "  ✅ Running (PID: $FRONTEND_PID)"
    else
        echo "  ❌ Not running (stale PID file)"
    fi
else
    echo "  ❌ Not running"
fi

echo ""
echo "URLs:"
echo "  Frontend: http://127.0.0.1:5173"
echo "  Backend:  http://127.0.0.1:8000"
echo ""
