@echo off
chcp 65001 >nul
echo ===========================================
echo    Paper Search Demo Start
echo ===========================================
echo.

echo [1/4] Starting Docker containers...
docker-compose up -d --build

echo.
echo [2/4] Waiting for services to be ready...
timeout /t 30 /nobreak

echo.
echo [3/4] Creating sample data and embeddings...
docker-compose exec api python create_embeddings.py

echo.
echo [4/4] Demo environment ready!
echo.
echo ===========================================
echo    Access Information
echo ===========================================
echo Web UI:       http://localhost:3000
echo API Docs:     http://localhost:8000/docs
echo API Health:   http://localhost:8000/health
echo ===========================================
echo.
echo Open your browser and go to http://localhost:3000
echo.
echo To stop: Press Ctrl+C and run: docker-compose down
echo.
pause