#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import logging
import requests
import threading
import time
from datetime import datetime
from urllib.parse import urlparse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# ============================================================
# CONFIGURACIÓN
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_USER = os.getenv("ADMIN_USERNAME", "luisr")
PORT = int(os.getenv("PORT", 10000))
RENDER_URL = os.getenv("RENDER_URL", "")

BOT_START_TIME = datetime.now()
bot_state = {"running": True, "checks_done": 0, "hits_total": 0, "users": set()}

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
logger = logging.getLogger("LuisBot")

# ============================================================
# INTENTAR IMPORTAR JCHECKER
# ============================================================
JCHECKER_AVAILABLE = False
try:
    # Intentar importar las funciones necesarias de JChecker
    sys.path.insert(0, os.getcwd())
    from jchecker_6 import c_datos, get_or_fetch_server_content, proxy_manager
    from cloudflare_bypass import is_cloudflare_protected, check_account_with_cloudflare_bypass
    JCHECKER_AVAILABLE = True
    logger.info("✅ JChecker y Cloudflare Bypass cargados correctamente")
except ImportError as e:
    logger.warning(f"⚠️ JChecker no disponible: {e}")

# ============================================================
# FUNCIONES DE VERIFICACIÓN
# ============================================================
STARS = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

def extract_from_url(url: str):
    """Extrae portal, usuario y contraseña de cualquier formato de URL IPTV"""
    # Formato: http://portal/get.php?username=user&password=pass
    match = re.search(r'//([^/]+)/get\.php\?username=([^&]+)&password=([^&]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    # Formato: http://portal/player_api.php?username=user&password=pass
    match = re.search(r'//([^/]+)/player_api\.php\?username=([^&]+)&password=([^&]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    # Formato: http://portal/playlist/user/pass/m3u_plus
    match = re.search(r'//([^/]+)/playlist/([^/]+)/([^/]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    # Formato: portal:port|user|pass
    if '|' in url:
        parts = url.split('|')
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
    
    return None, None, None

def verify_with_jchecker(portal: str, user: str, pwd: str):
    """Verifica usando JChecker si está disponible"""
    if not JCHECKER_AVAILABLE:
        return None
    
    try:
        base_url = f"http://{portal}"
        
        # Usar Cloudflare bypass si es necesario
        if is_cloudflare_protected(portal):
            logger.info(f"🌙 Usando Cloudflare bypass para {portal}")
            result = check_account_with_cloudflare_bypass(base_url, user, pwd)
            if result and result.get('status') == 'hit':
                return result
        
        # Verificación normal
        url = f"{base_url}/player_api.php?username={user}&password={pwd}"
        r = requests.get(url, timeout=30, verify=False)
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        if data.get('user_info', {}).get('auth') == 1:
            return {
                'user_info': data['user_info'],
                'is_xui': bool(data.get('server_info', {}).get('xui', False))
            }
    except Exception as e:
        logger.error(f"Error en JChecker: {e}")
    
    return None

def verify_direct(portal: str, user: str, pwd: str):
    """Verificación directa con requests"""
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}"
        r = requests.get(url, timeout=30, verify=False)
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        if data.get('user_info', {}).get('auth') == 1:
            return data
    except Exception as e:
        logger.error(f"Error en verificación directa: {e}")
    
    return None

def get_content_counts(portal: str, user: str, pwd: str):
    """Obtiene conteos de canales, películas y series"""
    live = vod = series = "?"
    
    try:
        # Si JChecker está disponible, usar c_datos
        if JCHECKER_AVAILABLE:
            base_url = f"http://{portal}"
            live, vod, series = c_datos(base_url, user, pwd)
            return live, vod, series
    except:
        pass
    
    # Fallback: contar desde las URLs
    try:
        # Canales en vivo
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_streams"
        r = requests.get(url, timeout=30, verify=False)
        if r.status_code == 200:
            data = r.json()
            live = str(len(data)) if isinstance(data, list) else "?"
    except:
        pass
    
    try:
        # Películas
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_vod_streams"
        r = requests.get(url, timeout=30, verify=False)
        if r.status_code == 200:
            data = r.json()
            vod = str(len(data)) if isinstance(data, list) else "?"
    except:
        pass
    
    try:
        # Series
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_series"
        r = requests.get(url, timeout=30, verify=False)
        if r.status_code == 200:
            data = r.json()
            series = str(len(data)) if isinstance(data, list) else "?"
    except:
        pass
    
    return live, vod, series

def get_server_location(host: str):
    """Obtiene ubicación del servidor"""
    try:
        ip = host.split(':')[0]
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Desconocido')
                code = data.get('countryCode', '')
                flags = {'US': '🇺🇸', 'MX': '🇲🇽', 'ES': '🇪🇸', 'AR': '🇦🇷', 'CO': '🇨🇴', 'CL': '🇨🇱', 'PE': '🇵🇪'}
                flag = flags.get(code, '🌍')
                return f"{country} {flag}"
    except:
        pass
    return "Desconocido 🌍"

def format_account_card(portal: str, user: str, pwd: str, info: dict, live: str, vod: str, series: str, tg_user: str = ""):
    """Formatea la tarjeta de información"""
    user_info = info.get('user_info', info)
    
    expire = user_info.get('exp_date', 'No expira')
    if expire and str(expire).isdigit() and int(expire) > 0:
        expire = datetime.fromtimestamp(int(expire)).strftime('%d/%m/%Y')
    
    active = user_info.get('active_cons', '0')
    max_con = user_info.get('max_connections', '0')
    status = user_info.get('status', 'Active')
    is_trial = "Trial" if "trial" in user.lower() else "No Trial"
    country = get_server_location(portal)
    
    m3u_link = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg_link = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    
    card = f"""
{STARS}
     🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{STARS}
➥ 🟢 CUENTA VÁLIDA
➥🆙 Estado: ✅ {status}
➥🧪 {is_trial}
➥🌐 Portal: {portal}
➥👤 Usuario: {user}
➥🔑 Contraseña: {pwd}
➥⏲ Vence: {expire}
➥👁 Conexiones: {active} / {max_con}
➥📍 País: {country}
{STARS}
       🦂 𝐂𝐎𝐍𝐓𝐄𝐍𝐈𝐃𝐎 🦂
{STARS}
➥📺 En Vivo: {live}
➥🎥 VOD: {vod}
➥📹 Series: {series}
{STARS}
➥🔗 <a href="{m3u_link}">M3U Link</a>   |   <a href="{epg_link}">EPG Link</a>
{STARS}
   ✔️ Verificado por @{tg_user}
   🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
{STARS}
🦂 𝐁𝐘 𝐋𝐔𝐈𝐒 𝐑 🦂
"""
    return card

# ============================================================
# COMANDOS DE TELEGRAM
# ============================================================
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_state["users"].add(update.effective_user.id)
    user = update.effective_user
    await update.message.reply_text(
        f"🦂 *BOT IPTV ULTRA* 🦂\n\n"
        f"Bienvenido *{user.first_name}*!\n\n"
        f"📎 *Envía una URL M3U o Xtream:*\n"
        f"`http://portal:8080/get.php?username=user&password=pass`\n\n"
        f"📝 *O usa el comando:*\n"
        f"`/check portal:8080 usuario contraseña`\n\n"
        f"🦂 *BY LUIS R* 🦂",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not bot_state["running"]:
        await update.message.reply_text("🔴 Bot apagado. Usa /start")
        return
    
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text(
            "📝 *Uso:* `/check portal:puerto usuario contraseña`\n"
            "📎 *Ejemplo:* `/check latinchannel.tv:8080 usuario pass`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    portal = args[0]
    user = args[1]
    pwd = args[2]
    
    msg = await update.message.reply_text("🦂 *Verificando cuenta...* 🦂", parse_mode=ParseMode.MARKDOWN)
    
    # Verificar
    result = verify_with_jchecker(portal, user, pwd)
    if not result:
        result = verify_direct(portal, user, pwd)
    
    if result:
        bot_state["hits_total"] += 1
        bot_state["checks_done"] += 1
        
        # Obtener conteos
        live, vod, series = get_content_counts(portal, user, pwd)
        
        tg_user = update.effective_user.username or update.effective_user.first_name
        card = format_account_card(portal, user, pwd, result, live, vod, series, tg_user)
        await msg.edit_text(card, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        bot_state["checks_done"] += 1
        await msg.edit_text(
            f"❌ *CUENTA INVÁLIDA*\n\n"
            f"Portal: `{portal}`\n"
            f"Usuario: `{user}`\n\n"
            f"🦂 *BY LUIS R* 🦂",
            parse_mode=ParseMode.MARKDOWN
        )

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    estado = "🟢 ACTIVO" if bot_state["running"] else "🔴 APAGADO"
    await update.message.reply_text(
        f"📊 *ESTADO DEL BOT*\n\n"
        f"▸ Estado: {estado}\n"
        f"▸ Checks: `{bot_state['checks_done']}`\n"
        f"▸ Hits: `{bot_state['hits_total']}`\n"
        f"▸ Usuarios: `{len(bot_state['users'])}`\n\n"
        f"🦂 BY LUIS R 🦂",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🚫 No autorizado")
        return
    bot_state["running"] = False
    await update.message.reply_text("🔴 Bot detenido. Usa /on para reactivar.")

async def cmd_on(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("🚫 No autorizado")
        return
    bot_state["running"] = True
    await update.message.reply_text("🟢 Bot reactivado.")

async def handle_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not bot_state["running"]:
        return
    
    text = update.message.text.strip()
    portal, user, pwd = extract_from_url(text)
    
    if portal and user and pwd:
        ctx.args = [portal, user, pwd]
        await cmd_check(update, ctx)
    else:
        await update.message.reply_text(
            f"🦂 *BY LUIS R* 🦂\n\n"
            f"Envía una URL válida:\n"
            f"`http://portal/get.php?username=user&password=pass`\n\n"
            f"O usa `/check portal usuario contraseña`",
            parse_mode=ParseMode.MARKDOWN
        )

# ============================================================
# MAIN
# ============================================================
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("on", cmd_on))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    logger.info("🦂 Bot IPTV ULTRA - BY LUIS R iniciado")
    app.run_polling()

if __name__ == "__main__":
    main()
