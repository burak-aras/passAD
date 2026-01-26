"""
Email Service - SMTP Email Sending
Handles email composition and sending via SMTP
"""

import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class EmailService:
    """Handles email sending operations"""
    
    def __init__(self):
        """Initialize email service with configuration"""
        self.smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', '25'))
        self.sender_email = os.getenv('SENDER_EMAIL', 'noreply@example.com')
        self.test_recipient = os.getenv('TEST_RECIPIENT', '')
        
        # Template directory
        self.template_dir = os.path.dirname(os.path.abspath(__file__))
        
        logger.info(f"EmailService initialized: {self.smtp_server}:{self.smtp_port}")
        if self.test_recipient:
            logger.warning(f"TEST MODE: All emails will be sent to {self.test_recipient}")
    
    def load_template(self, template_name='email_template.html'):
        """Load HTML email template"""
        # Check multiple possible locations
        possible_paths = [
            os.path.join(self.template_dir, '..', 'templates', 'emails', template_name),
            os.path.join(self.template_dir, '..', 'email_service', template_name),
            os.path.join('/app', 'templates', 'emails', template_name),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        logger.error(f"Email template not found: {template_name}")
        return None
    
    def send_password_expiry_warning(self, real_email, display_name, days_left, expiry_date, reset_link):
        """
        Send password expiration warning email
        
        Args:
            real_email: User's actual email address
            display_name: User's display name
            days_left: Days until password expires
            expiry_date: Password expiration date string
            reset_link: Password reset link with token
            
        Returns:
            bool: True if email sent successfully
        """
        # Determine recipient (test mode or real)
        recipient = self.test_recipient if self.test_recipient else real_email
        
        subject = f"UYARI: Parola Süreniz Dolmak Üzere ({days_left} Gün Kaldı)"
        
        # Load template
        html_template = self.load_template()
        if not html_template:
            return False
        
        # Test mode warning
        test_warning_html = ""
        if real_email != recipient:
            test_warning_html = f'''
            <div class="test-warning">
                <strong>⚠️ [TEST MODU]</strong> Bu mail normalde <strong>{real_email}</strong> adresine gidecekti.
            </div>
            '''
        
        # Replace placeholders
        html_content = html_template.replace('{{TEST_WARNING}}', test_warning_html)
        html_content = html_content.replace('{{DISPLAY_NAME}}', display_name)
        html_content = html_content.replace('{{EXPIRY_DATE}}', expiry_date)
        html_content = html_content.replace('{{DAYS_LEFT}}', str(days_left))
        html_content = html_content.replace('{{RESET_LINK}}', reset_link)
        
        # Build email
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.sendmail(self.sender_email, recipient, msg.as_string())
            logger.info(f"Email sent to {recipient} (original: {real_email})")
            return True
        except Exception as e:
            logger.error(f"Email send error ({recipient}): {e}")
            return False
    
    def send_password_reset_email(self, real_email, display_name, new_password):
        """
        Send password reset email with new password (for expired users)
        
        Args:
            real_email: User's actual email address
            display_name: User's display name
            new_password: The new password to send
            
        Returns:
            bool: True if email sent successfully
        """
        # Determine recipient (test mode or real)
        recipient = self.test_recipient if self.test_recipient else real_email
        
        subject = "Parolanız Sıfırlandı - Yeni Şifreniz"
        
        # Load password reset template
        html_template = self.load_template('password_reset_template.html')
        if not html_template:
            # Fallback to inline template if file not found
            html_template = self._get_password_reset_template()
        
        # Test mode warning
        test_warning_html = ""
        if real_email != recipient:
            test_warning_html = f'''
            <div class="test-warning">
                <strong>⚠️ [TEST MODU]</strong> Bu mail normalde <strong>{real_email}</strong> adresine gidecekti.
            </div>
            '''
        
        # Replace placeholders
        html_content = html_template.replace('{{TEST_WARNING}}', test_warning_html)
        html_content = html_content.replace('{{DISPLAY_NAME}}', display_name)
        html_content = html_content.replace('{{NEW_PASSWORD}}', new_password)
        
        # Build email
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.sendmail(self.sender_email, recipient, msg.as_string())
            logger.info(f"Password reset email sent to {recipient} (original: {real_email})")
            return True
        except Exception as e:
            logger.error(f"Password reset email send error ({recipient}): {e}")
            return False
    
    def _get_password_reset_template(self):
        """Fallback inline template for password reset emails"""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Şifre Yönetimi{% endblock %}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f5f5f5; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #dc3545; color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }
        .content { background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; }
        .password-box { background: #f8f9fa; border: 2px solid #dc3545; padding: 20px; margin: 20px 0; text-align: center; border-radius: 5px; }
        .password { font-size: 24px; font-weight: bold; color: #dc3545; letter-spacing: 2px; font-family: monospace; }
        .warning-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; color: #856404; }
        .test-warning { background-color: #fff3cd; color: #856404; padding: 15px; border: 1px solid #ffc107; border-radius: 5px; margin-bottom: 20px; }
        .footer { background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px; text-align: center; font-size: 12px; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        {{TEST_WARNING}}
        <div class="header">
            <h2>🔑 Parolanız Sıfırlandı</h2>
        </div>
        <div class="content">
            <p>Sayın <strong>{{DISPLAY_NAME}}</strong>,</p>
            <p>Şifrenizin süresi dolduğu için sistem yöneticisi tarafından parolanız sıfırlanmıştır.</p>
            <div class="password-box">
                <p><strong>Yeni Şifreniz:</strong></p>
                <p class="password">{{NEW_PASSWORD}}</p>
            </div>
            <div class="warning-box">
                <strong>⚠️ Önemli:</strong><br>
                • İlk girişinizde bu şifreyi değiştirmeniz önerilir.<br>
                • Bu şifreyi kimseyle paylaşmayın.<br>
                • Bu email'i okuduktan sonra silin.
            </div>
        </div>
        <div class="footer">
            <p><strong>IT Department</strong></p>
            <p>Bu otomatik bir mesajdır, lütfen yanıtlamayın.</p>
        </div>
    </div>
</body>
</html>'''
