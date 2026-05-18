#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              🦂 IPTV BOT ULTRA — BY LUIS R 🦂                               ║
║              Verificación HIT / FAIL / RETRY Perfecta                       ║
║              24/7 en Railway — Gratis                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import time
import threading
import logging
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
ADMIN_ID   = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL = os.getenv("RENDER_URL", "")          # URL de Railway/Render para keep-alive

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()      # silenciar SSL warnings

# ─────────────────────────────────────────────
#  ESTADO GLOBAL
# ─────────────────────────────────────────────
bot_active     = True
BOT_START_TIME = datetime.now()
STATS = {"checks": 0, "hits": 0, "fails": 0, "retries": 0, "users": set()}

# ─────────────────────────────────────────────
#  DISEÑO / SEPARADORES
# ─────────────────────────────────────────────
LINE = "━" * 38

FLAGS = {
    "US": "🇺🇸", "MX": "🇲🇽", "ES": "🇪🇸", "AR": "🇦🇷",
    "CO": "🇨🇴", "CL": "🇨🇱", "PE": "🇵🇪", "VE": "🇻🇪",
    "BR": "🇧🇷", "EC": "🇪🇨", "UY": "🇺🇾", "BO": "🇧🇴",
    "PA": "🇵🇦", "DO": "🇩🇴", "GT": "🇬🇹", "CR": "🇨🇷",
    "GB": "🇬🇧", "DE": "🇩🇪", "FR": "🇫🇷", "NL": "🇳🇱",
    "CA": "🇨🇦", "IT": "🇮🇹", "PT": "🇵🇹", "RU": "🇷🇺",
    "TR": "🇹🇷", "IN": "🇮🇳", "CN": "🇨🇳", "JP": "🇯🇵",
}

# ═══════════════════════════════════════════
#  EXTRACCIÓN DE URL IPTV
# ═══════════════════════════════════════════

