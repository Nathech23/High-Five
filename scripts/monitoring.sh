#!/bin/bash

# DGH Feedback System - Monitoring Script
# This script monitors system health and performance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
API_GATEWAY_URL="http://localhost:8080"
FEEDBACK_API_URL="http://localhost:8080/api/v1"
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3000"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_metric() {
    echo -e "${CYAN}[METRIC]${NC} $1"
}

# Get current timestamp
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Check if service is running
check_service_status() {
    local service_name="$1"
    local container_name="$2"
    
    if docker ps --filter name="$container_name" --filter status=running | grep -q "$container_name"; then
        log_success "$service_name is running"
        return 0
    else
        log_error "$service_name is not running"
        return 1
    fi
}

# Check HTTP endpoint
check_http_endpoint() {
    local service_name="$1"
    local url="$2"
    local expected_code="${3:-200}"
    
    local response=$(curl -s -w '%{http_code}' -o /dev/null "$url" 2>/dev/null || echo "000")
    
    if [ "$response" -eq "$expected_code" ]; then
        log_success "$service_name endpoint is healthy (HTTP $response)"
        return 0
    else
        log_error "$service_name endpoint is unhealthy (HTTP $response)"
        return 1
    fi
}

# Get response time
get_response_time() {
    local url="$1"
    local time=$(curl -s -w '%{time_total}' -o /dev/null "$url" 2>/dev/null || echo "0")
    echo "$time"
}

