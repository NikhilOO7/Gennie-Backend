#!/bin/bash

# Remove Obsolete Setup Files Script
# This removes all the temporary setup files that are no longer needed

echo "🧹 Removing obsolete setup and debugging files..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# List of obsolete files to remove
OBSOLETE_FILES=(
    "fix_database.py"
    "fix_db.py" 
    "get-pip.py"
    "init-database.sh"
    "init-db.sql"
    "setup_database.sh"
    "setup.py"
)

# Directories to remove completely
OBSOLETE_DIRS=(
    "setup/"
    "setup"
)

echo "🗑️  Removing obsolete setup files..."
for file in "${OBSOLETE_FILES[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        print_status "Removed $file"
    elif [ -L "$file" ]; then
        rm "$file"
        print_status "Removed symlink $file"
    fi
done

echo "🗑️  Removing obsolete directories..."
for dir in "${OBSOLETE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        print_status "Removed directory $dir"
    fi
done

# Also remove any other common temporary files
echo "🗑️  Removing additional temporary files..."
TEMP_PATTERNS=(
    "*.tmp"
    "*.temp" 
    "*~"
    "*.bak"
    "*.backup"
    "*.orig"
    "test_*.py"
    "debug_*.py"
    "fix_*.py"
    "setup_*.py"
    "init_*.py"
)

for pattern in "${TEMP_PATTERNS[@]}"; do
    if ls $pattern 1> /dev/null 2>&1; then
        rm $pattern
        print_status "Removed $pattern files"
    fi
done

echo "🗑️  Cleaning any remaining setup artifacts..."
# Remove any files that might be leftover from setup processes
find . -maxdepth 1 -name "*setup*" -type f -delete 2>/dev/null || true
find . -maxdepth 1 -name "*init*" -type f -delete 2>/dev/null || true
find . -maxdepth 1 -name "*fix*" -type f -delete 2>/dev/null || true

print_status "Cleanup completed!"

echo ""
echo "📋 Summary of removed files:"
echo "================================"
echo "✅ Database setup scripts (replaced by Alembic migrations)"
echo "✅ Temporary fix/debug scripts (no longer needed)"
echo "✅ Manual initialization files (automated with proper setup)"
echo "✅ Old setup directory and contents"
echo ""
print_info "What you have now:"
echo "  🎯 Clean project structure"
echo "  🎯 Alembic for database migrations"
echo "  🎯 Proper FastAPI application"
echo "  🎯 Environment-based configuration"
echo ""
print_info "If you need to reset the database:"
echo "  📝 Use: alembic downgrade base"
echo "  📝 Then: alembic upgrade head"
echo ""
print_info "If you need to create new migrations:"
echo "  📝 Use: alembic revision --autogenerate -m 'description'"
echo "  📝 Then: alembic upgrade head"