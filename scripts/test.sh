#!/bin/bash

# DGH Feedback System - Test Script
# This script runs comprehensive tests on the system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Base URLs
API_GATEWAY_URL="http://localhost:8080"
FEEDBACK_API_URL="http://localhost:8080/api/v1"

# Test counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test helper function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_code="$3"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_info "Running: $test_name"
    
    if eval "$test_command" &> /dev/null; then
        local actual_code=$?
        if [ "$actual_code" -eq "${expected_code:-0}" ]; then
            log_success "$test_name"
        else
            log_failure "$test_name (expected code $expected_code, got $actual_code)"
        fi
    else
        log_failure "$test_name (command failed)"
    fi
}

# HTTP test helper
http_test() {
    local test_name="$1"
    local url="$2"
    local expected_code="$3"
    local method="${4:-GET}"
    local data="$5"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    log_info "HTTP Test: $test_name"
    
    local curl_cmd="curl -s -o /dev/null -w '%{http_code}'"
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        curl_cmd="$curl_cmd -X POST -H 'Content-Type: application/json' -d '$data'"
    fi
    
    curl_cmd="$curl_cmd '$url'"
    
    local actual_code=$(eval "$curl_cmd")
    
    if [ "$actual_code" -eq "$expected_code" ]; then
        log_success "$test_name (HTTP $actual_code)"
    else
        log_failure "$test_name (expected HTTP $expected_code, got $actual_code)"
    fi
}

# Authentication helper
get_auth_token() {
    local username="$1"
    local password="$2"
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
        "$API_GATEWAY_URL/auth/login")
    
    echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4
}

# Test Docker services are running
test_docker_services() {
    log_info "Testing Docker services..."
    
    local services=("dgh_postgres" "dgh_redis" "dgh_mongodb" "dgh_traefik" "dgh_api_gateway" "dgh_feedback_api")
    
    for service in "${services[@]}"; do
        run_test "Docker service $service is running" \
                 "docker ps --filter name=$service --filter status=running | grep -q $service"
    done
}

# Test database connectivity
test_database_connectivity() {
    log_info "Testing database connectivity..."
    
    # PostgreSQL
    run_test "PostgreSQL connection" \
             "docker-compose exec -T postgres pg_isready -U dgh_user -d dgh_feedback"
    
    # Redis
    run_test "Redis connection" \
             "docker-compose exec -T redis redis-cli ping | grep -q PONG"
    
    # MongoDB
    run_test "MongoDB connection" \
             "docker-compose exec -T mongodb mongosh --eval 'db.adminCommand(\"ping\")' | grep -q ok"
}

# Test API health endpoints
test_health_endpoints() {
    log_info "Testing health endpoints..."
    
    http_test "API Gateway health" "$API_GATEWAY_URL/health" 200
    http_test "Feedback API health" "$FEEDBACK_API_URL/../health" 200
    http_test "Feedback API detailed health" "$FEEDBACK_API_URL/../health/detailed" 200
    http_test "Feedback API readiness" "$FEEDBACK_API_URL/../health/ready" 200
    http_test "Feedback API liveness" "$FEEDBACK_API_URL/../health/live" 200
}

# Test authentication
test_authentication() {
    log_info "Testing authentication..."
    
    # Test login with valid credentials
    http_test "Login with admin credentials" \
             "$API_GATEWAY_URL/auth/login" 200 "POST" \
             '{"username":"admin","password":"admin123"}'
    
    http_test "Login with staff credentials" \
             "$API_GATEWAY_URL/auth/login" 200 "POST" \
             '{"username":"staff","password":"staff123"}'
    
    # Test login with invalid credentials
    http_test "Login with invalid credentials" \
             "$API_GATEWAY_URL/auth/login" 401 "POST" \
             '{"username":"invalid","password":"invalid"}'
    
    # Test token verification
    local token=$(get_auth_token "admin" "admin123")
    if [ -n "$token" ]; then
        local verify_response=$(curl -s -w '%{http_code}' -o /dev/null \
                               -H "Authorization: Bearer $token" \
                               "$API_GATEWAY_URL/auth/verify")
        
        if [ "$verify_response" -eq 200 ]; then
            log_success "Token verification"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            log_failure "Token verification (HTTP $verify_response)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
    else
        log_failure "Token generation for verification test"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        TESTS_TOTAL=$((TESTS_TOTAL + 1))
    fi
}

