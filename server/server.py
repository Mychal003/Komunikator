import socket
import threading
import sys
import os

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType
from server.client_handler import ClientHandler

class ChatServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Słownik przechowujący klientów {nick: ClientHandler}
        self.clients = {}
        self.clients_lock = threading.Lock()
        
        self.running = False
    
    def start(self):
        """Uruchamia serwer"""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            print(f"🚀 Serwer uruchomiony na {self.host}:{self.port}")
            print("Oczekiwanie na połączenia...")
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    print(f"📞 Nowe połączenie z {address}")
                    
                    # Tworzymy handler dla klienta
                    client_handler = ClientHandler(client_socket, address, self)
                    client_thread = threading.Thread(target=client_handler.handle)
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error:
                    if self.running:
                        print("❌ Błąd podczas akceptowania połączenia")
                    break
                    
        except Exception as e:
            print(f"❌ Błąd serwera: {e}")
        finally:
            self.shutdown()
    
    def add_client(self, nick: str, client_handler):
        """Dodaje klienta do listy aktywnych"""
        with self.clients_lock:
            if nick in self.clients:
                return False  # Nick zajęty
            self.clients[nick] = client_handler
            
        # Powiadom wszystkich o nowym użytkowniku
        join_message = Protocol.create_system_message(f"{nick} dołączył do czatu")
        self.broadcast_message(join_message, exclude_user=nick)
        
        # Wyślij listę użytkowników do nowego klienta
        user_list = list(self.clients.keys())
        list_message = Protocol.create_user_list_message(user_list)
        client_handler.send_message(list_message)
        
        print(f"✅ Użytkownik {nick} dołączył. Aktywni użytkownicy: {len(self.clients)}")
        return True
    
    def remove_client(self, nick: str):
        """Usuwa klienta z listy aktywnych"""
        with self.clients_lock:
            if nick in self.clients:
                del self.clients[nick]
                
        # Powiadom pozostałych o odejściu
        leave_message = Protocol.create_system_message(f"{nick} opuścił czat")
        self.broadcast_message(leave_message)
        
        print(f"👋 Użytkownik {nick} opuścił czat. Aktywni użytkownicy: {len(self.clients)}")
    
    def broadcast_message(self, message: str, exclude_user: str = None):
        """Wysyła wiadomość do wszystkich klientów"""
        with self.clients_lock:
            disconnected_clients = []
            
            for nick, client_handler in self.clients.items():
                if exclude_user and nick == exclude_user:
                    continue
                    
                if not client_handler.send_message(message):
                    disconnected_clients.append(nick)
            
            # Usuń rozłączonych klientów
            for nick in disconnected_clients:
                del self.clients[nick]
    
    def get_user_list(self):
        """Zwraca listę aktywnych użytkowników"""
        with self.clients_lock:
            return list(self.clients.keys())
    
    def shutdown(self):
        """Wyłącza serwer"""
        self.running = False
        
        # Zamknij wszystkie połączenia klientów
        with self.clients_lock:
            for client_handler in self.clients.values():
                client_handler.disconnect()
            self.clients.clear()
        
        # Zamknij socket serwera
        try:
            self.socket.close()
        except:
            pass
        
        print("🛑 Serwer wyłączony")

def main():
    server = ChatServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Otrzymano sygnał przerwania...")
        server.shutdown()

if __name__ == "__main__":
    main()