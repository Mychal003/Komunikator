import socket
import sys
import os

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType
from common.utils import validate_nick, validate_message, clean_text

class ClientHandler:
    def __init__(self, client_socket, address, server):
        self.client_socket = client_socket
        self.address = address
        self.server = server
        self.nick = None
        self.connected = True
        
        # Ustawienia timeout dla socketa
        self.client_socket.settimeout(60)  # 60 sekund timeout
    
    def handle(self):
        """Główna pętla obsługi klienta"""
        try:
            # Najpierw klient musi się zalogować
            if not self.authenticate():
                self.server.log(f"Nieudane uwierzytelnienie z {self.address}")
                return
            
            self.server.log(f"Użytkownik {self.nick} uwierzytelniony pomyślnie")
            
            # Pętla odbierania wiadomości
            while self.connected:
                try:
                    data = self.client_socket.recv(1024).decode('utf-8')
                    if not data:
                        self.server.log(f"Puste dane od {self.nick}, rozłączam")
                        break
                    
                    # Przetwórz otrzymaną wiadomość
                    self.process_message(data)
                    
                except socket.timeout:
                    # Sprawdź czy klient nadal żyje
                    if not self.ping_client():
                        self.server.log(f"Klient {self.nick} nie odpowiada na ping")
                        break
                    continue
                except socket.error as e:
                    self.server.log(f"Błąd socketa dla {self.nick}: {e}")
                    break
                except UnicodeDecodeError as e:
                    self.server.log(f"Błąd dekodowania od {self.nick}: {e}")
                    error_msg = Protocol.create_system_message("Błąd kodowania znaków")
                    self.send_message(error_msg)
                    continue
                    
        except Exception as e:
            self.server.log(f"❌ Błąd w obsłudze klienta {self.address}: {e}")
        finally:
            self.disconnect()
    
    def authenticate(self):
        """Proces uwierzytelniania - otrzymanie nicku"""
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Wyślij prośbę o nick
                if attempt == 0:
                    welcome_msg = Protocol.create_system_message("Podaj swój nick:")
                else:
                    welcome_msg = Protocol.create_system_message(f"Spróbuj ponownie ({max_attempts - attempt} prób pozostało):")
                
                self.send_message(welcome_msg)
                
                # Odbierz nick z timeout
                self.client_socket.settimeout(30)  # 30 sekund na podanie nicku
                data = self.client_socket.recv(1024).decode('utf-8')
                
                if not data:
                    return False
                
                message = Protocol.parse_message(data)
                
                if message['type'] == MessageType.JOIN:
                    nick = clean_text(message['user'].strip())
                    
                    # Waliduj nick
                    is_valid, error_msg = validate_nick(nick)
                    if not is_valid:
                        error_response = Protocol.create_system_message(f"Błąd: {error_msg}")
                        self.send_message(error_response)
                        attempt += 1
                        continue
                    
                    # Sprawdź czy nick jest wolny
                    if self.server.add_client(nick, self):
                        self.nick = nick
                        success_msg = Protocol.create_system_message(f"Witaj {nick}! Możesz teraz pisać wiadomości.")
                        self.send_message(success_msg)
                        self.client_socket.settimeout(60)  # Przywróć normalny timeout
                        return True
                    else:
                        error_msg = Protocol.create_system_message("Nick zajęty! Wybierz inny.")
                        self.send_message(error_msg)
                        attempt += 1
                        continue
                else:
                    error_msg = Protocol.create_system_message("Nieprawidłowy format wiadomości")
                    self.send_message(error_msg)
                    attempt += 1
                    continue
            
            except socket.timeout:
                timeout_msg = Protocol.create_system_message("Przekroczono czas oczekiwania na nick")
                self.send_message(timeout_msg)
                return False
            except Exception as e:
                self.server.log(f"❌ Błąd uwierzytelniania: {e}")
                attempt += 1
                continue
        
        # Przekroczono maksymalną liczbę prób
        final_error = Protocol.create_system_message("Przekroczono maksymalną liczbę prób logowania")
        self.send_message(final_error)
        return False
    
    def process_message(self, raw_data):
        """Przetwarza otrzymaną wiadomość"""
        try:
            message = Protocol.parse_message(raw_data)
            
            if message['type'] == MessageType.MESSAGE:
                content = clean_text(message['content'])
                
                # Waliduj wiadomość
                is_valid, error_msg = validate_message(content)
                if not is_valid:
                    error_response = Protocol.create_system_message(f"Błąd: {error_msg}")
                    self.send_message(error_response)
                    return
                
                # Sprawdź czy to komenda
                if content.startswith('/'):
                    self.handle_command(content)
                else:
                    # Zwykła wiadomość - przekaż wszystkim
                    formatted_message = Protocol.create_message(
                        MessageType.MESSAGE,
                        self.nick,
                        content
                    )
                    self.server.broadcast_message(formatted_message)
                    self.server.log(f"Wiadomość od {self.nick}: {content[:50]}...")
                
            elif message['type'] == MessageType.LEAVE:
                # Klient chce się rozłączyć
                self.server.log(f"Klient {self.nick} żąda rozłączenia")
                self.disconnect()
            
            else:
                # Nieznany typ wiadomości
                error_msg = Protocol.create_system_message("Nieznany typ wiadomości")
                self.send_message(error_msg)
                
        except Exception as e:
            self.server.log(f"Błąd przetwarzania wiadomości od {self.nick}: {e}")
            error_msg = Protocol.create_system_message("Błąd przetwarzania wiadomości")
            self.send_message(error_msg)
    
    def handle_command(self, command):
        """Obsługuje komendy specjalne"""
        cmd = command.strip().lower()
        
        self.server.log(f"Komenda od {self.nick}: {cmd}")
        
        if cmd == '/list':
            # Wyślij listę użytkowników
            users = self.server.get_user_list()
            user_list_text = f"Aktywni użytkownicy ({len(users)}): " + ", ".join(users)
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
/list - lista użytkowników online
/quit - wyjście z czatu
/ping - sprawdź połączenie
/time - aktualny czas serwera
/help - ta pomoc"""
            help_msg = Protocol.create_system_message(help_text)
            self.send_message(help_msg)
            
        elif cmd == '/ping':
            # Test połączenia
            ping_msg = Protocol.create_system_message("Pong! Połączenie działa.")
            self.send_message(ping_msg)
            
        elif cmd == '/time':
            # Czas serwera
            import datetime
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time_msg = Protocol.create_system_message(f"Czas serwera: {current_time}")
            self.send_message(time_msg)
            
        else:
            error_msg = Protocol.create_system_message(f"Nieznana komenda: {command}. Wpisz /help aby zobaczyć dostępne komendy.")
            self.send_message(error_msg)
    
    def ping_client(self):
        """Sprawdza czy klient nadal jest aktywny"""
        try:
            ping_msg = Protocol.create_system_message("")  # Pusta wiadomość jako ping
            return self.send_message(ping_msg)
        except:
            return False
    
    def send_message(self, message):
        """Wysyła wiadomość do klienta"""
        try:
            if not self.connected:
                return False
                
            self.client_socket.send(message.encode('utf-8'))
            return True
        except socket.error as e:
            self.server.log(f"Błąd wysyłania do {self.nick}: {e}")
            self.connected = False
            return False
        except Exception as e:
            self.server.log(f"Nieoczekiwany błąd wysyłania do {self.nick}: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Rozłącza klienta"""
        if self.connected:
            self.connected = False
            
            # Usuń z listy klientów serwera
            if self.nick:
                self.server.remove_client(self.nick)
                self.server.log(f"Klient {self.nick} ({self.address}) rozłączony")
            
            # Zamknij socket
            try:
                self.client_socket.close()
            except:
                pass