#!/usr/bin/env python3
"""
Launcher dla klienta komunikatora IP (wersja konsolowa)
"""

import sys
import os

# Dodaj katalog główny do ścieżki
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importuj i uruchom klienta
if __name__ == "__main__":
    print("🗨️ Uruchamianie klienta komunikatora IP...")
    try:
        from client.client import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 Klient zatrzymany przez użytkownika")
    except Exception as e:
        print(f"❌ Błąd uruchamiania klienta: {e}")
        input("Naciśnij Enter aby zamknąć...")