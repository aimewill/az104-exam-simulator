# AZ-104 Exam Simulator - Scripts Reference

## Quick Commands

### Start the Application
```bash
./start.sh
```
Starts both backend and frontend servers in the background.

**What it does:**
- Kills any existing instances
- Starts backend on http://127.0.0.1:8000
- Waits for backend to be ready
- Starts frontend on http://127.0.0.1:5173
- Shows URLs and log locations

### Stop the Application
```bash
./stop.sh
```
Cleanly stops both servers.

**What it does:**
- Reads PIDs from `.pids/` directory
- Gracefully kills backend and frontend
- Cleans up any lingering processes
- Removes PID files

### Check Status
```bash
./status.sh
```
Shows if servers are running and responding.

**What it does:**
- Checks if processes are alive
- Tests backend API
- Shows question count from database
- Displays access URLs

## Log Files

Logs are stored in `/tmp/`:
- Backend: `/tmp/az104_backend.log`
- Frontend: `/tmp/az104_frontend.log`

View logs in real-time:
```bash
# Backend logs
tail -f /tmp/az104_backend.log

# Frontend logs
tail -f /tmp/az104_frontend.log
```

## PID Files

Process IDs are stored in `.pids/`:
- `.pids/backend.pid`
- `.pids/frontend.pid`

These files are automatically created by `start.sh` and removed by `stop.sh`.

## Troubleshooting

### Servers won't start
```bash
# Force kill everything and try again
pkill -9 -f "uvicorn|vite|node"
./start.sh
```

### Check if ports are in use
```bash
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
```

### Clean restart
```bash
./stop.sh
rm -rf .pids/
./start.sh
```

## Access URLs

Once started:
- **Frontend (User Interface)**: http://127.0.0.1:5173
- **Backend (API)**: http://127.0.0.1:8000
- **API Docs**: http://127.0.0.1:8000/docs
