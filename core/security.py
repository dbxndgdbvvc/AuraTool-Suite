import hashlib
import os

class SecurityManager:
    """Provides cryptographic utilities for local data protection and integrity verification."""
    
    @staticmethod
    def hash_data(data: str) -> str:
        """Returns SHA-256 hash of given string data."""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_token() -> str:
        """Generates a secure random token."""
        return os.urandom(24).hex()
