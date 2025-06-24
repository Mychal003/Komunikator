#!/usr/bin/env python3
"""
Uruchamia wszystkie komponenty komunikatora
"""

import subprocess
import time
import sys
import os
import signal

processes = []

def cleanup(signum=None, frame=None):
    """Zatrzymuje wszystkie procesy"""
    print("\n🛑 Zatrzymywanie wszystkich procesów...")
    for p in processes:
        try:
            p.terminate()
        except:
            pass
    sys.exit(0)

def start_process(script, name, delay=2):
    """Uruchamia proces i czeka"""
    print(f"🚀 Uruchamianie {name}...")
    p = subprocess.Popen([sys.executable, script])
    processes.append(p)
    time.sleep(delay)
    return p

def main():
    # Obsługa Ctrl+C
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("🗨️ KOMUNIKATOR IP - Uruchamianie wszystkich komponentów")
    print("=" * 60)
    print("Naciśnij Ctrl+C aby zatrzymać wszystko\n")
    
    try:
        # 1. Serwer TCP
        start_process("start_server.py", "Serwer TCP", 3)
        
        # 2. WebSocket Bridge
        start_process("websocket_bridge.py", "WebSocket Bridge", 3)
        
        # 3. AI Bot (opcjonalnie)
        if "--with-bot" in sys.argv:
            # Sprawdź czy jest API key
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                start_process("llm_bot.py", "AI Bot", 2)
            else:
                print("⚠️ Pomijam AI Bot - brak OPENAI_API_KEY")
        
        # 4. Web Server
        start_process("start_web_server.py", "Web Server", 2)
        
        print("\n✅ Wszystkie komponenty uruchomione!")
        print(f"🌐 Otwórz przeglądarkę: http://localhost:8000/web_client.html")
        print("\n📝 Logi są wyświetlane w osobnych oknach terminala")
        print("Naciśnij Ctrl+C aby zatrzymać wszystko\n")
        
        # Czekaj na zakończenie
        while True:
            time.sleep(1)
            # Sprawdź czy procesy żyją
            for p in processes:
                if p.poll() is not None:
                    print(f"⚠️ Proces {p.args} zakończył się")
                    cleanup()
                    
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"❌ Błąd: {e}")
        cleanup()

if __name__ == "__main__":
    main()