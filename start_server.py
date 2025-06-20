#!/usr/bin/env python3
"""
Launcher dla serwera komunikatora IP
"""

import sys
import os

# Dodaj katalog główny do ścieżki
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importuj i uruchom serwer
if __name__ == "__main__":
    print("🗨️ Uruchamianie serwera komunikatora IP...")
    try:
        from server.server import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 Serwer zatrzymany przez użytkownika")
    except Exception as e:
        print(f"❌ Błąd uruchamiania serwera: {e}")
        input("Naciśnij Enter aby zamknąć...")