#!/usr/bin/env python3
"""
Graficzny interfejs użytkownika (opcjonalny)
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
from client import Client

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Komunikator IP")
        self.root.geometry("600x400")
        
        self.client = Client()
        self.setup_ui()
        
    def setup_ui(self):
        """Tworzy interfejs użytkownika"""
        # Okno czatu
        self.chat_display = scrolledtext.ScrolledText(self.root, state='disabled')
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Pole wprowadzania wiadomości
        self.message_entry = tk.Entry(self.root)
        self.message_entry.pack(fill=tk.X, padx=10, pady=5)
        self.message_entry.bind('<Return>', self.send_message)
        
        # Przycisk wysyłania
        self.send_button = tk.Button(self.root, text="Wyślij", command=self.send_message)
        self.send_button.pack(pady=5)
        
    def send_message(self, event=None):
        """Wysyła wiadomość"""
        message = self.message_entry.get()
        if message.strip():
            # Implementacja wysyłania
            self.display_message(f"Ty: {message}")
            self.message_entry.delete(0, tk.END)
            
    def display_message(self, message):
        """Wyświetla wiadomość w oknie czatu"""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()
