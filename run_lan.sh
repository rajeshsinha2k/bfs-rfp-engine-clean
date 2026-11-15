#!/bin/zsh
mkdir -p logs
LAN_IP=$(ipconfig getifaddr en0 || echo "localhost")

echo "======================================================"
echo " Autonomous BFS Pre-Sales RFP Engine (LAN Mode)"
echo " Desktop UI:             http://localhost:5173"
echo " Mobile / Windows LAN:   http://$LAN_IP:5173"
echo " FastAPI LAN Host:       http://$LAN_IP:8000"
echo " Backend Log:            ./logs/backend.log"
echo " Frontend Log:           ./logs/frontend.log"
echo " Press Ctrl + C to stop both servers cleanly."
echo "======================================================"

source ./startVenv.sh
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACK_PID=$!

(cd frontend && npm run dev -- --host 0.0.0.0 --port 5173) > logs/frontend.log 2>&1 &
FRONT_PID=$!

trap "kill $BACK_PID $FRONT_PID 2>/dev/null; echo '\nServers stopped.'" EXIT
wait
