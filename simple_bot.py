#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              ⚡ IPTV BOT ULTRA RÁPIDO — BY LUIS R ⚡                         ║
║                    VERSIÓN TURBO — 24/7 PRO MAX                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import requests
import json
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# CONFIGURACIÓN — NO CAMBIES NADA, USA VARIABLES DE ENTORNO
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL = os.getenv("RENDER_URL", "")

# Estado del bot
bot_active = True
BOT_START_TIME = datetime.now()
STATS = {"checks": 0, "hits": 0, "users": set()}

# Timeouts reducidos para máxima velocidad
TIMEOUT = 8  # Segundos (reducido de 25 a 8)
MAX_RETRIES = 2
FAST_MODE = True

# Emojis y símbolos para diseño supremo
S = "═" * 55
ICONS = {
    "valid": "✅", "invalid": "❌", "warning": "⚠️", "active": "🟢",
    "inactive": "🔴", "tv": "📺", "movie": "🎬", "series": "📹",
    "globe": "🌐", "user": "👤", "pass": "🔑", "date": "📅",
    "time": "⏰", "connections": "👥", "location": "📍", "link": "🔗",
    "scorpion": "🦂", "fire": "⚡", "crown": "👑", "star": "⭐", "fast": "🚀"
}

# ============================================================
# FUNCIONES RÁPIDAS
# ============================================================

