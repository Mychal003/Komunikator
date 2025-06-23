#!/usr/bin/env python3
"""
AI Bot integration dla komunikatora IP
Używa OpenAI API do inteligentnych odpowiedzi
"""

import socket
import threading
import time
import json
import re
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Dodaj ścieżkę do common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.protocol import Protocol, MessageType
from common.utils import validate_nick

class AIBot:
    def __init__(self, 
                 openai_api_key: str,
                 bot_name: str = "🤖AIBot",
                 server_host: str = "localhost", 
                 server_port: int = 12345,
                 model: str = "gpt-3.5-turbo"):
        
        self.bot_name = bot_name
        self.server_host = server_host
        self.server_port = server_port
        self.model = model
        self.socket = None
        self.connected = False
        self.running = False
        
        # OpenAI setup
        if not OPENAI_AVAILABLE:
            raise ImportError("Zainstaluj OpenAI: pip install openai")
        
        self.client = openai.OpenAI(api_key=openai_api_key)
        
        # Kontekst rozmowy i pamięć
        self.conversation_history: List[Dict] = []
        self.user_contexts: Dict[str, List[Dict]] = {}
        self.last_message_time = {}
        
        # Konfiguracja bota
        self.config = {
            'max_history': 20,  # Maksymalna liczba wiadomości w pamięci
            'response_delay': 1.0,  # Opóźnienie przed odpowiedzią (sekundy)
            'max_response_length': 400,  # Maksymalna długość odpowiedzi
            'personality': 'helpful_assistant',  # Osobowość bota
            'respond_to_mentions': True,  # Odpowiadaj gdy ktoś wspomni bota
            'respond_to_questions': True,  # Odpowiadaj na pytania
            'respond_probability': 0.3,  # Prawdopodobieństwo odpowiedzi na zwykłe wiadomości
        }
        
        # System prompt dla różnych osobowości
        self.personalities = {
            'helpful_assistant': {
                'system_prompt': """Jesteś pomocnym asystentem AI w polskim czacie internetowym. 
                Odpowiadaj krótko, przyjaźnie i po polsku. Używaj emoji gdy to stosowne. 
                Pomagaj użytkownikom, odpowiadaj na pytania i bądź częścią społeczności.""",
                'greeting': "Cześć! Jestem AI bot 🤖 Mogę pomóc w czacie!"
            },
            'funny_bot': {
                'system_prompt': """Jesteś zabawnym botem w polskim czacie. Lubisz żarty, 
                memy i rozmowy. Odpowiadaj z humorem, używaj emoji i bądź pozytywny. 
                Czasem opowiedz żart lub ciekawostkę.""",
                'greeting': "Hej! Jestem zabawny bot 😄 Gotowy na rozmowę i żarty!"
            },
            'technical_expert': {
                'system_prompt': """Jesteś ekspertem technicznym w polskim czacie. 
                Specjalizujesz się w programowaniu, technologii i rozwiązywaniu problemów. 
                Odpowiadaj precyzyjnie ale przystępnie.""",
                'greeting': "Witam! Jestem tech bot 💻 Pomogę z zagadnieniami technicznymi!"
            }
        }
        
        print(f"🤖 AI Bot inicjalizowany...")
        print(f"   Model: {self.model}")
        print(f"   Osobowość: {self.config['personality']}")
        print(f"   Serwer: {self.server_host}:{self.server_port}")

    def connect_to_server(self) -> bool:
        """Łączy bota z serwerem TCP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect((self.server_host, self.server_port))
            
            # Włącz szyfrowanie jeśli dostępne
            try:
                from common.encryption import is_encryption_available
                if is_encryption_available():
                    encryption_password = "komunikator_secure_2025"
                    Protocol.enable_encryption(encryption_password)
                    print("🔒 Szyfrowanie włączone dla bota")
            except ImportError:
                print("⚠️ Szyfrowanie niedostępne dla bota")
            
            # Wyślij wiadomość JOIN
            join_message = Protocol.create_message(MessageType.JOIN, self.bot_name)
            self.socket.send(join_message.encode('utf-8'))
            
            self.connected = True
            self.running = True
            
            print(f"✅ Bot połączony z serwerem jako {self.bot_name}")
            
            # Uruchom wątek odbierający wiadomości
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Przywitaj się w czacie
            time.sleep(2)  # Poczekaj chwilę
            greeting = self.personalities[self.config['personality']]['greeting']
            self.send_message(greeting)
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd połączenia bota: {e}")
            return False

    def receive_messages(self):
        """Odbiera wiadomości z serwera"""
        while self.running and self.connected:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = Protocol.parse_message(data)
                self.process_message(message)
                
            except socket.timeout:
                continue
            except socket.error as e:
                print(f"❌ Błąd odbierania wiadomości: {e}")
                break
            except Exception as e:
                print(f"❌ Nieoczekiwany błąd: {e}")
                continue
        
        self.connected = False
        print("🔌 Bot rozłączony z serwera")

    def process_message(self, message: Dict):
        """Przetwarza otrzymaną wiadomość"""
        msg_type = message.get('type', '')
        user = message.get('user', '')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        
        # Ignoruj własne wiadomości i wiadomości systemowe
        if user == self.bot_name or msg_type != MessageType.MESSAGE:
            return
        
        # Dodaj do historii konwersacji
        self.add_to_history(user, content, timestamp)
        
        # Sprawdź czy bot powinien odpowiedzieć
        if self.should_respond(user, content):
            # Dodaj opóźnienie dla naturalności
            delay = self.config['response_delay']
            threading.Timer(delay, self.generate_and_send_response, [user, content]).start()

    def should_respond(self, user: str, content: str) -> bool:
        """Określa czy bot powinien odpowiedzieć na wiadomość"""
        content_lower = content.lower()
        
        # Zawsze odpowiadaj gdy ktoś wspomni bota
        if self.config['respond_to_mentions']:
            bot_mentions = [self.bot_name.lower(), 'bot', 'ai', '🤖']
            if any(mention in content_lower for mention in bot_mentions):
                return True
        
        # Odpowiadaj na pytania
        if self.config['respond_to_questions']:
            question_indicators = ['?', 'jak', 'dlaczego', 'co', 'gdzie', 'kiedy', 'czy', 'help', 'pomoc']
            if any(indicator in content_lower for indicator in question_indicators):
                return True
        
        # Odpowiadaj na pozdrowienia
        greetings = ['cześć', 'hej', 'siema', 'witaj', 'hello', 'hi']
        if any(greeting in content_lower for greeting in greetings):
            return True
        
        # Losowo odpowiadaj na inne wiadomości
        import random
        if random.random() < self.config['respond_probability']:
            return True
        
        return False

    def add_to_history(self, user: str, content: str, timestamp: str):
        """Dodaje wiadomość do historii konwersacji"""
        message_entry = {
            'user': user,
            'content': content,
            'timestamp': timestamp
        }
        
        # Globalna historia
        self.conversation_history.append(message_entry)
        if len(self.conversation_history) > self.config['max_history']:
            self.conversation_history.pop(0)
        
        # Historia per użytkownik
        if user not in self.user_contexts:
            self.user_contexts[user] = []
        
        self.user_contexts[user].append(message_entry)
        if len(self.user_contexts[user]) > 10:  # Maksymalnie 10 wiadomości per użytkownik
            self.user_contexts[user].pop(0)
        
        self.last_message_time[user] = datetime.now()

    def generate_and_send_response(self, user: str, content: str):
        """Generuje odpowiedź AI i wysyła ją"""
        try:
            # Przygotuj kontekst
            context = self.prepare_context(user, content)
            
            # Wygeneruj odpowiedź
            response = self.generate_ai_response(context)
            
            if response:
                # Ogranicz długość odpowiedzi
                if len(response) > self.config['max_response_length']:
                    response = response[:self.config['max_response_length']] + "..."
                
                # Dodaj prefix dla odpowiedzi na konkretną osobę
                if user in content or any(mention in content.lower() for mention in [self.bot_name.lower(), 'bot']):
                    response = f"@{user} {response}"
                
                self.send_message(response)
                print(f"🤖 Odpowiedź dla {user}: {response[:50]}...")
            
        except Exception as e:
            print(f"❌ Błąd generowania odpowiedzi: {e}")
            # Fallback response
            fallback_responses = [
                "Przepraszam, mam problem z odpowiedzią 😅",
                "Hmm, nie jestem pewien jak odpowiedzieć 🤔",
                "Spróbuj zapytać ponownie 🔄"
            ]
            import random
            fallback = random.choice(fallback_responses)
            self.send_message(fallback)

    def prepare_context(self, user: str, content: str) -> str:
        """Przygotowuje kontekst dla AI"""
        personality = self.personalities[self.config['personality']]
        
        # Historia ostatnich wiadomości
        recent_history = ""
        for msg in self.conversation_history[-5:]:  # Ostatnie 5 wiadomości
            recent_history += f"{msg['user']}: {msg['content']}\n"
        
        # Kontekst użytkownika
        user_context = ""
        if user in self.user_contexts:
            user_msgs = self.user_contexts[user][-3:]  # Ostatnie 3 wiadomości użytkownika
            for msg in user_msgs:
                user_context += f"{msg['content']}\n"
        
        context = f"""
{personality['system_prompt']}