# Test API endpoints
test_api_endpoints() {
    log_info "Testing API endpoints..."
    
    # Get admin token for authenticated requests
    local token=$(get_auth_token "admin" "admin123")
    
    if [ -z "$token" ]; then
        log_failure "Could not get admin token for API tests"
        return
    fi
    
    # Test departments endpoint
    local dept_response=$(curl -s -w '%{http_code}' -o /dev/null \
                         -H "Authorization: Bearer $token" \
                         "$FEEDBACK_API_URL/departments")
    
    if [ "$dept_response" -eq 200 ]; then
        log_success "Departments API endpoint"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_failure "Departments API endpoint (HTTP $dept_response)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Test patients endpoint
    local patients_response=$(curl -s -w '%{http_code}' -o /dev/null \
                             -H "Authorization: Bearer $token" \
                             "$FEEDBACK_API_URL/patients")
    
    if [ "$patients_response" -eq 200 ]; then
        log_success "Patients API endpoint"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_failure "Patients API endpoint (HTTP $patients_response)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Test feedbacks endpoint
    local feedbacks_response=$(curl -s -w '%{http_code}' -o /dev/null \
                              -H "Authorization: Bearer $token" \
                              "$FEEDBACK_API_URL/feedbacks")
    
    if [ "$feedbacks_response" -eq 200 ]; then
        log_success "Feedbacks API endpoint"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_failure "Feedbacks API endpoint (HTTP $feedbacks_response)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Test feedback stats endpoint
    local stats_response=$(curl -s -w '%{http_code}' -o /dev/null \
                          -H "Authorization: Bearer $token" \
                          "$FEEDBACK_API_URL/feedbacks/stats")
    
    if [ "$stats_response" -eq 200 ]; then
        log_success "Feedback stats API endpoint"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_failure "Feedback stats API endpoint (HTTP $stats_response)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

# Test CRUD operations
test_crud_operations() {
    log_info "Testing CRUD operations..."
    
    local token=$(get_auth_token "admin" "admin123")
    
    if [ -z "$token" ]; then
        log_failure "Could not get admin token for CRUD tests"
        return
    fi
    
    # Test creating a new patient
    local patient_data='{
        "first_name": "Test",
        "last_name": "Patient",
        "phone": "+237123456789",
        "email": "test.patient@test.cm",
        "preferred_language": "fr",
        "department_id": 1
    }'
    
    local create_response=$(curl -s -w '%{http_code}' -o /tmp/patient_response.json \
                           -X POST \
                           -H "Authorization: Bearer $token" \
                           -H "Content-Type: application/json" \
                           -d "$patient_data" \
                           "$FEEDBACK_API_URL/patients")
    
    if [ "$create_response" -eq 201 ]; then
        log_success "Patient creation"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        
        # Extract patient ID for further tests
        local patient_id=$(grep -o '"id":[0-9]*' /tmp/patient_response.json | cut -d':' -f2)
        
        if [ -n "$patient_id" ]; then
            # Test reading the created patient
            local read_response=$(curl -s -w '%{http_code}' -o /dev/null \
                                 -H "Authorization: Bearer $token" \
                                 "$FEEDBACK_API_URL/patients/$patient_id")
            
            if [ "$read_response" -eq 200 ]; then
                log_success "Patient read"
                TESTS_PASSED=$((TESTS_PASSED + 1))
            else
                log_failure "Patient read (HTTP $read_response)"
                TESTS_FAILED=$((TESTS_FAILED + 1))
            fi
            TESTS_TOTAL=$((TESTS_TOTAL + 1))
            
            # Test updating the patient
            local update_data='{"phone": "+237987654321"}'
            local update_response=$(curl -s -w '%{http_code}' -o /dev/null \
                                   -X PUT \
                                   -H "Authorization: Bearer $token" \
                                   -H "Content-Type: application/json" \
                                   -d "$update_data" \
                                   "$FEEDBACK_API_URL/patients/$patient_id")
            
            if [ "$update_response" -eq 200 ]; then
                log_success "Patient update"
                TESTS_PASSED=$((TESTS_PASSED + 1))
            else
                log_failure "Patient update (HTTP $update_response)"
                TESTS_FAILED=$((TESTS_FAILED + 1))
            fi
            TESTS_TOTAL=$((TESTS_TOTAL + 1))
            
            # Test deleting the patient
            local delete_response=$(curl -s -w '%{http_code}' -o /dev/null \
                                   -X DELETE \
                                   -H "Authorization: Bearer $token" \
                                   "$FEEDBACK_API_URL/patients/$patient_id")
            
            if [ "$delete_response" -eq 204 ]; then
                log_success "Patient deletion"
                TESTS_PASSED=$((TESTS_PASSED + 1))
            else
                log_failure "Patient deletion (HTTP $delete_response)"
                TESTS_FAILED=$((TESTS_FAILED + 1))
            fi
            TESTS_TOTAL=$((TESTS_TOTAL + 1))
        fi
    else
        log_failure "Patient creation (HTTP $create_response)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Clean up temp file
    rm -f /tmp/patient_response.json
}

# Test performance
test_performance() {
    log_info "Testing performance..."
    
    local token=$(get_auth_token "admin" "admin123")
    
    if [ -z "$token" ]; then
        log_failure "Could not get admin token for performance tests"
        return
    fi
    
    # Test response time for departments endpoint
    local start_time=$(date +%s%N)
    local response=$(curl -s -w '%{http_code}' -o /dev/null \
                    -H "Authorization: Bearer $token" \
                    "$FEEDBACK_API_URL/departments")
    local end_time=$(date +%s%N)
    
    local duration_ms=$(( (end_time - start_time) / 1000000 ))
    
    if [ "$response" -eq 200 ] && [ "$duration_ms" -lt 1000 ]; then
        log_success "Response time test (${duration_ms}ms < 1000ms)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log_failure "Response time test (${duration_ms}ms >= 1000ms or HTTP $response)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

# Generate test report
generate_report() {
    echo ""
    echo "=================================================="
    echo "🧪 Test Results Summary"
    echo "=================================================="
    echo "Total Tests: $TESTS_TOTAL"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "Status: ${GREEN}ALL TESTS PASSED${NC} ✅"
        return 0
    else
        echo -e "Status: ${RED}SOME TESTS FAILED${NC} ❌"
        return 1
    fi
}

# Main test function
main() {
    echo "=================================================="
    echo "🧪 DGH Feedback System - Test Suite"
    echo "=================================================="
    echo ""
    
    # Wait for services to be ready
    sleep 5
    
    test_docker_services
    test_database_connectivity
    test_health_endpoints
    test_authentication
    test_api_endpoints
    test_crud_operations
    test_performance
    
    generate_report
}

# Run main function
main "$@"