def get_country_flag(country_code: str) -> str:
    flags = {'US': '🇺🇸', 'MX': '🇲🇽', 'CA': '🇨🇦', 'GB': '🇬🇧', 'ES': '🇪🇸',
             'FR': '🇫🇷', 'DE': '🇩🇪', 'IT': '🇮🇹', 'BR': '🇧🇷', 'AR': '🇦🇷',
             'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'CL': '🇨🇱', 'EC': '🇪🇨'}
    return flags.get(country_code.upper(), '🌍')

def get_server_location_fast(host: str) -> str:
    """Obtiene ubicación rápida con timeout corto"""
    try:
        ip = host.split(':')[0]
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Desconocido')
                code = data.get('countryCode', '')
                return f"{country} {get_country_flag(code)}"
    except:
        pass
    return "Desconocido 🌍"

def extract_from_url(url: str):
    """Extracción rápida de datos de URLs"""
    patterns = [
        r'//([^/]+)/get\.php\?username=([^&]+)&password=([^&]+)',
        r'//([^/]+)/player_api\.php\?username=([^&]+)&password=([^&]+)',
        r'//([^/]+)/playlist/([^/]+)/([^/]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2), match.group(3)
    if '|' in url:
        parts = url.split('|')
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
    parts = url.split()
    if len(parts) == 3 and ':' in parts[0]:
        return parts[0], parts[1], parts[2]
    return None, None, None

def verify_account_fast(portal: str, user: str, pwd: str):
    """Verificación ultra rápida con timeout reducido y retry automático"""
    headers = {
        'User-Agent': 'VLC/3.0.16 LibVLC/3.0.16',  # Simula VLC real
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            url = f"http://{portal}/player_api.php?username={user}&password={pwd}"
            r = requests.get(url, timeout=TIMEOUT, verify=False, headers=headers)
            
            if r.status_code == 200:
                data = r.json()
                if data.get('user_info', {}).get('auth') == 1:
                    return {
                        'user_info': data['user_info'],
                        'server_info': data.get('server_info', {}),
                        'is_xui': bool(data.get('server_info', {}).get('xui', False))
                    }
            elif r.status_code == 401:
                # Credenciales inválidas, no reintentar
                return None
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                return None
            continue
        except:
            return None
    return None

def get_content_counts_fast(portal: str, user: str, pwd: str):
    """Obtiene conteos en paralelo para máxima velocidad"""
    live = vod = series = "0"
    
    def fetch(url):
        try:
            r = requests.get(url, timeout=TIMEOUT, verify=False)
            if r.status_code == 200:
                data = r.json()
                return len(data) if isinstance(data, list) else 0
        except:
            pass
        return 0
    
    base = f"http://{portal}/player_api.php?username={user}&password={pwd}"
    
    # Ejecutar en paralelo
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch, f"{base}&action=get_live_streams"): "live",
            executor.submit(fetch, f"{base}&action=get_vod_streams"): "vod",
            executor.submit(fetch, f"{base}&action=get_series"): "series"
        }
        for future in futures:
            count = future.result()
            if futures[future] == "live":
                live = f"{count:,}" if count > 0 else "0"
            elif futures[future] == "vod":
                vod = f"{count:,}" if count > 0 else "0"
            elif futures[future] == "series":
                series = f"{count:,}" if count > 0 else "0"
    
    return live, vod, series

def get_categories_fast(portal: str, user: str, pwd: str, limit: int = 12) -> str:
    """Obtiene categorías rápidamente"""
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_categories"
        r = requests.get(url, timeout=TIMEOUT, verify=False)
        if r.status_code == 200:
            cats = r.json()
            if isinstance(cats, list) and cats:
                result = []
                for cat in cats[:limit]:
                    name = cat.get('category_name', 'Sin nombre').replace('\\/', '/').strip()
                    if name:
                        result.append(f"  {ICONS['tv']} {name}")
                if len(cats) > limit:
                    result.append(f"  {ICONS['star']} ...y {len(cats)-limit} más")
                return '\n'.join(result)
    except:
        pass
    return ""

def format_supreme_card(portal: str, user: str, pwd: str, result: dict, live: str, vod: str, series: str, tg_user: str = "") -> str:
    """Tarjeta suprema de información"""
    ui = result.get('user_info', {})
    si = result.get('server_info', {})
    
    # Expiración
    expire = ui.get('exp_date', 'No expira')
    expire_str = "No expira"
    if expire and str(expire).isdigit() and int(expire) > 0:
        try:
            expire_str = datetime.fromtimestamp(int(expire)).strftime('%d/%m/%Y')
        except:
            expire_str = str(expire)
    
    # Creación
    created = ui.get('created_at', None)
    created_str = "No disponible"
    if created and str(created).isdigit() and int(created) > 0:
        try:
            created_str = datetime.fromtimestamp(int(created)).strftime('%d/%m/%Y')
        except:
            created_str = str(created)
    
    # Conexiones
    active = ui.get('active_cons', '0')
    max_con = ui.get('max_connections', '0')
    status = ui.get('status', 'Active')
    is_trial = "Trial" if "trial" in user.lower() else "No Trial"
    location = get_server_location_fast(portal)
    
    # Enlaces
    is_xui = result.get('is_xui', False)
    if is_xui:
        m3u_link = f"http://{portal}/playlist/{user}/{pwd}/m3u_plus"
        epg_link = f"http://{portal}/playlist/{user}/{pwd}/xmltv"
    else:
        m3u_link = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        epg_link = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    
    # Categorías
    categories = get_categories_fast(portal, user, pwd)
    
    # Construcción de la tarjeta
    card = f"""
{S}
{ICONS['scorpion']} 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 {ICONS['scorpion']}
{S}
{ICONS['valid']} 𝐂𝐔𝐄𝐍𝐓𝐀: {ICONS['active']} 𝐕Á𝐋𝐈𝐃𝐀
{ICONS['tv']} 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
{ICONS['user']} 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{ICONS['pass']} 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: {pwd}
{ICONS['date']} 𝐂𝐫𝐞𝐚𝐝𝐚: {created_str}
{ICONS['time']} 𝐄𝐱𝐩𝐢𝐫𝐚: {expire_str}
{ICONS['connections']} 𝐂𝐨𝐧𝐞𝐱𝐢𝐨𝐧𝐞𝐬: {active} / {max_con}
{ICONS['location']} 𝐔𝐛𝐢𝐜𝐚𝐜𝐢ó𝐧: {location}
{ICONS['star']} 𝐓𝐢𝐩𝐨: {is_trial}
{S}
{ICONS['fire']} 𝐂𝐎𝐍𝐓𝐄𝐍𝐈𝐃𝐎 𝐃𝐈𝐒𝐏𝐎𝐍𝐈𝐁𝐋𝐄 {ICONS['fire']}
{S}
{ICONS['tv']} 𝐄𝐧 𝐕𝐢𝐯𝐨: {live}
{ICONS['movie']} 𝐏𝐞𝐥í𝐜𝐮𝐥𝐚𝐬: {vod}
{ICONS['series']} 𝐒𝐞𝐫𝐢𝐞𝐬: {series}
{S}
{ICONS['link']} 𝐄𝐍𝐋𝐀𝐂𝐄𝐒 𝐃𝐈𝐑𝐄𝐂𝐓𝐎𝐒
{S}
{ICONS['tv']} <a href="{m3u_link}">𝐋𝐢𝐬𝐭𝐚 𝐌𝟑𝐔</a>
{ICONS['time']} <a href="{epg_link}">𝐆𝐮í𝐚 𝐄𝐏𝐆</a>
"""
    if categories:
        card += f"""
{S}
{ICONS['scorpion']} 𝐂𝐀𝐓𝐄𝐆𝐎𝐑Í𝐀𝐒 {ICONS['scorpion']}
{S}
{categories}
"""
    card += f"""
{S}
{ICONS['crown']} 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫 𝐋𝐔𝐈𝐒 𝐑 {ICONS['crown']}
{ICONS['date']} {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{S}
"""
    return card

def format_invalid_card(portal: str, user: str, tg_user: str = "") -> str:
    return f"""
{S}
{ICONS['scorpion']} 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 {ICONS['scorpion']}
{S}
{ICONS['invalid']} 𝐂𝐔𝐄𝐍𝐓𝐀: {ICONS['inactive']} 𝐈𝐍𝐕Á𝐋𝐈𝐃𝐀
{ICONS['tv']} 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
{ICONS['user']} 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{S}
{ICONS['warning']} 𝐏𝐨𝐬𝐢𝐛𝐥𝐞𝐬 𝐜𝐚𝐮𝐬𝐚𝐬:
{ICONS['warning']} • Credenciales incorrectas
{ICONS['warning']} • Servidor caído o lento
{ICONS['warning']} • Servidor protegido
{S}
{ICONS['crown']} 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫 𝐋𝐔𝐈𝐒 𝐑 {ICONS['crown']}
{ICONS['date']} {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{S}
"""

# ============================================================
# KEEP-ALIVE PARA RENDER
# ============================================================
def keep_alive_loop():
    if RENDER_URL:
        while True:
            try:
                requests.get(RENDER_URL, timeout=5)
            except:
                pass
            time.sleep(600)

# ============================================================
# COMANDOS DE TELEGRAM
# ============================================================
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(f"{ICONS['invalid']} No autorizado")
        return
    global bot_active
    bot_active = True
    STATS["users"].add(update.effective_user.id)
    await update.message.reply_text(
        f"{ICONS['fast']} *ＢＯＴ ＩＰＴＶ ＵＬＴＲＡ ＲÁＰＩＤＯ* {ICONS['fast']}\n\n"
        f"{ICONS['active']} Bot *ACTIVADO*\n"
        f"{ICONS['fast']} Modo *TURBO*\n\n"
        f"{ICONS['tv']} Envía una URL o usa /check\n"
        f"{ICONS['scorpion']} BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(f"{ICONS['invalid']} No autorizado")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(f"{ICONS['inactive']} *Bot APAGADO*\n\nUsa /start\n{ICONS['scorpion']} BY LUIS R", parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(f"{ICONS['invalid']} No autorizado")
        return
    estado = f"{ICONS['active']} ACTIVO" if bot_active else f"{ICONS['inactive']} APAGADO"
    uptime = datetime.now() - BOT_START_TIME
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    mins, secs = divmod(rem, 60)
    await update.message.reply_text(
        f"{ICONS['fast']} *ＥＳＴＡＤＯ* {ICONS['fast']}\n\n"
        f"{ICONS['tv']} Estado: {estado}\n"
        f"{ICONS['time']} Activo: {hours:02d}h {mins:02d}m {secs:02d}s\n"
        f"{ICONS['star']} Checks: {STATS['checks']}\n"
        f"{ICONS['valid']} Hits: {STATS['hits']}\n"
        f"{ICONS['users']} Usuarios: {len(STATS['users'])}\n\n"
        f"{ICONS['scorpion']} BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_active
    if not bot_active or not is_admin(update):
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            f"{ICONS['tv']} *Uso:* `/check portal:puerto usuario pass`\n"
            f"{ICONS['fast']} *Ejemplo:* `/check latinchannel.tv:8080 user pass`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    portal, user, pwd = args[0], args[1], args[2]
    msg = await update.message.reply_text(f"{ICONS['fast']} *Verificando...* {ICONS['fast']}", parse_mode=ParseMode.MARKDOWN)
    STATS["checks"] += 1
    result = verify_account_fast(portal, user, pwd)
    if result:
        STATS["hits"] += 1
        await msg.edit_text(f"{ICONS['fire']} *Obteniendo contenido...* {ICONS['fire']}", parse_mode=ParseMode.MARKDOWN)
        live, vod, series = get_content_counts_fast(portal, user, pwd)
        tg_user = update.effective_user.username or update.effective_user.first_name
        card = format_supreme_card(portal, user, pwd, result, live, vod, series, tg_user)
        await msg.edit_text(card, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        tg_user = update.effective_user.username or update.effective_user.first_name
        card = format_invalid_card(portal, user, tg_user)
        await msg.edit_text(card, parse_mode=ParseMode.MARKDOWN)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or not is_admin(update):
        return
    text = update.message.text.strip()
    portal, user, pwd = extract_from_url(text)
    if portal and user and pwd:
        context.args = [portal, user, pwd]
        await check_command(update, context)
    elif text.startswith('http'):
        await update.message.reply_text(f"{ICONS['warning']} *Formato no reconocido*\n\nUsa:\n`http://portal:8080/get.php?username=user&password=pass`", parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{ICONS['fast']} *ＣＯＭＡＮＤＯＳ* {ICONS['fast']}\n\n"
        f"{ICONS['tv']} /start - Encender\n"
        f"{ICONS['inactive']} /stop - Apagar\n"
        f"{ICONS['star']} /status - Estado\n"
        f"{ICONS['valid']} /check - Verificar\n"
        f"{ICONS['link']} /help - Ayuda\n\n"
        f"{ICONS['crown']} BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )

# ============================================================
# MAIN
# ============================================================
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        return
    if RENDER_URL:
        threading.Thread(target=keep_alive_loop, daemon=True).start()
    print(f"{ICONS['fast']} IPTV BOT ULTRA RÁPIDO - BY LUIS R")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    print(f"{ICONS['active']} Bot iniciado - Modo TURBO activado")
    app.run_polling()

if __name__ == "__main__":
    main()
