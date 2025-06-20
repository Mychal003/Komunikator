import re
import socket

def validate_nick(nick):
    """Waliduje nick użytkownika"""
    if not nick or len(nick.strip()) == 0:
        return False, "Nick nie może być pusty"
    
    nick = nick.strip()
    
    if len(nick) < 2:
        return False, "Nick musi mieć co najmniej 2 znaki"
    
    if len(nick) > 20:
        return False, "Nick nie może mieć więcej niż 20 znaków"
    
    # Sprawdź czy zawiera tylko dozwolone znaki
    if not re.match(r'^[a-zA-Z0-9_-]+$', nick):
        return False, "Nick może zawierać tylko litery, cyfry, _ i -"
    
    return True, "OK"

def validate_message(message):
    """Waliduje wiadomość"""
    if not message or len(message.strip()) == 0:
        return False, "Wiadomość nie może być pusta"
    
    if len(message) > 500:
        return False, "Wiadomość może mieć maksymalnie 500 znaków"
    
    return True, "OK"

def get_local_ip():
    """Zwraca lokalny adres IP"""
    try:
        # Utwórz socket i połącz się z dowolnym adresem
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def format_file_size(bytes_size):
    """Formatuje rozmiar pliku"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def clean_text(text):
    """Czyści tekst z niebezpiecznych znaków"""
    if not text:
        return ""
    
    # Usuń znaki kontrolne
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Ogranicz długość
    if len(cleaned) > 1000:
        cleaned = cleaned[:1000] + "..."
    
    return cleaned.strip()

def is_valid_port(port):
    """Sprawdza czy port jest poprawny"""
    try:
        port_num = int(port)
        return 1024 <= port_num <= 65535
    except:
        return False

def is_valid_ip(ip):
    """Sprawdza czy adres IP jest poprawny"""
    try:
        socket.inet_aton(ip)
        return True
    except:
        return False