# Check container health
check_container_health() {
    log_info "Checking container health..."
    echo ""
    
    local containers=(
        "PostgreSQL:dgh_postgres"
        "Redis:dgh_redis"
        "MongoDB:dgh_mongodb"
        "Traefik:dgh_traefik"
        "API Gateway:dgh_api_gateway"
        "Feedback API:dgh_feedback_api"
        "Prometheus:dgh_prometheus"
        "Grafana:dgh_grafana"
    )
    
    local healthy_count=0
    local total_count=${#containers[@]}
    
    for container_info in "${containers[@]}"; do
        IFS=':' read -r service_name container_name <<< "$container_info"
        if check_service_status "$service_name" "$container_name"; then
            healthy_count=$((healthy_count + 1))
        fi
    done
    
    echo ""
    log_metric "Container Health: $healthy_count/$total_count healthy"
    
    if [ $healthy_count -eq $total_count ]; then
        return 0
    else
        return 1
    fi
}

# Check API endpoints
check_api_health() {
    log_info "Checking API endpoint health..."
    echo ""
    
    local endpoints=(
        "API Gateway Health:$API_GATEWAY_URL/health"
        "Feedback API Health:$FEEDBACK_API_URL/../health"
        "Feedback API Ready:$FEEDBACK_API_URL/../health/ready"
        "Feedback API Live:$FEEDBACK_API_URL/../health/live"
        "Prometheus:$PROMETHEUS_URL/-/healthy"
        "Grafana:$GRAFANA_URL/api/health"
    )
    
    local healthy_endpoints=0
    local total_endpoints=${#endpoints[@]}
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r name url <<< "$endpoint_info"
        if check_http_endpoint "$name" "$url"; then
            healthy_endpoints=$((healthy_endpoints + 1))
        fi
    done
    
    echo ""
    log_metric "API Health: $healthy_endpoints/$total_endpoints endpoints healthy"
    
    if [ $healthy_endpoints -eq $total_endpoints ]; then
        return 0
    else
        return 1
    fi
}

# Check database connectivity
check_database_health() {
    log_info "Checking database connectivity..."
    echo ""
    
    # PostgreSQL
    if docker exec dgh_postgres pg_isready -U dgh_user -d dgh_feedback &>/dev/null; then
        log_success "PostgreSQL is accessible"
        
        # Get connection count
        local pg_connections=$(docker exec dgh_postgres psql -U dgh_user -d dgh_feedback -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
        log_metric "PostgreSQL active connections: $pg_connections"
        
        # Get database size
        local db_size=$(docker exec dgh_postgres psql -U dgh_user -d dgh_feedback -t -c "SELECT pg_size_pretty(pg_database_size('dgh_feedback'));" 2>/dev/null | xargs)
        log_metric "Database size: $db_size"
    else
        log_error "PostgreSQL is not accessible"
    fi
    
    # Redis
    if docker exec dgh_redis redis-cli ping | grep -q PONG 2>/dev/null; then
        log_success "Redis is accessible"
        
        # Get Redis info
        local redis_memory=$(docker exec dgh_redis redis-cli info memory | grep used_memory_human | cut -d':' -f2 | tr -d '\r')
        log_metric "Redis memory usage: $redis_memory"
        
        local redis_keys=$(docker exec dgh_redis redis-cli dbsize 2>/dev/null)
        log_metric "Redis keys count: $redis_keys"
    else
        log_error "Redis is not accessible"
    fi
    
    # MongoDB
    if docker exec dgh_mongodb mongosh --eval "db.adminCommand('ping')" &>/dev/null; then
        log_success "MongoDB is accessible"
        
        # Get MongoDB stats
        local mongo_stats=$(docker exec dgh_mongodb mongosh --quiet --eval "JSON.stringify(db.stats())" 2>/dev/null)
        if [ -n "$mongo_stats" ]; then
            local db_count=$(echo "$mongo_stats" | grep -o '"collections":[0-9]*' | cut -d':' -f2)
            log_metric "MongoDB collections: ${db_count:-0}"
        fi
    else
        log_error "MongoDB is not accessible"
    fi
    
    echo ""
}

# Check system resources
check_system_resources() {
    log_info "Checking system resources..."
    echo ""
    
    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    log_metric "CPU usage: ${cpu_usage}%"
    
    # Memory usage
    local memory_info=$(free -h | grep '^Mem:')
    local memory_used=$(echo "$memory_info" | awk '{print $3}')
    local memory_total=$(echo "$memory_info" | awk '{print $2}')
    log_metric "Memory usage: $memory_used / $memory_total"
    
    # Disk usage
    local disk_usage=$(df -h / | tail -1 | awk '{print $5}')
    log_metric "Disk usage: $disk_usage"
    
    # Docker stats
    log_info "Container resource usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | head -10
    
    echo ""
}

# Check API performance
check_api_performance() {
    log_info "Checking API performance..."
    echo ""
    
    # Test endpoints with response times
    local endpoints=(
        "API Gateway Health:$API_GATEWAY_URL/health"
        "Feedback API Health:$FEEDBACK_API_URL/../health"
        "Departments API:$FEEDBACK_API_URL/departments"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r name url <<< "$endpoint_info"
        local response_time=$(get_response_time "$url")
        local response_time_ms=$(echo "$response_time * 1000" | bc -l 2>/dev/null | cut -d'.' -f1)
        
        if [ -n "$response_time_ms" ] && [ "$response_time_ms" -gt 0 ]; then
            if [ "$response_time_ms" -lt 200 ]; then
                log_success "$name: ${response_time_ms}ms"
            elif [ "$response_time_ms" -lt 1000 ]; then
                log_warning "$name: ${response_time_ms}ms (slow)"
            else
                log_error "$name: ${response_time_ms}ms (very slow)"
            fi
        else
            log_error "$name: timeout or error"
        fi
    done
    
    echo ""
}

# Check recent logs for errors
check_recent_errors() {
    log_info "Checking recent errors (last 100 lines)..."
    echo ""
    
    local services=("dgh_api_gateway" "dgh_feedback_api" "dgh_postgres" "dgh_redis")
    local error_count=0
    
    for service in "${services[@]}"; do
        local errors=$(docker logs --tail 100 "$service" 2>&1 | grep -i -E "(error|exception|failed|fatal)" | wc -l)
        
        if [ "$errors" -gt 0 ]; then
            log_warning "$service: $errors recent errors"
            error_count=$((error_count + errors))
            
            # Show last few errors
            echo "Recent errors from $service:"
            docker logs --tail 20 "$service" 2>&1 | grep -i -E "(error|exception|failed|fatal)" | tail -3 | while read -r line; do
                echo "  $line"
            done
            echo ""
        else
            log_success "$service: no recent errors"
        fi
    done
    
    log_metric "Total recent errors: $error_count"
    echo ""
}

# Generate system statistics
generate_statistics() {
    log_info "Generating system statistics..."
    echo ""
    
    # Get authentication token for API calls
    local token=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' \
        "$API_GATEWAY_URL/auth/login" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$token" ]; then
        # Get system statistics
        local stats_response=$(curl -s -H "Authorization: Bearer $token" "$FEEDBACK_API_URL/feedbacks/stats" 2>/dev/null)
        
        if echo "$stats_response" | grep -q "total_feedbacks"; then
            local total_feedbacks=$(echo "$stats_response" | grep -o '"total_feedbacks":[0-9]*' | cut -d':' -f2)
            local avg_rating=$(echo "$stats_response" | grep -o '"avg_rating":[0-9.]*' | cut -d':' -f2)
            local urgent_count=$(echo "$stats_response" | grep -o '"urgent_count":[0-9]*' | cut -d':' -f2)
            
            log_metric "Total Feedbacks: ${total_feedbacks:-0}"
            log_metric "Average Rating: ${avg_rating:-0}"
            log_metric "Urgent Feedbacks: ${urgent_count:-0}"
        fi
        
        # Get departments count
        local dept_response=$(curl -s -H "Authorization: Bearer $token" "$FEEDBACK_API_URL/departments" 2>/dev/null)
        local dept_count=$(echo "$dept_response" | grep -o '"id":[0-9]*' | wc -l)
        log_metric "Departments: $dept_count"
        
        # Get patients count
        local patients_response=$(curl -s -H "Authorization: Bearer $token" "$FEEDBACK_API_URL/patients?limit=1" 2>/dev/null)
        if echo "$patients_response" | grep -q '"id":'; then
            log_metric "Patients: Active"
        else
            log_metric "Patients: No data"
        fi
    else
        log_warning "Could not authenticate to get detailed statistics"
    fi
    
    echo ""
}

# Check security status
check_security() {
    log_info "Checking security status..."
    echo ""
    
    # Check if containers are running as non-root
    local containers=("dgh_api_gateway" "dgh_feedback_api")
    
    for container in "${containers[@]}"; do
        local user_info=$(docker exec "$container" whoami 2>/dev/null || echo "unknown")
        if [ "$user_info" = "root" ]; then
            log_warning "$container is running as root"
        else
            log_success "$container is running as: $user_info"
        fi
    done
    
    # Check for HTTPS
    if curl -s -k "https://localhost" &>/dev/null; then
        log_success "HTTPS is available"
    else
        log_warning "HTTPS is not configured"
    fi
    
    # Check authentication
    local auth_test=$(curl -s -w '%{http_code}' -o /dev/null "$FEEDBACK_API_URL/patients")
    if [ "$auth_test" -eq 401 ] || [ "$auth_test" -eq 403 ]; then
        log_success "API authentication is enforced"
    else
        log_warning "API might not be properly protected (HTTP $auth_test)"
    fi
    
    echo ""
}

# Generate monitoring report
generate_report() {
    local timestamp=$(get_timestamp)
    local report_file="monitoring_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "Generating monitoring report: $report_file"
    
    {
        echo "DGH Feedback System - Monitoring Report"
        echo "======================================="
        echo "Generated: $timestamp"
        echo ""
        
        echo "CONTAINER STATUS:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        
        echo "SYSTEM RESOURCES:"
        echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
        echo "Memory: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')"
        echo "Disk: $(df -h / | tail -1 | awk '{print $5}')"
        echo ""
        
        echo "API ENDPOINTS STATUS:"
        local endpoints=(
            "$API_GATEWAY_URL/health"
            "$FEEDBACK_API_URL/../health"
            "$PROMETHEUS_URL/-/healthy"
            "$GRAFANA_URL/api/health"
        )
        
        for endpoint in "${endpoints[@]}"; do
            local status=$(curl -s -w '%{http_code}' -o /dev/null "$endpoint" 2>/dev/null || echo "ERROR")
            echo "$endpoint: $status"
        done
        echo ""
        
        echo "RECENT ERRORS:"
        local services=("dgh_api_gateway" "dgh_feedback_api")
        for service in "${services[@]}"; do
            local errors=$(docker logs --tail 50 "$service" 2>&1 | grep -i -E "(error|exception|failed|fatal)" | wc -l)
            echo "$service: $errors errors"
        done
        echo ""
        
        echo "DATABASE STATUS:"
        echo "PostgreSQL: $(docker exec dgh_postgres pg_isready -U dgh_user -d dgh_feedback 2>/dev/null && echo "OK" || echo "ERROR")"
        echo "Redis: $(docker exec dgh_redis redis-cli ping 2>/dev/null || echo "ERROR")"
        echo "MongoDB: $(docker exec dgh_mongodb mongosh --eval "db.adminCommand('ping')" 2>/dev/null | grep -q '"ok" : 1' && echo "OK" || echo "ERROR")"
        
    } > "$report_file"
    
    log_success "Report saved to: $report_file"
}

# Show dashboard
show_dashboard() {
    clear
    echo "=================================================="
    echo "🏥 DGH Feedback System - Live Dashboard"
    echo "=================================================="
    echo "Last Update: $(get_timestamp)"
    echo ""
    
    # Quick status overview
    local container_status="🔴"
    local api_status="🔴"
    local db_status="🔴"
    
    # Check containers
    if docker ps | grep -q "dgh_"; then
        container_status="🟢"
    fi
    
    # Check API
    if curl -s "$API_GATEWAY_URL/health" | grep -q "healthy"; then
        api_status="🟢"
    fi
    
    # Check databases
    if docker exec dgh_postgres pg_isready -U dgh_user -d dgh_feedback &>/dev/null; then
        db_status="🟢"
    fi
    
    echo "Status Overview:"
    echo "  Containers: $container_status"
    echo "  APIs: $api_status"
    echo "  Databases: $db_status"
    echo ""
    
    # System metrics
    echo "System Metrics:"
    echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "  Memory: $(free -h | grep '^Mem:' | awk '{print $3 "/" $2}')"
    echo "  Disk: $(df -h / | tail -1 | awk '{print $5}')"
    echo ""
    
    # Quick container overview
    echo "Container Status:"
    docker ps --format "  {{.Names}}: {{.Status}}" | grep dgh_ | head -8
    echo ""
    
    echo "Press Ctrl+C to exit dashboard mode"
    echo "Run with --full for complete monitoring"
}

# Continuous monitoring mode
continuous_monitoring() {
    log_info "Starting continuous monitoring mode (press Ctrl+C to stop)..."
    
    while true; do
        show_dashboard
        sleep 10
    done
}

# Show help
show_help() {
    echo "DGH Feedback System Monitoring Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -f, --full          Run full monitoring check"
    echo "  -d, --dashboard     Show live dashboard"
    echo "  -c, --continuous    Continuous monitoring mode"
    echo "  -r, --report        Generate monitoring report"
    echo "  --containers        Check only container health"
    echo "  --apis              Check only API health"
    echo "  --databases         Check only database health"
    echo "  --performance       Check only API performance"
    echo ""
    echo "Examples:"
    echo "  $0                  Quick health check"
    echo "  $0 --full           Complete system monitoring"
    echo "  $0 --dashboard      Live dashboard view"
    echo "  $0 --continuous     Continuous monitoring"
}

# Main monitoring function
main() {
    local mode="quick"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--full)
                mode="full"
                shift
                ;;
            -d|--dashboard)
                mode="dashboard"
                shift
                ;;
            -c|--continuous)
                mode="continuous"
                shift
                ;;
            -r|--report)
                mode="report"
                shift
                ;;
            --containers)
                mode="containers"
                shift
                ;;
            --apis)
                mode="apis"
                shift
                ;;
            --databases)
                mode="databases"
                shift
                ;;
            --performance)
                mode="performance"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Execute based on mode
    case $mode in
        "quick")
            echo "🔍 DGH Feedback System - Quick Health Check"
            echo "============================================"
            echo ""
            check_container_health
            check_api_health
            ;;
        "full")
            echo "🔍 DGH Feedback System - Full Monitoring"
            echo "========================================"
            echo ""
            check_container_health
            check_api_health
            check_database_health
            check_system_resources
            check_api_performance
            check_recent_errors
            generate_statistics
            check_security
            ;;
        "dashboard")
            show_dashboard
            ;;
        "continuous")
            continuous_monitoring
            ;;
        "report")
            generate_report
            ;;
        "containers")
            check_container_health
            ;;
        "apis")
            check_api_health
            ;;
        "databases")
            check_database_health
            ;;
        "performance")
            check_api_performance
            ;;
    esac
    
    echo ""
    log_info "Monitoring completed at $(get_timestamp)"
}

# Handle interruption for continuous mode
trap 'echo ""; log_info "Monitoring stopped"; exit 0' INT TERM

# Run main function
main "$@"