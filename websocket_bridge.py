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
import time  # ✅ DODANO IMPORT
import sys
import os
from typing import Dict, Set

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType
from common.utils import validate_nick, validate_message

class WebSocketBridge:
    def __init__(self, tcp_host='localhost', tcp_port=12345, ws_port=8765):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.ws_port = ws_port
        
        # WebSocket połączenia {websocket: client_info}
        self.websocket_clients: Dict[websockets.WebSocketServerProtocol, dict] = {}
        
        # TCP połączenia {nick: tcp_socket}
        self.tcp_connections: Dict[str, socket.socket] = {}
        
        # Bridge TCP connection - pojedyncze połączenie do serwera dla przekazywania wiadomości
        self.bridge_socket = None
        self.bridge_connected = False
        self.bridge_nick = "🌉WebBridge"
        
        print(f"🌐 WebSocket Bridge uruchamiany...")
        print(f"   WebSocket serwer: ws://localhost:{ws_port}")
        print(f"   TCP serwer: {tcp_host}:{tcp_port}")
        print(f"   Bridge obsługuje TCP boty: ✅")

    async def handle_websocket_connection(self, websocket):
        """Obsługuje nowe połączenie WebSocket"""
        client_ip = websocket.remote_address[0]
        print(f"🔗 Nowe połączenie WebSocket z {client_ip}")
        
        # Zarejestruj klienta
        self.websocket_clients[websocket] = {
            'ip': client_ip,
            'nick': None,
            'tcp_socket': None,
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
        except Exception as e:
            print(f"❌ Błąd WebSocket: {e}")
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
            self.bridge_socket.send(join_message.encode('utf-8'))
            
            # Zaktualizuj informacje o kliencie WebSocket
            client_info = self.websocket_clients[websocket]
            client_info['nick'] = nick
            client_info['connected'] = True
            
            # Dodaj do rejestru (nie potrzebujemy osobnego TCP socketa)
            self.tcp_connections[nick] = websocket  # Używamy WebSocket jako identyfikator
            
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
            # Wyślij wiadomość przez TCP Bridge zamiast indywidualnego połączenia
            if self.bridge_connected and self.bridge_socket:
                chat_message = Protocol.create_message(MessageType.MESSAGE, nick, content)
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

    def tcp_receive_loop(self, websocket, tcp_socket, nick):
        """Pętla odbierająca wiadomości z TCP serwera (w osobnym wątku)"""
        try:
            while True:
                tcp_socket.settimeout(60)
                data = tcp_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                # Parsuj wiadomość TCP
                message = Protocol.parse_message(data)
                
                # Konwertuj na format WebSocket
                ws_message = self.convert_tcp_to_websocket(message)
                
                # Wyślij do WebSocket (asyncio.run_coroutine_threadsafe dla thread safety)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.send_to_websocket(websocket, ws_message))
                loop.close()
                
        except socket.timeout:
            print(f"⏰ Timeout TCP dla {nick}")
        except socket.error as e:
            print(f"❌ Błąd TCP dla {nick}: {e}")
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd TCP dla {nick}: {e}")
        finally:
            # Powiadom WebSocket o rozłączeniu
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.send_to_websocket(websocket, {
                    'type': 'tcp_disconnected',
                    'message': 'Połączenie z serwerem zostało przerwane'
                }))
                loop.close()
            except:
                pass

    def convert_tcp_to_websocket(self, tcp_message):
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

    async def send_to_websocket(self, websocket, data):
        """Wysyła dane do WebSocket"""
        try:
            if websocket in self.websocket_clients:
                await websocket.send(json.dumps(data))
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"❌ Błąd wysyłania do WebSocket: {e}")

    async def cleanup_websocket_client(self, websocket):
        """Czyści zasoby po rozłączeniu WebSocket"""
        if websocket in self.websocket_clients:
            client_info = self.websocket_clients[websocket]
            nick = client_info.get('nick')
            tcp_socket = client_info.get('tcp_socket')
            
            # Zamknij TCP połączenie
            if tcp_socket:
                try:
                    if nick:
                        leave_message = Protocol.create_message(MessageType.LEAVE, nick)
                        tcp_socket.send(leave_message.encode('utf-8'))
                except:
                    pass
                try:
                    tcp_socket.close()
                except:
                    pass
            
            # Usuń z rejestrów
            if nick and nick in self.tcp_connections:
                del self.tcp_connections[nick]
            
            del self.websocket_clients[websocket]
            
            if nick:
                print(f"🧹 Wyczyszczono zasoby dla {nick}")

    async def start_server(self):
        """Uruchamia WebSocket serwer"""
        print(f"🚀 Uruchamianie WebSocket serwera na porcie {self.ws_port}...")
        
        # Uruchom bridge TCP connection w osobnym wątku
        bridge_thread = threading.Thread(target=self.start_tcp_bridge)
        bridge_thread.daemon = True
        bridge_thread.start()
        
        server = await websockets.serve(
            self.handle_websocket_connection,
            "localhost",
            self.ws_port
        )
        
        print(f"✅ WebSocket Bridge gotowy!")
        print(f"   Otwórz przeglądarkę: http://localhost:8000")
        print(f"   WebSocket endpoint: ws://localhost:{self.ws_port}")
        print(f"   TCP Bridge: {'✅ Połączony' if self.bridge_connected else '❌ Rozłączony'}")
        
        await server.wait_closed()

    def start_tcp_bridge(self):
        """Uruchamia TCP bridge connection w osobnym wątku"""
        while True:
            try:
                print(f"🌉 Łączenie TCP Bridge z serwerem...")
                self.bridge_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.bridge_socket.settimeout(30)
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
                self.bridge_socket.send(join_message.encode('utf-8'))
                
                self.bridge_connected = True
                print(f"✅ TCP Bridge połączony jako {self.bridge_nick}")
                
                # Pętla odbierania wiadomości z TCP serwera
                while self.bridge_connected:
                    try:
                        data = self.bridge_socket.recv(1024).decode('utf-8')
                        if not data:
                            break
                        
                        message = Protocol.parse_message(data)
                        
                        # Przekaż wiadomość do wszystkich WebSocket klientów
                        if message.get('user') != self.bridge_nick:  # Nie przekazuj własnych wiadomości
                            asyncio.run(self.broadcast_to_websockets(message))
                            
                    except socket.timeout:
                        continue
                    except socket.error as e:
                        print(f"❌ Błąd TCP Bridge: {e}")
                        break
                
                self.bridge_connected = False
                print("🔌 TCP Bridge rozłączony")
                
            except Exception as e:
                print(f"❌ Błąd TCP Bridge: {e}")
                self.bridge_connected = False
                
            # Próba ponownego połączenia po 5 sekundach
            if not self.bridge_connected:
                print("🔄 Próba ponownego połączenia TCP Bridge za 5 sekund...")
                time.sleep(5)

    async def broadcast_to_websockets(self, tcp_message):
        """Przekazuje wiadomość TCP do wszystkich klientów WebSocket"""
        if not self.websocket_clients:
            return
            
        ws_message = self.convert_tcp_to_websocket(tcp_message)
        
        # Wyślij do wszystkich połączonych WebSocket klientów
        disconnected = []
        for websocket in self.websocket_clients:
            try:
                await websocket.send(json.dumps(ws_message))
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