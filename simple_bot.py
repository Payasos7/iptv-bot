#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           🦂 IPTV BOT ULTRA MEGA DIOS DE DIOSES — BY LUIS R 🦂               ║
║                      VERSIÓN SUPREMA - 24/7 PRO MAX                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import requests
import json
import socket
import time
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# CONFIGURACIÓN SUPREMA
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL = os.getenv("RENDER_URL", "")

# Estado del bot
bot_active = True
BOT_START_TIME = datetime.now()
STATS = {"checks": 0, "hits": 0, "users": set()}

# Emojis y símbolos
STARS = "═══════════════════════════════════════════════════════════════"
ICONS = {
    "valid": "✅", "invalid": "❌", "warning": "⚠️", "active": "🟢",
    "inactive": "🔴", "tv": "📺", "movie": "🎬", "series": "📹",
    "globe": "🌐", "user": "👤", "pass": "🔑", "date": "📅",
    "time": "⏰", "connections": "👥", "location": "📍", "link": "🔗",
    "scorpion": "🦂", "fire": "🔥", "crown": "👑", "star": "⭐"
}

# ============================================================
# FUNCIONES SUPREMAS
# ============================================================

def get_country_flag(country_code: str) -> str:
    """Bandera por código de país"""
    flags = {
        'US': '🇺🇸', 'MX': '🇲🇽', 'CA': '🇨🇦', 'GB': '🇬🇧', 'ES': '🇪🇸',
        'FR': '🇫🇷', 'DE': '🇩🇪', 'IT': '🇮🇹', 'BR': '🇧🇷', 'AR': '🇦🇷',
        'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'CL': '🇨🇱', 'EC': '🇪🇨',
        'UY': '🇺🇾', 'PY': '🇵🇾', 'BO': '🇧🇴', 'CR': '🇨🇷', 'PA': '🇵🇦',
        'DO': '🇩🇴', 'PR': '🇵🇷', 'CU': '🇨🇺', 'JP': '🇯🇵', 'CN': '🇨🇳',
        'KR': '🇰🇷', 'IN': '🇮🇳', 'RU': '🇷🇺', 'AU': '🇦🇺', 'NZ': '🇳🇿'
    }
    return flags.get(country_code.upper(), '🌍')

def get_server_location(host: str) -> str:
    """Obtiene ubicación del servidor con IP-API"""
    try:
        ip = host.split(':')[0]
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Desconocido')
                code = data.get('countryCode', '')
                flag = get_country_flag(code)
                city = data.get('city', '')
                if city:
                    return f"{city}, {country} {flag}"
                return f"{country} {flag}"
    except:
        pass
    return "Desconocido 🌍"

def extract_from_url(url: str):
    """Extractor universal de datos de cualquier URL IPTV"""
    # Formato Xtream Codes
    patterns = [
        r'//([^/]+)/get\.php\?username=([^&]+)&password=([^&]+)',
        r'//([^/]+)/player_api\.php\?username=([^&]+)&password=([^&]+)',
        r'//([^/]+)/c/.*?/([^/]+)/([^/]+)',
        r'//([^/]+)/playlist/([^/]+)/([^/]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2), match.group(3)
    
    # Formato con barras verticales: portal|user|pass
    if '|' in url:
        parts = url.split('|')
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
    
    # Formato con espacios: portal user pass
    parts = url.split()
    if len(parts) == 3 and ':' in parts[0]:
        return parts[0], parts[1], parts[2]
    
    return None, None, None

def verify_account(portal: str, user: str, pwd: str):
    """Verificación ultra rápida con múltiples intentos"""
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Connection': 'keep-alive'
        }
        
        r = requests.get(url, timeout=25, verify=False, headers=headers)
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        user_info = data.get('user_info', {})
        
        if user_info.get('auth') == 1:
            return {
                'user_info': user_info,
                'server_info': data.get('server_info', {}),
                'is_xui': bool(data.get('server_info', {}).get('xui', False))
            }
        return None
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_content_counts(portal: str, user: str, pwd: str):
    """Obtiene conteos de contenido con manejo de errores"""
    live = vod = series = "0"
    
    endpoints = [
        ('live', f"/player_api.php?username={user}&password={pwd}&action=get_live_streams"),
        ('vod', f"/player_api.php?username={user}&password={pwd}&action=get_vod_streams"),
        ('series', f"/player_api.php?username={user}&password={pwd}&action=get_series")
    ]
    
    for name, endpoint in endpoints:
        try:
            url = f"http://{portal}{endpoint}"
            r = requests.get(url, timeout=20, verify=False)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    count = len(data)
                    if name == 'live':
                        live = f"{count:,}"
                    elif name == 'vod':
                        vod = f"{count:,}"
                    elif name == 'series':
                        series = f"{count:,}"
        except:
            pass
    
    return live, vod, series

