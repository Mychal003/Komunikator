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
        """Obsługuje komendy specjalne - POPRAWIONA WERSJA"""
        cmd = command.strip().lower()
        
        self.server.log(f"Komenda od {self.nick}: {cmd}")
        
        if cmd == '/list' or cmd == '/users':
            # Wyślij listę użytkowników - POPRAWIONA WERSJA
            users = self.server.get_user_list()
            
            # Wyślij jako USER_LIST message (dla WebSocket)
            user_list_msg = Protocol.create_user_list_message(users)
            self.send_message(user_list_msg)
            
            # Także wyślij tekstową wersję (dla kompatybilności)
            user_list_text = f"Aktywni użytkownicy ({len(users)}): " + ", ".join(users)
            text_msg = Protocol.create_system_message(user_list_text)
            self.send_message(text_msg)
            
        elif cmd == '/quit':
            # Rozłącz klienta
            goodbye_msg = Protocol.create_system_message("Do widzenia!")
            self.send_message(goodbye_msg)
            self.disconnect()
            
        elif cmd == '/help':
            # Pomoc - rozszerzona lista komend
            help_text = """🔧 Dostępne komendy:
/list, /users - lista użytkowników online
/quit - wyjście z czatu
/ping - sprawdź połączenie
/time - aktualny czas serwera
/status - status serwera
/help - ta pomoc

💡 Wskazówki:
- Aby wysłać wiadomość, po prostu wpisz tekst
- Maksymalna długość wiadomości: 500 znaków
- Nick może mieć 2-20 znaków (litery, cyfry, _, -)"""
            help_msg = Protocol.create_system_message(help_text)
            self.send_message(help_msg)
            
        elif cmd == '/ping':
            # Test połączenia
            ping_msg = Protocol.create_system_message("🏓 Pong! Połączenie działa.")
            self.send_message(ping_msg)
            
        elif cmd == '/time':
            # Czas serwera
            import datetime
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time_msg = Protocol.create_system_message(f"🕐 Czas serwera: {current_time}")
            self.send_message(time_msg)
            
        elif cmd == '/status':
            # Status serwera - NOWA KOMENDA
            try:
                stats = self.server.get_server_status()
                status_msg = Protocol.create_system_message(
                    f"📊 Status serwera:\n"
                    f"⏰ Czas działania: {stats['uptime']}\n"
                    f"👥 Użytkownicy online: {stats['users']}\n"
                    f"💬 Wiadomości wysłane: {stats['messages']}\n"
                    f"🏆 Szczyt użytkowników: {stats['peak_users']}"
                )
                self.send_message(status_msg)
            except Exception as e:
                error_msg = Protocol.create_system_message(f"❌ Błąd pobierania statusu: {e}")
                self.send_message(error_msg)
            
        elif cmd == '/who':
            # Alternatywna komenda dla listy użytkowników
            users = self.server.get_user_list()
            if users:
                who_text = f"👥 Kto jest online ({len(users)}):\n"
                for i, user in enumerate(users, 1):
                    if user == self.nick:
                        who_text += f"   {i}. {user} (to Ty) ⭐\n"
                    else:
                        who_text += f"   {i}. {user}\n"
            else:
                who_text = "👻 Nikt nie jest online"
            
            who_msg = Protocol.create_system_message(who_text)
            self.send_message(who_msg)
            
        elif cmd.startswith('/nick '):
            # Zmiana nicku - NOWA FUNKCJA
            new_nick = cmd[6:].strip()
            
            if not new_nick:
                error_msg = Protocol.create_system_message("❌ Użycie: /nick <nowy_nick>")
                self.send_message(error_msg)
                return
            
            # Waliduj nowy nick
            is_valid, error_msg = validate_nick(new_nick)
            if not is_valid:
                error_response = Protocol.create_system_message(f"❌ Nieprawidłowy nick: {error_msg}")
                self.send_message(error_response)
                return
            
            # Sprawdź czy nick nie jest zajęty
            if new_nick in self.server.get_user_list():
                error_msg = Protocol.create_system_message("❌ Nick już zajęty!")
                self.send_message(error_msg)
                return
            
            # Zmień nick
            old_nick = self.nick
            if self.server.change_user_nick(old_nick, new_nick):
                self.nick = new_nick
                success_msg = Protocol.create_system_message(f"✅ Nick zmieniony z '{old_nick}' na '{new_nick}'")
                self.send_message(success_msg)
                
                # Powiadom wszystkich o zmianie
                announce_msg = Protocol.create_system_message(f"📝 {old_nick} zmienił nick na {new_nick}")
                self.server.broadcast_message(announce_msg, exclude_user=new_nick)
            else:
                error_msg = Protocol.create_system_message("❌ Nie udało się zmienić nicku")
                self.send_message(error_msg)
                
        elif cmd == '/clear':
            # Wyczyść ekran (tylko informacyjnie)
            clear_msg = Protocol.create_system_message("🧹 Aby wyczyścić ekran, odśwież stronę lub wyczyść terminal")
            self.send_message(clear_msg)
            
        elif cmd.startswith('/msg '):
            # Prywatna wiadomość - NOWA FUNKCJA
            parts = cmd[5:].split(' ', 1)
            if len(parts) < 2:
                error_msg = Protocol.create_system_message("❌ Użycie: /msg <nick> <wiadomość>")
                self.send_message(error_msg)
                return
            
            target_nick, private_msg = parts
            target_nick = target_nick.strip()
            
            if target_nick == self.nick:
                error_msg = Protocol.create_system_message("❌ Nie możesz wysłać wiadomości do siebie")
                self.send_message(error_msg)
                return
            
            if self.server.send_private_message(self.nick, target_nick, private_msg):
                confirm_msg = Protocol.create_system_message(f"📤 Prywatna wiadomość wysłana do {target_nick}")
                self.send_message(confirm_msg)
            else:
                error_msg = Protocol.create_system_message(f"❌ Użytkownik {target_nick} nie jest online")
                self.send_message(error_msg)
        
        else:
            # Nieznana komenda
            error_msg = Protocol.create_system_message(f"❌ Nieznana komenda: {command}\n💡 Wpisz /help aby zobaczyć dostępne komendy.")
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