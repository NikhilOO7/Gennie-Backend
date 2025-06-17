#!/usr/bin/env python3
"""
Generate a clean requirements.txt with only the packages we explicitly need
"""

import subprocess
import sys

def get_package_version(package_name):
    """Get the installed version of a package"""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', package_name], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version: '):
                    return line.split('Version: ')[1].strip()
    except Exception:
        pass
    return None

# Our required packages
required_packages = [
    'fastapi',
    'uvicorn',
    'sqlalchemy', 
    'psycopg2-binary',
    'alembic',
    'asyncpg',
    'redis',
    'aioredis',
    'python-multipart',
    'python-jose',
    'passlib',
    'openai',
    'vaderSentiment',
    'textblob',
    'websockets',
    'httpx',
    'pydantic',
    'pydantic-settings',
    'python-dotenv',
    'pytest',
    'pytest-asyncio'
]

print("📦 Generating clean requirements.txt...")
print("="*50)

requirements_content = []

for package in required_packages:
    version = get_package_version(package)
    if version:
        requirements_content.append(f"{package}=={version}")
        print(f"✅ {package}=={version}")
    else:
        print(f"❌ {package} - version not found")

# Write to requirements.txt
with open('requirements.txt', 'w') as f:
    f.write('\n'.join(requirements_content))
    f.write('\n')

print("="*50)
print(f"✅ Clean requirements.txt generated with {len(requirements_content)} packages!")
print("\nTo use this requirements.txt in the future:")
print("pip install -r requirements.txt")
