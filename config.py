#!/usr/bin/env python3
"""
Centralna konfiguracja dla komunikatora IP
"""

# Połączenie
DEFAULT_HOST = 'localhost'
DEFAULT_TCP_PORT = 12345
DEFAULT_WS_PORT = 8765
DEFAULT_HTTP_PORT = 8000

# Szyfrowanie
ENCRYPTION_PASSWORD = "komunikator_secure_2025"

# Limity
MAX_CLIENTS = 50
MAX_MESSAGE_LENGTH = 500
MAX_NICK_LENGTH = 20
MIN_NICK_LENGTH = 2
SOCKET_TIMEOUT = 60
PING_TIMEOUT = 30

# Logowanie
LOG_FILE = 'server.log'
LOG_DIR = 'logs'

# Bot AI
BOT_DEFAULT_NAME = "🤖AIBot"
BOT_MODEL = "gpt-3.5-turbo"
BOT_MAX_HISTORY = 20
BOT_RESPONSE_DELAY = 1.0
BOT_MAX_RESPONSE_LENGTH = 400

# WebSocket Bridge
BRIDGE_NICK = "🌉WebBridge"
BRIDGE_RECONNECT_DELAY = 5

# Historia
HISTORY_FILE = 'chat_history.json'
HISTORY_MAX_MESSAGES = 1000

# Statystyki
STATS_FILE = 'server_stats.json'
STATS_INTERVAL = 300  # 5 minut