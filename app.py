"""
PassCore - Active Directory Password Reset Web Application
Token-based password reset system with admin panel
"""

from flask import Flask, render_template, request, flash
from services.token_service import TokenService
from services.ad_service import ADService
from services.log_service import LogService
from admin import admin_bp
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', '645eaed8083d9e4a2416d253cde78a0c6186379f5ebd4ab3aade65a00656cf8a')

# Register admin blueprint
app.register_blueprint(admin_bp)

# Initialize services
token_service = TokenService()
ad_service = ADService()
log_service = LogService()


@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    """Token-based password reset - username is pre-filled and readonly"""
    
    # Validate token
    valid, username, message = token_service.validate_token(token)
    
    if not valid:
        flash(message, 'error')
        logger.warning(f"Invalid token access attempt: {token[:10]}...")
        return render_template('error.html', message=message), 403
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        ip_address = request.remote_addr
        
        # Validation
        if not all([current_password, new_password, confirm_password]):
            flash('Tüm alanları doldurun!', 'error')
            return render_template('reset.html', username=username, token=token)
        
        if new_password != confirm_password:
            flash('Yeni şifreler eşleşmiyor!', 'error')
            return render_template('reset.html', username=username, token=token)
        
        if current_password == new_password:
            flash('Yeni şifre mevcut şifre ile aynı olamaz!', 'error')
            return render_template('reset.html', username=username, token=token)
        
        # Change password
        success, msg = ad_service.change_password(
            username,
            current_password,
            new_password
        )
        
        if success:
            token_service.mark_token_used(token)
            # Log successful password change
            log_service.log_password_change(username, token, 'success', None, ip_address)
            flash(msg, 'success')
            logger.info(f"Password changed successfully for user: {username}")
            return render_template('success.html', username=username)
        else:
            # Log failed password change
            log_service.log_password_change(username, token, 'failed', msg, ip_address)
            flash(msg, 'error')
            logger.warning(f"Password change failed for user: {username}")
            return render_template('reset.html', username=username, token=token)
    
    # GET request - show form
    logger.info(f"Token-based reset form displayed for user: {username}")
    return render_template('reset.html', username=username, token=token)


@app.route('/health')
def health_check():
    """Health check endpoint for Docker"""
    return {'status': 'healthy'}, 200


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('error.html', message='Sayfa bulunamadı'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', message='Sunucu hatası oluştu'), 500


if __name__ == '__main__':
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', 80))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting PassCore on {host}:{port}")
    logger.info(f"Admin panel available at /admin")
    app.run(host=host, port=port, debug=debug)
