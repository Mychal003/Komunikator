import socket
import threading
import sys
import os
import time

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType

class ChatClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.nick = ""
        self.receiving_thread = None
        self.authenticated = False
    
    def connect(self):
        """Łączy się z serwerem"""
        try:
            self.socket.settimeout(30)  # 30 sekund timeout
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"🔗 Połączono z serwerem {self.host}:{self.port}")
            
            # Włącz szyfrowanie jeśli dostępne
            try:
                from common.encryption import is_encryption_available
                if is_encryption_available():
                    encryption_password = "komunikator_secure_2025"  # TO SAMO co serwer
                    Protocol.enable_encryption(encryption_password)
                    print("🔒 Szyfrowanie komunikacji włączone")
                else:
                    print("⚠️ Szyfrowanie niedostępne - zainstaluj 'pip install cryptography'")
            except ImportError:
                print("⚠️ Moduł szyfrowania niedostępny")
            
            return True
            
        except socket.timeout:
            print(f"❌ Timeout - nie można połączyć się z serwerem w ciągu 30 sekund")
            return False
        except socket.error as e:
            print(f"❌ Nie można połączyć się z serwerem: {e}")
            return False
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd połączenia: {e}")
            return False
    
    def receive_messages(self):
        """Odbiera wiadomości z serwera"""
        buffer = ""
        
        while self.connected:
            try:
                self.socket.settimeout(60)  # 60 sekund timeout
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    print("\n🔌 Serwer zamknął połączenie")
                    break
                
                # Dodaj do bufora
                buffer += data
                
                # Przetwórz wszystkie kompletne wiadomości w buforze
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():  # Ignoruj puste linie
                        message = Protocol.parse_message(line.strip())
                        if message:  # Tylko jeśli parsowanie się powiodło
                            self.display_message(message)
                
            except socket.timeout:
                # Wyślij ping do serwera
                try:
                    ping_msg = Protocol.create_system_message("")
                    self.socket.send(ping_msg.encode('utf-8'))
                except:
                    print("\n❌ Utracono połączenie z serwerem")
                    break
                continue
            except socket.error as e:
                print(f"\n❌ Błąd sieci: {e}")
                break
            except Exception as e:
                print(f"\n❌ Błąd odbierania: {e}")
                continue
        
        self.connected = False
        print("\n🔌 Rozłączono z serwera")
    
    def display_message(self, message):
        """Wyświetla otrzymaną wiadomość"""
        if not message:
            return
            
        msg_type = message.get('type', '')
        user = message.get('user', '')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        encrypted = message.get('encrypted', False)
        
        # Formatowanie z kolorami jeśli dostępne
        try:
            from common.colors import colored
            use_colors = True
        except ImportError:
            use_colors = False
        
        if msg_type == MessageType.MESSAGE:
            # Pokaż ikonę zamka dla zaszyfrowanych wiadomości
            encryption_icon = "🔒" if encrypted else ""
            
            if use_colors:
                if user == self.nick:
                    print(colored.bright_yellow(f"[{timestamp}] Ty: {content} {encryption_icon}"))
                else:
                    print(colored.user_message(user, f"[{timestamp}] {content} {encryption_icon}"))
            else:
                if user == self.nick:
                    print(f"[{timestamp}] Ty: {content} {encryption_icon}")
                else:
                    print(f"[{timestamp}] {user}: {content} {encryption_icon}")
            
        elif msg_type == MessageType.SYSTEM:
            if content.strip():  # Tylko niepuste wiadomości systemowe
                if use_colors:
                    print(colored.system(f"🔔 SYSTEM: {content}"))
                else:
                    print(f"🔔 SYSTEM: {content}")
                
                # Jeśli to wiadomość powitalna, oznacz jako uwierzytelniony
                if "Witaj" in content and self.nick in content:
                    self.authenticated = True
            
        elif msg_type == MessageType.USER_LIST:
            try:
                import json
                users = json.loads(content)
                if use_colors:
                    print(colored.info(f"👥 Użytkownicy online: {', '.join(users)}"))
                else:
                    print(f"👥 Użytkownicy online: {', '.join(users)}")
            except:
                if use_colors:
                    print(colored.info(f"👥 Lista użytkowników: {content}"))
                else:
                    print(f"👥 Lista użytkowników: {content}")
                
        elif msg_type == MessageType.ERROR:
            if use_colors:
                print(colored.error(f"❌ BŁĄD: {content}"))
            else:
                print(f"❌ BŁĄD: {content}")
    
    def send_message(self, message):
        """Wysyła wiadomość do serwera"""
        try:
            if not self.connected:
                return False
                
            # Sprawdź czy wiadomość nie jest pusta
            if not message or not message.strip():
                return True
                
            self.socket.send(message.encode('utf-8'))
            return True
        except socket.error as e:
            print(f"❌ Błąd wysyłania: {e}")
            self.connected = False
            return False
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd wysyłania: {e}")
            return False
    
    def disconnect(self):
        """Rozłącza się z serwerem"""
        if self.connected:
            self.connected = False
            
            try:
                # Wyślij wiadomość o rozłączeniu jeśli to możliwe
                if self.nick:
                    leave_message = Protocol.create_message(MessageType.LEAVE, self.nick)
                    self.socket.send(leave_message.encode('utf-8'))
                    time.sleep(0.1)  # Krótka pauza na dostarczenie
            except:
                pass
            
            try:
                self.socket.close()
            except:
                pass
            
            print("👋 Rozłączono z serwerem")

