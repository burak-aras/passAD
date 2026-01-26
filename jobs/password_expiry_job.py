"""
Password Expiry Job - Checks AD and sends warning emails
Scheduled job to notify users about expiring passwords
"""

import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ad_service import ADService
from services.email_service import EmailService
from services.token_service import TokenService
from services.log_service import LogService
from datetime import timedelta

# Logging setup
LOG_DIR = os.getenv('LOG_DIR', '/app/data')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'password_expiry_job.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_password_expiry_check():
    """Main function to check AD and send emails"""
    logger.info("=" * 80)
    logger.info("STARTING PASSWORD EXPIRATION CHECK")
    logger.info("=" * 80)
    
    # Configuration
    warning_start = int(os.getenv('WARNING_START', '0'))
    warning_end = int(os.getenv('WARNING_END', '7'))
    passcore_url = os.getenv('PASSCORE_URL', 'http://localhost')
    token_validity_hours = int(os.getenv('TOKEN_VALIDITY_HOURS', '24'))
    
    # Initialize services
    ad_service = ADService()
    email_service = EmailService()
    token_service = TokenService()
    log_service = LogService()
    
    # Log job start
    log_service.log_activity('job_started', f'Warning period: {warning_start}-{warning_end} days')
    
    # Get users with expiring passwords
    users = ad_service.get_users_with_expiring_passwords(warning_start, warning_end)
    
    if not users:
        logger.info("No users found with expiring passwords")
        log_service.log_activity('job_completed', 'No users found')
        logger.info("=" * 80)
        return
    
    logger.info(f"Found {len(users)} users with passwords expiring in {warning_start}-{warning_end} days")
    logger.info("-" * 80)
    
    count_sent = 0
    count_failed = 0
    count_no_email = 0
    
    # Get test recipient for logging
    test_recipient = os.getenv('TEST_RECIPIENT', '')
    
    for user in users:
        username = user['username']
        display_name = user['display_name']
        email = user['email']
        days_left = user['days_left']
        expire_date = user['expire_date']
        
        # Format expiry date (Turkey timezone +3)
        expiry_date_str = (expire_date + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M')
        
        log_msg = f"User: {display_name:30} | Days left: {days_left:2}"
        
        if email:
            # Generate token
            token = token_service.generate_token(username, token_validity_hours)
            reset_link = f"{passcore_url}/reset/{token}"
            
            # Determine where email goes
            sent_to = test_recipient if test_recipient else email
            
            # Send email
            if email_service.send_password_expiry_warning(
                email, display_name, days_left, expiry_date_str, reset_link
            ):
                logger.info(f"✓ {log_msg}")
                # Log to database
                log_service.log_email(username, display_name, email, sent_to, token, days_left, 'sent')
                count_sent += 1
            else:
                logger.error(f"✗ {log_msg} -> FAILED")
                # Log failure
                log_service.log_email(username, display_name, email, sent_to, token, days_left, 'failed', 'SMTP error')
                count_failed += 1
        else:
            logger.warning(f"⚠ {log_msg} -> NO EMAIL")
            count_no_email += 1
    
    # Cleanup old tokens and logs
    tokens_deleted = token_service.cleanup_expired_tokens()
    logs_deleted = log_service.cleanup_old_logs()
    
    if tokens_deleted > 0:
        logger.info(f"Cleaned up {tokens_deleted} expired tokens")
    if logs_deleted > 0:
        logger.info(f"Cleaned up {logs_deleted} old log entries")
    
    # Log job completion
    log_service.log_activity('job_completed', f'Sent={count_sent}, Failed={count_failed}, No Email={count_no_email}')
    
    logger.info("-" * 80)
    logger.info(f"SUMMARY: Sent={count_sent}, Failed={count_failed}, No Email={count_no_email}")
    logger.info("=" * 80)


if __name__ == "__main__":
    run_password_expiry_check()
