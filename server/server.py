import socket
import threading
import sys
import os
import datetime
import logging

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType
from client_handler import ClientHandler

class ChatServer:
    def __init__(self, host='localhost', port=12345, log_file='server.log'):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Słownik przechowujący klientów {nick: ClientHandler}
        self.clients = {}
        self.clients_lock = threading.Lock()
        
        self.running = False
        self.max_clients = 50  # Maksymalna liczba klientów
        
        # Konfiguracja logowania
        self.setup_logging(log_file)
        
        # Statystyki serwera
        self.stats = {
            'start_time': None,
            'total_connections': 0,
            'total_messages': 0,
            'peak_users': 0
        }
    
    def setup_logging(self, log_file):
        """Konfiguruje system logowania"""
        # Utwórz katalog logs jeśli nie istnieje
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_path = os.path.join(log_dir, log_file)
        
        # Konfiguracja loggera
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log(self, message, level='info'):
        """Loguje wiadomość"""
        if level == 'info':
            self.logger.info(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)
        elif level == 'debug':
            self.logger.debug(message)
    
    def start(self):
        """Uruchamia serwer"""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            self.stats['start_time'] = datetime.datetime.now()
            
            self.log(f"🚀 Serwer uruchomiony na {self.host}:{self.port}")
            self.log(f"Maksymalna liczba klientów: {self.max_clients}")
            self.log("Oczekiwanie na połączenia...")
            
            # Uruchom wątek statystyk
            stats_thread = threading.Thread(target=self.stats_worker)
            stats_thread.daemon = True
            stats_thread.start()
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    
                    # Sprawdź limit klientów
                    with self.clients_lock:
                        if len(self.clients) >= self.max_clients:
                            self.log(f"Odrzucono połączenie z {address} - przekroczono limit klientów", 'warning')
                            client_socket.close()
                            continue
                    
                    self.log(f"📞 Nowe połączenie z {address}")
                    self.stats['total_connections'] += 1
                    
                    # Tworzymy handler dla klienta
                    client_handler = ClientHandler(client_socket, address, self)
                    client_thread = threading.Thread(target=client_handler.handle)
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        self.log(f"❌ Błąd podczas akceptowania połączenia: {e}", 'error')
                    break
                except Exception as e:
                    self.log(f"❌ Nieoczekiwany błąd: {e}", 'error')
                    break
                    
        except Exception as e:
            self.log(f"❌ Błąd serwera: {e}", 'error')
        finally:
            self.shutdown()
    
    def stats_worker(self):
        """Wątek do wyświetlania statystyk co 5 minut"""
        import time
        while self.running:
            time.sleep(300)  # 5 minut
            if self.running:
                self.print_stats()
    
    def print_stats(self):
        """Wyświetla statystyki serwera"""
        uptime = datetime.datetime.now() - self.stats['start_time']
        with self.clients_lock:
            current_users = len(self.clients)
        
        self.log(f"📊 Statystyki serwera:")
        self.log(f"   Aktywni użytkownicy: {current_users}")
        self.log(f"   Szczyt użytkowników: {self.stats['peak_users']}")
        self.log(f"   Całkowite połączenia: {self.stats['total_connections']}")
        self.log(f"   Całkowite wiadomości: {self.stats['total_messages']}")
        self.log(f"   Czas działania: {uptime}")
    
    def add_client(self, nick: str, client_handler):
        """Dodaje klienta do listy aktywnych"""
        with self.clients_lock:
            if nick in self.clients:
                return False  # Nick zajęty
            self.clients[nick] = client_handler
            
            # Aktualizuj statystyki
            current_count = len(self.clients)
            if current_count > self.stats['peak_users']:
                self.stats['peak_users'] = current_count
        
        # Powiadom wszystkich o nowym użytkowniku
        join_message = Protocol.create_system_message(f"{nick} dołączył do czatu")
        self.broadcast_message(join_message, exclude_user=nick)
        
        # Wyślij listę użytkowników do nowego klienta
        user_list = list(self.clients.keys())
        list_message = Protocol.create_user_list_message(user_list)
        client_handler.send_message(list_message)
        
        self.log(f"✅ Użytkownik {nick} dołączył. Aktywni użytkownicy: {len(self.clients)}")
        return True
    
    def remove_client(self, nick: str):
        """Usuwa klienta z listy aktywnych"""
        with self.clients_lock:
            if nick in self.clients:
                del self.clients[nick]
                
        # Powiadom pozostałych o odejściu
        leave_message = Protocol.create_system_message(f"{nick} opuścił czat")
        self.broadcast_message(leave_message)
        
        self.log(f"👋 Użytkownik {nick} opuścił czat. Aktywni użytkownicy: {len(self.clients)}")
    
    def broadcast_message(self, message: str, exclude_user: str = None):
        """Wysyła wiadomość do wszystkich klientów"""
        self.stats['total_messages'] += 1
        
        with self.clients_lock:
            disconnected_clients = []
            successful_sends = 0
            
            for nick, client_handler in self.clients.items():
                if exclude_user and nick == exclude_user:
                    continue
                    
                if client_handler.send_message(message):
                    successful_sends += 1
                else:
                    disconnected_clients.append(nick)
            
            # Usuń rozłączonych klientów
            for nick in disconnected_clients:
                self.log(f"Usuwam rozłączonego klienta: {nick}", 'warning')
                del self.clients[nick]
        
        if disconnected_clients:
            self.log(f"Broadcast do {successful_sends} klientów, {len(disconnected_clients)} rozłączonych")
    
    def broadcast_system_message(self, content: str):
        """Wysyła wiadomość systemową do wszystkich"""
        system_msg = Protocol.create_system_message(content)
        self.broadcast_message(system_msg)
        self.log(f"Wiadomość systemowa: {content}")
    
    def get_user_list(self):
        """Zwraca listę aktywnych użytkowników"""
        with self.clients_lock:
            return list(self.clients.keys())
    
    def get_client_count(self):
        """Zwraca liczbę aktywnych klientów"""
        with self.clients_lock:
            return len(self.clients)
    
    def kick_user(self, nick: str, reason: str = "Wyrzucony przez administratora"):
        """Wyrzuca użytkownika z serwera"""
        with self.clients_lock:
            if nick in self.clients:
                client_handler = self.clients[nick]
                kick_msg = Protocol.create_system_message(f"Zostałeś wyrzucony: {reason}")
                client_handler.send_message(kick_msg)
                client_handler.disconnect()
                self.log(f"Użytkownik {nick} został wyrzucony: {reason}")
                return True
        return False
    
    def shutdown(self):
        """Wyłącza serwer"""
        self.log("🛑 Rozpoczynam wyłączanie serwera...")
        self.running = False
        
        # Powiadom wszystkich klientów o wyłączeniu
        shutdown_msg = Protocol.create_system_message("Serwer zostanie wyłączony za 5 sekund...")
        self.broadcast_message(shutdown_msg)
        
        import time
        time.sleep(1)  # Daj czas na dostarczenie wiadomości
        
        # Zamknij wszystkie połączenia klientów
        with self.clients_lock:
            for nick, client_handler in self.clients.items():
                goodbye_msg = Protocol.create_system_message("Serwer został wyłączony")
                try:
                    client_handler.send_message(goodbye_msg)
                except:
                    pass
                client_handler.disconnect()
            self.clients.clear()
        
        # Zamknij socket serwera
        try:
            self.socket.close()
        except:
            pass
        
        # Wyświetl końcowe statystyki
        self.print_stats()
        self.log("🛑 Serwer wyłączony")

def main():
    # Pobierz parametry z linii komend
    import argparse
    parser = argparse.ArgumentParser(description='Serwer komunikatora IP')
    parser.add_argument('--host', default='localhost', help='Adres hosta (domyślnie: localhost)')
    parser.add_argument('--port', type=int, default=12345, help='Port serwera (domyślnie: 12345)')
    parser.add_argument('--max-clients', type=int, default=50, help='Max klientów (domyślnie: 50)')
    parser.add_argument('--log-file', default='server.log', help='Plik logów (domyślnie: server.log)')
    
    args = parser.parse_args()
    
    server = ChatServer(args.host, args.port, args.log_file)
    server.max_clients = args.max_clients
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Otrzymano sygnał przerwania...")
        server.shutdown()

if __name__ == "__main__":
    main()