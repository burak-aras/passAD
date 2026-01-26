"""
AD Service - Active Directory Operations
Handles LDAP authentication, password changes, and user queries
"""

from ldap3 import Server, Connection, ALL, Tls, extend, MODIFY_REPLACE
from ldap3.core.exceptions import LDAPException
from datetime import datetime, timedelta
import logging
import ssl
import os
import secrets
import string

logger = logging.getLogger(__name__)


def generate_secure_password(length=12):
    """
    Generate a secure random password meeting AD complexity requirements
    
    Returns:
        str: A secure password with at least 1 uppercase, 1 lowercase, 1 digit, 1 special char
    """
    # Character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*()_+-="
    
    # Ensure at least one of each required type
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Fill the rest with random characters from all sets
    all_chars = uppercase + lowercase + digits + special
    password.extend(secrets.choice(all_chars) for _ in range(length - 4))
    
    # Shuffle the password
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)
    
    return ''.join(password_list)


class ADService:
    """Manages Active Directory operations"""
    
    def __init__(self):
        """Initialize AD service with configuration"""
        self.server_address = os.getenv('AD_SERVER', '192.168.1.100')
        self.domain = os.getenv('AD_DOMAIN', 'example.local')
        self.base_dn = os.getenv('AD_BASE_DN', 'DC=example,DC=local')
        self.use_ssl = os.getenv('AD_USE_SSL', 'False').lower() == 'true'
        self.port = 636 if self.use_ssl else 389
        
        # Service account for queries (optional)
        self.service_user = os.getenv('AD_USER', '')
        self.service_password = os.getenv('AD_PASSWORD', '')
        
        # Password policy
        self.password_min_length = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
        
        self.server = Server(
            self.server_address,
            port=self.port,
            use_ssl=self.use_ssl,
            get_info=ALL
        )
        
        logger.info(f"ADService initialized: {self.server_address}:{self.port}")
    
    def authenticate_user(self, username, password):
        """
        Authenticate user against Active Directory
        
        Args:
            username: Username (without domain)
            password: User's password
            
        Returns:
            tuple: (success: bool, message: str, user_dn: str or None)
        """
        try:
            user_format = f"{username}@{self.domain}"
            logger.info(f"Authenticating: {user_format}")
            
            conn = Connection(
                self.server,
                user=user_format,
                password=password,
                auto_bind=True
            )
            
            # Get user DN
            search_filter = f"(sAMAccountName={username})"
            conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                attributes=['distinguishedName', 'cn']
            )
            
            if conn.entries:
                user_dn = str(conn.entries[0].distinguishedName)
                user_cn = str(conn.entries[0].cn)
                conn.unbind()
                logger.info(f"User {username} authenticated successfully")
                return True, f"Hoş geldiniz, {user_cn}!", user_dn
            else:
                conn.unbind()
                return False, "Kullanıcı dizinde bulunamadı!", None
                
        except Exception as e:
            logger.error(f"Authentication failed for {username}: {str(e)}")
            return False, "Kullanıcı adı veya şifre hatalı!", None
    
    def change_password(self, username, old_password, new_password):
        """
        Change user password in Active Directory
        
        Args:
            username: Username
            old_password: Current password
            new_password: New password
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # First authenticate
            success, message, user_dn = self.authenticate_user(username, old_password)
            if not success:
                return False, "Mevcut şifreniz hatalı!"
            
            # Validate new password
            is_valid, validation_msg = self.validate_password(new_password)
            if not is_valid:
                return False, validation_msg
            
            user_format = f"{username}@{self.domain}"
            
            # Create TLS configuration
            tls = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
            
            if self.use_ssl:
                ssl_server = Server(
                    self.server_address,
                    port=636,
                    use_ssl=True,
                    tls=tls,
                    get_info=ALL
                )
                conn = Connection(
                    ssl_server,
                    user=user_format,
                    password=old_password,
                    auto_bind=True
                )
            else:
                # Use StartTLS
                starttls_server = Server(
                    self.server_address,
                    port=389,
                    use_ssl=False,
                    tls=tls,
                    get_info=ALL
                )
                conn = Connection(
                    starttls_server,
                    user=user_format,
                    password=old_password
                )
                
                conn.open()
                if not conn.start_tls():
                    return False, "Güvenli bağlantı kurulamadı."
                if not conn.bind():
                    return False, "Kimlik doğrulama başarısız oldu."
            
            # Change password using AD extended operation
            result = extend.microsoft.modifyPassword.ad_modify_password(
                conn,
                user_dn,
                new_password,
                old_password
            )
            
            # Log detailed result
            logger.info(f"Password change result: {result}")
            logger.info(f"Connection result: {conn.result}")
            
            conn.unbind()
            
            if result:
                logger.info(f"Password changed successfully for: {username}")
                return True, "Şifreniz başarıyla değiştirildi!"
            else:
                # Get detailed error from AD
                error_detail = conn.result if hasattr(conn, 'result') else {}
                error_desc = error_detail.get('description', 'Bilinmeyen hata')
                error_msg = error_detail.get('message', '')
                
                logger.error(f"Password change failed for {username}: {error_detail}")
                
                # Parse Windows error codes
                if '0000052D' in str(error_msg):
                    return False, "Şifre geçmiş politikasına uymuyor. Daha önce kullanılmamış bir şifre seçin."
                elif '00000524' in str(error_msg):
                    return False, "Şifre minimum uzunluk gereksinimini karşılamıyor."
                elif '00000525' in str(error_msg):
                    return False, "Kullanıcı bulunamadı."
                elif 'constraintViolation' in str(error_detail):
                    return False, "Şifre politika gereksinimlerini karşılamıyor (karmaşıklık veya geçmiş)."
                else:
                    return False, f"Şifre değiştirme başarısız: {error_desc}"
                
        except Exception as e:
            logger.error(f"Password change error: {str(e)}")
            error_msg = str(e)
            
            # Detailed error parsing
            if 'constraintViolation' in error_msg:
                if '0000052D' in error_msg:
                    return False, "Şifre geçmiş politikasına uymuyor. Daha önce kullanılmamış bir şifre seçin."
                return False, "Yeni şifre politika gereksinimlerini karşılamıyor."
            elif 'unwillingToPerform' in error_msg:
                return False, "AD şifre değiştirmeyi reddetti. SSL/TLS bağlantısı gerekebilir."
            elif 'strongAuthRequired' in error_msg:
                return False, "Güçlü kimlik doğrulama gerekli. LDAPS kullanılmalı."
            
            return False, f"Şifre değiştirme hatası: {error_msg}"
    
    def validate_password(self, password):
        """Validate password against policy"""
        if len(password) < self.password_min_length:
            return False, f"Şifre en az {self.password_min_length} karakter olmalıdır!"
        
        if not any(c.isupper() for c in password):
            return False, "Şifre en az bir büyük harf içermelidir!"
        
        if not any(c.islower() for c in password):
            return False, "Şifre en az bir küçük harf içermelidir!"
        
        if not any(c.isdigit() for c in password):
            return False, "Şifre en az bir rakam içermelidir!"
        
        return True, "Şifre geçerli"
    
    def admin_reset_password(self, username, new_password):
        """
        Reset a user's password using admin/service account credentials
        Used for expired password scenarios where user cannot authenticate
        
        Args:
            username: Target username (without domain)
            new_password: New password to set
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.service_user or not self.service_password:
            logger.error("Service account not configured for admin reset")
            return False, "Service account yapılandırılmamış!"
        
        try:
            # Create TLS configuration
            tls = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
            
            if self.use_ssl:
                # Use LDAPS (port 636)
                ssl_server = Server(
                    self.server_address,
                    port=636,
                    use_ssl=True,
                    tls=tls,
                    get_info=ALL
                )
                conn = Connection(
                    ssl_server,
                    user=self.service_user,
                    password=self.service_password,
                    auto_bind=True
                )
            else:
                # Use StartTLS (port 389)
                starttls_server = Server(
                    self.server_address,
                    port=389,
                    use_ssl=False,
                    tls=tls,
                    get_info=ALL
                )
                conn = Connection(
                    starttls_server,
                    user=self.service_user,
                    password=self.service_password
                )
                
                conn.open()
                if not conn.start_tls():
                    return False, "Güvenli bağlantı kurulamadı."
                if not conn.bind():
                    return False, "Service account kimlik doğrulama başarısız."
            
            logger.info(f"Admin connected for password reset: {username}")
            
            # Find user DN
            search_filter = f"(sAMAccountName={username})"
            conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                attributes=['distinguishedName']
            )
            
            if not conn.entries:
                conn.unbind()
                return False, f"Kullanıcı bulunamadı: {username}"
            
            user_dn = str(conn.entries[0].distinguishedName)
            logger.info(f"Found user DN: {user_dn}")
            
            # Encode password for AD (Unicode with quotes)
            encoded_password = ('"%s"' % new_password).encode('utf-16-le')
            
            # Reset password using modify operation
            conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded_password])]})
            
            if conn.result['result'] == 0:
                logger.info(f"Admin password reset successful for: {username}")
                conn.unbind()
                return True, "Şifre başarıyla sıfırlandı!"
            else:
                error_detail = conn.result
                error_desc = error_detail.get('description', 'Bilinmeyen hata')
                error_msg = error_detail.get('message', '')
                
                logger.error(f"Admin password reset failed for {username}: {error_detail}")
                conn.unbind()
                
                # Parse Windows error codes
                if 'insufficientAccessRights' in str(error_detail):
                    return False, "Yetki hatası! Service account'a Domain Admin yetkisi verilmeli."
                elif '0000052D' in str(error_msg):
                    return False, "Şifre geçmiş politikasına uymuyor."
                elif 'constraintViolation' in str(error_detail):
                    return False, "Şifre politika gereksinimlerini karşılamıyor."
                else:
                    return False, f"Şifre sıfırlama başarısız: {error_desc}"
                    
        except Exception as e:
            logger.error(f"Admin password reset error: {str(e)}")
            error_msg = str(e)
            
            if 'insufficientAccessRights' in error_msg:
                return False, "Yetki hatası! Service account'a Domain Admin yetkisi verilmeli."
            elif 'unwillingToPerform' in error_msg:
                return False, "AD şifre sıfırlamayı reddetti. SSL/TLS bağlantısı gerekebilir."
            
            return False, f"Şifre sıfırlama hatası: {error_msg}"

    
    def get_users_with_expiring_passwords(self, warning_start=0, warning_end=7):
        """
        Get users whose passwords are about to expire
        
        Args:
            warning_start: Minimum days until expiry
            warning_end: Maximum days until expiry
            
        Returns:
            list: List of user dicts with password expiry info
        """
        if not self.service_user or not self.service_password:
            logger.error("Service account not configured")
            return []
        
        try:
            conn = Connection(
                self.server,
                user=self.service_user,
                password=self.service_password,
                auto_bind=True
            )
            logger.info(f"Connected to AD: {self.server_address}")
            
            # Get password policy
            conn.search(
                search_base=self.base_dn,
                search_filter='(objectClass=domainDNS)',
                attributes=['maxPwdAge']
            )
            
            val = conn.entries[0].maxPwdAge.value
            if isinstance(val, timedelta):
                max_age_days = abs(val.days)
            else:
                max_age_days = int(abs(val) / (10000000 * 86400))
            
            logger.info(f"Password policy: {max_age_days} days")
            
            # Search for active users
            search_filter = '(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2))(!(userAccountControl:1.2.840.113556.1.4.803:=65536)))'
            conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                attributes=['sAMAccountName', 'displayName', 'mail', 'pwdLastSet'],
                paged_size=1000
            )
            
            users = []
            for entry in conn.entries:
                pwd_last_set = entry.pwdLastSet.value
                if not pwd_last_set or pwd_last_set == 0:
                    continue
                
                # Convert to datetime
                if isinstance(pwd_last_set, datetime):
                    last_set_date = pwd_last_set.replace(tzinfo=None)
                else:
                    us = pwd_last_set / 10
                    last_set_date = datetime(1601, 1, 1) + timedelta(microseconds=us)
                
                expire_date = last_set_date + timedelta(days=max_age_days)
                days_left = (expire_date - datetime.utcnow()).days
                
                if warning_start <= days_left <= warning_end:
                    users.append({
                        'username': str(entry.sAMAccountName.value),
                        'display_name': str(entry.displayName.value) if entry.displayName else str(entry.sAMAccountName.value),
                        'email': str(entry.mail.value) if entry.mail else None,
                        'days_left': days_left,
                        'expire_date': expire_date
                    })
            
            conn.unbind()
            logger.info(f"Found {len(users)} users with expiring passwords")
            return users
            
        except Exception as e:
            logger.error(f"AD query error: {str(e)}")
            return []
    
    def get_all_users(self):
        """
        Get all users from AD with password expiry information
        
        Returns:
            tuple: (users: list, max_age_days: int)
        """
        if not self.service_user or not self.service_password:
            logger.error("Service account not configured")
            return [], 0
        
        try:
            conn = Connection(
                self.server,
                user=self.service_user,
                password=self.service_password,
                auto_bind=True
            )
            logger.info(f"Connected to AD: {self.server_address}")
            
            # Get password policy
            conn.search(
                search_base=self.base_dn,
                search_filter='(objectClass=domainDNS)',
                attributes=['maxPwdAge']
            )
            
            val = conn.entries[0].maxPwdAge.value
            if isinstance(val, timedelta):
                max_age_days = abs(val.days)
            else:
                max_age_days = int(abs(val) / (10000000 * 86400))
            
            # Search for active users
            search_filter = '(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2))(!(userAccountControl:1.2.840.113556.1.4.803:=65536)))'
            conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                attributes=['sAMAccountName', 'displayName', 'mail', 'pwdLastSet', 'department'],
                paged_size=1000
            )
            
            users = []
            for entry in conn.entries:
                pwd_last_set = entry.pwdLastSet.value
                
                # Calculate expiry
                if pwd_last_set and pwd_last_set != 0:
                    if isinstance(pwd_last_set, datetime):
                        last_set_date = pwd_last_set.replace(tzinfo=None)
                    else:
                        us = pwd_last_set / 10
                        last_set_date = datetime(1601, 1, 1) + timedelta(microseconds=us)
                    
                    expire_date = last_set_date + timedelta(days=max_age_days)
                    days_left = (expire_date - datetime.utcnow()).days
                else:
                    expire_date = None
                    days_left = None
                
                users.append({
                    'username': str(entry.sAMAccountName.value),
                    'display_name': str(entry.displayName.value) if entry.displayName else str(entry.sAMAccountName.value),
                    'email': str(entry.mail.value) if entry.mail else None,
                    'department': str(entry.department.value) if entry.department else None,
                    'days_left': days_left,
                    'expire_date': expire_date,
                    'last_set': last_set_date if pwd_last_set else None
                })
            
            conn.unbind()
            
            # Sort by days_left (None values at end)
            users.sort(key=lambda x: (x['days_left'] is None, x['days_left'] if x['days_left'] is not None else 9999))
            
            logger.info(f"Found {len(users)} total users")
            return users, max_age_days
            
        except Exception as e:
            logger.error(f"AD query error: {str(e)}")
            return [], 0
