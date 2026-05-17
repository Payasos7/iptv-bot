#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de Telegram - Extractor Universal de IPTV
BY LUIS R
Funcionalidades:
- Extrae y verifica enlaces Xtream Codes (player_api.php)
- Extrae y verifica enlaces M3U / M3U8
- Procesa archivos TXT con listados de enlaces
- Sistema de encendido/apagado del bot (/start, /stop)
- Soporte para proxies
"""

import os
import sys
import re
import json
import time
import logging
import threading
import queue
import requests
from datetime import datetime
from urllib.parse import urlparse, unquote
from typing import Dict, Optional, Tuple, List, Any

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Intento de importar módulos del JChecker (para funcionalidad avanzada) ---
try:
    from jchecker_6 import (
        c_datos, get_or_fetch_server_content, proxy_manager as jc_proxy_manager,
        http_manager, setup_logger, create_directories, DIRECTORIES
    )
    # También intentamos importar el bypass de cloudflare
    try:
        import cloudflare_bypass
        CLOUDFLARE_BYPASS_AVAILABLE = True
        logger.info("✅ Módulo Cloudflare Bypass cargado")
    except ImportError:
        CLOUDFLARE_BYPASS_AVAILABLE = False
        logger.warning("⚠️ Cloudflare Bypass no disponible")
    JCHECKER_AVAILABLE = True
    logger.info("✅ Módulos de JChecker cargados correctamente")
except ImportError as e:
    logger.warning(f"⚠️ No se pudieron cargar módulos de JChecker: {e}")
    logger.warning("⚠️ Se usará verificador simplificado")
    JCHECKER_AVAILABLE = False
    CLOUDFLARE_BYPASS_AVAILABLE = False
    # Definimos una versión simplificada de c_datos si no está disponible
    def c_datos(panel, user, password, session=None, proxy=None):
        """Versión simplificada de c_datos"""
        return "?", "?", "?"

# --- Configuración del Bot ---
BOT_TOKEN = "8708803857:AAHsIF_AbBuM_GPam1MWYBBRFycRSWAA4Cs"
ADMIN_CHAT_ID = "1183299436"
PROCESSING_QUEUE = queue.Queue()
BOT_RUNNING = True
BOT_LOCK = threading.Lock()

# --- Sistema de Proxy Manager (Adaptado de JChecker) ---
class BotProxyManager:
    """Gestor de proxies para el bot"""
    def __init__(self):
        self.enabled = False
        self.proxies = []
        self.current_proxy_index = 0
        self.lock = threading.Lock()
        self.proxy_type = "http"
        self.proxy_file = None

    def load_proxies(self, filename: str, proxy_type: str) -> bool:
        """Carga proxies desde un archivo"""
        if not os.path.exists(filename):
            logger.error(f"Archivo de proxies no encontrado: {filename}")
            return False

        self.proxy_type = proxy_type
        self.proxy_file = filename

        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                raw_proxies = [line.strip() for line in f if line.strip()]

            self.proxies = []
            for proxy in raw_proxies:
                formatted = self._format_proxy(proxy, proxy_type)
                if formatted:
                    self.proxies.append(formatted)

            if self.proxies:
                self.enabled = True
                logger.info(f"✅ {len(self.proxies)} proxies cargados desde {filename}")
                return True
            else:
                logger.warning(f"No se encontraron proxies válidos en {filename}")
                return False

        except Exception as e:
            logger.error(f"Error cargando proxies: {e}")
            return False

    def _format_proxy(self, proxy: str, proxy_type: str) -> Optional[Dict]:
        """Formatea un proxy para requests"""
        proxy = proxy.strip()
        proxy_type_lower = proxy_type.lower()

        # Formato con autenticación: user:pass@host:port
        if '@' in proxy:
            auth_part, addr_part = proxy.split('@', 1)
            if ':' in auth_part:
                user, password = auth_part.split(':', 1)
                host, port = addr_part.rsplit(':', 1)
            else:
                return None
        # Formato simple: host:port
        elif ':' in proxy:
            parts = proxy.split(':')
            if len(parts) == 2:
                host, port = parts[0], parts[1]
                user, password = None, None
            elif len(parts) == 4:
                host, port, user, password = parts
            else:
                return None
        else:
            return None

        try:
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                return None
        except ValueError:
            return None

        if proxy_type_lower in ['socks5', '5']:
            if user and password:
                proxy_url = f'socks5://{user}:{password}@{host}:{port}'
            else:
                proxy_url = f'socks5://{host}:{port}'
        elif proxy_type_lower in ['socks4', '4']:
            if user and password:
                proxy_url = f'socks4://{user}:{password}@{host}:{port}'
            else:
                proxy_url = f'socks4://{host}:{port}'
        else:
            if user and password:
                proxy_url = f'http://{user}:{password}@{host}:{port}'
            else:
                proxy_url = f'http://{host}:{port}'

        return {'http': proxy_url, 'https': proxy_url}

    def get_proxy(self) -> Optional[Dict]:
        """Obtiene el siguiente proxy (round-robin)"""
        if not self.enabled or not self.proxies:
            return None

        with self.lock:
            proxy = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            return proxy

    def remove_proxy(self, proxy: Dict):
        """Marca un proxy como malo (opcional)"""
        # Por simplicidad, no removemos proxies en esta versión
        pass

# Instancia global del gestor de proxies
bot_proxy_manager = BotProxyManager()

# --- Funciones de Utilidad (Basadas en JChecker) ---
def get_country_flag(country_code: str) -> str:
    """Obtiene emoji de bandera del país"""
    flags = {
        'US': '🇺🇸', 'MX': '🇲🇽', 'CA': '🇨🇦', 'GB': '🇬🇧', 'ES': '🇪🇸',
        'FR': '🇫🇷', 'DE': '🇩🇪', 'IT': '🇮🇹', 'BR': '🇧🇷', 'AR': '🇦🇷',
        'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'CL': '🇨🇱', 'EC': '🇪🇨',
    }
    return flags.get(country_code.upper(), '🌍')

def get_server_location(host: str) -> str:
    """Obtiene ubicación del servidor usando IP-API"""
    try:
        # Resolver IP
        import socket
        ip = socket.gethostbyname(host)
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Desconocido')
                country_code = data.get('countryCode', '')
                flag = get_country_flag(country_code)
                return f"{country} {flag}"
    except Exception as e:
        logger.debug(f"Error obteniendo ubicación: {e}")
    return "Desconocido 🌍"

def escape_html(text: str) -> str:
    """Escapa caracteres para HTML de Telegram"""
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# --- Extracción de Datos de URLs ---
def extract_xtream_data(url: str) -> Optional[Dict]:
    """Extrae datos de una URL Xtream Codes (player_api.php)"""
    # Patrones para diferentes formatos
    patterns = [
        r'(?:https?://)?([^/]+)/player_api\.php\?username=([^&]+)&password=([^&]+)',
        r'(?:https?://)?([^/]+)/get\.php\?username=([^&]+)&password=([^&]+)',
        r'(?:https?://)?([^/]+)/c/.*?/([^/]+)/([^/]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                portal = groups[0]
                username = groups[1]
                password = groups[2]
                return {
                    'type': 'xtream',
                    'portal': portal,
                    'username': username,
                    'password': password,
                    'original_url': url
                }
    return None

def extract_m3u_data(url: str) -> Optional[Dict]:
    """Extrae datos de una URL M3U"""
    # Patrón para URLs M3U con autenticación
    pattern = r'(?:https?://)?([^/]+)/get\.php\?username=([^&]+)&password=([^&]+)&type=m3u'
    match = re.search(pattern, url)
    if match:
        return {
            'type': 'm3u',
            'portal': match.group(1),
            'username': match.group(2),
            'password': match.group(3),
            'original_url': url
        }

    # Patrón para formato player_api con action
    pattern2 = r'(?:https?://)?([^/]+)/player_api\.php\?username=([^&]+)&password=([^&]+)'
    match2 = re.search(pattern2, url)
    if match2:
        return {
            'type': 'm3u',
            'portal': match2.group(1),
            'username': match2.group(2),
            'password': match2.group(3),
            'original_url': url
        }

    return None

def extract_playlist_data(url: str) -> Optional[Dict]:
    """Intenta extraer datos de cualquier URL de playlist"""
    # Primero probar como Xtream
    data = extract_xtream_data(url)
    if data:
        return data

    # Luego como M3U
    data = extract_m3u_data(url)
    if data:
        return data

    return None

# --- Verificación de Cuenta (Adaptada de JChecker) ---
def verify_account(portal: str, username: str, password: str, use_proxy: bool = False) -> Dict:
    """Verifica una cuenta IPTV usando la lógica de JChecker"""
    result = {
        'success': False,
        'status': 'fail',
        'user_info': {},
        'live_count': '?',
        'vod_count': '?',
        'series_count': '?',
        'error': None
    }

    protocol = 'https' if 'https://' in portal else 'http'
    portal_clean = portal.replace('http://', '').replace('https://', '')
    base_url = f"{protocol}://{portal_clean}"

    # Intentar usar Cloudflare bypass si está disponible
    if CLOUDFLARE_BYPASS_AVAILABLE and cloudflare_bypass.is_cloudflare_protected(portal_clean):
        logger.info(f"🌙 Usando Cloudflare bypass para {portal_clean}")
        try:
            cf_result = cloudflare_bypass.check_account_with_cloudflare_bypass(
                base_url, username, password
            )
            if cf_result and cf_result.get('status') == 'hit':
                result['success'] = True
                result['status'] = 'hit'
                result['user_info'] = cf_result.get('user_info', {})
                # Obtener contenido
                live, vod, series = c_datos(base_url, username, password)
                result['live_count'] = live
                result['vod_count'] = vod
                result['series_count'] = series
                return result
        except Exception as e:
            logger.error(f"Error en Cloudflare bypass: {e}")

    # Construir URL de verificación
    verify_url = f"{base_url}/player_api.php?username={username}&password={password}"
    proxy = bot_proxy_manager.get_proxy() if use_proxy and bot_proxy_manager.enabled else None

    try:
        # Headers específicos (como en JChecker)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Connection': 'keep-alive',
        }

        response = requests.get(verify_url, headers=headers, proxies=proxy, timeout=(10, 30), verify=False)

        if response.status_code != 200:
            result['error'] = f"HTTP {response.status_code}"
            return result

        # Parsear JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            result['error'] = "Respuesta no es JSON"
            return result

        # Validar estructura
        if 'user_info' not in data:
            result['error'] = "Formato de respuesta inválido"
            return result

        user_info = data['user_info']
        auth = user_info.get('auth', 0)

        try:
            auth_int = int(auth)
        except (ValueError, TypeError):
            result['error'] = "auth no numérico"
            return result

        if auth_int == 0:
            result['error'] = "Credenciales inválidas"
            return result

        # Cuenta válida
        result['success'] = True
        result['status'] = 'hit' if user_info.get('status') == 'Active' else 'custom'
        result['user_info'] = user_info
        result['is_xui'] = bool(data.get('server_info', {}).get('xui', False))

        # Obtener conteos de contenido usando c_datos
        try:
            live, vod, series = c_datos(base_url, username, password)
            result['live_count'] = live if live != "?" else "0"
            result['vod_count'] = vod if vod != "?" else "0"
            result['series_count'] = series if series != "?" else "0"
        except Exception as e:
            logger.error(f"Error en c_datos: {e}")
            result['live_count'] = "?"
            result['vod_count'] = "?"
            result['series_count'] = "?"

        return result

    except requests.exceptions.Timeout:
        result['error'] = "Timeout"
        return result
    except requests.exceptions.ConnectionError:
        result['error'] = "Error de conexión"
        return result
    except Exception as e:
        result['error'] = str(e)
        return result

# --- Formato de Mensaje (Estilo Solicitado) ---
def format_account_message(user_info: Dict, portal: str, username: str, password: str,
                           live_count: str, vod_count: str, series_count: str,
                           user_first_name: str = "") -> str:
    """Formatea el mensaje con el estilo moderno solicitado"""
    
    # Extraer datos
    expire = user_info.get('exp_date')
    expire_str = "No expira"
    if expire and expire != "null":
        try:
            if str(expire).isdigit():
                expire_str = datetime.fromtimestamp(int(expire)).strftime('%d/%m/%Y %H:%M')
            else:
                expire_str = str(expire)
        except:
            expire_str = "Formato inválido"

    active_cons = user_info.get('active_cons', '0')
    max_cons = user_info.get('max_connections', '0')
    status = user_info.get('status', 'Active')
    is_trial = "Trial" if "trial" in username.lower() or "test" in username.lower() else "No Trial"

    # Obtener país
    host = portal.split(':')[0]
    country = get_server_location(host)

    # Construcción del mensaje con el formato exacto
    separator = "━━━━━━━━━━━━━━━━━━━━━━"
    
    message = f"""
{separator}
     ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★
{separator}
➥ 🟢 CUENTA VÁLIDA
➥🆙 Estado: ✅ {status}
➥🧪 {is_trial}
➥🌐 Portal: {portal}
➥👤 Usuario: {username}
➥🔑 Contraseña: {password}
➥⏲ Vence: {expire_str}
➥👁 Conexiones: {active_cons} / {max_cons}
➥📍 País: {country}
{separator}
       ★彡ᴄᴏɴᴛᴇɴᴛ彡★
{separator}
➥📺 En Vivo: {live_count}
➥🎥 VOD: {vod_count}
➥📹 Series: {series_count}
{separator}
➥🔗 M3U Link   |   EPG Link
{separator}
    ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★
{separator}
  ➠ • Procesando categorías...
{separator}

   ✔️ Verificado por BY LUIS R
   🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{separator}"""

    # Mensaje personalizado para el usuario
    if user_first_name:
        message = f"✨ @{user_first_name}, aquí tienes el resultado ✨\n" + message
    else:
        message = f"✨ ¡Hola! Aquí tienes el resultado ✨\n" + message

    return message

def format_error_message(error: str, user_first_name: str = "") -> str:
    """Formatea mensaje de error"""
    separator = "━━━━━━━━━━━━━━━━━━━━━━"
    message = f"""
{separator}
     ★彡ᴇʀʀᴏʀ ᴇɴ ᴠᴇʀɪꜰɪᴄᴀᴄɪóɴ彡★
{separator}
➥ ❌ Estado: FALLIDO
➥ 📋 Error: {error}
{separator}

   ✔️ Verificado por BY LUIS R
   🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{separator}"""
    
    if user_first_name:
        message = f"❌ @{user_first_name}, ocurrió un error:\n" + message
    return message

# --- Procesamiento de Enlaces Individuales ---
def process_single_url(url: str, use_proxy: bool) -> Dict:
    """Procesa un enlace individual y devuelve resultado"""
    # Extraer datos
    data = extract_playlist_data(url)
    if not data:
        return {
            'success': False,
            'error': 'No se pudo extraer información del enlace',
            'url': url
        }

    # Verificar cuenta
    result = verify_account(data['portal'], data['username'], data['password'], use_proxy)

    if result['success']:
        return {
            'success': True,
            'portal': data['portal'],
            'username': data['username'],
            'password': data['password'],
            'live_count': result.get('live_count', '?'),
            'vod_count': result.get('vod_count', '?'),
            'series_count': result.get('series_count', '?'),
            'user_info': result.get('user_info', {}),
            'url': url
        }
    else:
        return {
            'success': False,
            'error': result.get('error', 'Verificación fallida'),
            'portal': data['portal'],
            'username': data['username'],
            'url': url
        }

# --- Procesamiento de Archivos TXT ---
def process_txt_file(file_content: str, use_proxy: bool) -> str:
    """Procesa un archivo TXT con múltiples enlaces"""
    lines = file_content.strip().split('\n')
    results = []
    total = len([l for l in lines if l.strip()])
    processed = 0
    valid = 0
    invalid = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        processed += 1
        result = process_single_url(line, use_proxy)

        if result['success']:
            valid += 1
            user_info = result.get('user_info', {})
            expire = user_info.get('exp_date', 'No expira')
            if expire and expire != "null":
                try:
                    if str(expire).isdigit():
                        expire = datetime.fromtimestamp(int(expire)).strftime('%Y-%m-%d')
                except:
                    pass
            status = user_info.get('status', 'Active')
            results.append(f"[✅ VÁLIDA] {result['portal']} | {result['username']} | {result['password']} | Exp: {expire} | Status: {status} | Live: {result['live_count']} | VOD: {result['vod_count']} | Series: {result['series_count']}")
        else:
            invalid += 1
            results.append(f"[❌ INVÁLIDA] {result.get('portal', '?')} | {result.get('username', '?')} | Error: {result.get('error', 'Desconocido')}")

    # Crear archivo de resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"verification_results_{timestamp}.txt"

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(f"=== RESULTADOS DE VERIFICACIÓN ===\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total procesados: {total}\n")
        f.write(f"Válidas: {valid}\n")
        f.write(f"Inválidas: {invalid}\n")
        f.write(f"{'='*50}\n\n")
        f.write("\n".join(results))

    return output_filename

# --- Configuración Inicial del Bot ---
def setup_bot_proxies():
    """Configura los proxies al inicio del bot"""
    print("\n" + "="*60)
    print("🔧 CONFIGURACIÓN DE PROXIES PARA EL BOT")
    print("="*60)

    use_proxies = input("\n¿Desea usar proxies para las verificaciones? (s/n): ").lower() == 's'

    if not use_proxies:
        print("✅ Bot configurado SIN proxies")
        return False

    print("\n📁 BUSCANDO ARCHIVOS DE PROXIES...")
    proxy_dir = 'Proxies'

    if not os.path.exists(proxy_dir):
        os.makedirs(proxy_dir)
        print(f"⚠️ Carpeta '{proxy_dir}' creada. Agrega archivos de proxies allí.")
        return False

    proxy_files = [f for f in os.listdir(proxy_dir) if f.endswith('.txt')]

    if not proxy_files:
        print(f"⚠️ No se encontraron archivos .txt en la carpeta '{proxy_dir}'")
        return False

    print("\n📄 Archivos de proxies disponibles:")
    for i, file in enumerate(proxy_files, 1):
        print(f"  {i}. {file}")

    try:
        choice = int(input("\nSeleccione el número del archivo de proxies: "))
        if 1 <= choice <= len(proxy_files):
            proxy_file = os.path.join(proxy_dir, proxy_files[choice-1])

            print("\n🔧 Tipos de proxy:")
            print("  1. HTTP/HTTPS")
            print("  2. SOCKS5")
            print("  3. SOCKS4")

            type_choice = input("Seleccione el tipo de proxy: ")
            proxy_type_map = {'1': 'http', '2': 'socks5', '3': 'socks4'}
            proxy_type = proxy_type_map.get(type_choice, 'http')

            if bot_proxy_manager.load_proxies(proxy_file, proxy_type):
                print(f"✅ {len(bot_proxy_manager.proxies)} proxies cargados correctamente")
                return True
            else:
                print("❌ Error cargando proxies")
                return False
    except ValueError:
        print("❌ Opción inválida")
        return False

    return False

# --- Bot de Telegram ---
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Variable global para controlar el estado del bot
bot_active = True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Enciende el bot"""
    global bot_active
    user = update.effective_user
    user_name = user.first_name or user.username or "Usuario"

    if str(user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text(f"❌ Lo siento {user_name}, no tienes permiso para usar este bot.")
        return

    bot_active = True
    await update.message.reply_text(
        f"✨ ¡Bot ACTIVADO! ✨\n\n"
        f"✅ Hola {user_name}, el bot está listo para recibir enlaces.\n\n"
        f"📎 Puedes enviarme:\n"
        f"• Enlaces Xtream Codes (player_api.php)\n"
        f"• Enlaces M3U/M3U8\n"
        f"• Archivos TXT con listas de enlaces\n\n"
        f"🔧 Comandos disponibles:\n"
        f"/stop - Apagar el bot\n"
        f"/status - Ver estado del bot\n"
        f"/help - Ayuda\n\n"
        f"⚡ BY LUIS R"
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stop - Apaga el bot"""
    global bot_active
    user = update.effective_user

    if str(user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return

    bot_active = False
    await update.message.reply_text(
        "🛑 Bot APAGADO 🛑\n\n"
        "El bot ya no procesará más solicitudes.\n"
        "Usa /start para encenderlo nuevamente.\n\n"
        "⚡ BY LUIS R"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status - Muestra el estado del bot"""
    global bot_active
    user = update.effective_user

    if str(user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return

    status_text = "🟢 ACTIVO" if bot_active else "🔴 APAGADO"
    proxy_status = "✅ Conectado" if bot_proxy_manager.enabled else "❌ Sin proxies"
    proxy_count = len(bot_proxy_manager.proxies) if bot_proxy_manager.enabled else 0

    await update.message.reply_text(
        f"📊 ESTADO DEL BOT\n\n"
        f"Estado: {status_text}\n"
        f"Proxies: {proxy_status} ({proxy_count})\n"
        f"Modo: Extractor Universal\n"
        f"Versión: 2.0\n\n"
        f"⚡ BY LUIS R"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help - Muestra ayuda"""
    await update.message.reply_text(
        "📖 AYUDA - EXTRACTOR UNIVERSAL IPTV\n\n"
        "🔗 ENLACES SOPORTADOS:\n"
        "• http://portal/player_api.php?username=user&password=pass\n"
        "• http://portal/get.php?username=user&password=pass&type=m3u\n"
        "• http://portal/playlist/user/pass/m3u_plus\n\n"
        "📁 ARCHIVOS TXT:\n"
        "Envía un archivo .txt con un enlace por línea\n\n"
        "⚙️ COMANDOS:\n"
        "/start - Encender el bot\n"
        "/stop - Apagar el bot\n"
        "/status - Ver estado\n"
        "/help - Esta ayuda\n\n"
        "⚡ BY LUIS R - Extractor Universal"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los mensajes entrantes"""
    global bot_active

    # Verificar si el bot está activo
    if not bot_active:
        await update.message.reply_text("🔴 El bot está apagado. Usa /start para encenderlo.")
        return

    # Verificar permisos
    user = update.effective_user
    user_name = user.first_name or user.username or "Usuario"

    if str(user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text(f"❌ Lo siento {user_name}, no tienes permiso para usar este bot.")
        return

    # Mensaje de procesamiento
    processing_msg = await update.message.reply_text(f"⏳ Procesando tu solicitud, {user_name}...")

    # Obtener el texto o documento
    text = update.message.text
    document = update.message.document

    try:
        if document and document.file_name.endswith('.txt'):
            # Procesar archivo TXT
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()
            file_text = file_content.decode('utf-8', errors='ignore')

            await processing_msg.edit_text(f"📁 Procesando archivo con múltiples enlaces...\n⏳ Esto puede tomar unos momentos, {user_name}.")

            output_file = process_txt_file(file_text, bot_proxy_manager.enabled)

            # Enviar archivo de resultados
            with open(output_file, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=output_file,
                    caption=f"📊 Resultados de verificación\nProcesado por: {user_name}\nBY LUIS R"
                )

            # Limpiar archivo temporal
            os.remove(output_file)
            await processing_msg.delete()

        elif text:
            # Verificar si es un enlace
            if not (text.startswith('http://') or text.startswith('https://')):
                await processing_msg.edit_text(f"❌ {user_name}, por favor envía un enlace válido (http:// o https://)")
                return

            # Procesar enlace individual
            await processing_msg.edit_text(f"🔍 Analizando enlace...\n⏳ Por favor espera, {user_name}.")

            result = process_single_url(text, bot_proxy_manager.enabled)

            if result['success']:
                message = format_account_message(
                    result['user_info'],
                    result['portal'],
                    result['username'],
                    result['password'],
                    result['live_count'],
                    result['vod_count'],
                    result['series_count'],
                    user_name
                )
                await processing_msg.delete()
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                error_msg = format_error_message(result.get('error', 'Verificación fallida'), user_name)
                await processing_msg.edit_text(error_msg)
        else:
            await processing_msg.edit_text(f"❌ {user_name}, formato no válido. Envía un enlace o un archivo .txt")

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        await processing_msg.edit_text(f"❌ Error: {str(e)}\n\nPor favor intenta nuevamente.")

# --- Función Principal ---
def main():
    """Función principal del bot"""
    global bot_active

    print("="*60)
    print("   IPTV UNIVERSAL EXTRACTOR - BOT DE TELEGRAM")
    print("   BY LUIS R - Versión 2.0")
    print("="*60)

    # Configurar proxies
    use_proxies = setup_bot_proxies()

    # Crear directorios necesarios
    for directory in ['combo', 'hits', 'Proxies', 'sound', 'logs']:
        if not os.path.exists(directory):
            os.makedirs(directory)

    print("\n" + "="*60)
    print("🤖 INICIANDO BOT DE TELEGRAM...")
    print("="*60)

    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()

    # Registrar comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))

    # Registrar manejador de mensajes
    application.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_message))

    # Iniciar bot
    print("\n✅ Bot iniciado correctamente")
    print(f"📱 Token: {BOT_TOKEN[:15]}...")
    print("🎯 Comandos disponibles:")
    print("   /start  - Encender el bot")
    print("   /stop   - Apagar el bot")
    print("   /status - Ver estado")
    print("   /help   - Ayuda")
    print("\n" + "="*60)
    print("🟢 Bot ACTIVO - Esperando mensajes...")
    print("Presiona Ctrl+C para detener el bot")
    print("="*60)

    # Iniciar polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
    finally:
        print("\n👋 ¡Hasta luego! BY LUIS R")