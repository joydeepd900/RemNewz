import os
import json
from cryptography.fernet import Fernet, InvalidToken

class CryptoManager:
    def __init__(self):
        self.key = os.environ.get("ENCRYPTION_KEY")
        self.is_enabled = bool(self.key and self.key.strip())
        if self.is_enabled:
            try:
                self.fernet = Fernet(self.key.encode('utf-8'))
            except Exception as e:
                print(f"[crypto] Invalid ENCRYPTION_KEY format: {e}")
                self.is_enabled = False

    def encrypt_dict(self, data: list | dict) -> bytes:
        """Serialize a dict/list to JSON and encrypt it."""
        if not self.is_enabled:
            raise ValueError("Encryption is not enabled.")
        json_data = json.dumps(data).encode('utf-8')
        return self.fernet.encrypt(json_data)

    def decrypt_dict(self, cipher_data: bytes) -> list | dict:
        """Decrypt cipher data and deserialize JSON."""
        if not self.is_enabled:
            raise ValueError("Encryption is not enabled.")
        try:
            json_data = self.fernet.decrypt(cipher_data)
            return json.loads(json_data.decode('utf-8'))
        except InvalidToken:
            print("[crypto] Decryption failed! Invalid token/key.")
            return []
        except Exception as e:
            print(f"[crypto] Decryption error: {e}")
            return []
