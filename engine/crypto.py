import os
import json
from cryptography.fernet import Fernet, InvalidToken

class DecryptionError(Exception):
    """Exception raised when decryption fails due to invalid tokens, keys, or corruption."""
    pass

class CryptoManager:
    """
    Handles symmetric encryption and decryption operations using Fernet (AES-128-CBC).
    
    This manager fails securely. If an encryption key is provided but invalid, it raises
    a runtime error to prevent data loss or silent fallback to plaintext. If no key is
    provided, encryption is disabled.
    """
    def __init__(self):
        self.key = os.environ.get("ENCRYPTION_KEY")
        self.is_enabled = bool(self.key and self.key.strip())
        if self.is_enabled:
            try:
                self.fernet = Fernet(self.key.encode('utf-8'))
            except Exception as e:
                raise RuntimeError(f"Invalid ENCRYPTION_KEY format. Failing securely. Details: {e}")

    def encrypt_bytes(self, data: bytes) -> bytes:
        """
        Encrypt raw binary data using the Fernet symmetric key.
        
        Args:
            data (bytes): The plaintext binary data.
            
        Returns:
            bytes: The encrypted ciphertext binary data.
            
        Raises:
            ValueError: If encryption is not enabled.
        """
        if not self.is_enabled:
            raise ValueError("Encryption is not enabled.")
        return self.fernet.encrypt(data)

    def decrypt_bytes(self, cipher_data: bytes) -> bytes:
        """
        Decrypt ciphertext binary data using the Fernet symmetric key.
        
        Args:
            cipher_data (bytes): The encrypted binary data.
            
        Returns:
            bytes: The decrypted plaintext binary data.
            
        Raises:
            ValueError: If encryption is not enabled.
            DecryptionError: If the token is invalid or data is corrupted.
        """
        if not self.is_enabled:
            raise ValueError("Encryption is not enabled.")
        try:
            return self.fernet.decrypt(cipher_data)
        except InvalidToken:
            raise DecryptionError("Decryption failed! Invalid token/key.")
        except Exception as e:
            raise DecryptionError(f"Decryption error: {e}")

    def encrypt_dict(self, data: list | dict) -> bytes:
        """Serialize a dict/list to JSON and encrypt it."""
        json_data = json.dumps(data).encode('utf-8')
        return self.encrypt_bytes(json_data)

    def decrypt_dict(self, cipher_data: bytes) -> list | dict:
        """Decrypt cipher data and deserialize JSON."""
        json_data = self.decrypt_bytes(cipher_data)
        return json.loads(json_data.decode('utf-8'))
