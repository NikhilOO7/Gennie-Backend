#!/usr/bin/env python3
"""
Test script to verify database table creation works correctly
Run this script to test if all models can be created without the metadata conflict
"""

import sys
import os
import asyncio
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

def test_model_imports():
    """Test if all models can be imported without errors"""
    print("🔄 Testing model imports...")
    
    try:
        from app.models.user import User
        print("✅ User model imported successfully")
        
        from app.models.chat import Chat
        print("✅ Chat model imported successfully")
        
        from app.models.message import Message
        print("✅ Message model imported successfully")
        
        from app.models.emotion import Emotion
        print("✅ Emotion model imported successfully")
        
        from app.models.user_preferences import UserPreferences
        print("✅ UserPreferences model imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Model import failed: {str(e)}")
        return False

def test_database_setup():
    """Test database setup and table creation"""
    print("\n🔄 Testing database setup...")
    
    try:
        from app.database import Base, engine, create_tables, check_db_health
        print("✅ Database module imported successfully")
        
        # Check if we can inspect the metadata
        print(f"✅ Found {len(Base.metadata.tables)} tables in metadata:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def test_table_creation():
    """Test actual table creation"""
    print("\n🔄 Testing table creation...")
    
    try:
        from app.database import create_tables
        
        # Try to create tables
        success = await create_tables()
        
        if success:
            print("✅ Tables created successfully!")
            return True
        else:
            print("❌ Table creation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Table creation error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def test_model_creation():
    """Test creating model instances"""
    print("\n🔄 Testing model instance creation...")
    
    try:
        from app.models.user import User
        from app.models.chat import Chat
        from app.models.message import Message
        from app.models.emotion import Emotion
        from app.models.user_preferences import UserPreferences
        
        # Test User creation
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User"
        )
        print("✅ User instance created successfully")
        
        # Test Chat creation
        chat = Chat(
            user_id=1,
            title="Test Chat",
            ai_model="gpt-3.5-turbo"
        )
        print("✅ Chat instance created successfully")
        
        # Test Message creation (with the fixed metadata field)
        message = Message(
            chat_id=1,
            content="Test message",
            sender_type="user",
            message_metadata={"test": "data"}  # Using the renamed field
        )
        print("✅ Message instance created successfully")
        print(f"   - Message metadata: {message.message_metadata}")  # Direct field access
        
        # Test Emotion creation
        emotion = Emotion(
            chat_id=1,
            message_id=1,
            emotion_type="joy",
            confidence=0.8
        )
        print("✅ Emotion instance created successfully")
        
        # Test UserPreferences creation
        preferences = UserPreferences.create_default(user_id=1)
        print("✅ UserPreferences instance created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Model instance creation failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting Database Model Tests")
    print("=" * 50)
    
    # Test 1: Model imports
    test1_passed = test_model_imports()
    
    # Test 2: Database setup
    test2_passed = test_database_setup()
    
    # Test 3: Model instance creation
    test3_passed = test_model_creation()
    
    # Test 4: Table creation (only if previous tests pass)
    test4_passed = False
    if test1_passed and test2_passed:
        test4_passed = await test_table_creation()
    else:
        print("\n⚠️  Skipping table creation test due to previous failures")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY:")
    print(f"   ✅ Model Imports: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"   ✅ Database Setup: {'PASSED' if test2_passed else 'FAILED'}")
    print(f"   ✅ Model Creation: {'PASSED' if test3_passed else 'FAILED'}")
    print(f"   ✅ Table Creation: {'PASSED' if test4_passed else 'FAILED'}")
    
    all_passed = all([test1_passed, test2_passed, test3_passed, test4_passed])
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Your database models are ready!")
        print("✅ The 'metadata' field conflict has been resolved!")
        print("✅ You can now run your application without database errors!")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)