#!/bin/bash
# NOTE: Development helper script for infection cluster detection Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
}

# Function to start the development environment
start_dev() {
    print_status "Starting infection cluster detection development environment..."
    check_docker
    
    # Build and start services
    docker-compose up --build -d postgres
    
    print_status "Waiting for PostgreSQL to be ready..."
    docker-compose exec postgres pg_isready -U postgres -d infection_clusters
    
    print_status "Starting backend and frontend services..."
    docker-compose up --build -d backend frontend
    
    print_status "Development environment started successfully!"
    print_status "Frontend: http://localhost:4200"
    print_status "Backend API: http://localhost:8000"
    print_status "Backend Docs: http://localhost:8000/docs"
    print_status "Database: localhost:5432"
}

# Function to start with LLM service
start_with_llm() {
    print_status "Starting infection cluster detection with LLM service..."
    check_docker
    
    # Check if GPU is available
    if ! command -v nvidia-smi &> /dev/null; then
        print_warning "NVIDIA GPU not detected. LLM service may not work optimally."
    fi
    
    docker-compose --profile llm up --build -d
    
    print_status "Full environment with LLM started successfully!"
    print_status "Frontend: http://localhost:4200"
    print_status "Backend API: http://localhost:8000"
    print_status "LLM Service: http://localhost:8001"
    print_status "Backend Docs: http://localhost:8000/docs"
}

# Function to stop the environment
stop_dev() {
    print_status "Stopping development environment..."
    docker-compose down
    print_status "Environment stopped."
}

# Function to show logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$service"
    fi
}

# Function to reset the environment
reset_dev() {
    print_warning "This will remove all containers, volumes, and networks."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Resetting development environment..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_status "Environment reset complete."
    else
        print_status "Reset cancelled."
    fi
}

# Function to run database migrations
migrate_db() {
    print_status "Running database migrations..."
    docker-compose exec backend python -c "from database import create_tables; create_tables()"
    print_status "Database migrations completed."
}

# Function to check service health
health_check() {
    print_status "Checking service health..."
    
    # Check PostgreSQL
    if docker-compose exec postgres pg_isready -U postgres -d infection_clusters > /dev/null 2>&1; then
        print_status "✓ PostgreSQL: Healthy"
    else
        print_error "✗ PostgreSQL: Unhealthy"
    fi
    
    # Check Backend
    if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
        print_status "✓ Backend: Healthy"
    else
        print_error "✗ Backend: Unhealthy"
    fi
    
    # Check Frontend
    if curl -s http://localhost:4200 > /dev/null 2>&1; then
        print_status "✓ Frontend: Healthy"
    else
        print_error "✗ Frontend: Unhealthy"
    fi
}

# Main script logic
case "$1" in
    "start")
        start_dev
        ;;
    "start-llm")
        start_with_llm
        ;;
    "stop")
        stop_dev
        ;;
    "restart")
        stop_dev
        start_dev
        ;;
    "logs")
        show_logs "$2"
        ;;
    "reset")
        reset_dev
        ;;
    "migrate")
        migrate_db
        ;;
    "health")
        health_check
        ;;
    *)
        echo "Usage: $0 {start|start-llm|stop|restart|logs [service]|reset|migrate|health}"
        echo ""
        echo "Commands:"
        echo "  start      - Start development environment (postgres, backend, frontend)"
        echo "  start-llm  - Start with LLM service (requires GPU)"
        echo "  stop       - Stop all services"
        echo "  restart    - Stop and start development environment"
        echo "  logs       - Show logs for all services or specific service"
        echo "  reset      - Remove all containers, volumes, and networks"
        echo "  migrate    - Run database migrations"
        echo "  health     - Check health of all services"
        exit 1
        ;;
esac