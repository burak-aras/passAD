"""
Token Service - Unified Token Management
Handles token generation, validation, and storage using SQLite
"""

import sqlite3
import secrets
import logging
import os
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


class TokenService:
    """Manages password reset tokens with SQLite backend"""
    
    def __init__(self, db_path=None):
        """
        Initialize token service
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or os.getenv('TOKEN_DB_PATH', '/app/data/tokens.db')
        self.lock = Lock()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        logger.info(f"TokenService initialized with database: {self.db_path}")
    
    def _init_db(self):
        """Create tokens table if it doesn't exist"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT 0,
                    used_at TIMESTAMP
                )
            ''')
            # Create indexes for faster lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_username ON tokens(username)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_expires_at ON tokens(expires_at)
            ''')
            conn.commit()
            conn.close()
    
    def generate_token(self, username, validity_hours=24):
        """
        Generate a new password reset token for a user
        
        Args:
            username: AD username
            validity_hours: Token validity period in hours (default: 24)
            
        Returns:
            str: Generated token
        """
        token = secrets.token_urlsafe(32)
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=validity_hours)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Invalidate any existing unused tokens for this user
            cursor.execute('''
                UPDATE tokens 
                SET used = 1, used_at = ? 
                WHERE username = ? AND used = 0
            ''', (created_at, username))
            
            # Insert new token
            cursor.execute('''
                INSERT INTO tokens (token, username, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (token, username, created_at, expires_at))
            
            conn.commit()
            conn.close()
        
        logger.info(f"Generated token for user: {username}, expires: {expires_at}")
        return token
    
    def validate_token(self, token):
        """
        Validate a token and return associated username
        
        Args:
            token: Token to validate
            
        Returns:
            tuple: (valid: bool, username: str or None, message: str)
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, expires_at, used 
                FROM tokens 
                WHERE token = ?
            ''', (token,))
            
            result = cursor.fetchone()
            conn.close()
        
        if not result:
            logger.warning(f"Token not found: {token[:10]}...")
            return False, None, "Geçersiz veya bilinmeyen token"
        
        username, expires_at_str, used = result
        expires_at = datetime.fromisoformat(expires_at_str)
        
        # Check if already used
        if used:
            logger.warning(f"Token already used for user: {username}")
            return False, None, "Bu token daha önce kullanılmış"
        
        # Check if expired
        if datetime.utcnow() > expires_at:
            logger.warning(f"Token expired for user: {username}")
            return False, None, "Token süresi dolmuş. Lütfen yeni bir şifre sıfırlama isteği oluşturun"
        
        logger.info(f"Token validated successfully for user: {username}")
        return True, username, "Token geçerli"
    
    def mark_token_used(self, token):
        """
        Mark a token as used
        
        Args:
            token: Token to mark as used
            
        Returns:
            bool: True if successful
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE tokens 
                SET used = 1, used_at = ? 
                WHERE token = ?
            ''', (datetime.utcnow(), token))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
        
        if affected > 0:
            logger.info(f"Token marked as used: {token[:10]}...")
            return True
        else:
            logger.warning(f"Failed to mark token as used: {token[:10]}...")
            return False
    
    def cleanup_expired_tokens(self, days_old=7):
        """
        Remove expired tokens older than specified days
        
        Args:
            days_old: Remove tokens older than this many days (default: 7)
            
        Returns:
            int: Number of tokens removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM tokens 
                WHERE expires_at < ?
            ''', (cutoff_date,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired tokens")
        
        return deleted
