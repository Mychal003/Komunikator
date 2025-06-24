#!/usr/bin/env python3
"""
WebSocket Bridge dla nowoczesnego interfejsu komunikatora IP
Łączy HTML/JS frontend z TCP serwerem komunikatora
"""

import asyncio
import websockets
import json
import socket
import threading
import time
import sys
import os
from typing import Dict, Set
import concurrent.futures

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType
from common.utils import validate_nick, validate_message

# Debug informacje o wersji
print(f"🔍 Wersja websockets: {websockets.__version__}")
print(f"🔍 Wersja Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

class WebSocketBridge:
    def __init__(self, tcp_host='localhost', tcp_port=12345, ws_port=8765):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.ws_port = ws_port
        
        # WebSocket połączenia {websocket: client_info}
        self.websocket_clients: Dict[websockets.WebSocketServerProtocol, dict] = {}
        
        # TCP połączenia {nick: websocket}
        self.tcp_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Bridge TCP connection
        self.bridge_socket = None
        self.bridge_connected = False
        self.bridge_nick = "🌉WebBridge"
        
        # Event loop dla komunikacji między wątkami
        self.main_loop = None
        self.shutdown_event = threading.Event()
        
        print(f"🌐 WebSocket Bridge uruchamiany...")
        print(f"   WebSocket serwer: ws://localhost:{ws_port}")
        print(f"   TCP serwer: {tcp_host}:{tcp_port}")
        print(f"   Bridge obsługuje TCP boty: ✅")

    async def handle_websocket_connection(self, websocket, path=None):
        """Obsługuje nowe połączenie WebSocket - kompatybilne z różnymi wersjami biblioteki"""
        client_ip = websocket.remote_address[0]
        print(f"🔗 Nowe połączenie WebSocket z {client_ip}")
        
        # Zarejestruj klienta
        self.websocket_clients[websocket] = {
            'ip': client_ip,
            'nick': None,
            'connected': False
        }
        
        try:
            # Wyślij informację o dostępności szyfrowania
            await self.send_to_websocket(websocket, {
                'type': 'encryption_status',
                'available': True,
                'algorithm': 'AES-256-CBC'
            })
            
            async for message in websocket:
                await self.handle_websocket_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"🔌 Połączenie WebSocket z {client_ip} zamknięte")
        except websockets.exceptions.InvalidMessage:
            print(f"❌ Nieprawidłowa wiadomość WebSocket z {client_ip}")
        except Exception as e:
            print(f"❌ Błąd WebSocket z {client_ip}: {e}")
        finally:
            await self.cleanup_websocket_client(websocket)

    async def handle_websocket_message(self, websocket, message):
        """Obsługuje wiadomość z WebSocket"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'connect':
                await self.handle_connect_request(websocket, data)
            elif msg_type == 'disconnect':
                await self.handle_disconnect_request(websocket)
            elif msg_type == 'message':
                await self.handle_message_request(websocket, data)
            elif msg_type == 'ping':
                await self.send_to_websocket(websocket, {'type': 'pong'})
            else:
                await self.send_to_websocket(websocket, {
                    'type': 'error',
                    'message': f'Nieznany typ wiadomości: {msg_type}'
                })
                
        except json.JSONDecodeError:
            await self.send_to_websocket(websocket, {
                'type': 'error',
                'message': 'Nieprawidłowy format JSON'
            })
        except Exception as e:
            await self.send_to_websocket(websocket, {
                'type': 'error', 
                'message': f'Błąd przetwarzania: {str(e)}'
            })

    async def handle_connect_request(self, websocket, data):
        """Obsługuje żądanie połączenia z TCP serwerem"""
        host = data.get('host', self.tcp_host)
        port = data.get('port', self.tcp_port)
        nick = data.get('nick', '').strip()
        
        # Walidacja nicku
        is_valid, error_msg = validate_nick(nick)
        if not is_valid:
            await self.send_to_websocket(websocket, {
                'type': 'connection_error',
                'message': f'Nieprawidłowy nick: {error_msg}'
            })
            return
        
        # Sprawdź czy nick nie jest już zajęty
        if nick in self.tcp_connections:
            await self.send_to_websocket(websocket, {
                'type': 'connection_error',
                'message': 'Nick już zajęty'
            })
            return
        
        # Sprawdź czy TCP Bridge jest połączony
        if not self.bridge_connected:
            await self.send_to_websocket(websocket, {
                'type': 'connection_error',
                'message': 'Serwer TCP niedostępny'
            })
            return
        
        try:
            # Wyślij JOIN message przez TCP Bridge
            join_message = Protocol.create_message(MessageType.JOIN, nick)
            if join_message and join_message.strip():
                self.bridge_socket.send(join_message.encode('utf-8'))
            
            # Zaktualizuj informacje o kliencie WebSocket
            client_info = self.websocket_clients[websocket]
            client_info['nick'] = nick
            client_info['connected'] = True
            
            # Dodaj do rejestru
            self.tcp_connections[nick] = websocket
            
            # Powiadom WebSocket o sukcesie
            await self.send_to_websocket(websocket, {
                'type': 'connected',
                'host': host,
                'port': port,
                'nick': nick,
                'encryption': Protocol.encryption_enabled
            })
            
            print(f"✅ {nick} połączony przez WebSocket Bridge")
            
        except socket.error as e:
            await self.send_to_websocket(websocket, {
                'type': 'connection_error',
                'message': f'Błąd połączenia: {str(e)}'
            })
        except Exception as e:
            await self.send_to_websocket(websocket, {
                'type': 'connection_error',
                'message': f'Nieoczekiwany błąd: {str(e)}'
            })

    async def handle_disconnect_request(self, websocket):
        """Obsługuje żądanie rozłączenia"""
        client_info = self.websocket_clients.get(websocket, {})
        nick = client_info.get('nick')
        
        if nick and self.bridge_connected:
            try:
                # Wyślij LEAVE message przez TCP Bridge
                leave_message = Protocol.create_message(MessageType.LEAVE, nick)
                if leave_message and leave_message.strip():
                    self.bridge_socket.send(leave_message.encode('utf-8'))
            except:
                pass
            
            # Usuń z połączeń
            if nick in self.tcp_connections:
                del self.tcp_connections[nick]
            
            print(f"👋 {nick} rozłączony przez WebSocket")
        
        # Aktualizuj informacje o kliencie
        client_info['connected'] = False
        
        await self.send_to_websocket(websocket, {
            'type': 'disconnected'
        })

    async def handle_message_request(self, websocket, data):
        """Obsługuje wysłanie wiadomości do TCP serwera"""
        client_info = self.websocket_clients.get(websocket, {})
        if not client_info.get('connected'):
            await self.send_to_websocket(websocket, {
                'type': 'error',
                'message': 'Nie połączono z serwerem'
            })
            return
        
        nick = client_info.get('nick')
        content = data.get('content', '').strip()
        
        # Walidacja wiadomości
        is_valid, error_msg = validate_message(content)
        if not is_valid:
            await self.send_to_websocket(websocket, {
                'type': 'error',
                'message': f'Nieprawidłowa wiadomość: {error_msg}'
            })
            return
        
        try:
            # Wyślij wiadomość przez TCP Bridge
            if self.bridge_connected and self.bridge_socket:
                chat_message = Protocol.create_message(MessageType.MESSAGE, nick, content)
                if chat_message and chat_message.strip():
                    self.bridge_socket.send(chat_message.encode('utf-8'))
            else:
                await self.send_to_websocket(websocket, {
                    'type': 'error',
                    'message': 'Bridge TCP rozłączony'
                })
            
        except socket.error as e:
            await self.send_to_websocket(websocket, {
                'type': 'error',
                'message': f'Błąd wysyłania: {str(e)}'
            })
            await self.handle_disconnect_request(websocket)

    def convert_tcp_to_websocket(self, tcp_message):
        """Konwertuje wiadomość TCP na format WebSocket"""
        if tcp_message is None:
            return None
            
        msg_type = tcp_message.get('type', '')
        user = tcp_message.get('user', '')
        content = tcp_message.get('content', '').strip()
        timestamp = tcp_message.get('timestamp', '')
        encrypted = tcp_message.get('encrypted', False)
        
        # ✅ IGNORUJ wiadomości od Bridge'a
        if user == self.bridge_nick:
            return None
        
        # Filtruj puste wiadomości systemowe
        if msg_type == MessageType.SYSTEM and not content:
            return None
        
        if msg_type == MessageType.MESSAGE:
            if not content:
                return None
                
            return {
                'type': 'message',
                'author': user,
                'content': content,
                'timestamp': timestamp,
                'encrypted': encrypted
            }
            
        elif msg_type == MessageType.SYSTEM:
            if content:
                return {
                    'type': 'system_message',
                    'content': content,
                    'timestamp': timestamp
                }
                
        elif msg_type == MessageType.USER_LIST:
            try:
                users = json.loads(content)
                # ✅ Usuń bridge z listy użytkowników
                if self.bridge_nick in users:
                    users.remove(self.bridge_nick)
                return {
                    'type': 'users_list',
                    'users': users
                }
            except:
                return None
                
        elif msg_type == MessageType.ERROR:
            if content:
                return {
                    'type': 'error',
                    'message': content
                }
        
        # ✅ KLUCZOWA ZMIANA: Ignoruj nieznane typy zamiast zwracać error
        return None

    async def send_to_websocket(self, websocket, data):
        """Wysyła dane do WebSocket"""
        try:
            if websocket in self.websocket_clients:
                # Sprawdź stan połączenia w sposób kompatybilny z różnymi wersjami
                try:
                    # Dla nowszych wersji websockets
                    if hasattr(websocket, 'state') and websocket.state.name != 'OPEN':
                        return
                    # Dla starszych wersji websockets
                    elif hasattr(websocket, 'closed') and websocket.closed:
                        return
                except:
                    pass  # Jeśli sprawdzenie stanu się nie powiedzie, spróbuj wysłać
                
                await websocket.send(json.dumps(data))
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"❌ Błąd wysyłania do WebSocket: {e}")
            # Usuń problematyczne połączenie
            if websocket in self.websocket_clients:
                del self.websocket_clients[websocket]

    async def cleanup_websocket_client(self, websocket):
        """Czyści zasoby po rozłączeniu WebSocket"""
        if websocket in self.websocket_clients:
            client_info = self.websocket_clients[websocket]
            nick = client_info.get('nick')
            
            # Usuń z rejestrów
            if nick and nick in self.tcp_connections:
                del self.tcp_connections[nick]
                
                # Wyślij LEAVE message przez bridge
                if self.bridge_connected:
                    try:
                        leave_message = Protocol.create_message(MessageType.LEAVE, nick)
                        if leave_message and leave_message.strip():
                            self.bridge_socket.send(leave_message.encode('utf-8'))
                    except:
                        pass
            
            del self.websocket_clients[websocket]
            
            if nick:
                print(f"🧹 Wyczyszczono zasoby dla {nick}")

    def schedule_websocket_broadcast(self, ws_message):
        """Planuje wysłanie wiadomości do WebSocket klientów z głównego event loop"""
        if self.main_loop and not self.main_loop.is_closed():
            # Użyj call_soon_threadsafe aby bezpiecznie zaplanować task
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast_to_websockets(ws_message), 
                self.main_loop
            )
            try:
                # Czekaj maksymalnie 1 sekundę na wykonanie
                future.result(timeout=1.0)
            except concurrent.futures.TimeoutError:
                print("⚠️ Timeout podczas wysyłania do WebSocket klientów")
            except Exception as e:
                print(f"❌ Błąd wysyłania do WebSocket klientów: {e}")

    async def start_server(self):
        """Uruchamia WebSocket serwer"""
        print(f"🚀 Uruchamianie WebSocket serwera na porcie {self.ws_port}...")
        
        # Zapisz główny event loop
        self.main_loop = asyncio.get_event_loop()
        
        # Uruchom bridge TCP connection w osobnym wątku
        bridge_thread = threading.Thread(target=self.start_tcp_bridge)
        bridge_thread.daemon = True
        bridge_thread.start()
        
        # Obsługa połączeń WebSocket - kompatybilna z różnymi wersjami biblioteki
        async def connection_handler(websocket, path=None):
            try:
                await self.handle_websocket_connection(websocket, path)
            except websockets.exceptions.InvalidMessage as e:
                print(f"❌ Nieprawidłowa wiadomość WebSocket: {e}")
            except Exception as e:
                print(f"❌ Błąd obsługi WebSocket: {e}")
        
        try:
            # Bezpośrednie użycie metody klasy jako handler
            server = await websockets.serve(
                self.handle_websocket_connection,
                "localhost",
                self.ws_port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            print(f"✅ WebSocket Bridge gotowy!")
            print(f"   Otwórz przeglądarkę: http://localhost:8000")
            print(f"   WebSocket endpoint: ws://localhost:{self.ws_port}")
            print(f"   TCP Bridge: {'✅ Połączony' if self.bridge_connected else '❌ Rozłączony'}")
            
            # Czekaj na zakończenie
            await server.wait_closed()
            
        except KeyboardInterrupt:
            print("\n🛑 Otrzymano sygnał przerwania...")
        finally:
            # Sygnalizuj zakończenie
            self.shutdown_event.set()
            
            # Zakończ TCP bridge
            self.bridge_connected = False
            if self.bridge_socket:
                try:
                    self.bridge_socket.close()
                except:
                    pass
            
            # Statystyki końcowe
            print("📊 Statystyki końcowe:")
            print(f"   WebSocket klientów: {len(self.websocket_clients)}")
            print(f"   TCP połączeń: {len(self.tcp_connections)}")
            print(f"   Połączeni użytkownicy: {list(self.tcp_connections.keys())}")

    def start_tcp_bridge(self):
        """Uruchamia TCP bridge connection w osobnym wątku"""
        while not self.shutdown_event.is_set():
            try:
                print(f"🌉 Łączenie TCP Bridge z serwerem...")
                self.bridge_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.bridge_socket.settimeout(5)  # Krótszy timeout dla szybszego wykrywania błędów
                self.bridge_socket.connect((self.tcp_host, self.tcp_port))
                
                # Włącz szyfrowanie jeśli dostępne
                try:
                    from common.encryption import is_encryption_available
                    if is_encryption_available():
                        encryption_password = "komunikator_secure_2025"
                        Protocol.enable_encryption(encryption_password)
                        print("🔒 Szyfrowanie włączone dla TCP Bridge")
                except ImportError:
                    pass
                
                # Wyślij JOIN message dla bridge
                join_message = Protocol.create_message(MessageType.JOIN, self.bridge_nick)
                if join_message and join_message.strip():
                    self.bridge_socket.send(join_message.encode('utf-8'))
                
                self.bridge_connected = True
                print(f"✅ TCP Bridge połączony jako {self.bridge_nick}")
                
                # Pętla odbierania wiadomości z TCP serwera
                while self.bridge_connected and not self.shutdown_event.is_set():
                    try:
                        self.bridge_socket.settimeout(1)  # Krótki timeout dla sprawdzania shutdown
                        data = self.bridge_socket.recv(1024).decode('utf-8')
                        if not data:
                            break
                        
                        message = Protocol.parse_message(data)
                        
                        # Przekaż wiadomość do wszystkich WebSocket klientów
                        if message and message.get('user') != self.bridge_nick:
                            ws_message = self.convert_tcp_to_websocket(message)
                            if ws_message:
                                print(f"📤 Przekazuję do WebSocket: {ws_message['type']} od {ws_message.get('author', 'system')}")
                                self.schedule_websocket_broadcast(ws_message)
                            else:
                                    print(f"🔇 Pomijam wiadomość TCP: {message.get('type')} od {message.get('user')}")
                            
                    except socket.timeout:
                        continue  # Sprawdź shutdown_event i kontynuuj
                    except socket.error as e:
                        print(f"❌ Błąd TCP Bridge: {e}")
                        break
                
                self.bridge_connected = False
                print("🔌 TCP Bridge rozłączony")
                
            except Exception as e:
                print(f"❌ Błąd TCP Bridge: {e}")
                self.bridge_connected = False
                
            # Próba ponownego połączenia po 5 sekundach (jeśli nie shutdown)
            if not self.bridge_connected and not self.shutdown_event.is_set():
                print("🔄 Próba ponownego połączenia TCP Bridge za 5 sekund...")
                self.shutdown_event.wait(5)  # Przerywalny sleep

    async def broadcast_to_websockets(self, ws_message):
        """Przekazuje wiadomość do wszystkich klientów WebSocket"""
        if not self.websocket_clients or not ws_message:
            return
        
        # Wyślij do wszystkich połączonych WebSocket klientów
        disconnected = []
        for websocket in list(self.websocket_clients.keys()):
            try:
                # Sprawdź stan połączenia w sposób kompatybilny
                connection_ok = True
                try:
                    if hasattr(websocket, 'state') and websocket.state.name != 'OPEN':
                        connection_ok = False
                    elif hasattr(websocket, 'closed') and websocket.closed:
                        connection_ok = False
                except:
                    pass  # Jeśli sprawdzenie się nie powiedzie, spróbuj wysłać
                
                if connection_ok:
                    await websocket.send(json.dumps(ws_message))
                else:
                    disconnected.append(websocket)
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(websocket)
            except Exception as e:
                print(f"❌ Błąd wysyłania do WebSocket: {e}")
                disconnected.append(websocket)
        
        # Usuń rozłączonych klientów
        for ws in disconnected:
            if ws in self.websocket_clients:
                del self.websocket_clients[ws]

def main():
    """Główna funkcja"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WebSocket Bridge dla komunikatora IP')
    parser.add_argument('--tcp-host', default='localhost', help='Host TCP serwera')
    parser.add_argument('--tcp-port', type=int, default=12345, help='Port TCP serwera')
    parser.add_argument('--ws-port', type=int, default=8765, help='Port WebSocket serwera')
    
    args = parser.parse_args()
    
    bridge = WebSocketBridge(args.tcp_host, args.tcp_port, args.ws_port)
    
    try:
        asyncio.run(bridge.start_server())
    except KeyboardInterrupt:
        print("\n🛑 WebSocket Bridge zatrzymany")

if __name__ == "__main__":
    main()