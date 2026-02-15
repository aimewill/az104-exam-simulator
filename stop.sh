#!/bin/bash
# AZ-104 Exam Simulator - Stop Script

PROJECT_DIR="/Users/aimewill/Projects/Az104app"
PID_DIR="$PROJECT_DIR/.pids"

echo "🛑 Stopping AZ-104 Exam Simulator..."

# Stop backend
if [ -f "$PID_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$PID_DIR/backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "   Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            kill -9 $BACKEND_PID 2>/dev/null || true
        fi
        echo "   ✅ Backend stopped"
    else
        echo "   ⚠️  Backend not running"
    fi
    rm -f "$PID_DIR/backend.pid"
else
    echo "   ⚠️  No backend PID file found"
fi

# Stop frontend
if [ -f "$PID_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "   Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            kill -9 $FRONTEND_PID 2>/dev/null || true
        fi
        echo "   ✅ Frontend stopped"
    else
        echo "   ⚠️  Frontend not running"
    fi
    rm -f "$PID_DIR/frontend.pid"
else
    echo "   ⚠️  No frontend PID file found"
fi

# Clean up any lingering processes
echo "   Cleaning up any lingering processes..."
pkill -9 -f "uvicorn.*backend.app.main" 2>/dev/null || true
pkill -9 -f "vite.*5173" 2>/dev/null || true

echo ""
echo "✅ AZ-104 Exam Simulator stopped!"
echo ""
