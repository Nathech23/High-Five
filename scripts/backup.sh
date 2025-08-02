#!/bin/bash

# DGH Feedback System - Backup Script
# This script creates backups of databases and important data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

# Database configurations
POSTGRES_CONTAINER="dgh_postgres"
POSTGRES_DB="dgh_feedback"
POSTGRES_USER="dgh_user"

MONGODB_CONTAINER="dgh_mongodb"
MONGODB_DB="dgh_nlp"

REDIS_CONTAINER="dgh_redis"

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

# Create backup directory
create_backup_dir() {
    local backup_path="$BACKUP_DIR/$TIMESTAMP"
    
    if [ ! -d "$backup_path" ]; then
        mkdir -p "$backup_path"
        log_success "Created backup directory: $backup_path"
    fi
    
    echo "$backup_path"
}

# Check if containers are running
check_containers() {
    log_info "Checking if containers are running..."
    
    local containers=("$POSTGRES_CONTAINER" "$MONGODB_CONTAINER" "$REDIS_CONTAINER")
    
    for container in "${containers[@]}"; do
        if ! docker ps --filter name="$container" --filter status=running | grep -q "$container"; then
            log_error "Container $container is not running"
            exit 1
        fi
    done
    
    log_success "All required containers are running"
}

# Backup PostgreSQL database
backup_postgresql() {
    local backup_path="$1"
    local backup_file="$backup_path/postgresql_${TIMESTAMP}.sql"
    
    log_info "Backing up PostgreSQL database..."
    
    # Create SQL dump
    if docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$backup_file"; then
        log_success "PostgreSQL backup created: $backup_file"
        
        # Compress the backup
        gzip "$backup_file"
        log_success "PostgreSQL backup compressed: ${backup_file}.gz"
        
        # Get backup size
        local backup_size=$(du -h "${backup_file}.gz" | cut -f1)
        log_info "PostgreSQL backup size: $backup_size"
        
        return 0
    else
        log_error "Failed to create PostgreSQL backup"
        return 1
    fi
}

# Backup MongoDB database
backup_mongodb() {
    local backup_path="$1"
    local backup_dir="$backup_path/mongodb_${TIMESTAMP}"
    
    log_info "Backing up MongoDB database..."
    
    # Create MongoDB dump
    if docker exec "$MONGODB_CONTAINER" mongodump --db "$MONGODB_DB" --out "/tmp/mongo_backup_${TIMESTAMP}"; then
        # Copy from container to host
        docker cp "$MONGODB_CONTAINER:/tmp/mongo_backup_${TIMESTAMP}" "$backup_dir"
        
        # Clean up container backup
        docker exec "$MONGODB_CONTAINER" rm -rf "/tmp/mongo_backup_${TIMESTAMP}"
        
        # Compress the backup
        tar -czf "${backup_dir}.tar.gz" -C "$backup_path" "mongodb_${TIMESTAMP}"
        rm -rf "$backup_dir"
        
        log_success "MongoDB backup created and compressed: ${backup_dir}.tar.gz"
        
        # Get backup size
        local backup_size=$(du -h "${backup_dir}.tar.gz" | cut -f1)
        log_info "MongoDB backup size: $backup_size"
        
        return 0
    else
        log_error "Failed to create MongoDB backup"
        return 1
    fi
}

# Backup Redis data
backup_redis() {
    local backup_path="$1"
    local backup_file="$backup_path/redis_${TIMESTAMP}.rdb"
    
    log_info "Backing up Redis data..."
    
    # Force Redis to save current data
    if docker exec "$REDIS_CONTAINER" redis-cli BGSAVE; then
        # Wait for background save to complete
        sleep 5
        
        # Copy RDB file from container
        if docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$backup_file"; then
            # Compress the backup
            gzip "$backup_file"
            
            log_success "Redis backup created and compressed: ${backup_file}.gz"
            
            # Get backup size
            local backup_size=$(du -h "${backup_file}.gz" | cut -f1)
            log_info "Redis backup size: $backup_size"
            
            return 0
        else
            log_error "Failed to copy Redis RDB file"
            return 1
        fi
    else
        log_error "Failed to create Redis backup"
        return 1
    fi
}

# Backup application configuration
backup_configuration() {
    local backup_path="$1"
    local config_backup="$backup_path/configuration_${TIMESTAMP}.tar.gz"
    
    log_info "Backing up application configuration..."
    
    # Files and directories to backup
    local config_items=(
        ".env"
        "docker-compose.yml"
        "traefik/traefik.yml"
        "traefik/dynamic.yml"
        "monitoring/prometheus.yml"
    )
    
    # Create temporary directory for config files
    local temp_dir="/tmp/dgh_config_backup_${TIMESTAMP}"
    mkdir -p "$temp_dir"
    
    # Copy configuration files
    for item in "${config_items[@]}"; do
        if [ -f "$item" ]; then
            cp "$item" "$temp_dir/"
        elif [ -d "$item" ]; then
            cp -r "$item" "$temp_dir/"
        else
            log_warning "Configuration item not found: $item"
        fi
    done
    
    # Create tar archive
    tar -czf "$config_backup" -C "$temp_dir" .
    
    # Clean up temporary directory
    rm -rf "$temp_dir"
    
    log_success "Configuration backup created: $config_backup"
    
    # Get backup size
    local backup_size=$(du -h "$config_backup" | cut -f1)
    log_info "Configuration backup size: $backup_size"
}

