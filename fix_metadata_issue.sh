#!/bin/bash

echo "🔧 Fixing SQLAlchemy metadata issue..."

# Check if we're in the right directory
if [[ ! -f "app/models/chat.py" ]]; then
    echo "❌ chat.py not found. Make sure you're in the project root."
    exit 1
fi

# Backup the original file
cp app/models/chat.py app/models/chat.py.backup
echo "✅ Backed up original chat.py"

# Replace 'metadata' with 'message_metadata' in the chat.py file
sed -i.tmp 's/metadata = Column/message_metadata = Column/g' app/models/chat.py
sed -i.tmp 's/metadata=/message_metadata=/g' app/models/chat.py

# Clean up temporary files
rm -f app/models/chat.py.tmp

echo "✅ Updated metadata column name to message_metadata"

# Test if the fix worked
echo "🧪 Testing the fix..."

# Activate virtual environment if it exists
if [[ -d "venv" ]]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Test importing the models
if python -c "from app.models.chat import Chat, Message; print('✅ Models import successfully')"; then
    echo "✅ SQLAlchemy models fixed"
else
    echo "❌ Models still have issues"
    echo "Please manually update your app/models/chat.py file:"
    echo "  Change: metadata = Column(JSON, nullable=True)"
    echo "  To:     message_metadata = Column(JSON, nullable=True)"
    exit 1
fi

# Test importing the main app
if python -c "from app.main import app; print('✅ FastAPI app loads successfully')"; then
    echo "✅ FastAPI application loads successfully"
    echo "🎉 Fix complete! You can now run: uvicorn app.main:app --reload"
else
    echo "❌ FastAPI app still has issues"
    echo "Please check your imports and other files"
    exit 1
fi

echo ""
echo "🚀 Ready to start the application!"
echo "📝 Changes made:"
echo "   - Renamed 'metadata' column to 'message_metadata' in Message model"
echo "   - This avoids conflict with SQLAlchemy's reserved 'metadata' attribute"
echo ""
echo "💡 Next steps:"
echo "   1. Run: uvicorn app.main:app --reload"
echo "   2. If you have existing data, create a migration:"
echo "      alembic revision --autogenerate -m 'Rename metadata to message_metadata'"
echo "      alembic upgrade head"