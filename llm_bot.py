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
        self.authenticated = False
        
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
            'max_history': 10,  # Zmniejszona historia
            'response_delay': 1.5,  # Zwiększone opóźnienie 
            'max_response_length': 200,  # Krótsze odpowiedzi
            'personality': 'helpful_assistant',
            'respond_to_mentions': True,
            'respond_to_questions': True,
            'respond_probability': 0.2,  # Mniejsza częstotliwość
        }
        
        # System prompt dla osobowości
        self.personalities = {
            'helpful_assistant': {
                'system_prompt': """Jesteś pomocnym asystentem AI w polskim czacie internetowym. 
                Odpowiadaj BARDZO krótko, max 1-2 zdania. Używaj emoji okazjonalnie. 
                Bądź pomocny ale nie dominuj rozmowy.""",
                'greeting': "Cześć! Jestem AI bot 🤖 Mogę pomóc!"
            },
            'funny_bot': {
                'system_prompt': """Jesteś zabawnym botem w polskim czacie. 
                Odpowiadaj krótko z humorem. Max 1-2 zdania. Używaj emoji.""",
                'greeting': "Hej! Jestem zabawny bot 😄 Gotowy na rozmowę!"
            },
            'technical_expert': {
                'system_prompt': """Jesteś ekspertem technicznym w polskim czacie. 
                Odpowiadaj precyzyjnie ale krótko. Max 1-2 zdania na temat tech.""",
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
            
            # Poczekaj na uwierzytelnienie
            start_time = time.time()
            while not self.authenticated and time.time() - start_time < 10:
                time.sleep(0.1)
            
            if self.authenticated:
                # Przywitaj się w czacie
                time.sleep(2)
                greeting = self.personalities[self.config['personality']]['greeting']
                self.send_message(greeting)
                print("✅ Bot uwierzytelniony i aktywny!")
                return True
            else:
                print("❌ Bot nie został uwierzytelniony")
                return False
            
        except Exception as e:
            print(f"❌ Błąd połączenia bota: {e}")
            return False

    def receive_messages(self):
        """Odbiera wiadomości z serwera"""
        buffer = ""
        
        while self.running and self.connected:
            try:
                self.socket.settimeout(60)
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                # Dodaj do bufora i przetwórz linie
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        message = Protocol.parse_message(line.strip())
                        if message:
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

    def receive_messages(self):
        """Odbiera wiadomości z serwera z debugowaniem"""
        buffer = ""
        
        while self.running and self.connected:
            try:
                self.socket.settimeout(5)  # Krótszy timeout dla debugowania
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    print("🔌 Serwer zamknął połączenie")
                    break
                
                print(f"📥 RAW data: {repr(data)}")  # DEBUG: pokaż surowe dane
                
                # Dodaj do bufora i przetwórz linie
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        print(f"📨 Parsing line: {repr(line.strip())}")  # DEBUG
                        message = Protocol.parse_message(line.strip())
                        print(f"📋 Parsed message: {message}")  # DEBUG
                        if message:
                            self.process_message(message)
                
            except socket.timeout:
                print("⏰ Socket timeout - bot czeka...")  # DEBUG
                continue
            except socket.error as e:
                print(f"❌ Błąd odbierania wiadomości: {e}")
                break
            except Exception as e:
                print(f"❌ Nieoczekiwany błąd: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        self.connected = False
        print("🔌 Bot rozłączony z serwera")

    def process_message(self, message: Dict):
        """Przetwarza otrzymaną wiadomość z debugowaniem"""
        msg_type = message.get('type', '')
        user = message.get('user', '')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')
        
        print(f"🔍 Processing: type={msg_type}, user={user}, content={content[:50]}...")  # DEBUG
        
        # Sprawdź uwierzytelnienie - rozszerzone warunki
        if msg_type == MessageType.SYSTEM:
            print(f"🔔 System message: {content}")
            if any(keyword in content for keyword in ["Witaj", "witaj", "Welcome", "welcome", self.bot_name]):
                self.authenticated = True
                print("✅ Bot uwierzytelniony przez system message!")
                return
        
        # Sprawdź czy otrzymaliśmy USER_LIST (oznacza że jesteśmy na liście)
        if msg_type == MessageType.USER_LIST:
            print(f"👥 User list received: {content}")
            try:
                users = json.loads(content) if content.startswith('[') else content.split(',')
                if self.bot_name in users or any(self.bot_name in user for user in users):
                    self.authenticated = True
                    print("✅ Bot uwierzytelniony przez user list!")
                    return
            except Exception as e:
                print(f"❌ Error parsing user list: {e}")
        
        # Jeśli nie jesteśmy jeszcze uwierzytelnieni, ale otrzymujemy zwykłe wiadomości
        # to prawdopodobnie uwierzytelnienie przeszło
        if not self.authenticated and msg_type == MessageType.MESSAGE and user != self.bot_name:
            print("🤔 Receiving messages from others - assuming authenticated")
            self.authenticated = True
        
        # Ignoruj własne wiadomości i przetwarzaj tylko po uwierzytelnieniu
        if user == self.bot_name:
            print(f"🤖 Ignoring own message: {content[:30]}...")
            return
            
        if msg_type != MessageType.MESSAGE or not content.strip():
            print(f"🔇 Ignoring non-message: type={msg_type}")
            return
        
        if not self.authenticated:
            print("⚠️ Not authenticated yet, ignoring message")
            return
        
        print(f"📨 Processing user message: {user}: {content[:50]}...")
        
        # Dodaj do historii konwersacji
        self.add_to_history(user, content, timestamp)
        
        # Sprawdź czy bot powinien odpowiedzieć
        if self.should_respond(user, content):
            print(f"🤔 Bot will respond to: {content[:30]}...")
            # Dodaj opóźnienie dla naturalności
            delay = self.config['response_delay']
            threading.Timer(delay, self.generate_and_send_response, [user, content]).start()
        else:
            print(f"🔇 Bot will not respond to: {content[:30]}...")

    def connect_to_server(self) -> bool:
        """Łączy bota z serwerem TCP z lepszym debugowaniem"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect((self.server_host, self.server_port))
            print(f"🔗 Socket connected to {self.server_host}:{self.server_port}")
            
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
            print(f"📤 Sending JOIN: {repr(join_message)}")  # DEBUG
            self.socket.send(join_message.encode('utf-8'))
            
            self.connected = True
            self.running = True
            
            print(f"✅ Bot connected as {self.bot_name}")
            
            # Uruchom wątek odbierający wiadomości
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Poczekaj na uwierzytelnienie z dłuższym timeoutem
            print("⏳ Waiting for authentication...")
            start_time = time.time()
            while not self.authenticated and time.time() - start_time < 15:  # 15 sekund
                time.sleep(0.2)
                if time.time() - start_time > 5:
                    # Po 5 sekundach załóż że już jesteśmy uwierzytelnieni
                    print("🤔 No explicit auth received, assuming connected...")
                    self.authenticated = True
                    break
            
            if self.authenticated:
                # Poczekaj chwilę i wyślij przywitanie
                time.sleep(2)
                greeting = self.personalities[self.config['personality']]['greeting']
                print(f"📤 Sending greeting: {greeting}")
                self.send_message(greeting)
                print("✅ Bot authenticated and active!")
                return True
            else:
                print("❌ Bot authentication timeout")
                return False
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def should_respond(self, user: str, content: str) -> bool:
        """Określa czy bot powinien odpowiedzieć na wiadomość"""
        content_lower = content.lower()
        
        # Zawsze odpowiadaj gdy ktoś wspomni bota
        if self.config['respond_to_mentions']:
            bot_mentions = [self.bot_name.lower(), 'bot', 'ai', '🤖', '@' + self.bot_name.lower()]
            if any(mention in content_lower for mention in bot_mentions):
                print(f"🎯 Wykryto wzmiankę o bocie w: {content}")
                return True
        
        # Odpowiadaj na bezpośrednie pytania
        if self.config['respond_to_questions']:
            if content.strip().endswith('?'):
                print(f"❓ Wykryto pytanie: {content}")
                return True
            
            question_indicators = ['jak', 'dlaczego', 'co to', 'gdzie', 'kiedy', 'czy', 'help', 'pomoc']
            if any(indicator in content_lower for indicator in question_indicators):
                print(f"❓ Wykryto wskaźnik pytania: {content}")
                return True
        
        # Odpowiadaj na pozdrowienia skierowane do bota
        if any(greeting in content_lower for greeting in ['cześć', 'hej', 'siema', 'witaj', 'hello', 'hi']):
            if self.bot_name.lower() in content_lower or 'bot' in content_lower:
                print(f"👋 Wykryto pozdrowienie dla bota: {content}")
                return True
        
        # Losowo odpowiadaj na inne wiadomości (bardzo rzadko)
        import random
        if random.random() < self.config['respond_probability']:
            print(f"🎲 Losowa odpowiedź na: {content}")
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
        if len(self.user_contexts[user]) > 5:  # Max 5 wiadomości per user
            self.user_contexts[user].pop(0)
        
        self.last_message_time[user] = datetime.now()

    def generate_and_send_response(self, user: str, content: str):
        """Generuje odpowiedź AI i wysyła ją"""
        try:
            print(f"🧠 Generuję odpowiedź dla {user}...")
            
            # Przygotuj kontekst
            context = self.prepare_context(user, content)
            
            # Wygeneruj odpowiedź
            response = self.generate_ai_response(context)
            
            if response:
                # Ogranicz długość odpowiedzi
                if len(response) > self.config['max_response_length']:
                    response = response[:self.config['max_response_length']] + "..."
                
                # Usuń potencjalne powtórzenia nicku
                if response.startswith(f"@{user}"):
                    response = response[len(f"@{user}"):].strip()
                
                self.send_message(response)
                print(f"✅ Wysłano odpowiedź: {response[:50]}...")
            else:
                print("❌ Nie udało się wygenerować odpowiedzi")
                
        except Exception as e:
            print(f"❌ Błąd generowania odpowiedzi: {e}")
            # Fallback response
            fallback_responses = [
                "Przepraszam, mam problem z odpowiedzią 😅",
                "Hmm, nie jestem pewien 🤔",
                "Spróbuj zapytać ponownie 🔄"
            ]
            import random
            fallback = random.choice(fallback_responses)
            self.send_message(fallback)

    def prepare_context(self, user: str, content: str) -> str:
        """Przygotowuje kontekst dla AI"""
        personality = self.personalities[self.config['personality']]
        
        # Historia ostatnich wiadomości (max 3)
        recent_history = ""
        for msg in self.conversation_history[-3:]:
            recent_history += f"{msg['user']}: {msg['content']}\n"
        
        context = f"""
{personality['system_prompt']}

Ostatnie wiadomości w czacie:
{recent_history}

Użytkownik {user} napisał: {content}

Odpowiedz naturalnie PO POLSKU. Max 1-2 zdania. Nie powtarzaj nicku użytkownika.
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
                max_tokens=80,  # Bardzo krótkie odpowiedzi
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
            'authenticated': self.authenticated,
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
    api_key = input("🔑 Wprowadź OpenAI API key: ").strip()
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
        choice = int(input("Wybierz osobowość (1-3, Enter=1): ") or "1") - 1
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
            print("Teraz bot nasłuchuje i będzie odpowiadać w czacie...")
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