# Create backup manifest
create_manifest() {
    local backup_path="$1"
    local manifest_file="$backup_path/backup_manifest.txt"
    
    log_info "Creating backup manifest..."
    
    cat > "$manifest_file" << EOF
DGH Feedback System Backup Manifest
===================================

Backup Date: $(date)
Backup Directory: $backup_path
System Info: $(uname -a)

Backup Contents:
EOF
    
    # List all files in backup directory with sizes
    find "$backup_path" -type f -exec ls -lh {} \; | awk '{print $9 " (" $5 ")"}' >> "$manifest_file"
    
    # Add container versions
    echo "" >> "$manifest_file"
    echo "Container Versions:" >> "$manifest_file"
    docker-compose ps --services | xargs -I {} docker-compose ps {} >> "$manifest_file"
    
    # Add database statistics
    echo "" >> "$manifest_file"
    echo "Database Statistics:" >> "$manifest_file"
    
    # PostgreSQL stats
    local pg_stats=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
        SELECT 
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes
        FROM pg_stat_user_tables;
    " 2>/dev/null || echo "Could not retrieve PostgreSQL stats")
    
    echo "PostgreSQL:" >> "$manifest_file"
    echo "$pg_stats" >> "$manifest_file"
    
    log_success "Backup manifest created: $manifest_file"
}

# Clean old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups (older than $RETENTION_DAYS days)..."
    
    local deleted_count=0
    
    # Find and delete old backup directories
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -type d -name "*_*" -mtime +$RETENTION_DAYS | while read -r old_backup; do
            if [ -d "$old_backup" ]; then
                rm -rf "$old_backup"
                log_info "Deleted old backup: $old_backup"
                deleted_count=$((deleted_count + 1))
            fi
        done
    fi
    
    log_success "Cleanup completed. Deleted $deleted_count old backups"
}

# Verify backup integrity
verify_backup() {
    local backup_path="$1"
    
    log_info "Verifying backup integrity..."
    
    local verification_failed=0
    
    # Check if all expected files exist
    local expected_files=(
        "postgresql_${TIMESTAMP}.sql.gz"
        "mongodb_${TIMESTAMP}.tar.gz"
        "redis_${TIMESTAMP}.rdb.gz"
        "configuration_${TIMESTAMP}.tar.gz"
        "backup_manifest.txt"
    )
    
    for file in "${expected_files[@]}"; do
        if [ ! -f "$backup_path/$file" ]; then
            log_error "Missing backup file: $file"
            verification_failed=1
        fi
    done
    
    # Test compressed files
    for compressed_file in "$backup_path"/*.gz; do
        if [ -f "$compressed_file" ]; then
            if ! gzip -t "$compressed_file" 2>/dev/null; then
                log_error "Corrupted backup file: $compressed_file"
                verification_failed=1
            fi
        fi
    done
    
    # Test tar files
    for tar_file in "$backup_path"/*.tar.gz; do
        if [ -f "$tar_file" ]; then
            if ! tar -tzf "$tar_file" >/dev/null 2>&1; then
                log_error "Corrupted tar file: $tar_file"
                verification_failed=1
            fi
        fi
    done
    
    if [ $verification_failed -eq 0 ]; then
        log_success "Backup verification completed successfully"
        return 0
    else
        log_error "Backup verification failed"
        return 1
    fi
}

# Calculate total backup size
calculate_backup_size() {
    local backup_path="$1"
    
    local total_size=$(du -sh "$backup_path" | cut -f1)
    log_info "Total backup size: $total_size"
}

# Send backup notification (placeholder for future implementation)
send_notification() {
    local backup_path="$1"
    local status="$2"
    
    # This is a placeholder for email/SMS notification
    # In a real implementation, you would integrate with your notification system
    
    if [ "$status" = "success" ]; then
        log_info "Backup completed successfully. Notification would be sent here."
    else
        log_error "Backup failed. Error notification would be sent here."
    fi
}

# Main backup function
main() {
    echo "=================================================="
    echo "💾 DGH Feedback System - Backup Script"
    echo "=================================================="
    echo ""
    
    log_info "Starting backup process..."
    
    # Check prerequisites
    check_containers
    
    # Create backup directory
    local backup_path=$(create_backup_dir)
    
    # Perform backups
    local backup_success=1
    
    if ! backup_postgresql "$backup_path"; then
        backup_success=0
    fi
    
    if ! backup_mongodb "$backup_path"; then
        backup_success=0
    fi
    
    if ! backup_redis "$backup_path"; then
        backup_success=0
    fi
    
    backup_configuration "$backup_path"
    create_manifest "$backup_path"
    
    # Verify backup
    if ! verify_backup "$backup_path"; then
        backup_success=0
    fi
    
    # Calculate sizes
    calculate_backup_size "$backup_path"
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Final status
    echo ""
    if [ $backup_success -eq 1 ]; then
        log_success "Backup process completed successfully!"
        log_info "Backup location: $backup_path"
        send_notification "$backup_path" "success"
        exit 0
    else
        log_error "Backup process completed with errors!"
        send_notification "$backup_path" "failure"
        exit 1
    fi
}

# Show help
show_help() {
    echo "DGH Feedback System Backup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -r, --retention N   Set retention days (default: 30)"
    echo ""
    echo "This script creates backups of:"
    echo "  - PostgreSQL database"
    echo "  - MongoDB database"
    echo "  - Redis data"
    echo "  - Application configuration"
    echo ""
    echo "Backups are stored in: $BACKUP_DIR"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -r|--retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main "$@"