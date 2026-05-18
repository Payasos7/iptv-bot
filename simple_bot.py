#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║        🦂 IPTV BOT ULTRA INSTINTO — BY LUIS R 🦂            ║
║          Telegram Bot 24/7 — Render/GitHub Ready             ║
║              Integrado con JChecker v5.7                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import logging
import threading
import subprocess
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path

# ──────────────────────────────────────────────
#  DEPENDENCIAS
# ──────────────────────────────────────────────
try:
    from telegram import (
        Update, InlineKeyboardButton, InlineKeyboardMarkup,
        BotCommand
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
except ImportError:
    print("❌ Instala: pip install requests")
    sys.exit(1)

# ──────────────────────────────────────────────
#  CONFIGURACIÓN — EDITA ESTOS VALORES
# ──────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN", "TU_TOKEN_AQUI")
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))        # Tu Telegram user ID
ADMIN_USER  = os.getenv("ADMIN_USERNAME", "luisr")   # Sin @
PORT        = int(os.getenv("PORT", 10000))

# Render keep-alive URL (pon tu URL de Render aquí)
RENDER_URL  = os.getenv("RENDER_URL", "")

# ──────────────────────────────────────────────
#  ESTADO GLOBAL DEL BOT
# ──────────────────────────────────────────────
BOT_START_TIME = datetime.now()
bot_state = {
    "running":        True,
    "jchecker_proc":  None,   # subprocess de jchecker si lo lanzamos
    "checks_done":    0,
    "hits_total":     0,
    "users":          set(),
}

# ──────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("🦂LuisRBot")

# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
STARS = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

def uptime_str() -> str:
    delta = datetime.now() - BOT_START_TIME
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def is_admin(update: Update) -> bool:
    uid = update.effective_user.id
    return uid == ADMIN_ID

