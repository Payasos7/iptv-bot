#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║        🦂 IPTV BOT ULTRA INSTINTO — BY LUIS R 🦂            ║
║          Telegram Bot 24/7 — Render/GitHub Ready             ║
║         Acepta URLs M3U completas + combos + comandos        ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import json
import logging
import threading
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# ──────────────────────────────────────────────
#  DEPENDENCIAS
# ──────────────────────────────────────────────
try:
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup
    )
    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler,
        MessageHandler, filters, ContextTypes
    )
    from telegram.constants import ParseMode
except ImportError:
    print("❌ Instala: pip install python-telegram-bot>=20.0")
    sys.exit(1)

try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print("❌ Instala: pip install requests")
    sys.exit(1)

# ──────────────────────────────────────────────
#  CONFIGURACIÓN
# ──────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN",  "TU_TOKEN_AQUI")
ADMIN_ID   = int(os.getenv("ADMIN_ID", "0"))
ADMIN_USER = os.getenv("ADMIN_USERNAME", "luisr")
RENDER_URL = os.getenv("RENDER_URL", "")

# ──────────────────────────────────────────────
#  ESTADO GLOBAL
# ──────────────────────────────────────────────
BOT_START_TIME = datetime.now()
bot_state = {
    "running":     True,
    "checks_done": 0,
    "hits_total":  0,
    "users":       set(),
}

# ──────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("LuisRBot")

SEP = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ═══════════════════════════════════════════════
#  PARSER — reconoce cualquier formato de entrada
# ═══════════════════════════════════════════════

def parse_m3u_url(text: str):
    """
    Extrae (portal_con_puerto, usuario, password) desde:
      1. URL M3U completa:  http://portal:port/get.php?username=X&password=Y
      2. URL player_api:    http://portal:port/player_api.php?username=X&password=Y
      3. Combo pipe:        portal:port|user|pass
      4. Tres tokens:       portal:port user pass
    Retorna una tupla o None.
    """
    text = text.strip()

    # Formato 1 y 2: URL con http/https
    if text.startswith("http://") or text.startswith("https://"):
        try:
            parsed = urlparse(text)
            host   = parsed.hostname or ""
            port   = parsed.port
            portal = f"{host}:{port}" if port else host
            qs     = parse_qs(parsed.query)
            user   = qs.get("username", [None])[0]
            pwd    = qs.get("password",  [None])[0]
            if portal and user and pwd:
                return portal, user, pwd
        except Exception:
            pass

    # Formato 3: pipe
    if "|" in text:
        parts = [p.strip() for p in text.split("|")]
        if len(parts) >= 3 and "." in parts[0]:
            return parts[0], parts[1], parts[2]

    # Formato 4: espacios
    parts = text.split()
    if len(parts) == 3 and "." in parts[0]:
        return parts[0], parts[1], parts[2]

    return None


# ═══════════════════════════════════════════════
#  VERIFICADOR IPTV
# ═══════════════════════════════════════════════

def check_iptv(portal: str, user: str, pwd: str, timeout: int = 12):
    """Consulta la API del servidor. Devuelve dict con info o dict con 'error'."""
    base = portal if portal.startswith("http") else f"http://{portal}"
    api  = f"{base}/player_api.php?username={user}&password={pwd}"

    try:
        resp = requests.get(api, timeout=timeout, verify=False)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "connection"}
    except Exception as e:
        return {"error": str(e)}

    ui = data.get("user_info", {})
    si = data.get("server_info", {})

    exp_ts = ui.get("exp_date")
    try:
        exp_str = datetime.fromtimestamp(int(exp_ts)).strftime("%d/%m/%Y %H:%M") if exp_ts else "Sin fecha"
    except Exception:
        exp_str = str(exp_ts) if exp_ts else "Sin fecha"

    # Categorías en vivo
    cats_live = []
    try:
        r = requests.get(f"{base}/player_api.php?username={user}&password={pwd}&action=get_live_categories",
                         timeout=10, verify=False)
        raw = r.json()
        if isinstance(raw, list):
            cats_live = [f"• {c.get('category_name','?')}" for c in raw]
    except Exception:
        pass

    # VOD
    vod_count = 0
    try:
        r = requests.get(f"{base}/player_api.php?username={user}&password={pwd}&action=get_vod_categories",
                         timeout=10, verify=False)
        raw = r.json()
        if isinstance(raw, list):
            vod_count = len(raw)
    except Exception:
        pass

    # Series
    ser_count = 0
    try:
        r = requests.get(f"{base}/player_api.php?username={user}&password={pwd}&action=get_series_categories",
                         timeout=10, verify=False)
        raw = r.json()
        if isinstance(raw, list):
            ser_count = len(raw)
    except Exception:
        pass

    portal_clean = portal.replace("http://", "").replace("https://", "")
    active = str(ui.get("active_cons", "?"))
    max_c  = str(ui.get("max_connections", "?"))

    return {
        "ok":       True,
        "status":   ui.get("status", "unknown"),
        "portal":   portal_clean,
        "user":     user,
        "pwd":      pwd,
        "exp":      exp_str,
        "trial":    "Sí" if str(ui.get("is_trial","0")) == "1" else "No Trial",
        "conns":    f"{active} / {max_c}",
        "country":  si.get("country", "N/A"),
        "timezone": si.get("timezone", "N/A"),
        "live_cats":cats_live,
        "live_n":   str(len(cats_live)),
        "vod_n":    str(vod_count),
        "series_n": str(ser_count),
    }


