#!/usr/bin/env python3
"""
Statystyki serwera i analiza użytkowania
"""

import json
import datetime
import os
from typing import Dict, List
from collections import defaultdict

class ServerStats:
    def __init__(self, stats_file='server_stats.json'):
        self.stats_file = stats_file
        self.stats_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        self.stats_path = os.path.join(self.stats_dir, stats_file)
        
        # Utwórz katalog jeśli nie istnieje
        os.makedirs(self.stats_dir, exist_ok=True)
        
        # Statystyki bieżącej sesji
        self.session_stats = {
            'start_time': datetime.datetime.now(),
            'connections': 0,
            'messages_sent': 0,
            'commands_executed': 0,
            'peak_users': 0,
            'total_uptime': 0,
            'users_joined': [],
            'popular_commands': defaultdict(int),
            'hourly_activity': defaultdict(int),
            'daily_activity': defaultdict(int)
        }
        
        # Statystyki historyczne
        self.historical_stats = self.load_historical_stats()
    
    def load_historical_stats(self) -> Dict:
        """Ładuje historyczne statystyki z pliku"""
        try:
            if os.path.exists(self.stats_path):
                with open(self.stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    'total_sessions': 0,
                    'total_connections': 0,
                    'total_messages': 0,
                    'total_uptime_hours': 0,
                    'all_time_peak': 0,
                    'unique_users': set(),
                    'sessions_history': []
                }
        except Exception as e:
            print(f"⚠️ Błąd ładowania statystyk: {e}")
            return {}
    
    def record_connection(self, username: str = None):
        """Rejestruje nowe połączenie"""
        self.session_stats['connections'] += 1
        if username:
            self.session_stats['users_joined'].append({
                'user': username,
                'time': datetime.datetime.now().isoformat()
            })
    
    def record_message(self):
        """Rejestruje wysłaną wiadomość"""
        self.session_stats['messages_sent'] += 1
        
        # Zapisz aktywność godzinową
        hour = datetime.datetime.now().hour
        self.session_stats['hourly_activity'][hour] += 1
        
        # Zapisz aktywność dzienną
        date = datetime.datetime.now().date().isoformat()
        self.session_stats['daily_activity'][date] += 1
    
    def record_command(self, command: str):
        """Rejestruje wykonaną komendę"""
        self.session_stats['commands_executed'] += 1
        self.session_stats['popular_commands'][command] += 1
    
    def update_peak_users(self, current_count: int):
        """Aktualizuje szczyt użytkowników"""
        if current_count > self.session_stats['peak_users']:
            self.session_stats['peak_users'] = current_count
    
    def get_session_uptime(self) -> datetime.timedelta:
        """Zwraca czas działania bieżącej sesji"""
        return datetime.datetime.now() - self.session_stats['start_time']
    
    def get_current_stats(self) -> Dict:
        """Zwraca statystyki bieżącej sesji"""
        uptime = self.get_session_uptime()
        
        return {
            'session_duration': str(uptime),
            'connections': self.session_stats['connections'],
            'messages_sent': self.session_stats['messages_sent'],
            'commands_executed': self.session_stats['commands_executed'],
            'peak_users': self.session_stats['peak_users'],
            'unique_users_today': len(self.session_stats['users_joined']),
            'messages_per_hour': round(self.session_stats['messages_sent'] / max(uptime.total_seconds() / 3600, 0.1), 2),
            'most_popular_command': self.get_most_popular_command(),
            'busiest_hour': self.get_busiest_hour()
        }
    
    def get_most_popular_command(self) -> str:
        """Zwraca najpopularniejszą komendę"""
        if not self.session_stats['popular_commands']:
            return "brak"
        
        return max(self.session_stats['popular_commands'].items(), 
                  key=lambda x: x[1])[0]
    
    def get_busiest_hour(self) -> str:
        """Zwraca najbardziej aktywną godzinę"""
        if not self.session_stats['hourly_activity']:
            return "brak danych"
        
        busiest = max(self.session_stats['hourly_activity'].items(), 
                     key=lambda x: x[1])
        return f"{busiest[0]}:00 ({busiest[1]} wiadomości)"
    
    def get_formatted_stats(self) -> str:
        """Zwraca sformatowane statystyki jako tekst"""
        stats = self.get_current_stats()
        uptime = self.get_session_uptime()
        
        report = [
            "📊 STATYSTYKI SERWERA",
            "=" * 40,
            f"⏰ Czas działania: {uptime}",
            f"🔗 Połączenia: {stats['connections']}",
            f"💬 Wiadomości: {stats['messages_sent']}",
            f"⚡ Komendy: {stats['commands_executed']}",
            f"👥 Szczyt użytkowników: {stats['peak_users']}",
            f"📈 Wiadomości/godz: {stats['messages_per_hour']}",
            f"🏆 Popularna komenda: {stats['most_popular_command']}",
            f"⏰ Najbardziej aktywna godzina: {stats['busiest_hour']}",
            "=" * 40
        ]
        
        return "\n".join(report)
    
    def get_activity_graph(self) -> str:
        """Zwraca prosty wykres aktywności godzinowej"""
        if not self.session_stats['hourly_activity']:
            return "Brak danych o aktywności"
        
        max_activity = max(self.session_stats['hourly_activity'].values())
        scale_factor = 20 / max_activity if max_activity > 0 else 1
        
        graph = ["📈 AKTYWNOŚĆ GODZINOWA:", ""]
        
        for hour in range(24):
            activity = self.session_stats['hourly_activity'].get(hour, 0)
            bar_length = int(activity * scale_factor)
            bar = "█" * bar_length
            
            graph.append(f"{hour:2d}:00 |{bar:<20}| {activity}")
        
        return "\n".join(graph)
    
    def export_stats(self, filename: str = None) -> str:
        """Eksportuje statystyki do pliku"""
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stats_export_{timestamp}.txt"
        
        export_path = os.path.join(self.stats_dir, filename)
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write("STATYSTYKI SERWERA KOMUNIKATORA IP\n")
                f.write("=" * 50 + "\n")
                f.write(f"Wygenerowano: {datetime.datetime.now()}\n\n")
                
                f.write(self.get_formatted_stats())
                f.write("\n\n")
                f.write(self.get_activity_graph())
                f.write("\n\n")
                
                # Szczegóły komend
                f.write("STATYSTYKI KOMEND:\n")
                f.write("-" * 30 + "\n")
                for cmd, count in sorted(self.session_stats['popular_commands'].items(), 
                                       key=lambda x: x[1], reverse=True):
                    f.write(f"{cmd}: {count}\n")
                
                # Lista użytkowników
                f.write("\nUŻYTKOWNICY W SESJI:\n")
                f.write("-" * 30 + "\n")
                for user_info in self.session_stats['users_joined']:
                    time_str = datetime.datetime.fromisoformat(user_info['time']).strftime("%H:%M:%S")
                    f.write(f"{time_str} - {user_info['user']}\n")
            
            print(f"✅ Statystyki wyeksportowane do: {export_path}")
            return export_path
        except Exception as e:
            print(f"❌ Błąd eksportu statystyk: {e}")
            return ""
    
    def save_session_stats(self):
        """Zapisuje statystyki sesji do historii"""
        try:
            session_data = {
                'start_time': self.session_stats['start_time'].isoformat(),
                'end_time': datetime.datetime.now().isoformat(),
                'duration_minutes': int(self.get_session_uptime().total_seconds() / 60),
                'connections': self.session_stats['connections'],
                'messages': self.session_stats['messages_sent'],
                'commands': self.session_stats['commands_executed'],
                'peak_users': self.session_stats['peak_users']
            }
            
            # Aktualizuj historyczne statystyki
            self.historical_stats['total_sessions'] = self.historical_stats.get('total_sessions', 0) + 1
            self.historical_stats['total_connections'] = self.historical_stats.get('total_connections', 0) + session_data['connections']
            self.historical_stats['total_messages'] = self.historical_stats.get('total_messages', 0) + session_data['messages']
            
            if 'sessions_history' not in self.historical_stats:
                self.historical_stats['sessions_history'] = []
            
            self.historical_stats['sessions_history'].append(session_data)
            
            # Zachowaj tylko ostatnie 100 sesji
            if len(self.historical_stats['sessions_history']) > 100:
                self.historical_stats['sessions_history'] = self.historical_stats['sessions_history'][-100:]
            
            # Zapisz do pliku
            with open(self.stats_path, 'w', encoding='utf-8') as f:
                # Konwertuj set na listę dla JSON
                stats_to_save = self.historical_stats.copy()
                if 'unique_users' in stats_to_save and isinstance(stats_to_save['unique_users'], set):
                    stats_to_save['unique_users'] = list(stats_to_save['unique_users'])
                
                json.dump(stats_to_save, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ Błąd zapisywania statystyk: {e}")
            return False

# Globalna instancja statystyk
server_stats = ServerStats()