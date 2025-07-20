#!/bin/bash
# Check Database Services Status

echo "🔍 Checking service status..."
echo ""

# Check PostgreSQL
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "✅ PostgreSQL: Running"
    psql -U chatbot_user -d chatbot_db -c "SELECT version();" | head -n 3
else
    echo "❌ PostgreSQL: Not running"
fi

echo ""

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Running"
    redis-cli INFO server | grep redis_version
else
    echo "❌ Redis: Not running"
fi

echo ""
echo "📊 Database sizes:"
psql -U chatbot_user -d chatbot_db -c "SELECT pg_database_size('chatbot_db') as size;" 2>/dev/null || echo "Cannot get PostgreSQL size"
redis-cli INFO memory | grep used_memory_human 2>/dev/null || echo "Cannot get Redis memory usage"