def get_categories(portal: str, user: str, pwd: str, limit: int = 15) -> str:
    """Obtiene y formatea categorías"""
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_categories"
        r = requests.get(url, timeout=15, verify=False)
        
        if r.status_code == 200:
            cats = r.json()
            if isinstance(cats, list) and cats:
                result = []
                for cat in cats[:limit]:
                    name = cat.get('category_name', 'Sin nombre')
                    # Limpiar nombre
                    name = name.replace('\\/', '/').strip()
                    if name:
                        result.append(f"  {ICONS['tv']} {name}")
                
                if len(cats) > limit:
                    result.append(f"  {ICONS['star']} ...y {len(cats) - limit} categorías más")
                
                return '\n'.join(result) if result else ""
    except:
        pass
    return ""

def format_supreme_card(portal: str, user: str, pwd: str, result: dict, live: str, vod: str, series: str, tg_user: str = "") -> str:
    """Formatea la tarjeta suprema de información"""
    user_info = result.get('user_info', {})
    server_info = result.get('server_info', {})
    
    # Fecha de expiración
    expire = user_info.get('exp_date', 'No expira')
    expire_str = "No expira"
    if expire and str(expire).isdigit() and int(expire) > 0:
        try:
            expire_str = datetime.fromtimestamp(int(expire)).strftime('%d/%m/%Y')
        except:
            expire_str = str(expire)
    
    # Fecha de creación
    created = user_info.get('created_at', None)
    created_str = "No disponible"
    if created and str(created).isdigit() and int(created) > 0:
        try:
            created_str = datetime.fromtimestamp(int(created)).strftime('%d/%m/%Y')
        except:
            created_str = str(created)
    
    # Conexiones
    active_cons = user_info.get('active_cons', '0')
    max_cons = user_info.get('max_connections', '0')
    
    # Estado y Trial
    status = user_info.get('status', 'Active')
    is_trial = "Trial" if "trial" in user.lower() else "No Trial"
    
    # Ubicación
    location = get_server_location(portal)
    
    # Enlaces
    protocol = 'https' if server_info.get('https', False) else 'http'
    is_xui = result.get('is_xui', False)
    
    if is_xui:
        m3u_link = f"{protocol}://{portal}/playlist/{user}/{pwd}/m3u_plus"
        epg_link = f"{protocol}://{portal}/playlist/{user}/{pwd}/xmltv"
    else:
        m3u_link = f"{protocol}://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        epg_link = f"{protocol}://{portal}/xmltv.php?username={user}&password={pwd}"
    
    # Construcción de la tarjeta suprema
    card = f"""
{STARS}
{ICONS['scorpion']} 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 {ICONS['scorpion']}
{STARS}
{ICONS['valid']} 𝐂𝐔𝐄𝐍𝐓𝐀: {ICONS['active']} 𝐕Á𝐋𝐈𝐃𝐀
{ICONS['tv']} 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
{ICONS['user']} 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{ICONS['pass']} 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: {pwd}
{ICONS['date']} 𝐂𝐫𝐞𝐚𝐝𝐚: {created_str}
{ICONS['time']} 𝐄𝐱𝐩𝐢𝐫𝐚: {expire_str}
{ICONS['connections']} 𝐂𝐨𝐧𝐞𝐱𝐢𝐨𝐧𝐞𝐬: {active_cons} / {max_cons}
{ICONS['location']} 𝐔𝐛𝐢𝐜𝐚𝐜𝐢ó𝐧: {location}
{ICONS['star']} 𝐓𝐢𝐩𝐨: {is_trial}
{STARS}
{ICONS['fire']} 𝐂𝐎𝐍𝐓𝐄𝐍𝐈𝐃𝐎 𝐃𝐈𝐒𝐏𝐎𝐍𝐈𝐁𝐋𝐄 {ICONS['fire']}
{STARS}
{ICONS['tv']} 𝐄𝐧 𝐕𝐢𝐯𝐨: {live}
{ICONS['movie']} 𝐏𝐞𝐥í𝐜𝐮𝐥𝐚𝐬: {vod}
{ICONS['series']} 𝐒𝐞𝐫𝐢𝐞𝐬: {series}
{STARS}
{ICONS['link']} 𝐄𝐍𝐋𝐀𝐂𝐄𝐒 𝐃𝐈𝐑𝐄𝐂𝐓𝐎𝐒
{STARS}
{ICONS['tv']} <a href="{m3u_link}">𝐋𝐢𝐬𝐭𝐚 𝐌𝟑𝐔</a>
{ICONS['time']} <a href="{epg_link}">𝐆𝐮í𝐚 𝐄𝐏𝐆</a>
"""
    
    # Categorías (si se obtuvieron)
    categories = get_categories(portal, user, pwd)
    if categories:
        card += f"""
{STARS}
{ICONS['scorpion']} 𝐂𝐀𝐓𝐄𝐆𝐎𝐑Í𝐀𝐒 𝐃𝐄 𝐂𝐀𝐍𝐀𝐋𝐄𝐒 {ICONS['scorpion']}
{STARS}
{categories}
"""
    
    card += f"""
{STARS}
{ICONS['crown']} 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫 𝐋𝐔𝐈𝐒 𝐑 {ICONS['crown']}
{ICONS['date']} {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{STARS}
"""
    return card

