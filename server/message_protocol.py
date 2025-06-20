#!/usr/bin/env python3
"""
Protokół wiadomości serwera
"""

import json

class MessageProtocol:
    @staticmethod
    def encode_message(message_type, data):
        """Koduje wiadomość do wysłania"""
        message = {
            'type': message_type,
            'data': data
        }
        return json.dumps(message).encode('utf-8')
    
    @staticmethod
    def decode_message(raw_data):
        """Dekoduje otrzymaną wiadomość"""
        try:
            message = json.loads(raw_data.decode('utf-8'))
            return message['type'], message['data']
        except:
            return None, None
