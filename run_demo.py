#!/usr/bin/env python3
"""
Demo launcher - pokazuje możliwości komunikatora
"""

import sys
import os
import time
import threading

# Dodaj katalog główny do ścieżki
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from common.colors import colored, print_success, print_info, print_warning
from common.stats import server_stats
from common.history import HistoryManager

def print_banner():
    """Wyświetla banner aplikacji"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🗨️  KOMUNIKATOR IP                       ║
║                     Michał Pawlik                            ║
║                                                              ║
║  Features:                                                   ║
║  ✅ Komunikacja w czasie rzeczywistym                        ║
║  ✅ Obsługa wielu klientów                                   ║
║  ✅ Interfejs konsolowy i graficzny                          ║
║  ✅ System logowania                                         ║
║  ✅ Historia wiadomości                                      ║
║  ✅ Statystyki serwera                                       ║
║  ✅ Kolorowy interfejs                                       ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(colored.cyan(banner))

def show_menu():
    """Pokazuje menu główne"""
    print("\n" + colored.bold("🚀 WYBIERZ OPCJĘ:"))
    print("=" * 50)
    print(colored.green("1. 🖥️  Uruchom serwer"))
    print(colored.blue("2. 💻 Uruchom klienta konsolowego"))
    print(colored.magenta("3. 🎨 Uruchom klienta GUI"))
    print(colored.yellow("4. 📊 Pokaż demo statystyk"))
    print(colored.cyan("5. 🎨 Demo kolorów"))
    print(colored.bright_blue("6. 📝 Demo historii"))
    print(colored.bright_red("0. ❌ Wyjście"))
    print("=" * 50)

def demo_stats():
    """Demonstracja systemu statystyk"""
    print_info("Demo systemu statystyk...")
    
    # Symuluj trochę danych
    server_stats.record_connection("Jan")
    server_stats.record_connection("Anna") 
    server_stats.record_connection("Tomek")
    
    for i in range(20):
        server_stats.record_message()
        if i % 3 == 0:
            server_stats.record_command("/list")
        elif i % 5 == 0:
            server_stats.record_command("/help")
    
    server_stats.update_peak_users(3)
    
    print("\n" + server_stats.get_formatted_stats())
    print("\n" + server_stats.get_activity_graph())
    
    export_path = server_stats.export_stats()
    if export_path:
        print_success(f"Statystyki wyeksportowane do: {export_path}")

def demo_colors():
    """Demonstracja kolorów"""
    print_info("Demo kolorów w konsoli...")
    
    from common.colors import demo_colors
    demo_colors()

def demo_history():
    """Demonstracja systemu historii"""
    print_info("Demo systemu historii...")
    
    history = HistoryManager()
    
    # Dodaj przykładowe wiadomości
    history.add_message("Jan", "Witajcie!", "message")
    history.add_message("Anna", "Cześć Jan!", "message")
    history.add_message("Tomek", "Jak sprawy?", "message")
    history.add_message("system", "Anna dołączyła do czatu", "system")
    history.add_message("Jan", "Wszystko dobrze, dzięki!", "message")
    
    print("\n📝 Przykładowa historia:")
    recent = history.get_recent_messages(5)
    for msg in recent:
        timestamp = msg['timestamp'][:19]  # YYYY-MM-DD HH:MM:SS
        if msg['type'] == 'system':
            print(colored.system(f"[{timestamp}] SYSTEM: {msg['content']}"))
        else:
            print(colored.user_message(msg['user'], f"[{timestamp}] {msg['content']}"))
    
    # Pokaż statystyki
    stats = history.get_stats()
    print(f"\n📊 Statystyki historii:")
    print(f"   Całkowite wiadomości: {stats['total']}")
    print(f"   Unikalni użytkownicy: {stats['unique_users']}")
    print(f"   Najaktywniejszy: {stats['most_active_user']} ({stats['most_active_count']} wiadomości)")
    
    # Eksportuj
    export_path = history.export_to_txt()
    if export_path:
        print_success(f"Historia wyeksportowana do: {export_path}")

def run_server():
    """Uruchamia serwer"""
    print_info("Uruchamianie serwera...")
    try:
        from server.server import main as server_main
        server_main()
    except KeyboardInterrupt:
        print_warning("Serwer zatrzymany przez użytkownika")
    except Exception as e:
        print(colored.error(f"Błąd serwera: {e}"))

def run_console_client():
    """Uruchamia klienta konsolowego"""
    print_info("Uruchamianie klienta konsolowego...")
    try:
        from client.client import main as client_main
        client_main()
    except Exception as e:
        print(colored.error(f"Błąd klienta: {e}"))

def run_gui_client():
    """Uruchamia klienta GUI"""
    print_info("Uruchamianie GUI...")
    try:
        from client.gui import main as gui_main
        gui_main()
    except Exception as e:
        print(colored.error(f"Błąd GUI: {e}"))

def main():
    """Główna funkcja"""
    print_banner()
    
    while True:
        show_menu()
        
        try:
            choice = input(colored.bold("\n🔍 Wybierz opcję (0-6): ")).strip()
            
            if choice == "0":
                print_success("Do widzenia! 👋")
                break
            elif choice == "1":
                run_server()
            elif choice == "2":
                run_console_client()
            elif choice == "3":
                run_gui_client()
            elif choice == "4":
                demo_stats()
            elif choice == "5":
                demo_colors()
            elif choice == "6":
                demo_history()
            else:
                print_warning("Nieprawidłowy wybór! Spróbuj ponownie.")
                
        except KeyboardInterrupt:
            print_warning("\nPrzerwano przez użytkownika")
            break
        except EOFError:
            print_warning("\nZakończono")
            break
        
        # Mała pauza przed powrotem do menu
        input(colored.dim("\nNaciśnij Enter aby kontynuować..."))

if __name__ == "__main__":
    main()