def admin_only(func):
    """Decorador: solo admin puede usar el comando."""
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update):
            await update.message.reply_text(
                "🚫 *Acceso denegado.* Solo el administrador puede usar este comando.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, ctx)
    wrapper.__name__ = func.__name__
    return wrapper

def build_info_card(
    portal: str,
    user: str,
    password: str,
    expiry: str,
    country: str,
    connections: str,
    live: str = "?",
    vod: str = "?",
    series: str = "?",
    categories: list = None,
    created: str = None,
    trial: str = "No Trial",
    status: str = "ACTIVA",
    telegram_user: str = "",
) -> str:
    """Genera la tarjeta de información ULTRA PRO en formato Telegram."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    created_str = created or datetime.now().strftime("%d/%m/%Y")
    status_icon = "🟢" if status.upper() in ("ACTIVA", "ACTIVE", "VÁLIDA") else "🔴"

    m3u = f"https://{portal}/get.php?username={user}&password={password}&type=m3u_plus"
    epg = f"https://{portal}/xmltv.php?username={user}&password={password}"

    cats_text = ""
    if categories:
        for c in categories[:12]:
            cats_text += f"  ➠ {c}\n"
        if len(categories) > 12:
            cats_text += f"  ➕ ...y {len(categories)-12} categorías más\n"
    else:
        cats_text = "  ➠ Sin datos de categorías\n"

    card = (
        f"{STARS}\n"
        f"     🦂`ɪɴꜰᴏ ᴅᴇ ʟᴀ ᴄᴜᴇɴᴛᴀ` 🦂BY LUIS R🦂\n"
        f"{STARS}\n"
        f"➥ {status_icon} CUENTA *{status.upper()}*\n"
        f"➥🆙 Estado: ✅ *{status.upper()}*\n"
        f"➥🧪 Trial: `{trial}`\n"
        f"➥🌐 Portal: `{portal}`\n"
        f"➥👤 Usuario: `{user}`\n"
        f"➥🔑 Contraseña: `{password}`\n"
        f"➥📅 Creada: `{created_str}`\n"
        f"➥⏲ Vence: `{expiry}`\n"
        f"➥👁 Conexiones: `{connections}`\n"
        f"➥📍 País: `{country}`\n"
        f"{STARS}\n"
        f"       🦂`ᴄᴏɴᴛᴇɴɪᴅᴏ`🦂\n"
        f"{STARS}\n"
        f"➥📺 En Vivo: `{live}`\n"
        f"➥🎥 VOD: `{vod}`\n"
        f"➥📹 Series: `{series}`\n"
        f"{STARS}\n"
        f"➥🔗 [M3U]({m3u})   |   [EPG]({epg})\n"
        f"{STARS}\n"
        f"    🦂`ᴄᴀᴛᴇɢᴏʀíᴀs`🦂\n"
        f"{STARS}\n"
        f"{cats_text}"
        f"{STARS}\n"
        f"   ✔️ Verificado para @{telegram_user}\n"
        f"   🕐 {now_str}\n"
        f"{STARS}\n"
        f"🦂 *BY LUIS R* 🦂"
    )
    return card

# ──────────────────────────────────────────────
#  KEEP-ALIVE (para Render free tier)
# ──────────────────────────────────────────────
def keep_alive_loop():
    """Hace ping cada 14 min para que Render no duerma el servicio."""
    if not RENDER_URL:
        return
    logger.info(f"Keep-alive activado → {RENDER_URL}")
    while True:
        try:
            r = requests.get(RENDER_URL, timeout=10)
            logger.info(f"Keep-alive ping: {r.status_code}")
        except Exception as e:
            logger.warning(f"Keep-alive error: {e}")
        time.sleep(840)   # 14 minutos

# ──────────────────────────────────────────────
#  COMANDOS PRINCIPALES
# ──────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_state["users"].add(update.effective_user.id)
    user = update.effective_user
    kb = [
        [InlineKeyboardButton("📋 Info Cuenta",    callback_data="menu_info"),
         InlineKeyboardButton("🔍 Chequear URL",   callback_data="menu_check")],
        [InlineKeyboardButton("⚡ Estado del Bot", callback_data="menu_status"),
         InlineKeyboardButton("📂 Categorías",     callback_data="menu_cats")],
        [InlineKeyboardButton("🔗 Links M3U/EPG",  callback_data="menu_links"),
         InlineKeyboardButton("📊 Estadísticas",   callback_data="menu_stats")],
        [InlineKeyboardButton("🦂 BY LUIS R 🦂",   callback_data="menu_brand")],
    ]
    if user.id == ADMIN_ID:
        kb.append([
            InlineKeyboardButton("🟢 Iniciar Bot",  callback_data="admin_start"),
            InlineKeyboardButton("🔴 Detener Bot",  callback_data="admin_stop"),
        ])
        kb.append([
            InlineKeyboardButton("🛠 Panel Admin",  callback_data="admin_panel"),
        ])
    markup = InlineKeyboardMarkup(kb)
    txt = (
        f"🦂 *BOT IPTV ULTRA INSTINTO* 🦂\n"
        f"*BY LUIS R*\n"
        f"{STARS}\n"
        f"Bienvenido, *{user.first_name}*! 👋\n\n"
        f"Selecciona una opción del menú:"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)


async def cmd_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Muestra tarjeta de info con argumentos: /info portal usuario pass vence pais conex"""
    args = ctx.args
    if len(args) < 6:
        await update.message.reply_text(
            "📋 *Uso:*\n"
            "`/info portal usuario contraseña vencimiento país conexiones`\n\n"
            "*Ejemplo:*\n"
            "`/info tv.ejemplo.com:8080 miuser mipass 31/12/2026 Mexico 1/3`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    portal, user, pwd, expiry, country, conns = args[0], args[1], args[2], args[3], args[4], args[5]
    tg_user = update.effective_user.username or update.effective_user.first_name
    card = build_info_card(
        portal=portal, user=user, password=pwd,
        expiry=expiry, country=country, connections=conns,
        telegram_user=tg_user
    )
    await update.message.reply_text(card, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Chequea una URL IPTV: /check portal:port usuario contraseña"""
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text(
            "🔍 *Uso:*\n`/check portal:port usuario contraseña`\n\n"
            "*Ejemplo:*\n`/check tv.ejemplo.com:8080 miuser mipass`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    portal, user, pwd = args[0], args[1], args[2]
    msg = await update.message.reply_text("🔄 *Verificando cuenta...*", parse_mode=ParseMode.MARKDOWN)

    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}"
        resp = requests.get(url, timeout=10, verify=False)
        data = resp.json()

        ui = data.get("user_info", {})
        si = data.get("server_info", {})

        status  = ui.get("status", "unknown")
        exp_ts  = ui.get("exp_date")
        conns   = f"{ui.get('active_cons','?')} / {ui.get('max_connections','?')}"
        trial   = "Sí" if str(ui.get('is_trial','0')) == '1' else "No"

        exp_str = datetime.fromtimestamp(int(exp_ts)).strftime("%d/%m/%Y %H:%M") if exp_ts else "N/A"

        # Contar canales / vod / series
        try:
            cat_url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_categories"
            cats_r  = requests.get(cat_url, timeout=8, verify=False).json()
            live_cats = len(cats_r) if isinstance(cats_r, list) else 0
        except:
            live_cats = 0

        try:
            vod_url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_vod_categories"
            vod_r   = requests.get(vod_url, timeout=8, verify=False).json()
            vod_cats = len(vod_r) if isinstance(vod_r, list) else 0
        except:
            vod_cats = 0

        try:
            ser_url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_series_categories"
            ser_r   = requests.get(ser_url, timeout=8, verify=False).json()
            ser_cats = len(ser_r) if isinstance(ser_r, list) else 0
        except:
            ser_cats = 0

        bot_state["checks_done"] += 1
        if status == "Active":
            bot_state["hits_total"] += 1

        tg_user = update.effective_user.username or update.effective_user.first_name
        card = build_info_card(
            portal=portal, user=user, password=pwd,
            expiry=exp_str, country=si.get("country", "N/A"),
            connections=conns, live=str(live_cats),
            vod=str(vod_cats), series=str(ser_cats),
            trial=trial, status=status,
            telegram_user=tg_user
        )
        await msg.edit_text(card, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    except requests.exceptions.Timeout:
        await msg.edit_text("⏱ *Timeout:* El servidor no respondió a tiempo.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ *Error al verificar:*\n`{str(e)}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    running_icon = "🟢" if bot_state["running"] else "🔴"
    running_txt  = "EN LÍNEA" if bot_state["running"] else "DETENIDO"
    txt = (
        f"{STARS}\n"
        f"⚡ *ESTADO DEL BOT* ⚡\n"
        f"{STARS}\n"
        f"➥ {running_icon} Estado: *{running_txt}*\n"
        f"➥ ⏱ Uptime: `{uptime_str()}`\n"
        f"➥ 🔍 Checks realizados: `{bot_state['checks_done']}`\n"
        f"➥ ✅ Hits encontrados: `{bot_state['hits_total']}`\n"
        f"➥ 👥 Usuarios: `{len(bot_state['users'])}`\n"
        f"➥ 📅 Inicio: `{BOT_START_TIME.strftime('%d/%m/%Y %H:%M:%S')}`\n"
        f"{STARS}\n"
        f"🦂 *BY LUIS R* 🦂"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_state["running"] = False
    await update.message.reply_text(
        "🔴 *Bot marcado como DETENIDO.*\n"
        "El proceso sigue activo en Render.\n"
        "Usa /on para reactivar.",
        parse_mode=ParseMode.MARKDOWN
    )
    logger.warning("Bot detenido por admin.")


@admin_only
async def cmd_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_state["running"] = True
    await update.message.reply_text(
        "🟢 *Bot reactivado y EN LÍNEA.*\n"
        f"⏱ Uptime: `{uptime_str()}`",
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info("Bot reactivado por admin.")


@admin_only
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Envía un mensaje a todos los usuarios. /broadcast texto"""
    if not ctx.args:
        await update.message.reply_text("Uso: /broadcast <mensaje>")
        return
    msg_text = " ".join(ctx.args)
    count = 0
    for uid in bot_state["users"]:
        try:
            await ctx.bot.send_message(uid, f"📢 *Mensaje de Admin:*\n{msg_text}", parse_mode=ParseMode.MARKDOWN)
            count += 1
        except:
            pass
    await update.message.reply_text(f"✅ Mensaje enviado a {count} usuario(s).")


@admin_only
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🟢 Activar",      callback_data="admin_start"),
         InlineKeyboardButton("🔴 Detener",      callback_data="admin_stop")],
        [InlineKeyboardButton("📊 Stats",         callback_data="admin_stats"),
         InlineKeyboardButton("🧹 Limpiar logs",  callback_data="admin_clearlogs")],
        [InlineKeyboardButton("📢 Broadcast",     callback_data="admin_broadcast"),
         InlineKeyboardButton("⚙️ Config",         callback_data="admin_config")],
        [InlineKeyboardButton("🔙 Menú",          callback_data="back_main")],
    ]
    await update.message.reply_text(
        f"🛠 *PANEL ADMINISTRADOR*\n{STARS}\n"
        f"🦂 Admin: @{ADMIN_USER}\n"
        f"⏱ Uptime: `{uptime_str()}`\n"
        f"👥 Usuarios: `{len(bot_state['users'])}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = (
        f"🦂 *COMANDOS DISPONIBLES* 🦂\n"
        f"{STARS}\n"
        f"▸ /start — Menú principal\n"
        f"▸ /info portal user pass vence pais conex — Tarjeta de info\n"
        f"▸ /check portal user pass — Verificar cuenta en vivo\n"
        f"▸ /status — Estado del bot\n"
        f"▸ /help — Esta ayuda\n"
        f"{STARS}\n"
        f"*Solo Admin:*\n"
        f"▸ /on — Activar bot\n"
        f"▸ /stop — Detener bot\n"
        f"▸ /admin — Panel admin\n"
        f"▸ /broadcast texto — Mensaje masivo\n"
        f"{STARS}\n"
        f"🦂 *BY LUIS R* 🦂"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)


# ──────────────────────────────────────────────
#  CALLBACKS (botones inline)
# ──────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "menu_status":
        running_icon = "🟢" if bot_state["running"] else "🔴"
        txt = (
            f"⚡ *ESTADO DEL BOT*\n{STARS}\n"
            f"{running_icon} *{'EN LÍNEA' if bot_state['running'] else 'DETENIDO'}*\n"
            f"⏱ Uptime: `{uptime_str()}`\n"
            f"🔍 Checks: `{bot_state['checks_done']}`\n"
            f"✅ Hits: `{bot_state['hits_total']}`\n"
            f"👥 Usuarios: `{len(bot_state['users'])}`\n"
            f"{STARS}\n🦂 BY LUIS R 🦂"
        )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="back_main")]]))

    elif data == "menu_info":
        await q.edit_message_text(
            "📋 *¿Cómo ver info de una cuenta?*\n\n"
            "Usa el comando:\n"
            "`/info portal:puerto usuario contraseña vencimiento país conexiones`\n\n"
            "Ejemplo:\n"
            "`/info tv.ejemplo.com:8080 user123 pass456 31/12/2026 México 1/3`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="back_main")]]))

    elif data == "menu_check":
        await q.edit_message_text(
            "🔍 *Verificar cuenta en vivo:*\n\n"
            "`/check portal:puerto usuario contraseña`\n\n"
            "El bot consultará el servidor y te mostrará:\n"
            "✅ Estado, vencimiento, conexiones\n"
            "📺 Canales en vivo, VOD, Series\n"
            "🔗 Links M3U y EPG listos para copiar",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="back_main")]]))

    elif data == "menu_links":
        await q.edit_message_text(
            "🔗 *CÓMO GENERAR TUS LINKS*\n\n"
            "*M3U Plus:*\n"
            "`http://PORTAL/get.php?username=USER&password=PASS&type=m3u_plus`\n\n"
            "*EPG:*\n"
            "`http://PORTAL/xmltv.php?username=USER&password=PASS`\n\n"
            "Usa `/check` para generarlos automáticamente 🚀",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="back_main")]]))

    elif data == "menu_stats":
        await q.edit_message_text(
            f"📊 *ESTADÍSTICAS*\n{STARS}\n"
            f"🔍 Cuentas verificadas: `{bot_state['checks_done']}`\n"
            f"✅ Hits encontrados: `{bot_state['hits_total']}`\n"
            f"❌ Inválidas: `{bot_state['checks_done'] - bot_state['hits_total']}`\n"
            f"👥 Usuarios totales: `{len(bot_state['users'])}`\n"
            f"⏱ Tiempo activo: `{uptime_str()}`\n"
            f"{STARS}\n🦂 BY LUIS R 🦂",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="back_main")]]))

    elif data == "menu_cats":
        cats = [
            "🎬 CINE [101]", "🌍 MUNDO Y CULTURA [28]",
            "⚽ LATINO DEPORTES [77]", "🎭 ENTRETENIMIENTO [23]",
            "🧒 INFANTILES [20]", "🏠 EL GRAN HERMANO [7]",
            "🎪 EVENTOS ESPECIALES & DISNEY+ [401]", "🏈 NFL [8]",
            "🎞 CINEMA PREMIUM [15]", "🇺🇾 URUGUAY [41]",
            "🇲🇽 MÉXICO [45]", "🇨🇱 CHILE [43]",
            "🇪🇨 ECUADOR [23]", "🇦🇷 ARGENTINA [49]",
            "🇨🇴 COLOMBIA [21]", "🇵🇪 PERÚ [18]",
            "🇻🇪 VENEZUELA [22]", "🇺🇸 USA [38]",
            "🇪🇸 ESPAÑA [31]", "🇩🇴 REP. DOMINICANA [14]",
        ]
        cat_text = "\n".join(f"  ➠ {c}" for c in cats)
        await q.edit_message_text(
            f"📂 *CATEGORÍAS DISPONIBLES*\n{STARS}\n{cat_text}\n"
            f"  ➕ ...y más disponibles\n{STARS}\n🦂 BY LUIS R 🦂",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="back_main")]]))

    elif data == "menu_brand":
        await q.edit_message_text(
            "🦂 *BY LUIS R* 🦂\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Bot IPTV *ULTRA INSTINTO*\n"
            "Verificador + Info + 24/7\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Versión: `2.0 ULTRA PRO`\n"
            f"Motor: `JChecker v5.7`\n"
            f"Deploy: `Render + GitHub`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver", callback_data="back_main")]]))

    elif data == "admin_start":
        if not is_admin(update):
            await q.answer("🚫 Solo admin.", show_alert=True)
            return
        bot_state["running"] = True
        await q.answer("🟢 Bot activado!", show_alert=True)
        logger.info("Bot activado por admin vía inline.")

    elif data == "admin_stop":
        if not is_admin(update):
            await q.answer("🚫 Solo admin.", show_alert=True)
            return
        bot_state["running"] = False
        await q.answer("🔴 Bot detenido.", show_alert=True)
        logger.warning("Bot detenido por admin vía inline.")

    elif data == "admin_panel":
        if not is_admin(update):
            await q.answer("🚫 Solo admin.", show_alert=True)
            return
        kb = [
            [InlineKeyboardButton("🟢 Activar",  callback_data="admin_start"),
             InlineKeyboardButton("🔴 Detener",  callback_data="admin_stop")],
            [InlineKeyboardButton("📊 Stats",    callback_data="menu_stats")],
            [InlineKeyboardButton("🔙 Volver",   callback_data="back_main")],
        ]
        await q.edit_message_text(
            f"🛠 *PANEL ADMIN*\n{STARS}\n"
            f"🦂 Admin: @{ADMIN_USER}\n"
            f"⏱ Uptime: `{uptime_str()}`\n"
            f"👥 Usuarios: `{len(bot_state['users'])}`\n"
            f"🔍 Checks: `{bot_state['checks_done']}`\n"
            f"✅ Hits: `{bot_state['hits_total']}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb))

    elif data == "back_main":
        user  = update.effective_user
        kb = [
            [InlineKeyboardButton("📋 Info Cuenta",    callback_data="menu_info"),
             InlineKeyboardButton("🔍 Chequear URL",   callback_data="menu_check")],
            [InlineKeyboardButton("⚡ Estado del Bot", callback_data="menu_status"),
             InlineKeyboardButton("📂 Categorías",     callback_data="menu_cats")],
            [InlineKeyboardButton("🔗 Links M3U/EPG",  callback_data="menu_links"),
             InlineKeyboardButton("📊 Estadísticas",   callback_data="menu_stats")],
            [InlineKeyboardButton("🦂 BY LUIS R 🦂",   callback_data="menu_brand")],
        ]
        if user.id == ADMIN_ID:
            kb.append([
                InlineKeyboardButton("🟢 Activar Bot",  callback_data="admin_start"),
                InlineKeyboardButton("🔴 Detener Bot",  callback_data="admin_stop"),
            ])
            kb.append([InlineKeyboardButton("🛠 Panel Admin", callback_data="admin_panel")])
        await q.edit_message_text(
            f"🦂 *BOT IPTV ULTRA INSTINTO* 🦂\n*BY LUIS R*\n{STARS}\nSelecciona una opción:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb))


# ──────────────────────────────────────────────
#  MENSAJE GENÉRICO (acepta combos pegados)
# ──────────────────────────────────────────────
async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Detecta si pegan una línea tipo portal|user|pass y la verifica."""
    if not bot_state["running"]:
        return
    text = update.message.text or ""
    # Detectar formato combo: portal:port|user|pass  o  portal:port user pass
    parts = None
    if "|" in text:
        parts = text.strip().split("|")
    elif text.count(" ") == 2:
        parts = text.strip().split()

    if parts and len(parts) == 3:
        portal, user, pwd = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if "." in portal and len(user) > 2 and len(pwd) > 2:
            ctx.args = [portal, user, pwd]
            await cmd_check(update, ctx)
            return

    await update.message.reply_text(
        "🦂 Hola! Usa /help para ver todos los comandos.\n"
        "También puedes pegar un combo así:\n"
        "`portal:port|usuario|contraseña`",
        parse_mode=ParseMode.MARKDOWN
    )


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    if BOT_TOKEN == "TU_TOKEN_AQUI":
        print("❌ ERROR: Configura BOT_TOKEN en las variables de entorno.")
        print("   Render → Environment → Add Variable → BOT_TOKEN=tu_token")
        sys.exit(1)

    # Keep-alive thread
    if RENDER_URL:
        t = threading.Thread(target=keep_alive_loop, daemon=True)
        t.start()

    # Build app
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("info",      cmd_info))
    app.add_handler(CommandHandler("check",     cmd_check))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("stop",      cmd_stop))
    app.add_handler(CommandHandler("on",        cmd_on))
    app.add_handler(CommandHandler("admin",     cmd_admin))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("help",      cmd_help))

    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Generic messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    logger.info("🦂 Bot ULTRA INSTINTO BY LUIS R iniciado ✅")
    logger.info(f"   Admin ID : {ADMIN_ID}")
    logger.info(f"   Render   : {RENDER_URL or 'No configurado'}")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
