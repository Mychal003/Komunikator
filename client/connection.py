#!/usr/bin/env python3
"""
Zarządzanie połączeniem klienta
"""

import socket
import threading

class Connection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        
    def connect(self):
        """Nawiązuje połączenie z serwerem"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            print(f"Błąd połączenia: {e}")
            return False
            
    def send(self, data):
        """Wysyła dane do serwera"""
        if self.connected and self.socket:
            try:
                self.socket.send(data.encode('utf-8'))
                return True
            except:
                return False
        return False
        
    def receive(self):
        """Odbiera dane z serwera"""
        if self.connected and self.socket:
            try:
                return self.socket.recv(1024).decode('utf-8')
            except:
                return None
        return None
        
    def close(self):
        """Zamyka połączenie"""
        if self.socket:
            self.socket.close()
        self.connected = False
