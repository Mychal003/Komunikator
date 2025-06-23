import socket
import threading
import sys
import os

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
    
    def connect(self):
        """Łączy się z serwerem"""
        try:
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
            
            # Uruchom wątek odbierający wiadomości
            self.receiving_thread = threading.Thread(target=self.receive_messages)
            self.receiving_thread.daemon = True
            self.receiving_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Nie można połączyć się z serwerem: {e}")
            return False
    
    def receive_messages(self):
        """Odbiera wiadomości z serwera"""
        while self.connected:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = Protocol.parse_message(data)
                self.display_message(message)
                
            except socket.error:
                break
        
        self.connected = False
        print("\n🔌 Połączenie z serwerem zostało przerwane")
    
    def display_message(self, message):
        """Wyświetla otrzymaną wiadomość"""
        msg_type = message.get('type', '')
        user = message.get('user', '')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        encrypted = message.get('encrypted', False)
        
        if msg_type == MessageType.MESSAGE:
            # Pokaż ikonę zamka dla zaszyfrowanych wiadomości
            encryption_icon = "🔒" if encrypted else ""
            print(f"[{timestamp}] {user}: {content} {encryption_icon}")
            
        elif msg_type == MessageType.SYSTEM:
            print(f"🔔 SYSTEM: {content}")
            
        elif msg_type == MessageType.USER_LIST:
            # Lista użytkowników jest w content jako JSON
            import json
            try:
                users = json.loads(content)
                print(f"👥 Użytkownicy online: {', '.join(users)}")
            except:
                print(f"👥 Lista użytkowników: {content}")
                
        elif msg_type == MessageType.ERROR:
            print(f"❌ BŁĄD: {content}")
    
    def login(self):
        """Proces logowania"""
        while True:
            nick = input("Podaj swój nick: ").strip()
            if nick:
                self.nick = nick
                # Wyślij wiadomość JOIN
                join_message = Protocol.create_message(MessageType.JOIN, nick)
                self.send_message(join_message)
                break
            else:
                print("Nick nie może być pusty!")
    
    def send_message(self, message):
        """Wysyła wiadomość do serwera"""
        try:
            self.socket.send(message.encode('utf-8'))
            return True
        except socket.error:
            self.connected = False
            return False
    
    def start_chat(self):
        """Główna pętla czatu"""
        print("\n🎉 Jesteś w czacie! Wpisz /help aby zobaczyć dostępne komendy.")
        print("Wpisz /quit aby wyjść z czatu.")
        
        # Pokaż status szyfrowania
        try:
            from common.encryption import is_encryption_available
            if is_encryption_available() and Protocol.encryption_enabled:
                print("🔒 Twoje wiadomości są szyfrowane end-to-end!")
            else:
                print("⚠️ Komunikacja NIE jest szyfrowana")
        except:
            print("⚠️ Nie można sprawdzić statusu szyfrowania")
        
        print()  # Pusta linia
        
        try:
            while self.connected:
                try:
                    # Pobierz wiadomość od użytkownika
                    user_input = input()
                    
                    if not user_input.strip():
                        continue
                    
                    if user_input.strip() == '/quit':
                        # Wyślij wiadomość o rozłączeniu
                        leave_message = Protocol.create_message(MessageType.LEAVE, self.nick)
                        self.send_message(leave_message)
                        break
                    
                    elif user_input.startswith('/'):
                        # Komenda
                        if user_input.strip() == '/status':
                            # Pokaż status szyfrowania
                            self.show_encryption_status()
                        else:
                            command_message = Protocol.create_message(MessageType.MESSAGE, self.nick, user_input)
                            self.send_message(command_message)
                    
                    else:
                        # Zwykła wiadomość
                        chat_message = Protocol.create_message(MessageType.MESSAGE, self.nick, user_input)
                        self.send_message(chat_message)
                        
                except KeyboardInterrupt:
                    print("\n🛑 Otrzymano sygnał przerwania...")
                    break
                except EOFError:
                    print("\n🛑 Zakończono wprowadzanie...")
                    break
                    
        finally:
            self.disconnect()
    
    def show_encryption_status(self):
        """Pokazuje status szyfrowania"""
        try:
            from common.encryption import is_encryption_available, default_encryption
            
            print("🔒 STATUS SZYFROWANIA:")
            print(f"   Biblioteka dostępna: {'✅' if is_encryption_available() else '❌'}")
            print(f"   Szyfrowanie włączone: {'✅' if Protocol.encryption_enabled else '❌'}")
            
            if is_encryption_available():
                info = default_encryption.get_encryption_info()
                print(f"   Algorytm: {info['algorithm']}")
                print(f"   Wyprowadzanie klucza: {info['key_derivation']}")
                print(f"   Iteracje PBKDF2: {info['iterations']}")
            
            print()
        except ImportError:
            print("❌ Moduł szyfrowania niedostępny")
        except Exception as e:
            print(f"❌ Błąd sprawdzania szyfrowania: {e}")
    
    def disconnect(self):
        """Rozłącza się z serwerem"""
        if self.connected:
            self.connected = False
            
            try:
                # Wyślij wiadomość o rozłączeniu jeśli to możliwe
                leave_message = Protocol.create_message(MessageType.LEAVE, self.nick)
                self.socket.send(leave_message.encode('utf-8'))
            except:
                pass
            
            try:
                self.socket.close()
            except:
                pass
            
            print("👋 Rozłączono z serwerem")

def main():
    print("🗨️  Komunikator IP - Klient")
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
    
    # Utwórz klienta i połącz
    client = ChatClient(host, port)
    
    if client.connect():
        client.login()
        client.start_chat()
    else:
        print("❌ Nie udało się połączyć z serwerem")

if __name__ == "__main__":
    main()