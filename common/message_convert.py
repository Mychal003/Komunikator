#!/usr/bin/env python3
"""
Konwerter wiadomości między protokołem TCP a WebSocket
"""

import json
from typing import Dict, Any
from common.protocol import MessageType

class MessageConverter:
    """Konwertuje wiadomości między formatami TCP i WebSocket"""
    
    @staticmethod
    def tcp_to_websocket(tcp_message: Dict[str, Any]) -> Dict[str, Any]:
        """Konwertuje wiadomość TCP na format WebSocket"""
        msg_type = tcp_message.get('type', '')
        user = tcp_message.get('user', '')
        content = tcp_message.get('content', '')
        timestamp = tcp_message.get('timestamp', '')
        encrypted = tcp_message.get('encrypted', False)
        
        if msg_type == MessageType.MESSAGE:
            return {
                'type': 'message',
                'author': user,
                'content': content,
                'timestamp': timestamp,
                'encrypted': encrypted
            }
            
        elif msg_type == MessageType.SYSTEM:
            return {
                'type': 'system_message',
                'content': content,
                'timestamp': timestamp
            }
            
        elif msg_type == MessageType.USER_LIST:
            try:
                users = json.loads(content)
                return {
                    'type': 'users_list',
                    'users': users
                }
            except:
                return {
                    'type': 'system_message',
                    'content': 'Błąd parsowania listy użytkowników'
                }
                
        elif msg_type == MessageType.ERROR:
            return {
                'type': 'error',
                'message': content
            }
            
        else:
            return {
                'type': 'unknown',
                'content': content
            }
    
    @staticmethod
    def websocket_to_tcp(ws_message: Dict[str, Any], nick: str) -> str:
        """Konwertuje wiadomość WebSocket na format TCP"""
        msg_type = ws_message.get('type', '')
        
        if msg_type == 'connect':
            # To obsługujemy osobno w bridge
            return None
            
        elif msg_type == 'disconnect':
            from common.protocol import Protocol
            return Protocol.create_message(MessageType.LEAVE, nick)
            
        elif msg_type == 'message':
            from common.protocol import Protocol
            content = ws_message.get('content', '')
            return Protocol.create_message(MessageType.MESSAGE, nick, content)
            
        return None