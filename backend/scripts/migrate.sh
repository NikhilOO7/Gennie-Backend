#!/bin/bash
# Quick migration script

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

case "$1" in
    "create")
        if [ -z "$2" ]; then
            echo "Usage: ./scripts/migrate.sh create 'migration message'"
            exit 1
        fi
        python setup-scripts/setup_migrations.py create "$2"
        ;;
    "up")
        python setup-scripts/setup_migrations.py up
        ;;
    "down")
        python setup-scripts/setup_migrations.py down ${2:-1}
        ;;
    "status")
        python setup-scripts/setup_migrations.py status
        ;;
    "reset")
        python setup-scripts/setup_migrations.py reset
        ;;
    *)
        echo "Usage: ./scripts/migrate.sh {create|up|down|status|reset}"
        echo "  create 'message' - Create new migration"
        echo "  up              - Apply all migrations"
        echo "  down [n]        - Rollback n migrations (default: 1)"
        echo "  status          - Show migration status"
        echo "  reset           - Reset database (DANGEROUS!)"
        exit 1
        ;;
esac
