"""
Utility Service - Common utility functions and helpers
2025 standards with comprehensive utility functions
"""

import asyncio
import hashlib
import secrets
import string
import re
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import aiofiles
import json
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

class UtilsService:
    """
    Comprehensive utility service with common functions
    """
    
    def __init__(self):
        """Initialize utils service"""
        self.password_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        logger.info("Utils service initialized")
    
    # String utilities
    @staticmethod
    def clean_text(text: str, max_length: Optional[int] = None) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Truncate if needed
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rsplit(' ', 1)[0] + "..."
        
        return cleaned
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        if not text:
            return []
        
        # Simple keyword extraction - remove common words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'throughout',
            'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can',
            'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        # Extract words, convert to lowercase, filter out common words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in common_words]
        
        # Count frequency and return most common
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:max_keywords]]
    
    @staticmethod
    def truncate_smartly(text: str, max_length: int) -> str:
        """Intelligently truncate text at word boundaries"""
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        
        # Find the last sentence ending
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        
        # Find the latest sentence ending
        sentence_end = max(last_period, last_exclamation, last_question)
        
        if sentence_end > max_length * 0.7:  # Keep at least 70% of content
            return truncated[:sentence_end + 1]
        else:
            # Fallback to word boundary
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.5:
                return truncated[:last_space] + "..."
            else:
                return truncated + "..."
    
    # Security utilities
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_password(length: int = 12) -> str:
        """Generate secure random password"""
        utils = UtilsService()
        return ''.join(secrets.choice(utils.password_chars) for _ in range(length))
    
    @staticmethod
    def hash_string(text: str, algorithm: str = "sha256") -> str:
        """Hash string using specified algorithm"""
        if algorithm == "sha256":
            return hashlib.sha256(text.encode()).hexdigest()
        elif algorithm == "md5":
            return hashlib.md5(text.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    # Date/time utilities
    @staticmethod
    def format_datetime(dt: datetime, format_type: str = "iso") -> str:
        """Format datetime in various formats"""
        if format_type == "iso":
            return dt.isoformat()
        elif format_type == "human":
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif format_type == "date_only":
            return dt.strftime("%Y-%m-%d")
        elif format_type == "time_only":
            return dt.strftime("%H:%M:%S")
        else:
            return str(dt)
    
    @staticmethod
    def time_ago(dt: datetime) -> str:
        """Get human-readable time difference"""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        diff = now - dt
        
        if diff.days > 365:
            return f"{diff.days // 365} year{'s' if diff.days // 365 != 1 else ''} ago"
        elif diff.days > 30:
            return f"{diff.days // 30} month{'s' if diff.days // 30 != 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    # Data validation utilities
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.]*))?(?:\#(?:[\w.]*))?)?$'
        return re.match(pattern, url) is not None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove or replace unsafe characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 255 - len(ext) - 1 if ext else 255
            filename = name[:max_name_length] + ('.' + ext if ext else '')
        
        return filename
    
    # File utilities
    @staticmethod
    async def read_json_file(file_path: str) -> Dict[str, Any]:
        """Read JSON file asynchronously"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to read JSON file {file_path}: {str(e)}")
            return {}
    
    @staticmethod
    async def write_json_file(file_path: str, data: Dict[str, Any]) -> bool:
        """Write JSON file asynchronously"""
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, default=str))
            return True
        except Exception as e:
            logger.error(f"Failed to write JSON file {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_file_size_human(size_bytes: int) -> str:
        """Convert file size to human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    # Data processing utilities
    @staticmethod
    def paginate_list(items: List[Any], page: int, page_size: int) -> Tuple[List[Any], Dict[str, Any]]:
        """Paginate a list of items"""
        total_items = len(items)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        paginated_items = items[start_index:end_index]
        
        pagination_info = {
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_items + page_size - 1) // page_size,
            "has_next": end_index < total_items,
            "has_previous": page > 1,
            "start_index": start_index + 1 if paginated_items else 0,
            "end_index": min(end_index, total_items)
        }
        
        return paginated_items, pagination_info
    
    @staticmethod
    def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = UtilsService.deep_merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result
    
    # Email utilities
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> bool:
        """Send email using SMTP"""
        
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, cannot send email")
            return False
        
        try:
            from_email = from_email or settings.FROM_EMAIL
            if not from_email:
                logger.error("No from_email specified and FROM_EMAIL not configured")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            
            # Add text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                
                if settings.SMTP_USERNAME:
                    password = settings.get_smtp_password()
                    if password:
                        server.login(settings.SMTP_USERNAME, password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    # Performance utilities
    @staticmethod
    def measure_time(func):
        """Decorator to measure function execution time"""
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            try:
                result = await func(*args, **kwargs)
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.debug(f"Function {func.__name__} executed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}")
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            try:
                result = func(*args, **kwargs)
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.debug(f"Function {func.__name__} executed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    # Configuration utilities
    @staticmethod
    def get_config_value(key: str, default: Any = None) -> Any:
        """Get configuration value with fallback"""
        return getattr(settings, key, default)
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production"""
        return settings.ENVIRONMENT.lower() == "production"
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development"""
        return settings.ENVIRONMENT.lower() == "development"
    
    @staticmethod
    def generate_chat_title(
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        title: Optional[str] = None
    ) -> str:
        """Generate a standardized chat title"""
        if title:
            return UtilsService.clean_text(title, max_length=50)
        
        parts = []
        if user_id:
            parts.append(f"User {user_id}")
        if chat_id:
            parts.append(f"Chat {chat_id}")
        
        return " - ".join(parts) or "Untitled Chat"

# Create global service instance
utils_service = UtilsService()