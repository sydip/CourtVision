#!/usr/bin/env bash
cd /c/Users/saide/.vscode/CourtVision/backend
for S in 2023-24 2022-23 2021-22; do
  echo "########## INGEST $S ##########"
  C:/Python314/python.exe -m app.ingestion.cli sync-season --season "$S" --roster-source season --game-log-source league --skip-profiles
  echo "########## REBUILD $S ##########"
  C:/Python314/python.exe -m app.ingestion.cli rebuild-analytics --season "$S"
  echo "########## DONE $S ##########"
done
echo "ALL_HISTORICAL_DONE"
