#!/usr/bin/env python3
"""
Kolory i formatowanie tekstu w konsoli
"""

import os
import sys

class Colors:
    """Klasa z kolorami ANSI"""
    # Kolory podstawowe
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Kolory jasne
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Style
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    STRIKETHROUGH = '\033[9m'
    
    # Reset
    RESET = '\033[0m'
    
    # Sprawdź czy terminal obsługuje kolory
    @staticmethod
    def supports_color():
        """Sprawdza czy terminal obsługuje kolory"""
        return (
            hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and
            os.environ.get("TERM") != "dumb" and
            os.environ.get("NO_COLOR") is None
        )

class ColoredText:
    """Klasa do kolorowego formatowania tekstu"""
    
    def __init__(self, use_colors=None):
        if use_colors is None:
            self.use_colors = Colors.supports_color()
        else:
            self.use_colors = use_colors
    
    def _format(self, text, *codes):
        """Formatuje tekst z kodami kolorów"""
        if not self.use_colors:
            return text
        
        start_codes = ''.join(codes)
        return f"{start_codes}{text}{Colors.RESET}"
    
    def red(self, text):
        return self._format(text, Colors.RED)
    
    def green(self, text):
        return self._format(text, Colors.GREEN)
    
    def yellow(self, text):
        return self._format(text, Colors.YELLOW)
    
    def blue(self, text):
        return self._format(text, Colors.BLUE)
    
    def magenta(self, text):
        return self._format(text, Colors.MAGENTA)
    
    def cyan(self, text):
        return self._format(text, Colors.CYAN)
    
    def white(self, text):
        return self._format(text, Colors.WHITE)
    
    def bright_red(self, text):
        return self._format(text, Colors.BRIGHT_RED)
    
    def bright_green(self, text):
        return self._format(text, Colors.BRIGHT_GREEN)
    
    def bright_yellow(self, text):
        return self._format(text, Colors.BRIGHT_YELLOW)
    
    def bright_blue(self, text):
        return self._format(text, Colors.BRIGHT_BLUE)
    
    def bright_cyan(self, text):
        return self._format(text, Colors.BRIGHT_CYAN)
    
    def bold(self, text):
        return self._format(text, Colors.BOLD)
    
    def dim(self, text):
        return self._format(text, Colors.DIM)
    
    def italic(self, text):
        return self._format(text, Colors.ITALIC)
    
    def underline(self, text):
        return self._format(text, Colors.UNDERLINE)
    
    def success(self, text):
        return self._format(text, Colors.BRIGHT_GREEN, Colors.BOLD)
    
    def error(self, text):
        return self._format(text, Colors.BRIGHT_RED, Colors.BOLD)
    
    def warning(self, text):
        return self._format(text, Colors.BRIGHT_YELLOW, Colors.BOLD)
    
    def info(self, text):
        return self._format(text, Colors.BRIGHT_BLUE, Colors.BOLD)
    
    def system(self, text):
        return self._format(text, Colors.CYAN, Colors.BOLD)
    
    def user_message(self, user, message):
        """Formatuje wiadomość użytkownika z kolorowym nickiem"""
        if not self.use_colors:
            return f"{user}: {message}"
        
        # Różne kolory dla różnych użytkowników (hash nick)
        colors = [Colors.GREEN, Colors.YELLOW, Colors.BLUE, Colors.MAGENTA, Colors.CYAN]
        color_index = hash(user) % len(colors)
        user_color = colors[color_index]
        
        return f"{user_color}{user}{Colors.RESET}: {message}"
    
    def timestamp(self, text):
        return self._format(text, Colors.DIM)

# Globalna instancja
colored = ColoredText()

def print_colored(text, color_func=None):
    """Drukuje kolorowy tekst"""
    if color_func:
        print(color_func(text))
    else:
        print(text)

def print_success(text):
    print(colored.success(f"✅ {text}"))

def print_error(text):
    print(colored.error(f"❌ {text}"))

def print_warning(text):
    print(colored.warning(f"⚠️ {text}"))

def print_info(text):
    print(colored.info(f"ℹ️ {text}"))

def print_system(text):
    print(colored.system(f"🔔 {text}"))

# Demo kolorów
def demo_colors():
    """Pokazuje dostępne kolory"""
    ct = ColoredText()
    
    print("\n🎨 Demo kolorów:")
    print("=" * 40)
    
    print(ct.red("Czerwony tekst"))
    print(ct.green("Zielony tekst"))
    print(ct.blue("Niebieski tekst"))
    print(ct.yellow("Żółty tekst"))
    print(ct.magenta("Magenta tekst"))
    print(ct.cyan("Cyjan tekst"))
    
    print(ct.bold("Pogrubiony tekst"))
    print(ct.italic("Pochylony tekst"))
    print(ct.underline("Podkreślony tekst"))
    
    print(ct.success("Sukces!"))
    print(ct.error("Błąd!"))
    print(ct.warning("Ostrzeżenie!"))
    print(ct.info("Informacja"))
    print(ct.system("System"))
    
    print(ct.user_message("Jan", "Przykładowa wiadomość"))
    print(ct.user_message("Anna", "Kolejna wiadomość"))
    print(ct.user_message("Tomek", "Jeszcze jedna wiadomość"))
    
    print("=" * 40)

if __name__ == "__main__":
    demo_colors()