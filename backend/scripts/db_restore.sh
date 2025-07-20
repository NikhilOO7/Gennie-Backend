#!/bin/bash
# Database Restore Script

if [ -z "$1" ]; then
    echo "Usage: ./db_restore.sh <backup_file>"
    exit 1
fi

BACKUP_FILE=$1
DB_NAME="chatbot_db"

echo "⚠️  WARNING: This will restore the database from $BACKUP_FILE"
echo "All current data will be lost. Continue? (y/N)"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "🔄 Restoring database..."
    psql -U chatbot_user -h localhost $DB_NAME < "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ Database restored successfully"
    else
        echo "❌ Restore failed"
        exit 1
    fi
else
    echo "Restore cancelled"
fi
