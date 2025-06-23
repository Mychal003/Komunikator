#!/usr/bin/env python3
"""
Launcher dla webowego interfejsu komunikatora IP
"""

import http.server
import socketserver
import webbrowser
import threading
import time
import os
import sys

def start_http_server(port=8000):
    """Uruchamia prosty HTTP serwer"""
    handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌐 HTTP serwer uruchomiony na http://localhost:{port}")
        print(f"📁 Serwowanie plików z: {os.getcwd()}")
        httpd.serve_forever()

def open_browser(url, delay=2):
    """Otwiera przeglądarkę po opóźnieniu"""
    time.sleep(delay)
    print(f"🌍 Otwieranie przeglądarki: {url}")
    webbrowser.open(url)

def main():
    """Główna funkcja"""
    print("🗨️ Uruchamianie webowego interfejsu komunikatora IP...")
    print("=" * 60)
    
    # Sprawdź czy plik interfejsu istnieje
    html_file = "web_client.html"
    if not os.path.exists(html_file):
        print(f"❌ Nie znaleziono pliku {html_file}")
        print("💡 Skopiuj kod HTML do pliku web_client.html")
        return
    
    port = 8000
    url = f"http://localhost:{port}/{html_file}"
    
    # Uruchom przeglądarkę w osobnym wątku
    browser_thread = threading.Thread(target=open_browser, args=(url,))
    browser_thread.daemon = True
    browser_thread.start()
    
    print("📋 Instrukcje:")
    print("1. TCP serwer: python start_server.py")
    print("2. WebSocket bridge: python websocket_bridge.py") 
    print("3. Interface webowy jest już uruchomiony!")
    print("=" * 60)
    
    try:
        start_http_server(port)
    except KeyboardInterrupt:
        print("\n🛑 Serwer HTTP zatrzymany")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} jest już zajęty")
            print(f"🌍 Spróbuj otworzyć: {url}")
        else:
            print(f"❌ Błąd serwera HTTP: {e}")

if __name__ == "__main__":
    main()