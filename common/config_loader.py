#!/usr/bin/env python3
"""
Ładowanie i zarządzanie konfiguracją aplikacji
"""

import configparser
import os
from typing import Dict, Any

class ConfigLoader:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.defaults = self._get_defaults()
        self.load_config()
    
    def _get_defaults(self) -> Dict[str, Dict[str, Any]]:
        """Zwraca domyślne ustawienia konfiguracji"""
        return {
            'SERVER': {
                'host': 'localhost',
                'port': 12345,
                'max_clients': 50,
                'timeout': 60
            },
            'LOGGING': {
                'log_level': 'INFO',
                'log_file': 'server.log',
                'log_to_console': True,
                'log_to_file': True
            },
            'SECURITY': {
                'max_message_length': 500,
                'max_nick_length': 20,
                'min_nick_length': 2,
                'allowed_nick_chars': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
            },
            'FEATURES': {
                'enable_user_list': True,
                'enable_ping_pong': True,
                'enable_timestamps': True,
                'welcome_message': 'Witaj w komunikatorze IP!',
                'max_login_attempts': 3
            },
            'PERFORMANCE': {
                'buffer_size': 1024,
                'stats_interval': 300,
                'cleanup_interval': 60
            }
        }
    
    def load_config(self):
        """Ładuje konfigurację z pliku"""
        # Załaduj domyślne wartości
        for section, values in self.defaults.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
            
            for key, value in values.items():
                self.config.set(section, key, str(value))
        
        # Jeśli plik konfiguracji istnieje, załaduj go
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding='utf-8')
                print(f"✅ Załadowano konfigurację z {self.config_file}")
            except Exception as e:
                print(f"⚠️ Błąd ładowania konfiguracji z {self.config_file}: {e}")
                print("Używam domyślnych ustawień")
        else:
            print(f"⚠️ Plik {self.config_file} nie istnieje, używam domyślnych ustawień")
            self.create_default_config()
    
    def create_default_config(self):
        """Tworzy domyślny plik konfiguracji"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            print(f"✅ Utworzono domyślny plik konfiguracji: {self.config_file}")
        except Exception as e:
            print(f"❌ Nie można utworzyć pliku konfiguracji: {e}")
    
    def get(self, section: str, key: str, fallback=None):
        """Pobiera wartość z konfiguracji"""
        try:
            return self.config.get(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def getint(self, section: str, key: str, fallback=0):
        """Pobiera wartość liczbową z konfiguracji"""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getboolean(self, section: str, key: str, fallback=False):
        """Pobiera wartość boolean z konfiguracji"""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getfloat(self, section: str, key: str, fallback=0.0):
        """Pobiera wartość float z konfiguracji"""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def set(self, section: str, key: str, value):
        """Ustawia wartość w konfiguracji"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
    
    def save_config(self):
        """Zapisuje konfigurację do pliku"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            return True
        except Exception as e:
            print(f"❌ Błąd zapisywania konfiguracji: {e}")
            return False
    
    def get_server_config(self):
        """Zwraca konfigurację serwera"""
        return {
            'host': self.get('SERVER', 'host', 'localhost'),
            'port': self.getint('SERVER', 'port', 12345),
            'max_clients': self.getint('SERVER', 'max_clients', 50),
            'timeout': self.getint('SERVER', 'timeout', 60)
        }
    
    def get_logging_config(self):
        """Zwraca konfigurację logowania"""
        return {
            'log_level': self.get('LOGGING', 'log_level', 'INFO'),
            'log_file': self.get('LOGGING', 'log_file', 'server.log'),
            'log_to_console': self.getboolean('LOGGING', 'log_to_console', True),
            'log_to_file': self.getboolean('LOGGING', 'log_to_file', True)
        }
    
    def get_security_config(self):
        """Zwraca konfigurację bezpieczeństwa"""
        return {
            'max_message_length': self.getint('SECURITY', 'max_message_length', 500),
            'max_nick_length': self.getint('SECURITY', 'max_nick_length', 20),
            'min_nick_length': self.getint('SECURITY', 'min_nick_length', 2),
            'allowed_nick_chars': self.get('SECURITY', 'allowed_nick_chars', 
                                         'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
        }
    
    def get_features_config(self):
        """Zwraca konfigurację funkcjonalności"""
        return {
            'enable_user_list': self.getboolean('FEATURES', 'enable_user_list', True),
            'enable_ping_pong': self.getboolean('FEATURES', 'enable_ping_pong', True),
            'enable_timestamps': self.getboolean('FEATURES', 'enable_timestamps', True),
            'welcome_message': self.get('FEATURES', 'welcome_message', 'Witaj w komunikatorze IP!'),
            'max_login_attempts': self.getint('FEATURES', 'max_login_attempts', 3)
        }
    
    def get_performance_config(self):
        """Zwraca konfigurację wydajności"""
        return {
            'buffer_size': self.getint('PERFORMANCE', 'buffer_size', 1024),
            'stats_interval': self.getint('PERFORMANCE', 'stats_interval', 300),
            'cleanup_interval': self.getint('PERFORMANCE', 'cleanup_interval', 60)
        }
    
    def print_config(self):
        """Wyświetla aktualną konfigurację"""
        print("\n🔧 Aktualna konfiguracja:")
        print("=" * 40)
        
        for section in self.config.sections():
            print(f"\n[{section}]")
            for key, value in self.config.items(section):
                print(f"  {key} = {value}")
        
        print("=" * 40)

# Singleton instance
_config_instance = None

def get_config(config_file='config.ini'):
    """Zwraca instancję ConfigLoader (singleton)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader(config_file)
    return _config_instance