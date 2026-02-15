#!/bin/bash
# AZ-104 Exam Simulator - Start Script

set -e

PROJECT_DIR="/Users/aimewill/Projects/Az104app"
BACKEND_LOG="/tmp/az104_backend.log"
FRONTEND_LOG="/tmp/az104_frontend.log"
PID_DIR="$PROJECT_DIR/.pids"

# Create PID directory if it doesn't exist
mkdir -p "$PID_DIR"

echo "🚀 Starting AZ-104 Exam Simulator..."

# Kill any existing instances
echo "   Cleaning up any existing processes..."
pkill -9 -f "uvicorn.*backend.app.main" 2>/dev/null || true
pkill -9 -f "vite.*5173" 2>/dev/null || true
sleep 1

# Start Backend
echo "   Starting backend server..."
cd "$PROJECT_DIR"
source venv/bin/activate
nohup uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_DIR/backend.pid"
echo "   ✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "   Waiting for backend to initialize..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/api/import/status > /dev/null 2>&1; then
        echo "   ✅ Backend ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ❌ Backend failed to start. Check logs: $BACKEND_LOG"
        exit 1
    fi
    sleep 1
done

# Start Frontend
echo "   Starting frontend server..."
cd "$PROJECT_DIR/frontend"
nohup npm run dev -- --host 127.0.0.1 --port 5173 > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PID_DIR/frontend.pid"
echo "   ✅ Frontend started (PID: $FRONTEND_PID)"

# Wait for frontend to be ready
echo "   Waiting for frontend to initialize..."
sleep 3

echo ""
echo "✅ AZ-104 Exam Simulator is running!"
echo ""
echo "📊 Access the app at: http://127.0.0.1:5173"
echo "🔧 Backend API at:    http://127.0.0.1:8000"
echo ""
echo "📝 Logs:"
echo "   Backend:  $BACKEND_LOG"
echo "   Frontend: $FRONTEND_LOG"
echo ""
echo "🛑 To stop the app, run: ./stop.sh"
echo ""