# ═══════════════════════════════════════════════
#  TARJETA DE INFO ULTRA PRO
# ═══════════════════════════════════════════════

def build_card(info: dict, tg_user: str) -> str:
    portal = info["portal"]
    user   = info["user"]
    pwd    = info["pwd"]
    status = info["status"]

    if status.lower() in ("active", "activa"):
        st_icon = "🟢"
        st_txt  = "✅ ACTIVA"
    else:
        st_icon = "🔴"
        st_txt  = "❌ INACTIVA"

    m3u = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cats_list = info.get("live_cats", [])
    if cats_list:
        shown    = cats_list[:15]
        cats_txt = "\n".join(f"  ➠ {c}" for c in shown)
        if len(cats_list) > 15:
            cats_txt += f"\n  ➕ ...y {len(cats_list)-15} categorías más"
    else:
        cats_txt = "  ➠ Sin datos de categorías"

    return (
        f"{SEP}\n"
        f"     ★彡`ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ`彡★\n"
        f"     🦂 *BY LUIS R* 🦂\n"
        f"{SEP}\n"
        f"➥ {st_icon} CUENTA VÁLIDA\n"
        f"➥🆙 Estado: {st_txt}\n"
        f"➥🧪 Trial: `{info['trial']}`\n"
        f"➥🌐 Portal: `{portal}`\n"
        f"➥👤 Usuario: `{user}`\n"
        f"➥🔑 Contraseña: `{pwd}`\n"
        f"➥⏲ Vence: `{info['exp']}`\n"
        f"➥👁 Conexiones: `{info['conns']}`\n"
        f"➥📍 País: `{info['country']}`\n"
        f"➥🕐 Zona horaria: `{info['timezone']}`\n"
        f"{SEP}\n"
        f"       ★彡`ᴄᴏɴᴛᴇɴᴛ`彡★\n"
        f"{SEP}\n"
        f"➥📺 En Vivo: `{info['live_n']} categorías`\n"
        f"➥🎥 VOD: `{info['vod_n']} categorías`\n"
        f"➥📹 Series: `{info['series_n']} categorías`\n"
        f"{SEP}\n"
        f"➥🔗 [M3U Link]({m3u})  |  [EPG Link]({epg})\n"
        f"{SEP}\n"
        f"    ★彡`ᴄᴀᴛᴇɢᴏʀíᴀs`彡★\n"
        f"{SEP}\n"
        f"{cats_txt}\n"
        f"{SEP}\n"
        f"   ✔️ Verificado para @{tg_user}\n"
        f"   🕐 {now_str}\n"
        f"{SEP}\n"
        f"🦂 *BY LUIS R* 🦂"
    )


# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════

def uptime_str() -> str:
    delta = datetime.now() - BOT_START_TIME
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

def admin_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text("🚫 Solo admin puede usar este comando.")
            return
        return await func(update, ctx)
    wrapper.__name__ = func.__name__
    return wrapper

def main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("🔍 Cómo verificar", callback_data="cb_how"),
         InlineKeyboardButton("⚡ Estado",          callback_data="cb_status")],
        [InlineKeyboardButton("📊 Stats",           callback_data="cb_stats"),
         InlineKeyboardButton("❓ Ayuda",           callback_data="cb_help")],
        [InlineKeyboardButton("🦂 BY LUIS R 🦂",    callback_data="cb_brand")],
    ]
    if user_id == ADMIN_ID:
        kb.append([
            InlineKeyboardButton("🟢 Activar", callback_data="cb_on"),
            InlineKeyboardButton("🔴 Detener", callback_data="cb_off"),
        ])
        kb.append([InlineKeyboardButton("🛠 Panel Admin", callback_data="cb_admin")])
    return InlineKeyboardMarkup(kb)


