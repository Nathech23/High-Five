#!/bin/bash

# DGH Feedback System - Data Population Script
# This script populates the system with additional test data

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

# Get authentication token
get_auth_token() {
    log_info "Getting authentication token..."
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' \
        "$API_GATEWAY_URL/auth/login")
    
    local token=$(echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$token" ]; then
        log_success "Authentication token obtained"
        echo "$token"
    else
        log_error "Failed to get authentication token"
        exit 1
    fi
}

# Check if API is ready
check_api_ready() {
    log_info "Checking if API is ready..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$FEEDBACK_API_URL/../health" | grep -q "healthy"; then
            log_success "API is ready"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_info "Waiting for API... (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    log_error "API failed to become ready after $max_attempts attempts"
    exit 1
}

# Create additional patients
create_additional_patients() {
    local token="$1"
    
    log_info "Creating additional patients..."
    
    local patients=(
        '{"first_name":"Amina","last_name":"Sow","phone":"+237670111222","email":"amina.sow@email.cm","preferred_language":"fr","department_id":1}'
        '{"first_name":"David","last_name":"Kamga","phone":"+237680333444","email":"david.kamga@email.cm","preferred_language":"en","department_id":2}'
        '{"first_name":"Fatou","last_name":"Diallo","phone":"+237690555666","email":"fatou.diallo@email.cm","preferred_language":"douala","department_id":3}'
        '{"first_name":"Ibrahim","last_name":"Moussa","phone":"+237650777888","email":"ibrahim.moussa@email.cm","preferred_language":"fr","department_id":4}'
        '{"first_name":"Aissatou","last_name":"Ba","phone":"+237675999000","email":"aissatou.ba@email.cm","preferred_language":"bassa","department_id":5}'
        '{"first_name":"Emmanuel","last_name":"Ngono","phone":"+237685111222","email":"emmanuel.ngono@email.cm","preferred_language":"ewondo","department_id":1}'
        '{"first_name":"Raissa","last_name":"Talla","phone":"+237695333444","email":"raissa.talla@email.cm","preferred_language":"fr","department_id":2}'
        '{"first_name":"Yves","last_name":"Onana","phone":"+237655555666","email":"yves.onana@email.cm","preferred_language":"en","department_id":3}'
        '{"first_name":"Marthe","last_name":"Ngo","phone":"+237676777888","email":"marthe.ngo@email.cm","preferred_language":"fr","department_id":4}'
        '{"first_name":"Patrice","last_name":"Essama","phone":"+237687999000","email":"patrice.essama@email.cm","preferred_language":"douala","department_id":5}'
    )
    
    local created_count=0
    
    for patient_data in "${patients[@]}"; do
        local response=$(curl -s -w '%{http_code}' -o /tmp/patient_create.json \
                        -X POST \
                        -H "Authorization: Bearer $token" \
                        -H "Content-Type: application/json" \
                        -d "$patient_data" \
                        "$FEEDBACK_API_URL/patients")
        
        if [ "$response" -eq 201 ]; then
            created_count=$((created_count + 1))
        else
            log_warning "Failed to create patient (HTTP $response)"
        fi
    done
    
    log_success "Created $created_count additional patients"
    rm -f /tmp/patient_create.json
}

# Create additional feedbacks
create_additional_feedbacks() {
    local token="$1"
    
    log_info "Creating additional feedbacks..."
    
    # Get existing patients to create feedbacks for them
    local patients_response=$(curl -s \
                             -H "Authorization: Bearer $token" \
                             "$FEEDBACK_API_URL/patients?limit=50")
    
    # Extract patient IDs (simplified JSON parsing)
    local patient_ids=($(echo "$patients_response" | grep -o '"id":[0-9]*' | cut -d':' -f2 | head -20))
    
    if [ ${#patient_ids[@]} -eq 0 ]; then
        log_warning "No patients found, cannot create feedbacks"
        return
    fi
    
    local feedbacks=(
        '{"patient_id":ID_PLACEHOLDER,"department_id":1,"rating":4.5,"feedback_text":"Service excellent aux urgences. Personnel très professionnel.","language":"fr","wait_time_min":20,"resolution_time_min":30}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":2,"rating":5.0,"feedback_text":"Outstanding cardiac care. The medical team was exceptional.","language":"en","wait_time_min":15,"resolution_time_min":60}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":3,"rating":3.5,"feedback_text":"Service na pédiatrie na nye te bon, kasi ba nye te na retard petit.","language":"douala","wait_time_min":45,"resolution_time_min":40}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":4,"rating":4.0,"feedback_text":"Consultation satisfaisante en médecine générale. Médecin compétent.","language":"fr","wait_time_min":30,"resolution_time_min":25}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":5,"rating":2.5,"feedback_text":"Hihi surgery na nye te ma bon te, kasi ba nye te na problème na organisation.","language":"bassa","wait_time_min":90,"resolution_time_min":20}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":1,"rating":1.5,"feedback_text":"Service catastrophique! Temps d'\''attente inacceptable et personnel impoli.","language":"fr","wait_time_min":180,"resolution_time_min":10}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":2,"rating":4.8,"feedback_text":"Minga salongo te na cardiologie. Ba nye te ba professionnels mingi.","language":"ewondo","wait_time_min":25,"resolution_time_min":75}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":3,"rating":4.2,"feedback_text":"Great pediatric care. My child felt comfortable with the staff.","language":"en","wait_time_min":35,"resolution_time_min":45}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":4,"rating":3.8,"feedback_text":"Bon diagnostic mais l'\''attente était un peu longue.","language":"fr","wait_time_min":55,"resolution_time_min":35}'
        '{"patient_id":ID_PLACEHOLDER,"department_id":5,"rating":4.6,"feedback_text":"Intervention chirurgicale réussie. Équipe très compétente.","language":"fr","wait_time_min":40,"resolution_time_min":120}'
    )
    
    local created_count=0
    local patient_index=0
    
    for feedback_template in "${feedbacks[@]}"; do
        # Use modulo to cycle through available patients
        local patient_id=${patient_ids[$((patient_index % ${#patient_ids[@]}))]}
        patient_index=$((patient_index + 1))
        
        # Replace placeholder with actual patient ID
        local feedback_data=${feedback_template//ID_PLACEHOLDER/$patient_id}
        
        local response=$(curl -s -w '%{http_code}' -o /tmp/feedback_create.json \
                        -X POST \
                        -H "Authorization: Bearer $token" \
                        -H "Content-Type: application/json" \
                        -d "$feedback_data" \
                        "$FEEDBACK_API_URL/feedbacks")
        
        if [ "$response" -eq 201 ]; then
            created_count=$((created_count + 1))
        else
            log_warning "Failed to create feedback (HTTP $response)"
        fi
    done
    
    log_success "Created $created_count additional feedbacks"
    rm -f /tmp/feedback_create.json
}

# Create contact preferences
create_contact_preferences() {
    local token="$1"
    
    log_info "Creating contact preferences..."
    
    # This would typically be done through the API, but since we don't have
    # the contact preferences endpoint yet, we'll do it directly in the database
    
    local sql_commands="
    INSERT INTO contact_preferences (patient_id, preferred_method, preferred_time_start, preferred_time_end, preferred_language, is_active, created_at) 
    SELECT 
        p.id,
        CASE 
            WHEN p.id % 4 = 0 THEN 'sms'
            WHEN p.id % 4 = 1 THEN 'call'
            WHEN p.id % 4 = 2 THEN 'email'
            ELSE 'whatsapp'
        END,
        CASE 
            WHEN p.id % 3 = 0 THEN '08:00'
            WHEN p.id % 3 = 1 THEN '09:00'
            ELSE '10:00'
        END,
        CASE 
            WHEN p.id % 3 = 0 THEN '17:00'
            WHEN p.id % 3 = 1 THEN '18:00'
            ELSE '19:00'
        END,
        p.preferred_language,
        true,
        NOW()
    FROM patients p
    WHERE NOT EXISTS (
        SELECT 1 FROM contact_preferences cp WHERE cp.patient_id = p.id
    );
    "
    
    # Execute SQL commands
    if docker-compose exec -T postgres psql -U dgh_user -d dgh_feedback -c "$sql_commands" &> /dev/null; then
        log_success "Created contact preferences for patients"
    else
        log_warning "Failed to create contact preferences"
    fi
}

# Simulate some urgent feedbacks
mark_urgent_feedbacks() {
    local token="$1"
    
    log_info "Marking some feedbacks as urgent..."
    
    # Get feedbacks with low ratings
    local feedbacks_response=$(curl -s \
                              -H "Authorization: Bearer $token" \
                              "$FEEDBACK_API_URL/feedbacks?max_rating=2.5&limit=10")
    
    # Extract feedback IDs
    local feedback_ids=($(echo "$feedbacks_response" | grep -o '"id":[0-9]*' | cut -d':' -f2))
    
    local marked_count=0
    
    for feedback_id in "${feedback_ids[@]}"; do
        local response=$(curl -s -w '%{http_code}' -o /dev/null \
                        -X POST \
                        -H "Authorization: Bearer $token" \
                        "$FEEDBACK_API_URL/feedbacks/$feedback_id/mark-urgent")
        
        if [ "$response" -eq 200 ]; then
            marked_count=$((marked_count + 1))
        fi
    done
    
    log_success "Marked $marked_count feedbacks as urgent"
}

# Generate sample reminder data
create_sample_reminders() {
    log_info "Creating sample reminders..."
    
    local sql_commands="
    INSERT INTO reminders (patient_id, reminder_type_id, scheduled_date, message_content, delivery_method, status, created_at)
    SELECT 
        p.id,
        rt.id,
        NOW() + INTERVAL '1 day' + (p.id % 7) * INTERVAL '1 day',
        CASE rt.name
            WHEN 'appointment_reminder' THEN REPLACE(REPLACE(rt.template_fr, '{patient_name}', p.first_name || ' ' || p.last_name), '{date}', TO_CHAR(NOW() + INTERVAL '2 days', 'DD/MM/YYYY'))
            WHEN 'medication_reminder' THEN REPLACE(REPLACE(rt.template_fr, '{patient_name}', p.first_name || ' ' || p.last_name), '{medication}', 'Paracétamol')
            ELSE REPLACE(rt.template_fr, '{patient_name}', p.first_name || ' ' || p.last_name)
        END,
        CASE 
            WHEN p.id % 3 = 0 THEN 'sms'
            WHEN p.id % 3 = 1 THEN 'call'
            ELSE 'email'
        END,
        'scheduled',
        NOW()
    FROM patients p
    CROSS JOIN reminder_types rt
    WHERE p.id <= 10 AND rt.is_active = true
    LIMIT 30;
    "
    
    if docker-compose exec -T postgres psql -U dgh_user -d dgh_feedback -c "$sql_commands" &> /dev/null; then
        log_success "Created sample reminders"
    else
        log_warning "Failed to create sample reminders"
    fi
}

# Display statistics
show_statistics() {
    local token="$1"
    
    log_info "System Statistics:"
    
    # Get departments count
    local dept_response=$(curl -s -H "Authorization: Bearer $token" "$FEEDBACK_API_URL/departments")
    local dept_count=$(echo "$dept_response" | grep -o '"id":[0-9]*' | wc -l)
    echo "  📋 Departments: $dept_count"
    
    # Get patients count
    local patients_response=$(curl -s -H "Authorization: Bearer $token" "$FEEDBACK_API_URL/patients?limit=1000")
    local patients_count=$(echo "$patients_response" | grep -o '"id":[0-9]*' | wc -l)
    echo "  👥 Patients: $patients_count"
    
    # Get feedbacks count
    local feedbacks_response=$(curl -s -H "Authorization: Bearer $token" "$FEEDBACK_API_URL/feedbacks?limit=1000")
    local feedbacks_count=$(echo "$feedbacks_response" | grep -o '"id":[0-9]*' | wc -l)
    echo "  💬 Feedbacks: $feedbacks_count"
    
    # Get urgent feedbacks count
    local urgent_response=$(curl -s -H "Authorization: Bearer $token" "$FEEDBACK_API_URL/feedbacks/urgent")
    local urgent_count=$(echo "$urgent_response" | grep -o '"id":[0-9]*' | wc -l)
    echo "  🚨 Urgent Feedbacks: $urgent_count"
    
    # Get stats
    local stats_response=$(curl -s -H "Authorization: Bearer $token" "$FEEDBACK_API_URL/feedbacks/stats")
    if echo "$stats_response" | grep -q "avg_rating"; then
        local avg_rating=$(echo "$stats_response" | grep -o '"avg_rating":[0-9.]*' | cut -d':' -f2)
        echo "  ⭐ Average Rating: $avg_rating"
    fi
}

# Main function
main() {
    echo "=================================================="
    echo "📊 DGH Feedback System - Data Population"
    echo "=================================================="
    echo ""
    
    check_api_ready
    
    local token=$(get_auth_token)
    
    create_additional_patients "$token"
    create_additional_feedbacks "$token"
    create_contact_preferences "$token"
    mark_urgent_feedbacks "$token"
    create_sample_reminders
    
    echo ""
    show_statistics "$token"
    echo ""
    
    log_success "Data population completed successfully!"
}

# Run main function
main "$@"