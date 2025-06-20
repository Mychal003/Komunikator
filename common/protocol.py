import json
import datetime
from typing import Dict, Any

# Import szyfrowania
try:
    from .encryption import default_encryption, is_encryption_available
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

class MessageType:
    """Typy wiadomości w protokole"""
    MESSAGE = "message"
    JOIN = "join"
    LEAVE = "leave"
    USER_LIST = "user_list"
    ERROR = "error"
    SYSTEM = "system"

class Protocol:
    """Klasa do obsługi protokołu komunikacji z opcjonalnym szyfrowaniem"""
    
    encryption_enabled = False
    
    @classmethod
    def enable_encryption(cls, password: str = None):
        """Włącza szyfrowanie wiadomości"""
        if ENCRYPTION_AVAILABLE:
            if password:
                default_encryption.change_password(password)
            cls.encryption_enabled = True
            print("🔒 Szyfrowanie komunikacji zostało włączone")
        else:
            print("⚠️ Szyfrowanie niedostępne - zainstaluj 'cryptography'")
    
    @classmethod
    def disable_encryption(cls):
        """Wyłącza szyfrowanie wiadomości"""
        cls.encryption_enabled = False
        print("🔓 Szyfrowanie komunikacji zostało wyłączone")
    
    @staticmethod
    def create_message(msg_type: str, user: str, content: str = "") -> str:
        """Tworzy wiadomość w formacie protokołu z opcjonalnym szyfrowaniem"""
        # Szyfruj zawartość wiadomości jeśli włączone
        if Protocol.encryption_enabled and content and ENCRYPTION_AVAILABLE:
            if msg_type == MessageType.MESSAGE:
                # Szyfruj tylko zwykłe wiadomości, nie systemowe
                content = default_encryption.encrypt(content)
        
        message = {
            "type": msg_type,
            "user": user,
            "content": content,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "encrypted": Protocol.encryption_enabled and msg_type == MessageType.MESSAGE
        }
        return json.dumps(message) + "\n"
    
    @staticmethod
    def parse_message(raw_message: str) -> Dict[str, Any]:
        """Parsuje otrzymaną wiadomość z opcjonalnym deszyfrowaniem"""
        try:
            # Usuń znak końca linii
            clean_message = raw_message.strip()
            message = json.loads(clean_message)
            
            # Sprawdź czy wiadomość jest zaszyfrowana
            if message.get('encrypted', False) and Protocol.encryption_enabled and ENCRYPTION_AVAILABLE:
                if message.get('content'):
                    # Deszyfruj zawartość
                    message['content'] = default_encryption.decrypt(message['content'])
            
            return message
            
        except json.JSONDecodeError:
            return {
                "type": MessageType.ERROR,
                "user": "system",
                "content": "Błąd parsowania wiadomości",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "encrypted": False
            }
        except Exception as e:
            return {
                "type": MessageType.ERROR,
                "user": "system", 
                "content": f"Błąd przetwarzania wiadomości: {str(e)}",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "encrypted": False
            }
    
    @staticmethod
    def create_user_list_message(users: list) -> str:
        """Tworzy wiadomość z listą użytkowników"""
        return Protocol.create_message(
            MessageType.USER_LIST, 
            "system", 
            json.dumps(users)
        )
    
    @staticmethod
    def create_system_message(content: str) -> str:
        """Tworzy wiadomość systemową (nigdy nie szyfrowaną)"""
        message = {
            "type": MessageType.SYSTEM,
            "user": "system",
            "content": content,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "encrypted": False  # Wiadomości systemowe nigdy nie są szyfrowane
        }
        return json.dumps(message) + "\n"