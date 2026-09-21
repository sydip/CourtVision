#!/usr/bin/env bash
set -e
# Wait for the running 2024-25 sync-season to finish.
while tasklist //FI "PID eq 55896" //NH 2>/dev/null | grep -qi python; do
  sleep 20
done
cd /c/Users/saide/.vscode/CourtVision/backend
echo "=== sync-season finished; rebuilding analytics for 2024-25 ==="
C:/Python314/python.exe -m app.ingestion.cli rebuild-analytics --season 2024-25
echo "=== REBUILD 2024-25 DONE ==="
