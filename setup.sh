#!/bin/bash

# DGH Feedback System - Installation Script
# Author: DEV 1 Team
# Date: 2025-07-15

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Check required tools
check_requirements() {
    log_info "Checking system requirements..."
    
    local missing_tools=()
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install the missing tools and run this script again"
        exit 1
    fi
    
    log_success "All required tools are installed"
}

# Check Docker daemon
check_docker() {
    log_info "Checking Docker daemon..."
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or user doesn't have permission"
        log_info "Please start Docker daemon or add user to docker group:"
        log_info "sudo usermod -aG docker \$USER"
        log_info "Then log out and log back in"
        exit 1
    fi
    
    log_success "Docker daemon is running"
}

# Create environment file
create_env_file() {
    log_info "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_success "Created .env file from .env.example"
        else
            log_error ".env.example file not found"
            exit 1
        fi
    else
        log_warning ".env file already exists, skipping creation"
    fi
    
    # Generate random JWT secret if not set
    if grep -q "your-super-secret-jwt-key-change-in-production" .env; then
        JWT_SECRET=$(openssl rand -hex 32)
        sed -i "s/your-super-secret-jwt-key-change-in-production/${JWT_SECRET}/" .env
        log_success "Generated random JWT secret"
    fi
}

# Create required directories
create_directories() {
    log_info "Creating required directories..."
    
    local directories=(
        "traefik/certs"
        "monitoring/grafana/dashboards"
        "monitoring/grafana/provisioning"
        "logs"
        "backups"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "Created directory: $dir"
        fi
    done
}

# Set proper permissions
set_permissions() {
    log_info "Setting proper permissions..."
    
    # Make scripts executable
    chmod +x scripts/*.sh
    chmod +x setup.sh
    
    # Set permissions for logs directory
    chmod 755 logs
    
    # Set permissions for backup directory
    chmod 755 backups
    
    log_success "Permissions set correctly"
}

# Pull Docker images
pull_images() {
    log_info "Pulling required Docker images..."
    
    docker-compose pull
    
    log_success "Docker images pulled successfully"
}

# Build custom images
build_images() {
    log_info "Building custom Docker images..."
    
    docker-compose build --no-cache
    
    log_success "Custom images built successfully"
}

# Initialize databases
init_databases() {
    log_info "Initializing databases..."
    
    # Start only database services first
    docker-compose up -d postgres redis mongodb
    
    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."
    sleep 30
    
    # Check PostgreSQL
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose exec -T postgres pg_isready -U dgh_user -d dgh_feedback &> /dev/null; then
            log_success "PostgreSQL is ready"
            break
        fi
        
        attempt=$((attempt + 1))
        log_info "Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        log_error "PostgreSQL failed to start after $max_attempts attempts"
        exit 1
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
        log_success "Redis is ready"
    else
        log_error "Redis failed to start"
        exit 1
    fi
    
    # Check MongoDB
    if docker-compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" &> /dev/null; then
        log_success "MongoDB is ready"
    else
        log_error "MongoDB failed to start"
        exit 1
    fi
}

# Start all services
start_services() {
    log_info "Starting all services..."
    
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 20
    
    # Check service health
    local services=("api-gateway" "feedback-api")
    
    for service in "${services[@]}"; do
        local max_attempts=20
        local attempt=0
        
        while [ $attempt -lt $max_attempts ]; do
            if docker-compose exec -T $service curl -f http://localhost:8000/health &> /dev/null; then
                log_success "$service is healthy"
                break
            fi
            
            attempt=$((attempt + 1))
            log_info "Waiting for $service... (attempt $attempt/$max_attempts)"
            sleep 3
        done
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "$service failed to become healthy"
            exit 1
        fi
    done
}

# Populate test data
populate_test_data() {
    log_info "Populating test data..."
    
    if [ -f scripts/populate-data.sh ]; then
        ./scripts/populate-data.sh
        log_success "Test data populated"
    else
        log_warning "populate-data.sh script not found, skipping test data"
    fi
}

# Run tests
run_tests() {
    log_info "Running system tests..."
    
    if [ -f scripts/test.sh ]; then
        ./scripts/test.sh
        log_success "All tests passed"
    else
        log_warning "test.sh script not found, skipping tests"
    fi
}

# Display final information
show_final_info() {
    log_success "DGH Feedback System installation completed successfully!"
    echo ""
    log_info "Services are available at:"
    echo "  🌐 API Gateway:     http://localhost:8080"
    echo "  📖 API Documentation: http://localhost:8080/docs"
    echo "  📊 Monitoring:      http://localhost:9090"
    echo "  📈 Dashboards:      http://localhost:3000"
    echo ""
    log_info "Default login credentials:"
    echo "  👤 Admin: admin / admin123"
    echo "  👥 Staff: staff / staff123"
    echo "  👁️  Viewer: viewer / viewer123"
    echo ""
    log_info "Useful commands:"
    echo "  📋 View logs:       docker-compose logs -f [service_name]"
    echo "  🔄 Restart:         docker-compose restart"
    echo "  ⏹️  Stop:            docker-compose down"
    echo "  🔧 Update:          git pull && docker-compose up -d --build"
    echo ""
    log_info "For troubleshooting, check the logs or run:"
    echo "  ./scripts/monitoring.sh"
}

# Main installation function
main() {
    echo "=================================================="
    echo "🏥 DGH Feedback System - Installation Script"
    echo "=================================================="
    echo ""
    
    check_root
    check_requirements
    check_docker
    create_env_file
    create_directories
    set_permissions
    pull_images
    build_images
    init_databases
    start_services
    populate_test_data
    run_tests
    show_final_info
}

# Handle script interruption
trap 'log_error "Installation interrupted"; exit 1' INT TERM

# Run main function
main "$@"