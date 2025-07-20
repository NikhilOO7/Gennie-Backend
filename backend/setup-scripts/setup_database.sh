#!/bin/bash

# Database Setup Script for Gennie Backend
# This script installs and configures PostgreSQL and Redis on macOS

set -e  # Exit on error

echo "🚀 Starting Database Setup for Gennie Backend..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DB_NAME="chatbot_db"
DB_USER="chatbot_user"
DB_PASSWORD="GmwemWrdiJGdtLz697sFAJsvl"
REDIS_PORT=6379
POSTGRES_PORT=5432

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

echo -e "${YELLOW}📦 Step 1: Installing Homebrew (if needed)...${NC}"
if ! command_exists brew; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo -e "${GREEN}✓ Homebrew already installed${NC}"
fi

echo -e "\n${YELLOW}📦 Step 2: Installing PostgreSQL...${NC}"
if ! command_exists psql; then
    brew install postgresql@14
    echo 'export PATH="/usr/local/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
    export PATH="/usr/local/opt/postgresql@14/bin:$PATH"
else
    echo -e "${GREEN}✓ PostgreSQL already installed${NC}"
fi

# Start PostgreSQL service
echo -e "${YELLOW}Starting PostgreSQL service...${NC}"
brew services stop postgresql@14 2>/dev/null || true
brew services start postgresql@14

# For M1/M2 Macs, the path might be different
if [[ $(uname -m) == 'arm64' ]]; then
    export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
fi

echo -e "\n${YELLOW}📦 Step 3: Installing Redis...${NC}"
if ! command_exists redis-cli; then
    brew install redis
    brew services start redis
else
    echo -e "${GREEN}✓ Redis already installed${NC}"
    # Ensure Redis is running
    brew services start redis 2>/dev/null || true
fi

# Wait for services to start
echo -e "\n${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 5

# Check if PostgreSQL is running
echo -e "${YELLOW}Checking PostgreSQL status...${NC}"
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "${RED}PostgreSQL is not running. Attempting to start manually...${NC}"
    
    # Try to initialize the database if needed
    if [[ $(uname -m) == 'arm64' ]]; then
        POSTGRES_DIR="/opt/homebrew/var/postgresql@14"
    else
        POSTGRES_DIR="/usr/local/var/postgresql@14"
    fi
    
    if [ ! -d "$POSTGRES_DIR" ]; then
        echo -e "${YELLOW}Initializing PostgreSQL database...${NC}"
        initdb -D "$POSTGRES_DIR" -E UTF8
    fi
    
    # Try starting PostgreSQL manually
    brew services restart postgresql@14
    sleep 5
    
    # Check again
    if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo -e "${RED}Failed to start PostgreSQL. Please check the logs:${NC}"
        echo -e "${YELLOW}brew services list${NC}"
        echo -e "${YELLOW}tail -f $POSTGRES_DIR/server.log${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ PostgreSQL is running${NC}"

echo -e "\n${YELLOW}🔧 Step 4: Setting up PostgreSQL database...${NC}"

# Generate secure password if using default
if [ "$DB_PASSWORD" = "your_secure_password_here" ]; then
    DB_PASSWORD=$(generate_password)
    echo -e "${YELLOW}Generated secure password: ${GREEN}$DB_PASSWORD${NC}"
fi

# Create database and user
psql postgres <<EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    ELSE
        ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to the database and set up extensions
\c $DB_NAME
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF

echo -e "${GREEN}✓ PostgreSQL database setup complete${NC}"

echo -e "\n${YELLOW}🔧 Step 5: Testing Redis connection...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running and responding${NC}"
else
    echo -e "${RED}✗ Redis connection failed${NC}"
    exit 1
fi

echo -e "\n${YELLOW}📊 Step 6: Creating database management scripts...${NC}"

# Create scripts directory
mkdir -p ../scripts

# Create db_backup.sh
cat > ../scripts/db_backup.sh <<'EOF'
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
EOF

chmod +x ../scripts/db_backup.sh

# Create db_restore.sh
cat > ../scripts/db_restore.sh <<'EOF'
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
EOF

chmod +x ../scripts/db_restore.sh

# Create service status script
cat > ../scripts/check_services.sh <<'EOF'
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
EOF

chmod +x ../scripts/check_services.sh

echo -e "\n${GREEN}🎉 Database setup complete!${NC}"
echo -e "\n${YELLOW}📋 Summary:${NC}"
echo -e "  PostgreSQL Database: ${GREEN}$DB_NAME${NC}"
echo -e "  PostgreSQL User: ${GREEN}$DB_USER${NC}"
echo -e "  PostgreSQL Password: ${GREEN}$DB_PASSWORD${NC}"
echo -e "  PostgreSQL Port: ${GREEN}$POSTGRES_PORT${NC}"
echo -e "  Redis Port: ${GREEN}$REDIS_PORT${NC}"
echo -e "\n${YELLOW}📁 Created files:${NC}"
echo -e "  - ${GREEN}../.env${NC} (configuration file in project root)"
echo -e "  - ${GREEN}../scripts/db_backup.sh${NC} (backup script)"
echo -e "  - ${GREEN}../scripts/db_restore.sh${NC} (restore script)"
echo -e "  - ${GREEN}../scripts/check_services.sh${NC} (status check script)"
echo -e "\n${YELLOW}🚀 Next steps:${NC}"
echo -e "  1. Update ${GREEN}GEMINI_API_KEY${NC} in ../.env file"
echo -e "  2. Go to project root: ${GREEN}cd ..${NC}"
echo -e "  3. Run ${GREEN}alembic upgrade head${NC} to create database tables"
echo -e "  4. Start your application with ${GREEN}uvicorn app.main:app --reload${NC}"
echo -e "\n${YELLOW}💡 Useful commands:${NC}"
echo -e "  - Check services: ${GREEN}../scripts/check_services.sh${NC}"
echo -e "  - Backup database: ${GREEN}../scripts/db_backup.sh${NC}"
echo -e "  - Restore database: ${GREEN}../scripts/db_restore.sh <backup_file>${NC}"
echo -e "  - Stop services: ${GREEN}brew services stop postgresql@14 redis${NC}"
echo -e "  - Start services: ${GREEN}brew services start postgresql@14 redis${NC}"