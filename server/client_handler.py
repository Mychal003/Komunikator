import socket
import sys
import os

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType

class ClientHandler:
    def __init__(self, client_socket, address, server):
        self.client_socket = client_socket
        self.address = address
        self.server = server
        self.nick = None
        self.connected = True
    
    def handle(self):
        """Główna pętla obsługi klienta"""
        try:
            # Najpierw klient musi się zalogować
            if not self.authenticate():
                return
            
            # Pętla odbierania wiadomości
            while self.connected:
                try:
                    data = self.client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    # Przetwórz otrzymaną wiadomość
                    self.process_message(data)
                    
                except socket.timeout:
                    continue
                except socket.error:
                    break
                    
        except Exception as e:
            print(f"❌ Błąd w obsłudze klienta {self.address}: {e}")
        finally:
            self.disconnect()
    
    def authenticate(self):
        """Proces uwierzytelniania - otrzymanie nicku"""
        try:
            # Wyślij prośbę o nick
            welcome_msg = Protocol.create_system_message("Podaj swój nick:")
            self.send_message(welcome_msg)
            
            # Odbierz nick
            data = self.client_socket.recv(1024).decode('utf-8')
            if not data:
                return False
            
            message = Protocol.parse_message(data)
            
            if message['type'] == MessageType.JOIN:
                nick = message['user'].strip()
                
                # Sprawdź czy nick jest wolny
                if self.server.add_client(nick, self):
                    self.nick = nick
                    success_msg = Protocol.create_system_message(f"Witaj {nick}! Możesz teraz pisać wiadomości.")
                    self.send_message(success_msg)
                    return True
                else:
                    error_msg = Protocol.create_system_message("Nick zajęty! Spróbuj ponownie.")
                    self.send_message(error_msg)
                    return False
            
        except Exception as e:
            print(f"❌ Błąd uwierzytelniania: {e}")
            return False
        
        return False
    
    def process_message(self, raw_data):
        """Przetwarza otrzymaną wiadomość"""
        message = Protocol.parse_message(raw_data)
        
        if message['type'] == MessageType.MESSAGE:
            # Zwykła wiadomość - przekaż wszystkim
            formatted_message = Protocol.create_message(
                MessageType.MESSAGE,
                self.nick,
                message['content']
            )
            self.server.broadcast_message(formatted_message)
            
        elif message['type'] == MessageType.LEAVE:
            # Klient chce się rozłączyć
            self.disconnect()
            
        elif message['content'].startswith('/'):
            # Komenda specjalna
            self.handle_command(message['content'])
        
        else:
            # Nieznany typ wiadomości
            error_msg = Protocol.create_system_message("Nieznany typ wiadomości")
            self.send_message(error_msg)
    
    def handle_command(self, command):
        """Obsługuje komendy specjalne"""
        cmd = command.strip().lower()
        
        if cmd == '/list':
            # Wyślij listę użytkowników
            users = self.server.get_user_list()
            user_list_text = "Aktywni użytkownicy: " + ", ".join(users)
            list_msg = Protocol.create_system_message(user_list_text)
            self.send_message(list_msg)
            
        elif cmd == '/quit':
            # Rozłącz klienta
            goodbye_msg = Protocol.create_system_message("Do widzenia!")
            self.send_message(goodbye_msg)
            self.disconnect()
            
        elif cmd == '/help':
            # Pomoc
            help_text = """Dostępne komendy:
/list - lista użytkowników
/quit - wyjście z czatu
/help - ta pomoc"""
            help_msg = Protocol.create_system_message(help_text)
            self.send_message(help_msg)
            
        else:
            error_msg = Protocol.create_system_message(f"Nieznana komenda: {command}")
            self.send_message(error_msg)
    
    def send_message(self, message):
        """Wysyła wiadomość do klienta"""
        try:
            self.client_socket.send(message.encode('utf-8'))
            return True
        except socket.error:
            self.connected = False
            return False
    
    def disconnect(self):
        """Rozłącza klienta"""
        if self.connected:
            self.connected = False
            
            # Usuń z listy klientów serwera
            if self.nick:
                self.server.remove_client(self.nick)
            
            # Zamknij socket
            try:
                self.client_socket.close()
            except:
                pass
            
            print(f"🔌 Klient {self.address} ({self.nick}) rozłączony")