def format_invalid_card(portal: str, user: str, tg_user: str = "") -> str:
    """Tarjeta para cuenta inválida"""
    return f"""
{STARS}
{ICONS['scorpion']} 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 {ICONS['scorpion']}
{STARS}
{ICONS['invalid']} 𝐂𝐔𝐄𝐍𝐓𝐀: {ICONS['inactive']} 𝐈𝐍𝐕Á𝐋𝐈𝐃𝐀
{ICONS['tv']} 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
{ICONS['user']} 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{STARS}
{ICONS['warning']} 𝐏𝐨𝐬𝐢𝐛𝐥𝐞𝐬 𝐜𝐚𝐮𝐬𝐚𝐬:
{ICONS['warning']} • Credenciales incorrectas
{ICONS['warning']} • Servidor caído o lento
{ICONS['warning']} • Servidor protegido (Cloudflare)
{STARS}
{ICONS['crown']} 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫 𝐋𝐔𝐈𝐒 𝐑 {ICONS['crown']}
{ICONS['date']} {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{STARS}
"""

# ============================================================
# KEEP-ALIVE PARA RENDER
# ============================================================
def keep_alive_loop():
    """Mantiene el bot vivo en Render Free Tier"""
    if not RENDER_URL:
        return
    while True:
        try:
            requests.get(RENDER_URL, timeout=10)
        except:
            pass
        time.sleep(840)  # 14 minutos

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
    
    keyboard = [
        [InlineKeyboardButton(f"{ICONS['tv']} Verificar URL", callback_data="check_url")],
        [InlineKeyboardButton(f"{ICONS['star']} Estado del Bot", callback_data="status"),
         InlineKeyboardButton(f"{ICONS['link']} Enlaces", callback_data="links")],
        [InlineKeyboardButton(f"{ICONS['scorpion']} BY LUIS R", callback_data="about")]
    ]
    
    await update.message.reply_text(
        f"{ICONS['scorpion']} *ＢＯＴ ＩＰＴＶ ＵＬＴＲＡ* {ICONS['scorpion']}\n\n"
        f"{ICONS['active']} Bot *ACTIVADO*\n"
        f"{ICONS['crown']} Versión *SUPREMA v3.0*\n\n"
        f"{ICONS['tv']} Envía una URL o usa /help",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(f"{ICONS['invalid']} No autorizado")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(f"{ICONS['inactive']} *Bot APAGADO*\n\nUsa /start para encenderlo\n{ICONS['scorpion']} BY LUIS R", parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text(f"{ICONS['invalid']} No autorizado")
        return
    
    estado = f"{ICONS['active']} ACTIVO" if bot_active else f"{ICONS['inactive']} APAGADO"
    uptime = datetime.now() - BOT_START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    await update.message.reply_text(
        f"{ICONS['scorpion']} *ＥＳＴＡＤＯ ＤＥＬ ＢＯＴ* {ICONS['scorpion']}\n\n"
        f"{ICONS['tv']} Estado: {estado}\n"
        f"{ICONS['time']} Activo: {hours:02d}h {minutes:02d}m {seconds:02d}s\n"
        f"{ICONS['star']} Verificaciones: {STATS['checks']}\n"
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
            f"{ICONS['tv']} *Uso:* `/check portal:puerto usuario contraseña`\n"
            f"{ICONS['star']} *Ejemplo:* `/check latinchannel.tv:8080 usuario pass`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    portal, user, pwd = args[0], args[1], args[2]
    msg = await update.message.reply_text(f"{ICONS['scorpion']} *Verificando cuenta...* {ICONS['scorpion']}", parse_mode=ParseMode.MARKDOWN)
    
    STATS["checks"] += 1
    
    result = verify_account(portal, user, pwd)
    
    if result:
        STATS["hits"] += 1
        await msg.edit_text(f"{ICONS['fire']} *Obteniendo contenido...* {ICONS['fire']}", parse_mode=ParseMode.MARKDOWN)
        live, vod, series = get_content_counts(portal, user, pwd)
        
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
        await update.message.reply_text(
            f"{ICONS['warning']} *Formato no reconocido*\n\n"
            f"{ICONS['tv']} Usa:\n"
            f"`http://portal:8080/get.php?username=user&password=pass`\n\n"
            f"O el comando:\n"
            f"`/check portal:8080 usuario pass`",
            parse_mode=ParseMode.MARKDOWN
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{ICONS['scorpion']} *ＣＯＭＡＮＤＯＳ* {ICONS['scorpion']}\n\n"
        f"{ICONS['tv']} /start - Encender bot\n"
        f"{ICONS['inactive']} /stop - Apagar bot\n"
        f"{ICONS['star']} /status - Estado del bot\n"
        f"{ICONS['valid']} /check - Verificar cuenta\n"
        f"{ICONS['link']} /help - Esta ayuda\n\n"
        f"{ICONS['fire']} *ENLACES SOPORTADOS*\n"
        f"• Xtream Codes (player_api.php)\n"
        f"• M3U / M3U8\n"
        f"• Playlist\n\n"
        f"{ICONS['crown']} BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    if not is_admin(update):
        await query.edit_message_text(f"{ICONS['invalid']} No autorizado")
        return
    
    if data == "status":
        estado = f"{ICONS['active']} ACTIVO" if bot_active else f"{ICONS['inactive']} APAGADO"
        uptime = datetime.now() - BOT_START_TIME
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        await query.edit_message_text(
            f"{ICONS['scorpion']} *ＥＳＴＡＤＯ* {ICONS['scorpion']}\n\n"
            f"{ICONS['tv']} Estado: {estado}\n"
            f"{ICONS['time']} Activo: {hours:02d}h {minutes:02d}m {seconds:02d}s\n"
            f"{ICONS['star']} Checks: {STATS['checks']}\n"
            f"{ICONS['valid']} Hits: {STATS['hits']}\n"
            f"{ICONS['scorpion']} BY LUIS R",
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "check_url":
        await query.edit_message_text(
            f"{ICONS['tv']} *VERIFICAR URL*\n\n"
            f"Envía una URL como:\n"
            f"`http://portal:8080/get.php?username=user&password=pass`\n\n"
            f"O usa el comando:\n"
            f"`/check portal:8080 usuario pass`\n\n"
            f"{ICONS['scorpion']} BY LUIS R",
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "links":
        await query.edit_message_text(
            f"{ICONS['link']} *ENLACES DIRECTOS*\n\n"
            f"*M3U Playlist:*\n"
            f"`http://portal/get.php?username=user&password=pass&type=m3u_plus`\n\n"
            f"*EPG Guide:*\n"
            f"`http://portal/xmltv.php?username=user&password=pass`\n\n"
            f"{ICONS['scorpion']} BY LUIS R",
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "about":
        await query.edit_message_text(
            f"{ICONS['scorpion']} *ＢＹ ＬＵＩＳ Ｒ* {ICONS['scorpion']}\n\n"
            f"{ICONS['crown']} Bot IPTV ULTRA SUPREMO\n"
            f"{ICONS['fire']} Verificador 24/7\n"
            f"{ICONS['star']} Versión 3.0 PRO MAX\n\n"
            f"{ICONS['tv']} Características:\n"
            f"• URLs Xtream / M3U\n"
            f"• Categorías de canales\n"
            f"• Conteo de contenido\n"
            f"• Enlaces directos\n"
            f"• Diseño supremo\n\n"
            f"{ICONS['scorpion']} BY LUIS R",
            parse_mode=ParseMode.MARKDOWN
        )

# ============================================================
# MAIN
# ============================================================
def main():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no configurado")
        print("   Agrega BOT_TOKEN en Variables de entorno en Railway")
        return
    
    # Iniciar keep-alive
    if RENDER_URL:
        t = threading.Thread(target=keep_alive_loop, daemon=True)
        t.start()
    
    print(f"{ICONS['scorpion']} IPTV BOT ULTRA SUPREMO - BY LUIS R")
    print(f"{ICONS['tv']} Bot Token: {BOT_TOKEN[:10]}...")
    print(f"{ICONS['user']} Admin ID: {ADMIN_ID}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Callbacks y mensajes
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    print(f"{ICONS['active']} Bot iniciado correctamente - Esperando mensajes...")
    app.run_polling()

if __name__ == "__main__":
    main()
