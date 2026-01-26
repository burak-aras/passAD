"""
Crypto Service - Handles RSA Encryption/Decryption
Generates ephemeral RSA keys on startup and handles decryption of client-side encrypted passwords.
"""

import logging
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Random import get_random_bytes
import base64

logger = logging.getLogger(__name__)

class CryptoService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CryptoService, cls).__new__(cls)
            cls._instance._init_keys()
        return cls._instance
    
    def _init_keys(self):
        """Generate ephemeral RSA 2048-bit key pair"""
        try:
            logger.info("Generating ephemeral RSA keys...")
            key = RSA.generate(2048)
            self.private_key = key
            self.public_key_pem = key.publickey().export_key().decode('utf-8')
            logger.info("RSA keys generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate RSA keys: {str(e)}")
            raise e
            
    def get_public_key(self):
        """Get Public Key in PEM format to send to client"""
        return self.public_key_pem
        
    def decrypt_password(self, encrypted_b64):
        """
        Decrypt a Base64 encoded RSA encrypted password
        Returns the decrypted password string or None if failed
        """
        if not encrypted_b64:
            return None
            
        try:
            # Decode Base64
            encrypted_data = base64.b64decode(encrypted_b64)
            
            # Decrypt using Private Key
            sentinel = get_random_bytes(16) # Random bytes to return on error (security best practice)
            cipher = PKCS1_v1_5.new(self.private_key)
            decrypted_data = cipher.decrypt(encrypted_data, sentinel)
            
            if decrypted_data == sentinel:
                logger.warning("Decryption failed (sentinel returned)")
                return None
                
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            return None
