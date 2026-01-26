"""
Admin Panel - Flask Blueprint for Administration
Simple password-protected admin interface
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import os
import logging
import subprocess

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates/admin')

# Admin password from environment
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')


def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            logger.info(f"Admin login from IP: {request.remote_addr}")
            
            # Log activity
            from services.log_service import LogService
            log_service = LogService()
            log_service.log_activity('admin_login', 'Admin logged in', request.remote_addr)
            
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Hatalı şifre!', 'error')
            logger.warning(f"Failed admin login attempt from IP: {request.remote_addr}")
    
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    flash('Çıkış yapıldı.', 'success')
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard with statistics"""
    from services.log_service import LogService
    from services.token_service import TokenService
    
    log_service = LogService()
    token_service = TokenService()
    
    stats = log_service.get_dashboard_stats()
    
    # Get active tokens count
    with token_service.lock:
        import sqlite3
        conn = sqlite3.connect(token_service.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM tokens WHERE used = 0 AND expires_at > datetime("now")')
        active_tokens = cursor.fetchone()[0]
        conn.close()
    
    stats['active_tokens'] = active_tokens
    
    # Recent activity
    recent_activity = log_service.get_activity_logs(limit=10)
    
    return render_template('admin/dashboard.html', stats=stats, recent_activity=recent_activity)


@admin_bp.route('/emails')
@admin_required
def email_logs():
    """Email logs page"""
    from services.log_service import LogService
    log_service = LogService()
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    logs = log_service.get_email_logs(limit=per_page, offset=offset)
    
    return render_template('admin/email_logs.html', logs=logs, page=page)


@admin_bp.route('/passwords')
@admin_required
def password_logs():
    """Password change logs page"""
    from services.log_service import LogService
    log_service = LogService()
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    logs = log_service.get_password_logs(limit=per_page, offset=offset)
    
    return render_template('admin/password_logs.html', logs=logs, page=page)


@admin_bp.route('/tokens')
@admin_required
def token_logs():
    """Token status page"""
    from services.token_service import TokenService
    import sqlite3
    
    token_service = TokenService()
    
    with token_service.lock:
        conn = sqlite3.connect(token_service.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT token, username, created_at, expires_at, used, used_at,
                CASE 
                    WHEN used = 1 THEN 'used'
                    WHEN expires_at < datetime('now') THEN 'expired'
                    ELSE 'active'
                END as status
            FROM tokens 
            ORDER BY created_at DESC 
            LIMIT 100
        ''')
        tokens = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    return render_template('admin/token_logs.html', tokens=tokens)


@admin_bp.route('/run-job', methods=['POST'])
@admin_required
def run_job():
    """Manually trigger the password expiry check job"""
    from services.log_service import LogService
    
    log_service = LogService()
    log_service.log_activity('manual_job_trigger', 'Password expiry job manually triggered', request.remote_addr)
    
    try:
        # Import and run the job directly
        from jobs.password_expiry_job import run_password_expiry_check
        run_password_expiry_check()
        flash('Job başarıyla çalıştırıldı!', 'success')
    except Exception as e:
        flash(f'Job hatası: {str(e)}', 'error')
        logger.error(f"Manual job run failed: {str(e)}")
    
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/cleanup', methods=['POST'])
@admin_required
def cleanup():
    """Cleanup expired tokens and old logs"""
    from services.log_service import LogService
    from services.token_service import TokenService
    
    log_service = LogService()
    token_service = TokenService()
    
    # Cleanup tokens
    tokens_deleted = token_service.cleanup_expired_tokens()
    
    # Cleanup logs
    logs_deleted = log_service.cleanup_old_logs()
    
    log_service.log_activity('cleanup', f'Tokens: {tokens_deleted}, Logs: {logs_deleted}', request.remote_addr)
    
    flash(f'Temizlendi: {tokens_deleted} token, {logs_deleted} log', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users')
@admin_required
def users():
    """List all AD users with password expiry info"""
    from services.ad_service import ADService
    
    ad_service = ADService()
    users_list, max_age = ad_service.get_all_users()
    
    return render_template('admin/users.html', users=users_list, max_age=max_age)


@admin_bp.route('/send-email', methods=['POST'])
@admin_required
def send_manual_email():
    """Send manual password warning email to a specific user"""
    from services.ad_service import ADService, generate_secure_password
    from services.email_service import EmailService
    from services.token_service import TokenService
    from services.log_service import LogService
    from datetime import timedelta, datetime
    import os
    
    username = request.form.get('username')
    display_name = request.form.get('display_name')
    email = request.form.get('email')
    days_left = request.form.get('days_left', type=int)
    
    # Debug logging
    logger.info(f"Manual email request: username={username}, days_left={days_left}, type={type(days_left)}")
    
    if not email:
        flash('Bu kullanıcının email adresi yok!', 'error')
        return redirect(url_for('admin.users'))
    
    # Initialize services
    ad_service = ADService()
    email_service = EmailService()
    token_service = TokenService()
    log_service = LogService()
    
    # Configuration
    passcore_url = os.getenv('PASSCORE_URL', 'http://localhost')
    token_validity_hours = int(os.getenv('TOKEN_VALIDITY_HOURS', '24'))
    test_recipient = os.getenv('TEST_RECIPIENT', '')
    
    # Email goes to
    sent_to = test_recipient if test_recipient else email
    
    # Check if password is already expired (days_left < 0)
    if days_left is not None and days_left < 0:
        # === EXPIRED PASSWORD FLOW ===
        # Generate new password and reset via admin
        new_password = generate_secure_password()
        
        success, reset_msg = ad_service.admin_reset_password(username, new_password)
        
        if success:
            # Password reset successful, send email with new password
            if email_service.send_password_reset_email(email, display_name, new_password):
                log_service.log_email(username, display_name, email, sent_to, 'ADMIN_RESET', days_left, 'sent')
                log_service.log_activity('admin_password_reset', f'Password reset for {username}, email sent to {sent_to}', request.remote_addr)
                flash(f'Şifre sıfırlandı ve email gönderildi: {sent_to}', 'success')
            else:
                # Password was reset but email failed
                log_service.log_email(username, display_name, email, sent_to, 'ADMIN_RESET', days_left, 'failed', 'SMTP error')
                log_service.log_activity('admin_password_reset', f'Password reset for {username}, EMAIL FAILED', request.remote_addr)
                flash(f'Şifre sıfırlandı ama email gönderilemedi! Yeni şifre: {new_password}', 'warning')
        else:
            # Password reset failed
            log_service.log_activity('admin_password_reset_failed', f'{username}: {reset_msg}', request.remote_addr)
            flash(f'Şifre sıfırlama başarısız: {reset_msg}', 'error')
    else:
        # === NORMAL FLOW (password not expired yet) ===
        # Generate token and send warning email
        token = token_service.generate_token(username, token_validity_hours)
        reset_link = f"{passcore_url}/reset/{token}"
        
        # Format expiry date
        expire_date = datetime.utcnow() + timedelta(days=days_left if days_left else 0)
        expiry_date_str = (expire_date + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M')
        
        # Send email
        if email_service.send_password_expiry_warning(
            email, display_name, days_left or 0, expiry_date_str, reset_link
        ):
            log_service.log_email(username, display_name, email, sent_to, token, days_left or 0, 'sent')
            log_service.log_activity('manual_email', f'Sent to {username} ({sent_to})', request.remote_addr)
            flash(f'Email başarıyla gönderildi: {sent_to}', 'success')
        else:
            log_service.log_email(username, display_name, email, sent_to, token, days_left or 0, 'failed', 'SMTP error')
            flash('Email gönderilemedi!', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    """JSON API for dashboard stats (for auto-refresh)"""
    from services.log_service import LogService
    log_service = LogService()
    return jsonify(log_service.get_dashboard_stats())
