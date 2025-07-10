#!/bin/bash
# Database Backup Script

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="chatbot_db"

mkdir -p $BACKUP_DIR

echo "🔄 Starting database backup..."
pg_dump -U chatbot_user -h localhost $DB_NAME > "$BACKUP_DIR/backup_$TIMESTAMP.sql"

if [ $? -eq 0 ]; then
    echo "✅ Backup completed: $BACKUP_DIR/backup_$TIMESTAMP.sql"
    
    # Keep only last 7 backups
    ls -t $BACKUP_DIR/backup_*.sql | tail -n +8 | xargs rm -f 2>/dev/null
else
    echo "❌ Backup failed"
    exit 1
fi