def main():
    """Główna funkcja dla bezpośredniego uruchomienia"""
    print("🗨️ Komunikator IP - Klient")
    print("=" * 30)
    
    # Sprawdź dostępność szyfrowania
    try:
        from common.encryption import is_encryption_available
        if is_encryption_available():
            print("🔒 Szyfrowanie: dostępne")
        else:
            print("⚠️ Szyfrowanie: niedostępne (zainstaluj 'cryptography')")
    except ImportError:
        print("⚠️ Szyfrowanie: moduł niedostępny")
    
    print("=" * 30)
    
    # Pobierz adres serwera
    host = input("Adres serwera (Enter = localhost): ").strip()
    if not host:
        host = 'localhost'
    
    try:
        port = input("Port serwera (Enter = 12345): ").strip()
        port = int(port) if port else 12345
    except ValueError:
        port = 12345
    
    # Pobierz nick
    nick = input("Twój nick: ").strip()
    while not nick or len(nick) < 2:
        print("❌ Nick musi mieć co najmniej 2 znaki")
        nick = input("Twój nick: ").strip()
    
    # Utwórz klienta i połącz
    client = ChatClient(host, port)
    client.nick = nick
    
    if client.connect():
        # Wyślij JOIN message
        join_message = Protocol.create_message(MessageType.JOIN, nick)
        if client.send_message(join_message):
            print(f"📤 Wysłano żądanie dołączenia jako {nick}")
            
            # Uruchom wątek odbierający
            client.receiving_thread = threading.Thread(target=client.receive_messages)
            client.receiving_thread.daemon = True
            client.receiving_thread.start()
            
            # Poczekaj na uwierzytelnienie
            print("⏳ Oczekiwanie na uwierzytelnienie...")
            for i in range(10):  # Max 10 sekund oczekiwania
                if client.authenticated:
                    break
                time.sleep(1)
            
            if client.authenticated:
                print("\n✅ Uwierzytelniono pomyślnie!")
                print("💬 Możesz teraz pisać wiadomości...")
                print("⚡ Komendy: /help, /list, /quit")
                print()
                
                # Główna pętla czatu
                try:
                    while client.connected:
                        user_input = input()
                        
                        if not user_input.strip():
                            continue
                        
                        if user_input.strip().lower() == '/quit':
                            break
                        
                        # Wyślij wiadomość
                        message = Protocol.create_message(MessageType.MESSAGE, nick, user_input)
                        if not client.send_message(message):
                            print("❌ Błąd wysyłania wiadomości")
                            break
                            
                except KeyboardInterrupt:
                    print("\n🛑 Przerwano przez użytkownika")
                except EOFError:
                    print("\n🛑 Zakończono wprowadzanie")
            else:
                print("❌ Nie udało się uwierzytelnić w ciągu 10 sekund")
        
        client.disconnect()
    else:
        print("❌ Nie udało się połączyć z serwerem")

if __name__ == "__main__":
    main()