def extract_from_url(text: str):
    """Extrae portal, usuario y contraseña de cualquier formato IPTV."""
    patterns = [
        r'(?:https?://)?([^/\s]+)/get\.php\?username=([^&\s]+)&password=([^&\s]+)',
        r'(?:https?://)?([^/\s]+)/player_api\.php\?username=([^&\s]+)&password=([^&\s]+)',
        r'(?:https?://)?([^/\s]+)/playlist/([^/\s]+)/([^/\s]+)',
        r'(?:https?://)?([^/\s]+)/c/[^/]*/([^/\s]+)/([^/\s]+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2), m.group(3)

    # Formato: portal|usuario|password  o  portal usuario password
    if '|' in text:
        parts = [x.strip() for x in text.split('|')]
        if len(parts) == 3 and parts[0]:
            return parts[0], parts[1], parts[2]

    parts = text.split()
    if len(parts) == 3 and ':' in parts[0]:
        return parts[0], parts[1], parts[2]

    return None, None, None

# ═══════════════════════════════════════════
#  VERIFICACIÓN PRINCIPAL
# ═══════════════════════════════════════════

HEADERS = {
    "User-Agent": "VLC/3.0.18 LibVLC/3.0.18",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

def _get(url: str, timeout: int = 15) -> requests.Response | None:
    """GET silencioso; devuelve None en cualquier error de red."""
    try:
        return requests.get(url, headers=HEADERS, timeout=timeout,
                            verify=False, allow_redirects=True)
    except Exception:
        return None


def verify_account(portal: str, user: str, pwd: str) -> tuple[str, dict | None]:
    """
    Lógica de verificación:
      • HIT    → auth=1 y status='Active'
      • CUSTOM → auth=1 pero status != 'Active'  (cuenta existe pero vencida/suspendida)
      • FAIL   → auth=0  (credenciales incorrectas)
      • RETRY  → Sin respuesta, JSON inválido, estructura inesperada
    """
    # Intentar primero con player_api.php
    for scheme in ("http", "https"):
        url = f"{scheme}://{portal}/player_api.php?username={user}&password={pwd}"
        resp = _get(url)

        if resp is None:
            continue                            # error de red → probar https / RETRY final

        if resp.status_code != 200:
            log.warning(f"HTTP {resp.status_code} en {portal}")
            continue

        # ── Intentar parsear JSON ──────────────────────────────────────────
        raw = resp.text.strip()

        # A veces el servidor manda HTML de Cloudflare en vez de JSON
        if raw.startswith("<"):
            log.warning("Respuesta HTML (posible Cloudflare)")
            return "RETRY", None

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("JSON inválido")
            return "RETRY", None

        # ── Verificar estructura ───────────────────────────────────────────
        if not isinstance(data, dict) or "user_info" not in data:
            log.warning("Estructura inesperada (sin user_info)")
            return "RETRY", None

        ui   = data["user_info"]
        auth = ui.get("auth")

        if auth is None:
            return "RETRY", None

        try:
            auth = int(auth)
        except (ValueError, TypeError):
            return "RETRY", None

        if auth == 0:
            return "FAIL", None

        if auth == 1:
            status = ui.get("status", "")
            payload = {
                "user_info":   ui,
                "server_info": data.get("server_info", {}),
            }
            if status == "Active":
                return "HIT", payload
            else:
                return "CUSTOM", payload          # cuenta existe pero no activa

        # auth con valor no reconocido
        return "RETRY", None

    # Ningún scheme funcionó
    return "RETRY", None

# ═══════════════════════════════════════════
#  DATOS ADICIONALES
# ═══════════════════════════════════════════

def get_content_counts(portal: str, user: str, pwd: str) -> tuple[str, str, str]:
    live = vod = series = "N/D"
    base = f"http://{portal}/player_api.php?username={user}&password={pwd}"
    actions = [("get_live_streams", "live"),
               ("get_vod_streams",  "vod"),
               ("get_series",       "series")]
    for action, key in actions:
        r = _get(f"{base}&action={action}", timeout=20)
        if r and r.status_code == 200:
            try:
                d = r.json()
                count = str(len(d)) if isinstance(d, list) else "0"
                if key == "live":   live   = count
                elif key == "vod":  vod    = count
                else:               series = count
            except Exception:
                pass
    return live, vod, series


def get_categories(portal: str, user: str, pwd: str, limit: int = 15) -> str:
    url = (f"http://{portal}/player_api.php?username={user}&password={pwd}"
           f"&action=get_live_categories")
    r = _get(url, timeout=20)
    if not r or r.status_code != 200:
        return ""
    try:
        cats = r.json()
        if not isinstance(cats, list) or not cats:
            return ""

        # Conteo de canales por categoría (opcional, puede fallar)
        count_map: dict[str, int] = {}
        r2 = _get(
            f"http://{portal}/player_api.php?username={user}&password={pwd}"
            f"&action=get_live_streams", timeout=20)
        if r2 and r2.status_code == 200:
            try:
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


def get_server_location(portal: str) -> str:
    ip = portal.split(":")[0]
    r = _get(f"http://ip-api.com/json/{ip}", timeout=6)
    if r and r.status_code == 200:
        try:
            d = r.json()
            if d.get("status") == "success":
                country = d.get("country", "Desconocido")
                code    = d.get("countryCode", "")
                flag    = FLAGS.get(code, "🌍")
                return f"{country} {flag}"
        except Exception:
            pass
    return "Desconocido 🌍"

# ═══════════════════════════════════════════
#  TARJETAS DE RESULTADO
# ═══════════════════════════════════════════

def _ts(epoch) -> str:
    """Convierte epoch a fecha legible."""
    try:
        v = int(epoch)
        if v > 0:
            return datetime.fromtimestamp(v).strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    return "Sin fecha"


def card_hit(portal, user, pwd, ui, si, live, vod, series, cats) -> str:
    expire  = _ts(ui.get("exp_date", 0))
    created = _ts(ui.get("created_at", 0))
    active  = ui.get("active_cons", "0")
    maxcon  = ui.get("max_connections", "0")
    status  = ui.get("status", "Active")
    trial   = "✅ Trial" if ui.get("is_trial") else "❌ No Trial"
    location = get_server_location(portal)

    m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg = f"http://{portal}/xmltv.php?username={user}&password={pwd}"

    card = (
        f"{LINE}\n"
        f"     ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n"
        f"{LINE}\n"
        f"➥ 🟢 CUENTA VÁLIDA\n"
        f"➥ 🆙 Estado: ✅ {status.upper()}\n"
        f"➥ 🧪 Trial: {trial}\n"
        f"➥ 🌐 Portal: {portal}\n"
        f"➥ 👤 Usuario: {user}\n"
        f"➥ 🔑 Contraseña: {pwd}\n"
        f"➥ 📅 Creada: {created}\n"
        f"➥ ⏲ Vence: {expire}\n"
        f"➥ 👁 Conexiones: {active} / {maxcon}\n"
        f"➥ 📍 País: {location}\n"
        f"{LINE}\n"
        f"       ★彡ᴄᴏɴᴛᴇɴᴛ彡★\n"
        f"{LINE}\n"
        f"➥ 📺 En Vivo: {live}\n"
        f"➥ 🎥 VOD: {vod}\n"
        f"➥ 📹 Series: {series}\n"
        f"{LINE}\n"
        f'➥ 🔗 <a href="{m3u}">M3U Link</a>   |   <a href="{epg}">EPG Link</a>\n'
        f"{LINE}\n"
    )
    if cats:
        card += (
            f"    ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★\n"
            f"{LINE}\n"
            f"{cats}\n"
            f"{LINE}\n"
        )
    card += (
        f"  ✔️ Verificado por @{user}\n"
        f"  🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{LINE}"
    )
    return card


def card_custom(portal, user, pwd, ui) -> str:
    status  = ui.get("status", "Desconocido")
    expire  = _ts(ui.get("exp_date", 0))
    maxcon  = ui.get("max_connections", "0")
    return (
        f"{LINE}\n"
        f"     ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n"
        f"{LINE}\n"
        f"➥ 🟡 CUENTA EXISTE — NO ACTIVA\n"
        f"➥ 🆙 Estado: ⚠️ {status.upper()}\n"
        f"➥ 🌐 Portal: {portal}\n"
        f"➥ 👤 Usuario: {user}\n"
        f"➥ 🔑 Contraseña: {pwd}\n"
        f"➥ ⏲ Vence: {expire}\n"
        f"➥ 👥 Max conexiones: {maxcon}\n"
        f"{LINE}\n"
        f"  ⚠️ La cuenta existe pero no está activa\n"
        f"  🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{LINE}"
    )


def card_fail(portal, user) -> str:
    return (
        f"{LINE}\n"
        f"     ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n"
        f"{LINE}\n"
        f"➥ 🔴 CUENTA INVÁLIDA\n"
        f"➥ 🌐 Portal: {portal}\n"
        f"➥ 👤 Usuario: {user}\n"
        f"{LINE}\n"
        f"  ❌ Credenciales incorrectas (auth=0)\n"
        f"  🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{LINE}"
    )


def card_retry(portal, user) -> str:
    return (
        f"{LINE}\n"
        f"     ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★\n"
        f"{LINE}\n"
        f"➥ 🔄 SIN RESPUESTA / RETRY\n"
        f"➥ 🌐 Portal: {portal}\n"
        f"➥ 👤 Usuario: {user}\n"
        f"{LINE}\n"
        f"  ⚠️ El servidor no respondió correctamente\n"
        f"  ⚠️ Posible protección Cloudflare o servidor caído\n"
        f"  💡 Intenta de nuevo en unos minutos\n"
        f"  🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{LINE}"
    )

# ═══════════════════════════════════════════
#  KEEP-ALIVE (Railway 24/7)
# ═══════════════════════════════════════════

def keep_alive():
    """Ping periódico para que Railway/Render no duerma el servicio."""
    if not RENDER_URL:
        return
    while True:
        try:
            requests.get(RENDER_URL, timeout=8)
            log.info("Keep-alive ping OK")
        except Exception:
            pass
        time.sleep(540)   # cada 9 minutos

# ═══════════════════════════════════════════
#  HELPERS TELEGRAM
# ═══════════════════════════════════════════

def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID


async def do_check(update: Update, portal: str, user: str, pwd: str):
    """Lógica central de verificación (llamada desde /check y mensajes URL)."""
    global bot_active
    if not bot_active:
        return

    STATS["checks"] += 1
    STATS["users"].add(update.effective_user.id)

    msg = await update.message.reply_text("🔍 Verificando cuenta…")

    status, result = verify_account(portal, user, pwd)

    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text("📡 Obteniendo contenido y categorías…")
        ui   = result["user_info"]
        si   = result["server_info"]
        live, vod, series = get_content_counts(portal, user, pwd)
        cats = get_categories(portal, user, pwd)
        text = card_hit(portal, user, pwd, ui, si, live, vod, series, cats)
        await msg.edit_text(text, parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True)

    elif status == "CUSTOM":
        STATS["hits"] += 1          # cuenta real, aunque no activa
        ui = result["user_info"]
        text = card_custom(portal, user, pwd, ui)
        await msg.edit_text(text, parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True)

    elif status == "FAIL":
        STATS["fails"] += 1
        await msg.edit_text(card_fail(portal, user), parse_mode=ParseMode.HTML)

    else:  # RETRY
        STATS["retries"] += 1
        await msg.edit_text(card_retry(portal, user), parse_mode=ParseMode.HTML)

# ═══════════════════════════════════════════
#  COMANDOS
# ═══════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    global bot_active
    bot_active = True
    await update.message.reply_text(
        "🦂 *IPTV BOT ULTRA — BY LUIS R* 🦂\n\n"
        "🟢 Bot *ACTIVADO*\n\n"
        "📌 *Envía directamente la URL:*\n"
        "`http://portal:8080/get.php?username=USER&password=PASS`\n\n"
        "📌 *O usa el comando:*\n"
        "`/check portal:puerto usuario contraseña`\n\n"
        "🦂 BY LUIS R — 24/7 en Railway",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text("🔴 *Bot DETENIDO.*\nUsa /start para reactivarlo.",
                                    parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado.")
        return
    uptime = datetime.now() - BOT_START_TIME
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    estado = "🟢 ACTIVO" if bot_active else "🔴 DETENIDO"
    await update.message.reply_text(
        f"🦂 *ESTADO DEL BOT* 🦂\n\n"
        f"📺 Estado: {estado}\n"
        f"⏰ Uptime: {h:02d}h {m:02d}m {s:02d}s\n\n"
        f"✅ Hits: {STATS['hits']}\n"
        f"❌ Fails: {STATS['fails']}\n"
        f"🔄 Retries: {STATS['retries']}\n"
        f"⭐ Total checks: {STATS['checks']}\n"
        f"👥 Usuarios: {len(STATS['users'])}\n\n"
        f"🦂 BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or not bot_active:
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "📌 *Uso:* `/check portal:puerto usuario contraseña`\n"
            "🔥 *Ejemplo:* `/check latinchannel.tv:8080 laura.cal cal130325`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    await do_check(update, args[0], args[1], args[2])


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦂 *COMANDOS* 🦂\n\n"
        "/start — Encender bot\n"
        "/stop — Apagar bot\n"
        "/status — Estado y estadísticas\n"
        "/check `portal usuario pass` — Verificar cuenta\n"
        "/help — Esta ayuda\n\n"
        "💡 También puedes pegar cualquier URL M3U directamente.\n\n"
        "🦂 BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto: detecta URLs IPTV automáticamente."""
    if not is_admin(update) or not bot_active:
        return
    text = (update.message.text or "").strip()
    portal, user, pwd = extract_from_url(text)
    if portal and user and pwd:
        await do_check(update, portal, user, pwd)
    # Si no es una URL IPTV, ignorar silenciosamente

# ═══════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════

def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN no configurado. Agrega la variable de entorno.")
        return

    # Keep-alive en segundo plano
    threading.Thread(target=keep_alive, daemon=True).start()

    log.info("🦂 IPTV BOT ULTRA arrancando…")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("check",  cmd_check))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("✅ Bot iniciado — esperando mensajes.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
