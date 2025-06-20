#!/usr/bin/env python3
"""
Graficzny interfejs użytkownika dla komunikatora IP
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os
import socket

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType
from common.utils import validate_nick, validate_message

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🗨️ Komunikator IP")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Zmienne
        self.socket = None
        self.connected = False
        self.nick = ""
        self.host = "localhost"
        self.port = 12345
        self.receiving_thread = None
        
        # Style
        self.setup_styles()
        
        # Interfejs
        self.setup_ui()
        
        # Obsługa zamknięcia okna
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Konfiguruje style interfejsu"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Kolory
        self.colors = {
            'bg': '#2c3e50',
            'fg': '#ecf0f1',
            'accent': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'error': '#e74c3c'
        }
    
    def setup_ui(self):
        """Tworzy interfejs użytkownika"""
        # Główny kontener
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel połączenia (górny)
        self.setup_connection_panel(main_frame)
        
        # Panel czatu (środkowy)
        self.setup_chat_panel(main_frame)
        
        # Panel użytkowników (prawy)
        self.setup_users_panel(main_frame)
        
        # Panel wpisywania (dolny)
        self.setup_input_panel(main_frame)
        
        # Pasek statusu (najniżej)
        self.setup_status_bar(main_frame)
    
    def setup_connection_panel(self, parent):
        """Panel połączenia z serwerem"""
        conn_frame = ttk.LabelFrame(parent, text="Połączenie", padding=10)
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Wiersz 1: Host i Port
        row1 = ttk.Frame(conn_frame)
        row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row1, text="Host:").pack(side=tk.LEFT)
        self.host_entry = ttk.Entry(row1, width=15)
        self.host_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.host_entry.insert(0, self.host)
        
        ttk.Label(row1, text="Port:").pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(row1, width=8)
        self.port_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.port_entry.insert(0, str(self.port))
        
        # Wiersz 2: Nick i przycisk połączenia
        row2 = ttk.Frame(conn_frame)
        row2.pack(fill=tk.X)
        
        ttk.Label(row2, text="Nick:").pack(side=tk.LEFT)
        self.nick_entry = ttk.Entry(row2, width=15)
        self.nick_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.nick_entry.bind('<Return>', lambda e: self.toggle_connection())
        
        self.connect_btn = ttk.Button(row2, text="Połącz", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status połączenia
        self.connection_status = ttk.Label(row2, text="●", foreground="red")
        self.connection_status.pack(side=tk.RIGHT)
        
        ttk.Label(row2, text="Status:").pack(side=tk.RIGHT, padx=(0, 5))
    
    def setup_chat_panel(self, parent):
        """Panel głównego czatu"""
        # Kontener dla czatu i użytkowników
        chat_container = ttk.Frame(parent)
        chat_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Panel czatu
        chat_frame = ttk.LabelFrame(chat_container, text="Czat", padding=5)
        chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Obszar wiadomości
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            state='disabled',
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='#1e1e1e',
            fg='#ffffff'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Konfiguracja tagów kolorów
        self.chat_display.tag_config("system", foreground="#3498db", font=('Consolas', 10, 'bold'))
        self.chat_display.tag_config("error", foreground="#e74c3c", font=('Consolas', 10, 'bold'))
        self.chat_display.tag_config("user", foreground="#27ae60", font=('Consolas', 10, 'bold'))
        self.chat_display.tag_config("timestamp", foreground="#7f8c8d", font=('Consolas', 9))
        self.chat_display.tag_config("own_message", foreground="#f39c12")
    
    def setup_users_panel(self, parent):
        """Panel listy użytkowników"""
        users_frame = ttk.LabelFrame(parent.children[list(parent.children.keys())[-1]], text="Użytkownicy", padding=5)
        users_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # Lista użytkowników
        self.users_listbox = tk.Listbox(
            users_frame, 
            width=20,
            font=('Arial', 10),
            bg='#34495e',
            fg='#ecf0f1',
            selectbackground='#3498db'
        )
        self.users_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Licznik użytkowników
        self.users_count_label = ttk.Label(users_frame, text="Użytkowników: 0")
        self.users_count_label.pack(pady=(5, 0))
    
    def setup_input_panel(self, parent):
        """Panel wpisywania wiadomości"""
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Pole wpisywania
        self.message_entry = tk.Text(
            input_frame, 
            height=3,
            wrap=tk.WORD,
            font=('Arial', 11),
            state='disabled'
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.message_entry.bind('<Control-Return>', self.send_message)
        self.message_entry.bind('<KeyPress>', self.on_key_press)
        
        # Panel przycisków
        buttons_frame = ttk.Frame(input_frame)
        buttons_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.send_btn = ttk.Button(buttons_frame, text="Wyślij\n(Ctrl+Enter)", command=self.send_message, state='disabled')
        self.send_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.clear_btn = ttk.Button(buttons_frame, text="Wyczyść", command=self.clear_chat)
        self.clear_btn.pack(fill=tk.X)
    
    def setup_status_bar(self, parent):
        """Pasek statusu"""
        self.status_bar = ttk.Label(parent, text="Gotowy do połączenia", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X)
    
    def toggle_connection(self):
        """Przełącza połączenie (łączy/rozłącza)"""
        if not self.connected:
            self.connect_to_server()
        else:
            self.disconnect_from_server()
    
    def connect_to_server(self):
        """Łączy z serwerem"""
        # Pobierz dane z pól
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            self.show_message("BŁĄD: Nieprawidłowy port", "error")
            return
        
        nick = self.nick_entry.get().strip()
        
        # Walidacja
        is_valid, error_msg = validate_nick(nick)
        if not is_valid:
            self.show_message(f"BŁĄD: {error_msg}", "error")
            return
        
        if not host:
            self.show_message("BŁĄD: Podaj adres hosta", "error")
            return
        
        # Próba połączenia
        try:
            self.status_bar.config(text="Łączenie...")
            self.root.update()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10 sekund timeout
            self.socket.connect((host, port))
            
            self.host = host
            self.port = port
            self.nick = nick
            self.connected = True
            
            # Aktualizuj interfejs
            self.update_connection_status(True)
            
            # Uruchom wątek odbierania wiadomości
            self.receiving_thread = threading.Thread(target=self.receive_messages)
            self.receiving_thread.daemon = True
            self.receiving_thread.start()
            
            # Wyślij wiadomość JOIN
            join_message = Protocol.create_message(MessageType.JOIN, nick)
            self.socket.send(join_message.encode('utf-8'))
            
            self.show_message(f"Połączono z {host}:{port} jako {nick}", "system")
            
        except socket.timeout:
            self.show_message("BŁĄD: Przekroczono czas oczekiwania na połączenie", "error")
            self.socket = None
        except socket.error as e:
            self.show_message(f"BŁĄD: Nie można połączyć się z serwerem: {e}", "error")
            self.socket = None
        except Exception as e:
            self.show_message(f"BŁĄD: Nieoczekiwany błąd: {e}", "error")
            self.socket = None
    
    def disconnect_from_server(self):
        """Rozłącza z serwerem"""
        if self.connected and self.socket:
            # Wyślij wiadomość LEAVE
            try:
                leave_message = Protocol.create_message(MessageType.LEAVE, self.nick)
                self.socket.send(leave_message.encode('utf-8'))
            except:
                pass
            
            self.connected = False
            
            try:
                self.socket.close()
            except:
                pass
            
            self.socket = None
            
            # Aktualizuj interfejs
            self.update_connection_status(False)
            self.clear_users_list()
            self.show_message("Rozłączono z serwerem", "system")
    
    def receive_messages(self):
        """Odbiera wiadomości z serwera (w osobnym wątku)"""
        while self.connected and self.socket:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = Protocol.parse_message(data)
                self.root.after(0, self.process_message, message)  # Wykonaj w głównym wątku
                
            except socket.error:
                break
            except Exception as e:
                self.root.after(0, self.show_message, f"Błąd odbierania: {e}", "error")
                break
        
        # Rozłączenie
        if self.connected:
            self.root.after(0, self.disconnect_from_server)
    
    def process_message(self, message):
        """Przetwarza otrzymaną wiadomość"""
        msg_type = message.get('type', '')
        user = message.get('user', '')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        
        if msg_type == MessageType.MESSAGE:
            if user == self.nick:
                self.show_message(f"[{timestamp}] Ty: {content}", "own_message")
            else:
                self.show_message(f"[{timestamp}] {user}: {content}", "user")
            
        elif msg_type == MessageType.SYSTEM:
            if content.strip():  # Nie pokazuj pustych wiadomości systemowych (ping)
                self.show_message(f"SYSTEM: {content}", "system")
            
        elif msg_type == MessageType.USER_LIST:
            try:
                import json
                users = json.loads(content)
                self.update_users_list(users)
            except:
                pass
                
        elif msg_type == MessageType.ERROR:
            self.show_message(f"BŁĄD: {content}", "error")
    
    def send_message(self, event=None):
        """Wysyła wiadomość"""
        if not self.connected:
            return
        
        message_text = self.message_entry.get(1.0, tk.END).strip()
        
        if not message_text:
            return
        
        # Walidacja
        is_valid, error_msg = validate_message(message_text)
        if not is_valid:
            self.show_message(f"BŁĄD: {error_msg}", "error")
            return
        
        try:
            # Wyślij wiadomość
            chat_message = Protocol.create_message(MessageType.MESSAGE, self.nick, message_text)
            self.socket.send(chat_message.encode('utf-8'))
            
            # Wyczyść pole wprowadzania
            self.message_entry.delete(1.0, tk.END)
            
        except socket.error as e:
            self.show_message(f"BŁĄD wysyłania: {e}", "error")
            self.disconnect_from_server()
        
        return 'break'  # Zapobiega domyślnej obsłudze Enter
    
    def on_key_press(self, event):
        """Obsługuje naciśnięcie klawiszy w polu wiadomości"""
        if event.keysym == 'Return' and event.state & 0x4:  # Ctrl+Enter
            self.send_message()
            return 'break'
    
    def show_message(self, message, tag=""):
        """Wyświetla wiadomość w oknie czatu"""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n", tag)
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def clear_chat(self):
        """Czyści okno czatu"""
        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state='disabled')
    
    def update_users_list(self, users):
        """Aktualizuje listę użytkowników"""
        self.users_listbox.delete(0, tk.END)
        for user in sorted(users):
            if user == self.nick:
                self.users_listbox.insert(tk.END, f"● {user} (Ty)")
            else:
                self.users_listbox.insert(tk.END, f"● {user}")
        
        self.users_count_label.config(text=f"Użytkowników: {len(users)}")
    
    def clear_users_list(self):
        """Czyści listę użytkowników"""
        self.users_listbox.delete(0, tk.END)
        self.users_count_label.config(text="Użytkowników: 0")
    
    def update_connection_status(self, connected):
        """Aktualizuje status połączenia"""
        if connected:
            self.connection_status.config(text="●", foreground="green")
            self.connect_btn.config(text="Rozłącz")
            self.status_bar.config(text=f"Połączony z {self.host}:{self.port}")
            
            # Zablokuj pola połączenia
            self.host_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            self.nick_entry.config(state='disabled')
            
            # Odblokuj pole wiadomości
            self.message_entry.config(state='normal')
            self.send_btn.config(state='normal')
            self.message_entry.focus()
        else:
            self.connection_status.config(text="●", foreground="red")
            self.connect_btn.config(text="Połącz")
            self.status_bar.config(text="Rozłączony")
            
            # Odblokuj pola połączenia
            self.host_entry.config(state='normal')
            self.port_entry.config(state='normal')
            self.nick_entry.config(state='normal')
            
            # Zablokuj pole wiadomości
            self.message_entry.config(state='disabled')
            self.send_btn.config(state='disabled')
    
    def on_closing(self):
        """Obsługuje zamknięcie okna"""
        if self.connected:
            self.disconnect_from_server()
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()