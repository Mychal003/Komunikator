#!/usr/bin/env python3
"""
Launcher dla klienta komunikatora IP (wersja konsolowa)
Naprawiona wersja z obsługą błędów i debug
"""

import sys
import os
import socket
import threading
import time

# Dodaj katalog główny do ścieżki
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_server_connection(host='localhost', port=12345):
    """Testuje czy serwer TCP jest dostępny"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    """Główna funkcja z lepszą obsługą błędów"""
    print("🗨️ Uruchamianie klienta komunikatora IP...")
    print("=" * 50)
    
    # Sprawdź dostępność serwera TCP
    if not test_server_connection():
        print("❌ Serwer TCP nie jest dostępny!")
        print("💡 Upewnij się, że serwer działa: python start_server.py")
        input("Naciśnij Enter aby spróbować połączyć mimo to...")
    else:
        print("✅ Serwer TCP jest dostępny")
    
    try:
        # Importuj i uruchom klienta konsolowego
        from client.client import ChatClient
        
        print("\n🔧 Konfiguracja połączenia:")
        
        # Pobierz parametry połączenia
        host = input("Host serwera (Enter = localhost): ").strip()
        if not host:
            host = 'localhost'
        
        port_input = input("Port serwera (Enter = 12345): ").strip()
        try:
            port = int(port_input) if port_input else 12345
        except ValueError:
            print("❌ Nieprawidłowy port, używam 12345")
            port = 12345
        
        nick = input("Twój nick: ").strip()
        while not nick or len(nick) < 2:
            print("❌ Nick musi mieć co najmniej 2 znaki")
            nick = input("Twój nick: ").strip()
        
        print(f"\n🚀 Łączenie z {host}:{port} jako {nick}...")
        
        # Utwórz i połącz klienta
        client = ChatClient(host, port)
        client.nick = nick  # Ustaw nick przed połączeniem
        
        if client.connect():
            print("✅ Połączono z serwerem!")
            
            # Prześlij nick
            from common.protocol import Protocol, MessageType
            join_message = Protocol.create_message(MessageType.JOIN, nick)
            client.send_message(join_message)
            
            print("\n" + "="*50)
            print("💬 CZAT URUCHOMIONY")
            print("="*50)
            print("📝 Wpisz wiadomość i naciśnij Enter")
            print("⚡ Dostępne komendy:")
            print("   /help - pomoc")
            print("   /list - lista użytkowników") 
            print("   /quit - wyjście")
            print("="*50)
            print()
            
            # Uruchom obsługę wiadomości w osobnym wątku
            receive_thread = threading.Thread(target=client.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Główna pętla wprowadzania wiadomości
            try:
                while client.connected:
                    try:
                        user_input = input()
                        
                        if not user_input.strip():
                            continue
                        
                        if user_input.strip().lower() == '/quit':
                            break
                        
                        # Wyślij wiadomość
                        if user_input.startswith('/'):
                            # Komenda
                            message = Protocol.create_message(MessageType.MESSAGE, nick, user_input)
                        else:
                            # Zwykła wiadomość
                            message = Protocol.create_message(MessageType.MESSAGE, nick, user_input)
                        
                        if not client.send_message(message):
                            print("❌ Błąd wysyłania wiadomości")
                            break
                            
                    except KeyboardInterrupt:
                        print("\n🛑 Otrzymano Ctrl+C...")
                        break
                    except EOFError:
                        print("\n🛑 Zakończono wprowadzanie...")
                        break
                        
            finally:
                print("\n👋 Rozłączanie...")
                client.disconnect()
                
        else:
            print("❌ Nie udało się połączyć z serwerem")
            print("\n🔧 Możliwe przyczyny:")
            print("   • Serwer nie jest uruchomiony")
            print("   • Nieprawidłowy adres lub port")
            print("   • Firewall blokuje połączenie")
            print("   • Serwer jest przeciążony")
            
    except ImportError as e:
        print(f"❌ Błąd importu: {e}")
        print("💡 Sprawdź czy wszystkie pliki są w odpowiednich katalogach")
        
    except KeyboardInterrupt:
        print("\n🛑 Klient zatrzymany przez użytkownika")
        
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd: {e}")
        print("\n🐛 Szczegóły błędu:")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n📊 Sesja zakończona")
        input("Naciśnij Enter aby zamknąć...")

if __name__ == "__main__":
    main()