Ostatnia historia czatu:
{recent_history}

Ostatnie wiadomości od {user}:
{user_context}

Aktualna wiadomość od {user}: {content}

Odpowiedz krótko i naturalnie po polsku. Maksymalnie 2-3 zdania.
"""
        return context

    def generate_ai_response(self, context: str) -> Optional[str]:
        """Generuje odpowiedź za pomocą OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": context}
                ],
                max_tokens=150,
                temperature=0.7,
                frequency_penalty=0.5,
                presence_penalty=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Błąd OpenAI API: {e}")
            return None

    def send_message(self, content: str):
        """Wysyła wiadomość do czatu"""
        if not self.connected:
            return
        
        try:
            message = Protocol.create_message(MessageType.MESSAGE, self.bot_name, content)
            self.socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"❌ Błąd wysyłania wiadomości: {e}")

    def send_command(self, command: str):
        """Wysyła komendę do serwera"""
        if not self.connected:
            return
        
        try:
            message = Protocol.create_message(MessageType.MESSAGE, self.bot_name, command)
            self.socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"❌ Błąd wysyłania komendy: {e}")

    def change_personality(self, personality: str):
        """Zmienia osobowość bota"""
        if personality in self.personalities:
            self.config['personality'] = personality
            greeting = self.personalities[personality]['greeting']
            self.send_message(f"🔄 Zmieniłem osobowość! {greeting}")
            print(f"🎭 Zmieniono osobowość na: {personality}")
        else:
            available = ', '.join(self.personalities.keys())
            print(f"❌ Nieznana osobowość. Dostępne: {available}")

    def get_stats(self) -> Dict:
        """Zwraca statystyki bota"""
        return {
            'connected': self.connected,
            'total_conversations': len(self.conversation_history),
            'unique_users': len(self.user_contexts),
            'personality': self.config['personality'],
            'model': self.model
        }

    def disconnect(self):
        """Rozłącza bota z serwera"""
        if self.connected:
            try:
                goodbye_message = "👋 Bot się rozłącza. Do zobaczenia!"
                self.send_message(goodbye_message)
                time.sleep(1)
                
                leave_message = Protocol.create_message(MessageType.LEAVE, self.bot_name)
                self.socket.send(leave_message.encode('utf-8'))
            except:
                pass
            
            self.running = False
            self.connected = False
            
            try:
                self.socket.close()
            except:
                pass
            
            print("👋 Bot rozłączony")

