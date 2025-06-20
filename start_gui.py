#!/usr/bin/env python3
"""
Launcher dla interfejsu graficznego komunikatora IP
"""

import sys
import os

# Dodaj katalog główny do ścieżki
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importuj i uruchom GUI
if __name__ == "__main__":
    print("🗨️ Uruchamianie GUI komunikatora IP...")
    try:
        from client.gui import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 GUI zatrzymane przez użytkownika")
    except Exception as e:
        print(f"❌ Błąd uruchamiania GUI: {e}")
        print(f"💡 Upewnij się, że masz zainstalowany tkinter")
        input("Naciśnij Enter aby zamknąć...")