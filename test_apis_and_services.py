#!/usr/bin/env python3
"""
AI Chatbot Backend - Comprehensive API and Service Testing Script
Tests all endpoints, services, and integrations to verify everything works
"""

import asyncio
import json
import time
import random
import string
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
import websockets
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path.cwd()))

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'

class APITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_id = None
        self.test_chat_id = None
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def print_status(self, message: str, success: bool = True):
        """Print test status with color"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if success:
            print(f"{Colors.GREEN}[{timestamp}] ✅ {message}{Colors.NC}")
            self.tests_passed += 1
        else:
            print(f"{Colors.RED}[{timestamp}] ❌ {message}{Colors.NC}")
            self.tests_failed += 1
        
        self.test_results.append({
            "timestamp": timestamp,
            "message": message,
            "success": success
        })
    
    def print_warning(self, message: str):
        """Print warning message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.YELLOW}[{timestamp}] ⚠️  {message}{Colors.NC}")
    
    def print_info(self, message: str):
        """Print info message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.BLUE}[{timestamp}] ℹ️  {message}{Colors.NC}")
    
    def print_header(self, message: str):
        """Print section header"""
        print(f"\n{Colors.CYAN}{'='*60}")
        print(f"🧪 {message}")
        print(f"{'='*60}{Colors.NC}")
    
    def generate_test_data(self):
        """Generate random test data"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return {
            "username": f"testuser_{random_suffix}",
            "email": f"test_{random_suffix}@example.com",
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Add auth header if token is available
        if self.auth_token and 'headers' not in kwargs:
            kwargs['headers'] = {}
        if self.auth_token:
            kwargs['headers']['Authorization'] = f"Bearer {self.auth_token}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except requests.RequestException as e:
            self.print_status(f"Request failed: {method} {endpoint} - {str(e)}", False)
            return None
    
    def test_health_check(self):
        """Test health check endpoint"""
        self.print_header("HEALTH CHECK TESTS")
        
        response = self.make_request("GET", "/health")
        if response and response.status_code == 200:
            data = response.json()
            self.print_status("Health check endpoint working")
            
            # Check health data structure
            if "status" in data and "checks" in data:
                self.print_status("Health check response format correct")
                
                # Check individual services
                checks = data.get("checks", {})
                for service, status in checks.items():
                    if isinstance(status, dict) and status.get("status") == "healthy":
                        self.print_status(f"{service.title()} service healthy")
                    else:
                        self.print_status(f"{service.title()} service unhealthy", False)
            else:
                self.print_status("Health check response format incorrect", False)
        else:
            self.print_status("Health check endpoint failed", False)
    
    def test_authentication(self):
        """Test authentication endpoints"""
        self.print_header("AUTHENTICATION TESTS")
        
        test_user = self.generate_test_data()
        
        # Test user registration
        response = self.make_request("POST", "/api/v1/auth/register", json=test_user)
        if response and response.status_code == 201:
            self.print_status("User registration successful")
            user_data = response.json()
            self.test_user_id = user_data.get("user", {}).get("id")
        else:
            self.print_status("User registration failed", False)
            return False
        
        # Test user login
        login_data = {
            "email_or_username": test_user["email"],
            "password": test_user["password"]
        }
        response = self.make_request("POST", "/api/v1/auth/login", json=login_data)
        if response and response.status_code == 200:
            self.print_status("User login successful")
            auth_data = response.json()
            self.auth_token = auth_data.get("access_token")
            if self.auth_token:
                self.print_status("Access token received")
            else:
                self.print_status("Access token missing", False)
        else:
            self.print_status("User login failed", False)
            return False
        
        # Test protected endpoint
        response = self.make_request("GET", "/api/v1/users/me")
        if response and response.status_code == 200:
            self.print_status("Protected endpoint access successful")
        else:
            self.print_status("Protected endpoint access failed", False)
        
        return True
    
    def test_user_management(self):
        """Test user management endpoints"""
        self.print_header("USER MANAGEMENT TESTS")
        
        if not self.auth_token:
            self.print_status("Skipping user tests - no auth token", False)
            return
        
        # Test get current user
        response = self.make_request("GET", "/api/v1/users/me")
        if response and response.status_code == 200:
            self.print_status("Get current user profile successful")
            user_data = response.json()
            if "id" in user_data and "email" in user_data:
                self.print_status("User profile data complete")
            else:
                self.print_status("User profile data incomplete", False)
        else:
            self.print_status("Get current user profile failed", False)
        
        # Test update user profile
        update_data = {
            "bio": "Updated bio for testing",
            "first_name": "Updated"
        }
        response = self.make_request("PUT", "/api/v1/users/me", json=update_data)
        if response and response.status_code == 200:
            self.print_status("Update user profile successful")
        else:
            self.print_status("Update user profile failed", False)
    
    def test_chat_management(self):
        """Test chat management endpoints"""
        self.print_header("CHAT MANAGEMENT TESTS")
        
        if not self.auth_token:
            self.print_status("Skipping chat tests - no auth token", False)
            return
        
        # Test create chat
        chat_data = {
            "title": "Test Chat Session"
        }
        response = self.make_request("POST", "/api/v1/chat/", json=chat_data)
        if response and response.status_code == 201:
            self.print_status("Create chat successful")
            chat_response = response.json()
            self.test_chat_id = chat_response.get("id")
        else:
            self.print_status("Create chat failed", False)
            return
        
        # Test get user chats
        response = self.make_request("GET", "/api/v1/chat/")
        if response and response.status_code == 200:
            self.print_status("Get user chats successful")
            chats = response.json()
            if isinstance(chats, list) and len(chats) > 0:
                self.print_status("Chat list contains data")
            else:
                self.print_status("Chat list empty or invalid format", False)
        else:
            self.print_status("Get user chats failed", False)
        
        # Test get specific chat
        if self.test_chat_id:
            response = self.make_request("GET", f"/api/v1/chat/{self.test_chat_id}")
            if response and response.status_code == 200:
                self.print_status("Get specific chat successful")
            else:
                self.print_status("Get specific chat failed", False)
        
        # Test get chat messages
        if self.test_chat_id:
            response = self.make_request("GET", f"/api/v1/chat/{self.test_chat_id}/messages")
            if response and response.status_code == 200:
                self.print_status("Get chat messages successful")
            else:
                self.print_status("Get chat messages failed", False)
    
    def test_ai_conversation(self):
        """Test AI conversation endpoints"""
        self.print_header("AI CONVERSATION TESTS")
        
        if not self.auth_token:
            self.print_status("Skipping AI tests - no auth token", False)
            return
        
        # Test AI chat endpoint
        conversation_data = {
            "message": "Hello, this is a test message. How are you?",
            "chat_id": self.test_chat_id,
            "use_context": True,
            "detect_emotion": True,
            "enable_personalization": True
        }
        
        response = self.make_request("POST", "/api/v1/ai/chat", json=conversation_data)
        if response and response.status_code == 200:
            self.print_status("AI chat endpoint successful")
            ai_response = response.json()
            
            # Check response structure
            if "response" in ai_response:
                self.print_status("AI response contains message")
            else:
                self.print_status("AI response missing message", False)
            
            if "emotion_analysis" in ai_response:
                self.print_status("Emotion analysis included")
            else:
                self.print_status("Emotion analysis missing", False)
            
            if "metadata" in ai_response:
                self.print_status("Response metadata included")
            else:
                self.print_status("Response metadata missing", False)
        else:
            self.print_status("AI chat endpoint failed", False)
        
        # Test conversation history
        if self.test_chat_id:
            response = self.make_request("GET", f"/api/v1/chat/{self.test_chat_id}/messages")
            if response and response.status_code == 200:
                messages = response.json()
                if len(messages) >= 2:  # User message + AI response
                    self.print_status("Conversation history updated correctly")
                else:
                    self.print_status("Conversation history not updated", False)
            else:
                self.print_status("Could not verify conversation history", False)
    
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        self.print_header("WEBSOCKET TESTS")
        
        if not self.auth_token:
            self.print_status("Skipping WebSocket tests - no auth token", False)
            return
        
        try:
            # WebSocket URL with auth token
            ws_url = f"ws://localhost:8000/api/v1/ws/chat/{self.test_chat_id or 'test'}?token={self.auth_token}"
            
            async with websockets.connect(ws_url) as websocket:
                self.print_status("WebSocket connection established")
                
                # Send test message
                test_message = {
                    "type": "chat_message",
                    "data": {
                        "message": "Test WebSocket message"
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                self.print_status("WebSocket message sent")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    self.print_status("WebSocket response received")
                    
                    if "type" in response_data and "data" in response_data:
                        self.print_status("WebSocket response format correct")
                    else:
                        self.print_status("WebSocket response format incorrect", False)
                        
                except asyncio.TimeoutError:
                    self.print_status("WebSocket response timeout", False)
                
        except Exception as e:
            self.print_status(f"WebSocket connection failed: {str(e)}", False)
    
    def test_database_services(self):
        """Test database connectivity through internal services"""
        self.print_header("DATABASE SERVICE TESTS")
        
        try:
            # Import and test database functions
            from app.database import check_db_health, check_redis_health
            
            # Test database health
            import asyncio
            
            async def test_db_services():
                db_healthy = await check_db_health()
                redis_healthy = await check_redis_health()
                
                if db_healthy:
                    self.print_status("Database service healthy")
                else:
                    self.print_status("Database service unhealthy", False)
                
                if redis_healthy:
                    self.print_status("Redis service healthy")
                else:
                    self.print_status("Redis service unhealthy", False)
                
                return db_healthy and redis_healthy
            
            result = asyncio.run(test_db_services())
            return result
            
        except ImportError as e:
            self.print_status(f"Could not import database services: {str(e)}", False)
            return False
        except Exception as e:
            self.print_status(f"Database service test failed: {str(e)}", False)
            return False
    
    def test_ai_services(self):
        """Test AI services"""
        self.print_header("AI SERVICE TESTS")
        
        try:
            from app.services.openai_service import openai_service
            from app.services.emotion_service import emotion_service
            
            # Test OpenAI service
            import asyncio
            
            async def test_ai_services():
                # Test OpenAI health
                try:
                    openai_healthy = await openai_service.health_check()
                    if openai_healthy:
                        self.print_status("OpenAI service healthy")
                    else:
                        self.print_status("OpenAI service unhealthy (check API key)", False)
                except Exception as e:
                    self.print_status(f"OpenAI service test failed: {str(e)}", False)
                
                # Test emotion service
                try:
                    emotion_healthy = await emotion_service.health_check()
                    if emotion_healthy:
                        self.print_status("Emotion service healthy")
                    else:
                        self.print_status("Emotion service unhealthy", False)
                except Exception as e:
                    self.print_status(f"Emotion service test failed: {str(e)}", False)
                
                # Test emotion analysis
                try:
                    test_text = "I'm feeling happy and excited about this test!"
                    emotion_result = await emotion_service.analyze_emotion(test_text)
                    if emotion_result and "emotion" in emotion_result:
                        self.print_status("Emotion analysis working")
                    else:
                        self.print_status("Emotion analysis failed", False)
                except Exception as e:
                    self.print_status(f"Emotion analysis test failed: {str(e)}", False)
            
            asyncio.run(test_ai_services())
            
        except ImportError as e:
            self.print_status(f"Could not import AI services: {str(e)}", False)
        except Exception as e:
            self.print_status(f"AI service test failed: {str(e)}", False)
    
    def test_api_documentation(self):
        """Test API documentation endpoints"""
        self.print_header("API DOCUMENTATION TESTS")
        
        # Test OpenAPI schema
        response = self.make_request("GET", "/openapi.json")
        if response and response.status_code == 200:
            self.print_status("OpenAPI schema accessible")
            try:
                schema = response.json()
                if "paths" in schema and "components" in schema:
                    self.print_status("OpenAPI schema structure valid")
                else:
                    self.print_status("OpenAPI schema structure invalid", False)
            except json.JSONDecodeError:
                self.print_status("OpenAPI schema not valid JSON", False)
        else:
            self.print_status("OpenAPI schema not accessible", False)
        
        # Test Swagger UI
        response = self.make_request("GET", "/docs")
        if response and response.status_code == 200:
            self.print_status("Swagger UI accessible")
        else:
            self.print_status("Swagger UI not accessible", False)
        
        # Test ReDoc
        response = self.make_request("GET", "/redoc")
        if response and response.status_code == 200:
            self.print_status("ReDoc documentation accessible")
        else:
            self.print_status("ReDoc documentation not accessible", False)
    
    def test_error_handling(self):
        """Test error handling"""
        self.print_header("ERROR HANDLING TESTS")
        
        # Test 404 endpoint
        response = self.make_request("GET", "/nonexistent-endpoint")
        if response and response.status_code == 404:
            self.print_status("404 error handling working")
        else:
            self.print_status("404 error handling not working", False)
        
        # Test invalid JSON
        response = self.make_request("POST", "/api/v1/auth/register", 
                                   data="invalid json", 
                                   headers={"Content-Type": "application/json"})
        if response and response.status_code == 422:
            self.print_status("Invalid JSON error handling working")
        else:
            self.print_status("Invalid JSON error handling not working", False)
        
        # Test validation errors
        invalid_user = {"email": "invalid-email", "password": "123"}
        response = self.make_request("POST", "/api/v1/auth/register", json=invalid_user)
        if response and response.status_code == 422:
            self.print_status("Validation error handling working")
        else:
            self.print_status("Validation error handling not working", False)
    
    def generate_test_report(self):
        """Generate test report"""
        self.print_header("TEST REPORT")
        
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"{Colors.WHITE}📊 Test Summary:{Colors.NC}")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {Colors.GREEN}{self.tests_passed}{Colors.NC}")
        print(f"   Failed: {Colors.RED}{self.tests_failed}{Colors.NC}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.tests_failed > 0:
            print(f"\n{Colors.RED}❌ Failed Tests:{Colors.NC}")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['message']}")
        
        # Save detailed report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": self.tests_passed,
                "failed": self.tests_failed,
                "success_rate": success_rate
            },
            "results": self.test_results
        }
        
        with open("test_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        self.print_info("Detailed test report saved to test_report.json")
        
        return success_rate >= 80  # Consider 80%+ success rate as passing
    
    async def run_all_tests(self):
        """Run all tests"""
        print(f"{Colors.CYAN}")
        print("🧪 AI CHATBOT BACKEND - COMPREHENSIVE API TESTING")
        print("=" * 60)
        print(f"{Colors.NC}")
        print(f"Testing endpoint: {self.base_url}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Wait for server to be ready
        self.print_info("Waiting for server to be ready...")
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    self.print_status("Server is ready")
                    break
            except:
                if i < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    self.print_status("Server not responding - tests may fail", False)
        
        # Run all test suites
        self.test_health_check()
        self.test_database_services()
        self.test_ai_services()
        
        if self.test_authentication():
            self.test_user_management()
            self.test_chat_management()
            self.test_ai_conversation()
            await self.test_websocket_connection()
        
        self.test_api_documentation()
        self.test_error_handling()
        
        # Generate final report
        success = self.generate_test_report()
        
        if success:
            self.print_status("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
            print(f"{Colors.GREEN}Your AI Chatbot backend is working perfectly!{Colors.NC}")
        else:
            self.print_status("❌ SOME TESTS FAILED", False)
            print(f"{Colors.RED}Please check the failed tests and fix any issues.{Colors.NC}")
        
        return success

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Chatbot Backend API Testing Script")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL for the API (default: http://localhost:8000)")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick tests only (skip WebSocket and AI service tests)")
    
    args = parser.parse_args()
    
    tester = APITester(args.url)
    
    if args.quick:
        # Quick tests only
        tester.test_health_check()
        tester.test_api_documentation()
        success = tester.generate_test_report()
    else:
        # Full test suite
        success = asyncio.run(tester.run_all_tests())
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()