def main():
    """Główna funkcja - interaktywny launcher bota"""
    print("🤖 AI Bot dla komunikatora IP")
    print("=" * 40)
    
    if not OPENAI_AVAILABLE:
        print("❌ Brak biblioteki OpenAI!")
        print("Zainstaluj: pip install openai")
        return
    
    # Pobierz API key
    api_key = "REMOVEDt6Ry0vwjZkSxtUvyqQEx8SQtYo_hE4_MiZ_v27-k1OOp1iqfCh0sfQO5AkL3_T3BlbkFJzjBKdNye74-BEhpXjNEgSn3XZzXi7WYGCAOrocUgazBM19o_xl0zoK-nFEhp-mMJgfuuvfqE4A"
    if not api_key:
        print("❌ API key jest wymagany!")
        return
    
    # Konfiguracja bota
    bot_name = input("🤖 Nazwa bota (Enter = AIBot): ").strip() or "🤖AIBot"
    
    print("\n🎭 Dostępne osobowości:")
    personalities = ['helpful_assistant', 'funny_bot', 'technical_expert']
    for i, p in enumerate(personalities, 1):
        print(f"   {i}. {p}")
    
    try:
        choice = int(input("Wybierz osobowość (1-3): ")) - 1
        personality = personalities[choice] if 0 <= choice < len(personalities) else 'helpful_assistant'
    except:
        personality = 'helpful_assistant'
    
    # Utwórz i uruchom bota
    try:
        bot = AIBot(
            openai_api_key=api_key,
            bot_name=bot_name,
            model="gpt-3.5-turbo"
        )
        bot.config['personality'] = personality
        
        if bot.connect_to_server():
            print("\n✅ Bot uruchomiony pomyślnie!")
            print("Dostępne komendy:")
            print("   'stats' - pokaż statystyki")
            print("   'personality <nazwa>' - zmień osobowość")
            print("   'quit' - zakończ bota")
            print()
            
            # Pętla komend
            while bot.running:
                try:
                    cmd = input().strip().lower()
                    
                    if cmd == 'quit':
                        break
                    elif cmd == 'stats':
                        stats = bot.get_stats()
                        print(f"📊 Statystyki: {stats}")
                    elif cmd.startswith('personality '):
                        new_personality = cmd.split(' ', 1)[1]
                        bot.change_personality(new_personality)
                    elif cmd:
                        print("❓ Nieznana komenda")
                        
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
            
            bot.disconnect()
        else:
            print("❌ Nie udało się połączyć bota z serwerem")
            
    except KeyboardInterrupt:
        print("\n🛑 Bot zatrzymany przez użytkownika")
    except Exception as e:
        print(f"❌ Błąd bota: {e}")

if __name__ == "__main__":
    main()