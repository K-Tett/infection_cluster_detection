@echo off
REM NOTE: Windows development helper script for infection cluster detection Docker environment

setlocal enabledelayedexpansion

REM Function to check if Docker is running
:check_docker
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop.
    exit /b 1
)
goto :eof

REM Function to start the development environment
:start_dev
echo [INFO] Starting infection cluster detection development environment...
call :check_docker
if errorlevel 1 exit /b 1

REM Build and start services
docker-compose up --build -d postgres
if errorlevel 1 (
    echo [ERROR] Failed to start PostgreSQL
    exit /b 1
)

echo [INFO] Waiting for PostgreSQL to be ready...
timeout /t 10 /nobreak >nul
docker-compose exec postgres pg_isready -U postgres -d infection_clusters
if errorlevel 1 (
    echo [WARN] PostgreSQL may still be starting up...
    timeout /t 5 /nobreak >nul
)

echo [INFO] Starting backend and frontend services...
docker-compose up --build -d backend frontend
if errorlevel 1 (
    echo [ERROR] Failed to start backend and frontend services
    exit /b 1
)

echo [INFO] Development environment started successfully!
echo [INFO] Frontend: http://localhost:4200
echo [INFO] Backend API: http://localhost:8000
echo [INFO] Backend Docs: http://localhost:8000/docs
echo [INFO] Database: localhost:5432
goto :eof

REM Function to start with LLM service
:start_with_llm
echo [INFO] Starting infection cluster detection with LLM service...
call :check_docker
if errorlevel 1 exit /b 1

echo [WARN] Make sure you have NVIDIA GPU support configured for Docker
docker-compose --profile llm up --build -d
if errorlevel 1 (
    echo [ERROR] Failed to start services with LLM
    exit /b 1
)

echo [INFO] Full environment with LLM started successfully!
echo [INFO] Frontend: http://localhost:4200
echo [INFO] Backend API: http://localhost:8000
echo [INFO] LLM Service: http://localhost:8001
echo [INFO] Backend Docs: http://localhost:8000/docs
goto :eof

REM Function to stop the environment
:stop_dev
echo [INFO] Stopping development environment...
docker-compose down
echo [INFO] Environment stopped.
goto :eof

REM Function to show logs
:show_logs
if "%~2"=="" (
    docker-compose logs -f
) else (
    docker-compose logs -f %2
)
goto :eof

REM Function to reset the environment
:reset_dev
echo [WARN] This will remove all containers, volumes, and networks.
set /p confirm="Are you sure? (y/N): "
if /i "!confirm!"=="y" (
    echo [INFO] Resetting development environment...
    docker-compose down -v --remove-orphans
    docker system prune -f
    echo [INFO] Environment reset complete.
) else (
    echo [INFO] Reset cancelled.
)
goto :eof

REM Function to run database migrations
:migrate_db
echo [INFO] Running database migrations...
docker-compose exec backend python -c "from database import create_tables; create_tables()"
echo [INFO] Database migrations completed.
goto :eof

REM Function to check service health
:health_check
echo [INFO] Checking service health...

REM Check PostgreSQL
docker-compose exec postgres pg_isready -U postgres -d infection_clusters >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ✗ PostgreSQL: Unhealthy
) else (
    echo [INFO] ✓ PostgreSQL: Healthy
)

REM Check Backend
curl -s http://localhost:8000/health/ >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ✗ Backend: Unhealthy
) else (
    echo [INFO] ✓ Backend: Healthy
)

REM Check Frontend
curl -s http://localhost:4200 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ✗ Frontend: Unhealthy
) else (
    echo [INFO] ✓ Frontend: Healthy
)
goto :eof

REM Main script logic
if "%1"=="start" (
    call :start_dev
) else if "%1"=="start-llm" (
    call :start_with_llm
) else if "%1"=="stop" (
    call :stop_dev
) else if "%1"=="restart" (
    call :stop_dev
    call :start_dev
) else if "%1"=="logs" (
    call :show_logs %*
) else if "%1"=="reset" (
    call :reset_dev
) else if "%1"=="migrate" (
    call :migrate_db
) else if "%1"=="health" (
    call :health_check
) else (
    echo Usage: %0 {start^|start-llm^|stop^|restart^|logs [service]^|reset^|migrate^|health}
    echo.
    echo Commands:
    echo   start      - Start development environment ^(postgres, backend, frontend^)
    echo   start-llm  - Start with LLM service ^(requires GPU^)
    echo   stop       - Stop all services
    echo   restart    - Stop and start development environment
    echo   logs       - Show logs for all services or specific service
    echo   reset      - Remove all containers, volumes, and networks
    echo   migrate    - Run database migrations
    echo   health     - Check health of all services
)

endlocal