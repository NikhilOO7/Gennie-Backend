import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def setup_testing():
    """Set up testing infrastructure"""
    print("📋 Setting up testing infrastructure...")
    
    # Create test directories
    os.makedirs("tests", exist_ok=True)
    os.makedirs("tests/unit", exist_ok=True)
    os.makedirs("tests/integration", exist_ok=True)
    
    # Install test dependencies
    test_deps = [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.0.0",
        "httpx>=0.24.0",
        "pytest-mock>=3.10.0"
    ]
    
    for dep in test_deps:
        run_command(f"pip install {dep}", f"Installing {dep}")
    
    return True

def setup_vector_service():
    """Set up vector service dependencies"""
    print("🔍 Setting up vector service...")
    
    vector_deps = [
        "sentence-transformers>=2.2.0",
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0"
    ]
    
    for dep in vector_deps:
        run_command(f"pip install {dep}", f"Installing {dep}")
    
    return True

def setup_production_config():
    """Set up production configuration"""
    print("🚀 Setting up production configuration...")
    
    # Create production environment file template
    prod_env_template = """
# Production Environment Configuration
ENVIRONMENT=production
SECRET_KEY=your-super-secret-production-key-change-this
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/chatbot_db
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your-gemini-api-key
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com
SSL_REDIRECT=true
SECURE_COOKIES=true
"""
    
    with open(".env.production.template", "w") as f:
        f.write(prod_env_template)
    
    print("✅ Created .env.production.template")
    return True

def main():
    """Main setup function"""
    print("🎯 Phase 1 Completion Setup")
    print("=" * 50)
    
    success = True
    
    # Set up testing
    if not setup_testing():
        success = False
    
    # Set up vector service
    if not setup_vector_service():
        success = False
    
    # Set up production config
    if not setup_production_config():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Phase 1 completion setup finished successfully!")
        print("\nNext steps:")
        print("1. Copy the implementation code from the artifacts")
        print("2. Run tests: pytest tests/ -v")
        print("3. Set up your production environment")
        print("4. Deploy using Docker: docker-compose -f docker-compose.prod.yml up -d")
    else:
        print("❌ Setup completed with errors. Please check the output above.")
    
    return success

if __name__ == "__main__":
    main()