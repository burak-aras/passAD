"""
Log Service - Centralized Logging for Admin Panel
Handles email logs, password change logs, and activity tracking
"""

import sqlite3
import logging
import os
from datetime import datetime, timedelta, timezone
from threading import Lock

logger = logging.getLogger(__name__)


def get_local_time():
    """Get current time (relies on system timezone)"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class LogService:
    """Centralized logging service with SQLite backend"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv('LOG_DB_PATH', '/app/data/logs.db')
        self.lock = Lock()
        self.retention_days = int(os.getenv('LOG_RETENTION_DAYS', '30'))
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        logger.info(f"LogService initialized: {self.db_path}")
    
    def _init_db(self):
        """Create log tables"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Email logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    real_email TEXT,
                    sent_to TEXT,
                    token TEXT,
                    days_left INTEGER,
                    status TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Password change logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    token TEXT,
                    status TEXT,
                    error_message TEXT,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Activity logs (admin actions, job runs, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_created ON email_logs(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_created ON password_logs(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_logs(created_at)')
            
            conn.commit()
            conn.close()
    
    # === EMAIL LOGS ===
    
    def log_email(self, username, display_name, real_email, sent_to, token, days_left, status, error_message=None):
        """Log an email send attempt"""
        local_time = get_local_time()
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO email_logs (username, display_name, real_email, sent_to, token, days_left, status, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, display_name, real_email, sent_to, token, days_left, status, error_message, local_time))
            conn.commit()
            conn.close()
        logger.info(f"Email log: {username} -> {sent_to} ({status})")
    
    def get_email_logs(self, limit=100, offset=0, date_from=None, date_to=None):
        """Get email logs with pagination and filtering"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM email_logs WHERE 1=1'
            params = []
            
            if date_from:
                query += ' AND created_at >= ?'
                params.append(date_from)
            if date_to:
                query += ' AND created_at <= ?'
                params.append(date_to)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
    
    def get_email_stats(self, days=7):
        """Get email statistics for last N days"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM email_logs WHERE created_at >= ?
            ''', (cutoff,))
            
            row = cursor.fetchone()
            conn.close()
            return {'total': row[0] or 0, 'sent': row[1] or 0, 'failed': row[2] or 0}
    
    # === PASSWORD LOGS ===
    
    def log_password_change(self, username, token, status, error_message=None, ip_address=None):
        """Log a password change attempt"""
        local_time = get_local_time()
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO password_logs (username, token, status, error_message, ip_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, token, status, error_message, ip_address, local_time))
            conn.commit()
            conn.close()
        logger.info(f"Password log: {username} ({status})")
    
    def get_password_logs(self, limit=100, offset=0):
        """Get password change logs"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM password_logs 
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (limit, offset))
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
    
    def get_password_stats(self, days=7):
        """Get password change statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM password_logs WHERE created_at >= ?
            ''', (cutoff,))
            
            row = cursor.fetchone()
            conn.close()
            return {'total': row[0] or 0, 'success': row[1] or 0, 'failed': row[2] or 0}
    
    # === ACTIVITY LOGS ===
    
    def log_activity(self, action, details=None, ip_address=None):
        """Log an admin/system activity"""
        local_time = get_local_time()
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO activity_logs (action, details, ip_address, created_at)
                VALUES (?, ?, ?, ?)
            ''', (action, details, ip_address, local_time))
            conn.commit()
            conn.close()
        logger.info(f"Activity: {action}")
    
    def get_activity_logs(self, limit=100, offset=0):
        """Get activity logs"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM activity_logs 
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (limit, offset))
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
    
    # === CLEANUP ===
    
    def cleanup_old_logs(self):
        """Remove logs older than retention period"""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM email_logs WHERE created_at < ?', (cutoff,))
            email_deleted = cursor.rowcount
            
            cursor.execute('DELETE FROM password_logs WHERE created_at < ?', (cutoff,))
            password_deleted = cursor.rowcount
            
            cursor.execute('DELETE FROM activity_logs WHERE created_at < ?', (cutoff,))
            activity_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
        
        total = email_deleted + password_deleted + activity_deleted
        if total > 0:
            logger.info(f"Cleaned up {total} old log entries")
        return total
    
    # === DASHBOARD STATS ===
    
    def get_dashboard_stats(self):
        """Get all stats for dashboard"""
        return {
            'email': self.get_email_stats(days=7),
            'password': self.get_password_stats(days=7),
            'today': self._get_today_stats()
        }
    
    def _get_today_stats(self):
        """Get today's statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.utcnow().strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT COUNT(*) FROM email_logs 
                WHERE date(created_at) = date(?)
            ''', (today,))
            emails_today = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM password_logs 
                WHERE date(created_at) = date(?) AND status = 'success'
            ''', (today,))
            passwords_today = cursor.fetchone()[0]
            
            conn.close()
            return {'emails': emails_today, 'passwords': passwords_today}
