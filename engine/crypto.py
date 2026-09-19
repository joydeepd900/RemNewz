import os
import json
from cryptography.fernet import Fernet, InvalidToken

class DecryptionError(Exception):
    pass

class CryptoManager:
    def __init__(self):
        self.key = os.environ.get("ENCRYPTION_KEY")
        self.is_enabled = bool(self.key and self.key.strip())
        if self.is_enabled:
            try:
                self.fernet = Fernet(self.key.encode('utf-8'))
            except Exception as e:
                raise RuntimeError(f"Invalid ENCRYPTION_KEY format. Failing securely. Details: {e}")

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt raw binary data."""
        if not self.is_enabled:
            raise ValueError("Encryption is not enabled.")
        return self.fernet.encrypt(data)

    def decrypt_bytes(self, cipher_data: bytes) -> bytes:
        """Decrypt raw binary data."""
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
