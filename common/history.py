#!/usr/bin/env python3
"""
Zarządzanie historią wiadomości
"""

import os
import json
import datetime
from typing import List, Dict

class HistoryManager:
    def __init__(self, history_file='chat_history.json'):
        self.history_file = history_file
        self.history_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        self.history_path = os.path.join(self.history_dir, history_file)
        
        # Utwórz katalog jeśli nie istnieje
        os.makedirs(self.history_dir, exist_ok=True)
        
        self.messages = []
        self.load_history()
    
    def add_message(self, user: str, content: str, msg_type: str = "message"):
        """Dodaje wiadomość do historii"""
        message = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user": user,
            "content": content,
            "type": msg_type
        }
        
        self.messages.append(message)
        
        # Zachowuj tylko ostatnie 1000 wiadomości
        if len(self.messages) > 1000:
            self.messages = self.messages[-1000:]
        
        # Zapisz do pliku co 10 wiadomości
        if len(self.messages) % 10 == 0:
            self.save_history()
    
    def get_recent_messages(self, count: int = 50) -> List[Dict]:
        """Zwraca ostatnie N wiadomości"""
        return self.messages[-count:] if self.messages else []
    
    def get_messages_by_user(self, user: str) -> List[Dict]:
        """Zwraca wszystkie wiadomości od użytkownika"""
        return [msg for msg in self.messages if msg['user'] == user]
    
    def get_messages_by_date(self, date_str: str) -> List[Dict]:
        """Zwraca wiadomości z określonego dnia (YYYY-MM-DD)"""
        return [msg for msg in self.messages if msg['timestamp'].startswith(date_str)]
    
    def search_messages(self, query: str) -> List[Dict]:
        """Wyszukuje wiadomości zawierające określony tekst"""
        query_lower = query.lower()
        return [msg for msg in self.messages 
                if query_lower in msg['content'].lower() or query_lower in msg['user'].lower()]
    
    def load_history(self):
        """Ładuje historię z pliku"""
        try:
            if os.path.exists(self.history_path):
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.messages = data.get('messages', [])
                print(f"✅ Załadowano historię: {len(self.messages)} wiadomości")
            else:
                print(f"📝 Tworzę nowy plik historii: {self.history_path}")
        except Exception as e:
            print(f"⚠️ Błąd ładowania historii: {e}")
            self.messages = []
    
    def save_history(self):
        """Zapisuje historię do pliku"""
        try:
            history_data = {
                "created": datetime.datetime.now().isoformat(),
                "total_messages": len(self.messages),
                "messages": self.messages
            }
            
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ Błąd zapisywania historii: {e}")
            return False
    
    def export_to_txt(self, filename: str = None) -> str:
        """Eksportuje historię do pliku tekstowego"""
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_export_{timestamp}.txt"
        
        export_path = os.path.join(self.history_dir, filename)
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write("HISTORIA CZATU\n")
                f.write("=" * 50 + "\n")
                f.write(f"Eksportowano: {datetime.datetime.now()}\n")
                f.write(f"Liczba wiadomości: {len(self.messages)}\n\n")
                
                for msg in self.messages:
                    timestamp = datetime.datetime.fromisoformat(msg['timestamp'])
                    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    
                    if msg['type'] == 'system':
                        f.write(f"[{formatted_time}] SYSTEM: {msg['content']}\n")
                    else:
                        f.write(f"[{formatted_time}] {msg['user']}: {msg['content']}\n")
            
            print(f"✅ Historia wyeksportowana do: {export_path}")
            return export_path
        except Exception as e:
            print(f"❌ Błąd eksportu: {e}")
            return ""
    
    def get_stats(self) -> Dict:
        """Zwraca statystyki historii"""
        if not self.messages:
            return {"total": 0}
        
        # Policz wiadomości według użytkowników
        user_counts = {}
        for msg in self.messages:
            user = msg['user']
            user_counts[user] = user_counts.get(user, 0) + 1
        
        # Znajdź najaktywniejszego użytkownika
        most_active = max(user_counts.items(), key=lambda x: x[1]) if user_counts else ("", 0)
        
        # Policz wiadomości według dni
        dates = {}
        for msg in self.messages:
            date = msg['timestamp'][:10]  # YYYY-MM-DD
            dates[date] = dates.get(date, 0) + 1
        
        return {
            "total": len(self.messages),
            "unique_users": len(user_counts),
            "most_active_user": most_active[0],
            "most_active_count": most_active[1],
            "days_with_messages": len(dates),
            "user_counts": user_counts,
            "daily_counts": dates
        }
    
    def clear_history(self):
        """Czyści całą historię"""
        self.messages = []
        self.save_history()
        print("🗑️ Historia została wyczyszczona")