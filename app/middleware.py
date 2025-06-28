"""
Application Middleware - Security, logging, rate limiting, and compression
"""

import time
import json
import gzip
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timezone
from collections import defaultdict
import asyncio
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.datastructures import MutableHeaders
import aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse
    Uses Redis for distributed rate limiting if available, falls back to in-memory
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        
        # In-memory fallback storage
        self.request_counts: Dict[str, list] = defaultdict(list)
        
        # Try to connect to Redis for distributed rate limiting
        self.redis_client = None
        asyncio.create_task(self._init_redis())
    
    async def _init_redis(self):
        """Initialize Redis connection if available"""
        try:
            if settings.REDIS_URL:
                self.redis_client = await aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
                logger.info("Rate limiting using Redis")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {str(e)}")
            self.redis_client = None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limit_redis(self, client_id: str) -> bool:
        """Check rate limit using Redis"""
        try:
            key = f"rate_limit:{client_id}"
            current_time = int(time.time())
            window_start = current_time - self.window_seconds
            
            # Remove old entries
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            request_count = await self.redis_client.zcard(key)
            
            if request_count >= self.requests_per_minute:
                return False
            
            # Add current request
            await self.redis_client.zadd(key, {str(uuid.uuid4()): current_time})
            await self.redis_client.expire(key, self.window_seconds)
            
            return True
        
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {str(e)}")
            return True  # Allow request on error
    
    def _check_rate_limit_memory(self, client_id: str) -> bool:
        """Check rate limit using in-memory storage"""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Clean old requests
        self.request_counts[client_id] = [
            timestamp for timestamp in self.request_counts[client_id]
            if timestamp > window_start
        ]
        
        # Check limit
        if len(self.request_counts[client_id]) >= self.requests_per_minute:
            return False
        
        # Add current request
        self.request_counts[client_id].append(current_time)
        return True
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request through rate limiting"""
        # Skip rate limiting for health endpoints
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_ip(request)
        
        # Check rate limit
        if self.redis_client:
            allowed = await self._check_rate_limit_redis(client_id)
        else:
            allowed = self._check_rate_limit_memory(client_id)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": self.window_seconds
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + self.window_seconds)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        if self.redis_client:
            try:
                key = f"rate_limit:{client_id}"
                remaining = self.requests_per_minute - await self.redis_client.zcard(key)
                response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
                response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_seconds)
            except:
                pass
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Request/Response logging middleware
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("app.requests")
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Log request and response details"""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request
        self.logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("User-Agent", "Unknown")
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            self.logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": round(duration, 3),
                    "response_size": response.headers.get("Content-Length", "Unknown")
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{round(duration * 1000)}ms"
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            self.logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_seconds": round(duration, 3),
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware to protect against common attacks
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            # Prevent XSS attacks
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Enable XSS protection in older browsers
            "X-XSS-Protection": "1; mode=block",
            
            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy (formerly Feature Policy)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' ws: wss: https:;"
            ),
            
            # HSTS (only for production with HTTPS)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Add security headers to response"""
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            # Skip HSTS in development
            if header == "Strict-Transport-Security" and settings.ENVIRONMENT != "production":
                continue
            
            response.headers[header] = value
        
        # Remove sensitive headers
        sensitive_headers = ["Server", "X-Powered-By"]
        for header in sensitive_headers:
            if header in response.headers:
                del response.headers[header]
        
        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Response compression middleware to reduce bandwidth
    """
    
    def __init__(self, app, minimum_size: int = 1024):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compressible_types = {
            "text/html",
            "text/css",
            "text/plain",
            "text/xml",
            "text/javascript",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/rss+xml",
            "application/atom+xml",
            "image/svg+xml"
        }
    
    def _should_compress(self, request: Request, response: Response) -> bool:
        """Check if response should be compressed"""
        # Check if client accepts gzip
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding:
            return False
        
        # Check if already compressed
        if "Content-Encoding" in response.headers:
            return False
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if not any(ct in content_type for ct in self.compressible_types):
            return False
        
        # Check content length
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) < self.minimum_size:
            return False
        
        return True
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Compress response if applicable"""
        response = await call_next(request)
        
        # Check if we should compress
        if not self._should_compress(request, response):
            return response
        
        # For streaming responses, we can't compress easily
        if hasattr(response, "body_iterator"):
            return response
        
        try:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Compress body
            compressed_body = gzip.compress(body)
            
            # Check if compression actually reduced size
            if len(compressed_body) >= len(body):
                # Return original response
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            
            # Create compressed response
            headers = MutableHeaders(response.headers)
            headers["Content-Encoding"] = "gzip"
            headers["Content-Length"] = str(len(compressed_body))
            headers["Vary"] = "Accept-Encoding"
            
            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=dict(headers),
                media_type=response.media_type
            )
        
        except Exception as e:
            logger.error(f"Compression failed: {str(e)}")
            return response


class CORSMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with better configuration options
    """
    
    def __init__(
        self,
        app,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        expose_headers: list = None,
        allow_credentials: bool = True,
        max_age: int = 3600
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        self.allow_headers = allow_headers or ["*"]
        self.expose_headers = expose_headers or []
        self.allow_credentials = allow_credentials
        self.max_age = max_age
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        if "*" in self.allow_origins:
            return True
        
        return origin in self.allow_origins
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Handle CORS headers"""
        origin = request.headers.get("Origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            
            if origin and self._is_origin_allowed(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
                
                if self.allow_credentials:
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                
                if self.max_age:
                    response.headers["Access-Control-Max-Age"] = str(self.max_age)
            
            return response
        
        # Process regular requests
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
            
            if self.expose_headers:
                response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation middleware to ensure data integrity
    """
    
    def __init__(self, app, max_body_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Validate request before processing"""
        # Check content length
        content_length = request.headers.get("Content-Length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_body_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request body too large",
                            "max_size": self.max_body_size,
                            "provided_size": size
                        }
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid Content-Length header"}
                )
        
        # Check content type for POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("Content-Type", "")
            
            # Allow JSON and form data
            allowed_types = ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]
            
            if not any(ct in content_type for ct in allowed_types):
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "Unsupported Media Type",
                        "allowed_types": allowed_types,
                        "provided_type": content_type
                    }
                )
        
        return await call_next(request)


# Export all middleware classes
__all__ = [
    "RateLimitMiddleware",
    "LoggingMiddleware",
    "SecurityHeadersMiddleware",
    "CompressionMiddleware",
    "CORSMiddleware",
    "RequestValidationMiddleware"
]