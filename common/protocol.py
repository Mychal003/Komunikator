import json
import datetime
from typing import Dict, Any

class MessageType:
    """Typy wiadomości w protokole"""
    MESSAGE = "message"
    JOIN = "join"
    LEAVE = "leave"
    USER_LIST = "user_list"
    ERROR = "error"
    SYSTEM = "system"

class Protocol:
    """Klasa do obsługi protokołu komunikacji"""
    
    @staticmethod
    def create_message(msg_type: str, user: str, content: str = "") -> str:
        """Tworzy wiadomość w formacie protokołu"""
        message = {
            "type": msg_type,
            "user": user,
            "content": content,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return json.dumps(message) + "\n"
    
    @staticmethod
    def parse_message(raw_message: str) -> Dict[str, Any]:
        """Parsuje otrzymaną wiadomość"""
        try:
            # Usuń znak końca linii
            clean_message = raw_message.strip()
            return json.loads(clean_message)
        except json.JSONDecodeError:
            return {
                "type": MessageType.ERROR,
                "user": "system",
                "content": "Błąd parsowania wiadomości",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        """Tworzy wiadomość systemową"""
        return Protocol.create_message(MessageType.SYSTEM, "system", content)