# ═══════════════════════════════════════════════
#  PROCESADOR CENTRAL DE VERIFICACIÓN
# ═══════════════════════════════════════════════

async def do_check(update: Update, portal: str, user: str, pwd: str):
    tg_user = update.effective_user.username or update.effective_user.first_name or "usuario"
    msg = await update.message.reply_text(
        "⏳ *Verificando cuenta...*\n`Consultando servidor IPTV...`",
        parse_mode=ParseMode.MARKDOWN
    )
    info = check_iptv(portal, user, pwd)
    bot_state["checks_done"] += 1
    if info.get("ok") and info.get("status","").lower() in ("active","activa"):
        bot_state["hits_total"] += 1

    if "error" in info:
        err = info["error"]
        if err == "timeout":
            txt = (
                f"⏱ *Timeout — Sin respuesta*\n{SEP}\n"
                f"El servidor `{portal}` no respondió.\n\n"
                f"*Posibles causas:*\n"
                f"• Servidor caído o lento\n"
                f"• Puerto incorrecto\n"
                f"• Credenciales inválidas\n"
                f"• Servidor protegido (Cloudflare)\n"
                f"{SEP}\n🦂 *BY LUIS R* 🦂"
            )
        elif err == "connection":
            txt = (
                f"❌ *Sin conexión*\n{SEP}\n"
                f"No se pudo conectar a `{portal}`.\n"
                f"Verifica portal y puerto.\n"
                f"{SEP}\n🦂 *BY LUIS R* 🦂"
            )
        else:
            txt = f"❌ *Error:*\n`{err}`\n\n🦂 *BY LUIS R* 🦂"
        await msg.edit_text(txt, parse_mode=ParseMode.MARKDOWN)
        return

    card = build_card(info, tg_user)
    await msg.edit_text(card, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


# ═══════════════════════════════════════════════
#  COMANDOS
# ═══════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_state["users"].add(update.effective_user.id)
    name = update.effective_user.first_name or "usuario"
    await update.message.reply_text(
        f"🦂 *BOT IPTV ULTRA INSTINTO* 🦂\n*BY LUIS R*\n{SEP}\n"
        f"Bienvenido *{name}*! 👋\n\n"
        f"Pega directamente una URL M3U,\nun combo, o usa `/check`\n{SEP}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(update.effective_user.id)
    )


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Acepta: URL M3U completa, portal user pass, o portal|user|pass"""
    bot_state["users"].add(update.effective_user.id)
    if not ctx.args:
        await update.message.reply_text(
            "🔍 *Uso:*\n\n"
            "*URL completa:*\n"
            "`/check http://portal:port/get.php?username=X&password=Y&type=m3u_plus`\n\n"
            "*Separado:*\n"
            "`/check portal:port usuario contraseña`\n\n"
            "*Pipe:*\n"
            "`/check portal:port|usuario|contraseña`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    full = " ".join(ctx.args).strip()
    parsed = parse_m3u_url(full)
    if not parsed:
        await update.message.reply_text(
            "❌ *Formato no reconocido.*\n\n"
            "Envía la URL así:\n"
            "`http://portal:port/get.php?username=X&password=Y&type=m3u_plus`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    portal, user, pwd = parsed
    await do_check(update, portal, user, pwd)


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    icon   = "🟢" if bot_state["running"] else "🔴"
    estado = "EN LÍNEA" if bot_state["running"] else "DETENIDO"
    await update.message.reply_text(
        f"{SEP}\n⚡ *ESTADO DEL BOT*\n{SEP}\n"
        f"➥ {icon} *{estado}*\n"
        f"➥ ⏱ Uptime: `{uptime_str()}`\n"
        f"➥ 🔍 Checks: `{bot_state['checks_done']}`\n"
        f"➥ ✅ Hits: `{bot_state['hits_total']}`\n"
        f"➥ 👥 Usuarios: `{len(bot_state['users'])}`\n"
        f"{SEP}\n🦂 *BY LUIS R* 🦂",
        parse_mode=ParseMode.MARKDOWN
    )


@admin_only
async def cmd_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_state["running"] = True
    await update.message.reply_text("🟢 *Bot ACTIVADO* ✅", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_state["running"] = False
    await update.message.reply_text("🔴 *Bot DETENIDO*\nUsa /on para reactivar.", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Activar", callback_data="cb_on"),
         InlineKeyboardButton("🔴 Detener", callback_data="cb_off")],
        [InlineKeyboardButton("📊 Stats",   callback_data="cb_stats")],
        [InlineKeyboardButton("🔙 Menú",    callback_data="cb_back")],
    ])
    await update.message.reply_text(
        f"🛠 *PANEL ADMIN*\n{SEP}\n"
        f"Admin: @{ADMIN_USER}\n"
        f"⏱ Uptime: `{uptime_str()}`\n"
        f"👥 Usuarios: `{len(bot_state['users'])}`\n"
        f"🔍 Checks: `{bot_state['checks_done']}`\n"
        f"✅ Hits: `{bot_state['hits_total']}`",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )

@admin_only
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Uso: `/broadcast mensaje`", parse_mode=ParseMode.MARKDOWN)
        return
    txt  = " ".join(ctx.args)
    sent = 0
    for uid in bot_state["users"]:
        try:
            await ctx.bot.send_message(uid, f"📢 *Admin:*\n{txt}", parse_mode=ParseMode.MARKDOWN)
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Enviado a {sent} usuario(s).")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🦂 *AYUDA — COMANDOS* 🦂\n{SEP}\n"
        f"▸ /start — Menú principal\n"
        f"▸ /check `<url o portal user pass>` — Verificar\n"
        f"▸ /status — Estado del bot\n"
        f"▸ /help — Esta ayuda\n"
        f"{SEP}\n*Admin:*\n"
        f"▸ /on — Activar\n"
        f"▸ /stop — Detener\n"
        f"▸ /admin — Panel\n"
        f"▸ /broadcast `msg` — Mensaje masivo\n"
        f"{SEP}\n"
        f"*Pega directamente una URL M3U o combo:*\n"
        f"`http://portal:port/get.php?username=X&password=Y&type=m3u_plus`\n"
        f"`portal:port|usuario|contraseña`\n"
        f"{SEP}\n🦂 *BY LUIS R* 🦂",
        parse_mode=ParseMode.MARKDOWN
    )


# ═══════════════════════════════════════════════
#  MENSAJES DE TEXTO (URLs y combos sueltos)
# ═══════════════════════════════════════════════

async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_state["users"].add(update.effective_user.id)
    if not bot_state["running"]:
        await update.message.reply_text("🔴 El bot está pausado. Admin usa /on para reactivar.")
        return
    text   = (update.message.text or "").strip()
    parsed = parse_m3u_url(text)
    if parsed:
        portal, user, pwd = parsed
        await do_check(update, portal, user, pwd)
        return
    await update.message.reply_text(
        "🦂 *BY LUIS R* 🦂\n\nPega una URL M3U directamente o usa /help",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(update.effective_user.id)
    )


# ═══════════════════════════════════════════════
#  CALLBACKS INLINE
# ═══════════════════════════════════════════════

async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    uid  = update.effective_user.id
    await q.answer()
    back = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="cb_back")]]

    if data == "cb_status":
        icon   = "🟢" if bot_state["running"] else "🔴"
        estado = "EN LÍNEA" if bot_state["running"] else "DETENIDO"
        await q.edit_message_text(
            f"{SEP}\n⚡ *ESTADO*\n{SEP}\n"
            f"{icon} *{estado}*\n"
            f"⏱ Uptime: `{uptime_str()}`\n"
            f"🔍 Checks: `{bot_state['checks_done']}`\n"
            f"✅ Hits: `{bot_state['hits_total']}`\n"
            f"👥 Usuarios: `{len(bot_state['users'])}`\n"
            f"{SEP}\n🦂 *BY LUIS R* 🦂",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(back)
        )
    elif data == "cb_stats":
        fail = bot_state["checks_done"] - bot_state["hits_total"]
        await q.edit_message_text(
            f"{SEP}\n📊 *ESTADÍSTICAS*\n{SEP}\n"
            f"🔍 Verificadas: `{bot_state['checks_done']}`\n"
            f"✅ Válidas: `{bot_state['hits_total']}`\n"
            f"❌ Inválidas: `{fail}`\n"
            f"👥 Usuarios: `{len(bot_state['users'])}`\n"
            f"⏱ Uptime: `{uptime_str()}`\n"
            f"{SEP}\n🦂 *BY LUIS R* 🦂",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(back)
        )
    elif data == "cb_help":
        await q.edit_message_text(
            f"🦂 *AYUDA RÁPIDA*\n{SEP}\n"
            f"Pega una URL M3U directamente:\n"
            f"`http://portal:port/get.php?username=X&password=Y&type=m3u_plus`\n\n"
            f"O combo:\n`portal:port|usuario|contraseña`\n\n"
            f"O comando:\n`/check portal:port user pass`\n"
            f"{SEP}\n🦂 *BY LUIS R* 🦂",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(back)
        )
    elif data == "cb_how":
        await q.edit_message_text(
            f"🔍 *CÓMO VERIFICAR*\n{SEP}\n"
            f"*Método 1 — URL M3U directa:*\n"
            f"`http://portal:8080/get.php?username=user&password=pass&type=m3u_plus`\n\n"
            f"*Método 2 — Comando /check:*\n"
            f"`/check portal:8080 usuario contraseña`\n\n"
            f"*Método 3 — Combo pipe:*\n"
            f"`portal:8080|usuario|contraseña`\n"
            f"{SEP}\n🦂 *BY LUIS R* 🦂",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(back)
        )
    elif data == "cb_brand":
        await q.edit_message_text(
            f"🦂 *BY LUIS R* 🦂\n{SEP}\n"
            f"Bot IPTV *ULTRA INSTINTO*\n"
            f"Motor: `JChecker v5.7`\n"
            f"Versión: `2.0 ULTRA PRO`\n"
            f"Deploy: `Render + GitHub`\n"
            f"Uptime: `{uptime_str()}`\n{SEP}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(back)
        )
    elif data == "cb_on":
        if uid != ADMIN_ID:
            await q.answer("🚫 Solo admin.", show_alert=True); return
        bot_state["running"] = True
        await q.answer("🟢 Bot activado!", show_alert=True)
    elif data == "cb_off":
        if uid != ADMIN_ID:
            await q.answer("🚫 Solo admin.", show_alert=True); return
        bot_state["running"] = False
        await q.answer("🔴 Bot detenido.", show_alert=True)
    elif data == "cb_admin":
        if uid != ADMIN_ID:
            await q.answer("🚫 Solo admin.", show_alert=True); return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Activar", callback_data="cb_on"),
             InlineKeyboardButton("🔴 Detener", callback_data="cb_off")],
            [InlineKeyboardButton("📊 Stats",   callback_data="cb_stats")],
            [InlineKeyboardButton("🔙 Volver",  callback_data="cb_back")],
        ])
        await q.edit_message_text(
            f"🛠 *PANEL ADMIN*\n{SEP}\n"
            f"Admin: @{ADMIN_USER}\n"
            f"⏱ Uptime: `{uptime_str()}`\n"
            f"👥 Usuarios: `{len(bot_state['users'])}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )
    elif data == "cb_back":
        name = update.effective_user.first_name or "usuario"
        await q.edit_message_text(
            f"🦂 *BOT IPTV ULTRA INSTINTO* 🦂\n*BY LUIS R*\n{SEP}\n"
            f"Bienvenido *{name}*! 👋\n\nSelecciona una opción:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard(uid)
        )


# ═══════════════════════════════════════════════
#  KEEP-ALIVE (Render free tier)
# ═══════════════════════════════════════════════

def keep_alive_loop():
    if not RENDER_URL:
        return
    logger.info(f"Keep-alive → {RENDER_URL}")
    while True:
        try:
            r = requests.get(RENDER_URL, timeout=10)
            logger.info(f"Keep-alive OK: {r.status_code}")
        except Exception as e:
            logger.warning(f"Keep-alive error: {e}")
        time.sleep(840)


# ═══════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════

def main():
    if BOT_TOKEN == "TU_TOKEN_AQUI":
        print("❌ Configura BOT_TOKEN como variable de entorno en Render.")
        sys.exit(1)

    if RENDER_URL:
        threading.Thread(target=keep_alive_loop, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("check",     cmd_check))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("on",        cmd_on))
    app.add_handler(CommandHandler("stop",      cmd_stop))
    app.add_handler(CommandHandler("admin",     cmd_admin))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    logger.info("🦂 Bot ULTRA INSTINTO BY LUIS R — INICIADO ✅")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
