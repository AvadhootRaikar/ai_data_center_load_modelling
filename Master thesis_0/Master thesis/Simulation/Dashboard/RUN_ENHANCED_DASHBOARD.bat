@echo off
cd /d "%~dp0"
echo.
echo ============================================================================
echo            LAUNCHING ENHANCED HPC OPTIMIZATION DASHBOARD
echo                  Master's Thesis + DS Project v0 Features
echo ============================================================================
echo.
echo Dashboard URL: http://localhost:8501
echo.
echo Features:
echo   - Original thesis workload comparison and simulation
echo   - NEW: Scenario optimization analysis
echo   - NEW: Financial ROI calculations
echo   - NEW: Carbon impact tracking
echo   - NEW: 3-phase implementation roadmap
echo.
echo Press Ctrl+C in this window to stop the server
echo.
timeout /t 2 /nobreak
streamlit run app_enhanced.py
pause
