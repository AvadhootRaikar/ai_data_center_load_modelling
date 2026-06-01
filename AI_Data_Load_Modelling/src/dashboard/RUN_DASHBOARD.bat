@echo off
cd /d "%~dp0"
echo.
echo ============================================================================
echo                    LAUNCHING HPC OPTIMIZATION DASHBOARD
echo ============================================================================
echo.
echo Dashboard URL: http://localhost:8501
echo Press Ctrl+C in this window to stop the server
echo.
timeout /t 2 /nobreak
streamlit run dashboard/app_simplified.py
pause
