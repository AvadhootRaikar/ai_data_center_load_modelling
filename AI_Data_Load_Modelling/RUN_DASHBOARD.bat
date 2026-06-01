@echo off
echo.
echo ============================================================================
echo                    LAUNCHING HPC OPTIMIZATION DASHBOARD
echo ============================================================================
echo.
echo Dashboard Type: MODERN (4 tabs - recommended)
echo Dashboard URL: http://localhost:8501
echo.
echo Press Ctrl+C in this window to stop the server
echo.
pause
cd /d "%~dp0"
streamlit run src/dashboard/app_simplified.py
