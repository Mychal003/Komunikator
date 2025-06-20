#!/usr/bin/env python3
"""
Moduł szyfrowania komunikacji dla komunikatora IP
Używa AES-256 w trybie CBC z PBKDF2 do wyprowadzania klucza
"""

import os
import base64
import hashlib
from typing import Tuple, Optional

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes, padding
    from cryptography.hazmat.backends import default_backend
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

class ChatEncryption:
    """Klasa do szyfrowania/deszyfrowania wiadomości czatu"""
    
    def __init__(self, password: str = "default_chat_password"):
        self.password = password.encode('utf-8')
        self.salt = b'komunikator_salt_2025'  # W produkcji powinno być losowe
        self.iterations = 100000  # Liczba iteracji PBKDF2
        
        if not ENCRYPTION_AVAILABLE:
            print("⚠️ Biblioteka 'cryptography' nie jest zainstalowana")
            print("   Uruchom: pip install cryptography")
            print("   Szyfrowanie będzie wyłączone")
        
        # Wyprowadź klucz z hasła
        self._derive_key()
    
    def _derive_key(self):
        """Wyprowadza klucz AES z hasła używając PBKDF2"""
        if not ENCRYPTION_AVAILABLE:
            self.key = None
            return
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits dla AES-256
            salt=self.salt,
            iterations=self.iterations,
            backend=default_backend()
        )
        self.key = kdf.derive(self.password)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Szyfruje tekst i zwraca go jako base64
        Format: base64(iv + encrypted_data)
        """
        if not ENCRYPTION_AVAILABLE or self.key is None:
            # Jeśli szyfrowanie niedostępne, zwróć tekst bez zmian
            return plaintext
        
        try:
            # Konwertuj tekst na bajty
            data = plaintext.encode('utf-8')
            
            # Padding do wielokrotności 16 bajtów (AES block size)
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data)
            padded_data += padder.finalize()
            
            # Wygeneruj losowy IV (Initialization Vector)
            iv = os.urandom(16)
            
            # Szyfruj
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            
            # Połącz IV z zaszyfrowanymi danymi i zakoduj w base64
            encrypted_data = iv + ciphertext
            return base64.b64encode(encrypted_data).decode('ascii')
            
        except Exception as e:
            print(f"❌ Błąd szyfrowania: {e}")
            return plaintext  # W przypadku błędu zwróć oryginał
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Deszyfruje tekst z base64
        """
        if not ENCRYPTION_AVAILABLE or self.key is None:
            # Jeśli szyfrowanie niedostępne, zwróć tekst bez zmian
            return ciphertext
        
        try:
            # Dekoduj z base64
            encrypted_data = base64.b64decode(ciphertext.encode('ascii'))
            
            # Wyciągnij IV (pierwsze 16 bajtów)
            iv = encrypted_data[:16]
            actual_ciphertext = encrypted_data[16:]
            
            # Deszyfruj
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(actual_ciphertext) + decryptor.finalize()
            
            # Usuń padding
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data)
            data += unpadder.finalize()
            
            return data.decode('utf-8')
            
        except Exception as e:
            print(f"❌ Błąd deszyfrowania: {e}")
            return ciphertext  # W przypadku błędu zwróć oryginał
    
    def is_encrypted(self, text: str) -> bool:
        """Sprawdza czy tekst wygląda na zaszyfrowany (base64)"""
        if not ENCRYPTION_AVAILABLE:
            return False
            
        try:
            # Sprawdź czy to poprawny base64
            decoded = base64.b64decode(text.encode('ascii'))
            # Sprawdź czy ma odpowiednią długość (minimum IV + 16 bajtów danych)
            return len(decoded) >= 32
        except:
            return False
    
    def change_password(self, new_password: str):
        """Zmienia hasło szyfrowania"""
        self.password = new_password.encode('utf-8')
        self._derive_key()
        print("🔒 Hasło szyfrowania zostało zmienione")
    
    def get_encryption_info(self) -> dict:
        """Zwraca informacje o szyfrowaniu"""
        return {
            'available': ENCRYPTION_AVAILABLE,
            'algorithm': 'AES-256-CBC' if ENCRYPTION_AVAILABLE else 'None',
            'key_derivation': 'PBKDF2-SHA256' if ENCRYPTION_AVAILABLE else 'None',
            'iterations': self.iterations if ENCRYPTION_AVAILABLE else 0,
            'enabled': self.key is not None
        }

# Globalna instancja szyfrowania
default_encryption = ChatEncryption()

def encrypt_message(message: str, password: str = None) -> str:
    """Szyfruje wiadomość używając globalnej instancji lub podanego hasła"""
    if password:
        temp_encryption = ChatEncryption(password)
        return temp_encryption.encrypt(message)
    return default_encryption.encrypt(message)

def decrypt_message(encrypted_message: str, password: str = None) -> str:
    """Deszyfruje wiadomość używając globalnej instancji lub podanego hasła"""
    if password:
        temp_encryption = ChatEncryption(password)
        return temp_encryption.decrypt(encrypted_message)
    return default_encryption.decrypt(encrypted_message)

def set_encryption_password(password: str):
    """Ustawia hasło dla globalnej instancji szyfrowania"""
    default_encryption.change_password(password)

def is_encryption_available() -> bool:
    """Sprawdza czy szyfrowanie jest dostępne"""
    return ENCRYPTION_AVAILABLE

def demo_encryption():
    """Demonstracja szyfrowania"""
    print("\n🔒 DEMO SZYFROWANIA")
    print("=" * 40)
    
    if not ENCRYPTION_AVAILABLE:
        print("❌ Szyfrowanie niedostępne - zainstaluj 'cryptography'")
        print("   pip install cryptography")
        return
    
    # Test podstawowy
    original = "To jest tajny komunikat!"
    print(f"Oryginalny tekst: {original}")
    
    encrypted = encrypt_message(original)
    print(f"Zaszyfrowany: {encrypted}")
    
    decrypted = decrypt_message(encrypted)
    print(f"Odszyfrowany: {decrypted}")
    
    print(f"Czy poprawnie?: {'✅' if original == decrypted else '❌'}")
    
    # Test z różnymi hasłami
    print("\n📝 Test różnych haseł:")
    password1 = "haslo123"
    password2 = "inne_haslo"
    
    msg = "Wiadomość testowa"
    encrypted1 = encrypt_message(msg, password1)
    encrypted2 = encrypt_message(msg, password2)
    
    print(f"Szyfrowanie hasłem '{password1}': {encrypted1[:30]}...")
    print(f"Szyfrowanie hasłem '{password2}': {encrypted2[:30]}...")
    print(f"Czy różne?: {'✅' if encrypted1 != encrypted2 else '❌'}")
    
    # Próba deszyfrowania złym hasłem
    try:
        wrong_decrypt = decrypt_message(encrypted1, password2)
        print(f"Deszyfrowanie złym hasłem: {'❌ Udało się' if wrong_decrypt == msg else '✅ Nie udało się'}")
    except:
        print("✅ Deszyfrowanie złym hasłem nie powiodło się")
    
    # Informacje o szyfrowaniu
    info = default_encryption.get_encryption_info()
    print(f"\n🔧 Informacje o szyfrowaniu:")
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    print("=" * 40)

if __name__ == "__main__":
    demo_encryption()