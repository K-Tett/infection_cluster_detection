@echo off
REM NOTE: Simplified Windows/WSL startup script for Docker deployment
echo Starting Infection Cluster Detection System...
echo.

echo Building and starting Docker containers...
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

echo.
echo Waiting for services to start...
timeout /t 30 /nobreak > nul

echo.
echo ===================================
echo System Status:
echo ===================================
echo Frontend (Angular): http://localhost:4200
echo Backend API: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo Health Check: http://localhost:8000/health
echo.

echo To stop the system, run:
echo docker-compose down
echo.

echo To view logs, run:
echo docker-compose logs -f
echo.