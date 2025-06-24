import socket
import threading
import sys
import os
import datetime
import logging

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType
from common.colors import print_success, print_info, print_warning, colored
from common.history import HistoryManager
from common.stats import server_stats
from .client_handler import ClientHandler

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
        
        # Nowe moduły
        self.history = HistoryManager()
        self.use_colors = True
        
        # Statystyki serwera (stare + nowe)
        self.stats = {
            'start_time': None,
            'total_connections': 0,
            'total_messages': 0,
            'peak_users': 0
        }
        
        # Inicjalizuj nowy system statystyk
        server_stats.session_stats['start_time'] = datetime.datetime.now()
    
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
        """Loguje wiadomość z kolorami"""
        # Kolorowe logowanie w konsoli
        if level == 'info':
            self.logger.info(message)
            if self.use_colors:
                print_info(message)
        elif level == 'warning':
            self.logger.warning(message)
            if self.use_colors:
                print_warning(message)
        elif level == 'error':
            self.logger.error(message)
            if self.use_colors:
                print(colored.error(f"❌ {message}"))
        elif level == 'success':
            self.logger.info(message)
            if self.use_colors:
                print_success(message)
        elif level == 'debug':
            self.logger.debug(message)
    
    def start(self):
        """Uruchamia serwer"""
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            self.stats['start_time'] = datetime.datetime.now()
            
            # Włącz szyfrowanie jeśli dostępne
            try:
                from common.encryption import is_encryption_available
                if is_encryption_available():
                    # Hasło szyfrowania - w produkcji wczytaj z bezpiecznego pliku
                    encryption_password = "komunikator_secure_2025"
                    Protocol.enable_encryption(encryption_password)
                    self.log("🔒 Szyfrowanie komunikacji włączone", 'success')
                else:
                    self.log("⚠️ Szyfrowanie niedostępne - zainstaluj 'pip install cryptography'", 'warning')
            except ImportError:
                self.log("⚠️ Moduł szyfrowania niedostępny", 'warning')
            
            # Kolorowe powitanie
            if self.use_colors:
                print(colored.cyan("\n" + "="*60))
                print(colored.cyan("🗨️  KOMUNIKATOR IP - SERWER URUCHOMIONY"))
                print(colored.cyan("="*60))
                print(colored.green(f"🚀 Adres: {self.host}:{self.port}"))
                print(colored.yellow(f"👥 Maksymalnie klientów: {self.max_clients}"))
                print(colored.blue("📂 Logi zapisywane w folderze: logs/"))
                print(colored.magenta("🎨 Kolory: włączone"))
                
                # Status szyfrowania
                try:
                    from common.encryption import is_encryption_available
                    encryption_status = "włączone" if is_encryption_available() else "niedostępne"
                    print(colored.bright_red(f"🔒 Szyfrowanie: {encryption_status}"))
                except:
                    print(colored.bright_red("🔒 Szyfrowanie: niedostępne"))
                    
                print(colored.cyan("="*60 + "\n"))
            
            self.log(f"Serwer uruchomiony na {self.host}:{self.port}", 'success')
            self.log("Oczekiwanie na połączenia...", 'info')
            
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
                            self.log(f"Odrzucono połączenie z {address} - przekroczono limit", 'warning')
                            client_socket.close()
                            continue
                    
                    self.log(f"📞 Nowe połączenie z {address}", 'info')
                    self.stats['total_connections'] += 1
                    server_stats.record_connection()
                    
                    # Tworzymy handler dla klienta
                    client_handler = ClientHandler(client_socket, address, self)
                    client_thread = threading.Thread(target=client_handler.handle)
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        self.log(f"Błąd podczas akceptowania połączenia: {e}", 'error')
                    break
                except Exception as e:
                    self.log(f"Nieoczekiwany błąd: {e}", 'error')
                    break
                
        except Exception as e:
            self.log(f"Błąd serwera: {e}", 'error')
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
        
        # Używaj nowego systemu statystyk
        current_stats = server_stats.get_current_stats()
        
        self.log("📊 Statystyki serwera:", 'info')
        self.log(f"   ⏰ Czas działania: {uptime}", 'info')
        self.log(f"   👥 Aktywni użytkownicy: {current_users}", 'info')
        self.log(f"   🏆 Szczyt użytkowników: {current_stats['peak_users']}", 'info')
        self.log(f"   🔗 Całkowite połączenia: {current_stats['connections']}", 'info')
        self.log(f"   💬 Całkowite wiadomości: {current_stats['messages_sent']}", 'info')
        self.log(f"   📈 Wiadomości/godz: {current_stats['messages_per_hour']}", 'info')
    
    def add_client(self, nick: str, client_handler):
        """Dodaje klienta do listy aktywnych - ZAKTUALIZOWANA WERSJA"""
        with self.clients_lock:
            if nick in self.clients:
                return False  # Nick zajęty
            self.clients[nick] = client_handler
            
            # Aktualizuj statystyki
            current_count = len(self.clients)
            if current_count > self.stats['peak_users']:
                self.stats['peak_users'] = current_count
            
            # Aktualizuj nowy system statystyk
            server_stats.update_peak_users(current_count)
            server_stats.record_connection(nick)
        
        # Dodaj do historii
        self.history.add_message("system", f"{nick} dołączył do czatu", "system")
        
        # Powiadom wszystkich o nowym użytkowniku
        join_message = Protocol.create_system_message(f"{nick} dołączył do czatu")
        self.broadcast_message(join_message, exclude_user=nick)
        
        # WAŻNE: Wyślij aktualną listę użytkowników do WSZYSTKICH klientów
        self.broadcast_user_list()
        
        self.log(f"✅ {nick} dołączył. Aktywni: {len(self.clients)}", 'success')
        return True
    
    def remove_client(self, nick: str):
        """Usuwa klienta z listy aktywnych - ZAKTUALIZOWANA WERSJA"""
        with self.clients_lock:
            if nick in self.clients:
                del self.clients[nick]
        
        # Dodaj do historii
        self.history.add_message("system", f"{nick} opuścił czat", "system")
        
        # Powiadom pozostałych o odejściu
        leave_message = Protocol.create_system_message(f"{nick} opuścił czat")
        self.broadcast_message(leave_message)
        
        # WAŻNE: Wyślij aktualną listę użytkowników do WSZYSTKICH klientów
        self.broadcast_user_list()
        
        self.log(f"👋 {nick} opuścił czat. Aktywni: {len(self.clients)}", 'info')
    
    def broadcast_message(self, message: str, exclude_user: str = None, save_to_history: bool = True):
        """Wysyła wiadomość do wszystkich klientów"""
        self.stats['total_messages'] += 1
        server_stats.record_message()
        
        # Zapisz do historii (opcjonalnie)
        if save_to_history and exclude_user:
            # To jest zwykła wiadomość użytkownika
            try:
                parsed = Protocol.parse_message(message)
                if parsed['type'] == MessageType.MESSAGE:
                    self.history.add_message(parsed['user'], parsed['content'], "message")
            except:
                pass
        
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
            self.log(f"Broadcast: {successful_sends} OK, {len(disconnected_clients)} rozłączonych", 'warning')
    
    def broadcast_system_message(self, content: str):
        """Wysyła wiadomość systemową do wszystkich"""
        system_msg = Protocol.create_system_message(content)
        self.broadcast_message(system_msg, save_to_history=False)
        self.log(f"📢 System: {content}", 'info')
    
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
                self.log(f"👮 {nick} został wyrzucony: {reason}", 'warning')
                return True
        return False
    
    def handle_admin_command(self, command: str) -> str:
        """Obsługuje komendy administratora"""
        cmd_parts = command.strip().lower().split()
        
        if not cmd_parts:
            return "Brak komendy"
        
        base_cmd = cmd_parts[0]
        
        if base_cmd == "/stats":
            return server_stats.get_formatted_stats()
        
        elif base_cmd == "/history":
            if len(cmd_parts) > 1 and cmd_parts[1] == "export":
                path = self.history.export_to_txt()
                return f"Historia wyeksportowana do: {path}" if path else "Błąd eksportu"
            else:
                recent = self.history.get_recent_messages(10)
                result = "📝 Ostatnie 10 wiadomości:\n"
                for msg in recent:
                    result += f"[{msg['timestamp'][:19]}] {msg['user']}: {msg['content']}\n"
                return result
        
        elif base_cmd == "/kick" and len(cmd_parts) > 1:
            nick = cmd_parts[1]
            reason = " ".join(cmd_parts[2:]) if len(cmd_parts) > 2 else "Komenda administratora"
            success = self.kick_user(nick, reason)
            return f"Użytkownik {nick} {'wyrzucony' if success else 'nie znaleziony'}"
        
        elif base_cmd == "/broadcast" and len(cmd_parts) > 1:
            message = " ".join(cmd_parts[1:])
            self.broadcast_system_message(f"📢 OGŁOSZENIE: {message}")
            return f"Wysłano ogłoszenie: {message}"
        
        elif base_cmd == "/save":
            # Zapisz statystyki i historię
            stats_saved = server_stats.save_session_stats()
            history_saved = self.history.save_history()
            return f"Zapisano: statystyki={'✅' if stats_saved else '❌'}, historia={'✅' if history_saved else '❌'}"
        
        elif base_cmd == "/encryption":
            try:
                from common.encryption import is_encryption_available, default_encryption
                if is_encryption_available():
                    info = default_encryption.get_encryption_info()
                    result = "🔒 INFORMACJE O SZYFROWANIU:\n"
                    result += f"   Dostępne: {'✅' if info['available'] else '❌'}\n"
                    result += f"   Algorytm: {info['algorithm']}\n"
                    result += f"   Wyprowadzanie klucza: {info['key_derivation']}\n"
                    result += f"   Iteracje PBKDF2: {info['iterations']}\n"
                    result += f"   Włączone: {'✅' if Protocol.encryption_enabled else '❌'}\n"
                    
                    # Dodatkowe statystyki
                    with self.clients_lock:
                        active_clients = len(self.clients)
                    result += f"   Chronionych połączeń: {active_clients}\n"
                    
                    return result
                else:
                    return "❌ Szyfrowanie niedostępne - zainstaluj 'pip install cryptography'"
            except ImportError:
                return "❌ Moduł szyfrowania niedostępny"
            except Exception as e:
                return f"❌ Błąd sprawdzania szyfrowania: {e}"
        
        elif base_cmd == "/help":
            # Lista wszystkich komend administratora
            help_text = """🔧 KOMENDY ADMINISTRATORA:
/stats - statystyki serwera
/history - ostatnie wiadomości
/history export - eksportuj historię
/kick <nick> [powód] - wyrzuć użytkownika
/broadcast <wiadomość> - ogłoszenie dla wszystkich
/save - zapisz statystyki i historię
/encryption - informacje o szyfrowaniu
/help - ta pomoc"""
            return help_text
        
        else:
            return f"Nieznana komenda administratora: {command}\nWpisz /help aby zobaczyć dostępne komendy."
    
    def shutdown(self):
        """Wyłącza serwer"""
        self.log("🛑 Rozpoczynam wyłączanie serwera...", 'warning')
        self.running = False
        
        # Zapisz statystyki końcowe
        server_stats.save_session_stats()
        self.history.save_history()
        
        # Powiadom wszystkich klientów o wyłączeniu
        shutdown_msg = Protocol.create_system_message("🛑 Serwer zostanie wyłączony za 3 sekundy...")
        self.broadcast_message(shutdown_msg, save_to_history=False)
        
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
        
        # Eksportuj końcowe raporty
        stats_path = server_stats.export_stats()
        history_path = self.history.export_to_txt()
        
        if self.use_colors:
            print(colored.cyan("\n" + "="*60))
            print(colored.cyan("📊 RAPORTY KOŃCOWE WYGENEROWANE:"))
            if stats_path:
                print(colored.green(f"   📈 Statystyki: {stats_path}"))
            if history_path:
                print(colored.blue(f"   📝 Historia: {history_path}"))
            print(colored.cyan("="*60))
        
        self.log("🛑 Serwer wyłączony", 'success')

    def broadcast_user_list(self):
        """Wysyła aktualną listę użytkowników do wszystkich klientów"""
        with self.clients_lock:
            user_list = list(self.clients.keys())
        
        if user_list:  # Tylko jeśli są jakiś użytkownicy
            user_list_message = Protocol.create_user_list_message(user_list)
            
            # Wyślij do wszystkich klientów
            with self.clients_lock:
                disconnected_clients = []
                for nick, client_handler in self.clients.items():
                    if not client_handler.send_message(user_list_message):
                        disconnected_clients.append(nick)
                
                # Usuń rozłączonych klientów
                for nick in disconnected_clients:
                    self.log(f"Usuwam rozłączonego klienta: {nick}", 'warning')
                    del self.clients[nick]

    def get_server_status(self):
        """Zwraca status serwera"""
        if self.stats['start_time']:
            uptime = datetime.datetime.now() - self.stats['start_time']
            uptime_str = str(uptime).split('.')[0]  # Bez mikrosekund
        else:
            uptime_str = "Nieznany"
            
        with self.clients_lock:
            current_users = len(self.clients)
        
        return {
            'uptime': uptime_str,
            'users': current_users,
            'messages': self.stats['total_messages'],
            'peak_users': self.stats['peak_users']
        }

    def change_user_nick(self, old_nick, new_nick):
        """Zmienia nick użytkownika"""
        with self.clients_lock:
            if old_nick in self.clients and new_nick not in self.clients:
                client_handler = self.clients[old_nick]
                del self.clients[old_nick]
                self.clients[new_nick] = client_handler
                
                # Wyślij aktualną listę użytkowników do wszystkich
                self.broadcast_user_list()
                return True
        return False

    def send_private_message(self, sender_nick, target_nick, message):
        """Wysyła prywatną wiadomość"""
        with self.clients_lock:
            if target_nick in self.clients:
                target_handler = self.clients[target_nick]
                
                # Wiadomość dla odbiorcy
                target_msg = Protocol.create_system_message(f"📥 [Prywatnie od {sender_nick}]: {message}")
                
                # Wyślij wiadomość
                if target_handler.send_message(target_msg):
                    # Dodaj do historii
                    self.history.add_message(f"PRIV_{sender_nick}", f"Do {target_nick}: {message}", "private")
                    return True
        return False

def main():
    # Pobierz parametry z linii komend
    import argparse
    parser = argparse.ArgumentParser(description='Serwer komunikatora IP')
    parser.add_argument('--host', default='localhost', help='Adres hosta (domyślnie: localhost)')
    parser.add_argument('--port', type=int, default=12345, help='Port serwera (domyślnie: 12345)')
    parser.add_argument('--max-clients', type=int, default=50, help='Max klientów (domyślnie: 50)')
    parser.add_argument('--log-file', default='server.log', help='Plik logów (domyślnie: server.log)')
    parser.add_argument('--no-colors', action='store_true', help='Wyłącz kolory w konsoli')
    
    args = parser.parse_args()
    
    server = ChatServer(args.host, args.port, args.log_file)
    server.max_clients = args.max_clients
    server.use_colors = not args.no_colors
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Otrzymano sygnał przerwania...")
        server.shutdown()

if __name__ == "__main__":
    main()