@echo off
title Cyber Patrol Assistant
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" "run.py" %*
) else (
    python "run.py" %*
)
