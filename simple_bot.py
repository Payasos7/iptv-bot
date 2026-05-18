#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         🦂 IPTV BOT ULTRA SUPREMO — BY LUIS R 🦂                            ║
║              CON JCHECKER + CLOUDFLARE BYPASS                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import json
import time
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# IMPORTAR JCHECKER Y CLOUDFLARE BYPASS
# ============================================================
sys.path.insert(0, os.getcwd())

JCHECKER_AVAILABLE = False
CLOUDFLARE_AVAILABLE = False

try:
    from jchecker_6 import c_datos, get_or_fetch_server_content, proxy_manager
    JCHECKER_AVAILABLE = True
    print("✅ JChecker v5.7 cargado correctamente")
except ImportError as e:
    print(f"⚠️ JChecker no disponible: {e}")

try:
    from cloudflare_bypass import (
        is_cloudflare_protected, 
        check_account_with_cloudflare_bypass,
        get_content_with_cloudflare_bypass,
        get_categories_with_cloudflare_bypass
    )
    CLOUDFLARE_AVAILABLE = True
    print("✅ Cloudflare Bypass cargado correctamente")
except ImportError as e:
    print(f"⚠️ Cloudflare Bypass no disponible: {e}")

# ============================================================
# CONFIGURACIÓN
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL = os.getenv("RENDER_URL", "")

bot_active = True
BOT_START_TIME = datetime.now()
STATS = {"checks": 0, "hits": 0, "users": set()}

# Emojis
S = "═" * 55
ICONS = {
    "valid": "✅", "invalid": "❌", "warning": "⚠️", "active": "🟢",
    "inactive": "🔴", "tv": "📺", "movie": "🎬", "series": "📹",
    "globe": "🌐", "user": "👤", "pass": "🔑", "date": "📅",
    "time": "⏰", "connections": "👥", "location": "📍", "link": "🔗",
    "scorpion": "🦂", "fire": "🔥", "crown": "👑", "star": "⭐", "fast": "⚡"
}

# ============================================================
# FUNCIONES DE EXTRACCIÓN
# ============================================================
def extract_from_url(url: str):
    """Extrae portal, usuario y contraseña de URLs IPTV"""
    patterns = [
        r'//([^/]+)/get\.php\?username=([^&]+)&password=([^&]+)',
        r'//([^/]+)/player_api\.php\?username=([^&]+)&password=([^&]+)',
        r'//([^/]+)/playlist/([^/]+)/([^/]+)',
        r'//([^/]+)/c/.*?/([^/]+)/([^/]+)',
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

# ============================================================
# VERIFICACIÓN CON JCHECKER
# ============================================================
def verify_account_supreme(portal: str, user: str, pwd: str):
    """Verifica usando JChecker o Cloudflare Bypass si están disponibles"""
    base_url = f"http://{portal}"
    
    # 1. Intentar con Cloudflare Bypass si está disponible
    if CLOUDFLARE_AVAILABLE and is_cloudflare_protected(portal):
        print(f"🌙 Usando Cloudflare bypass para {portal}")
        try:
            result = check_account_with_cloudflare_bypass(base_url, user, pwd)
            if result and result.get('status') == 'hit':
                return {
                    'user_info': result.get('user_info', {}),
                    'server_info': {},
                    'is_xui': False,
                    'live': result.get('live_count', '?'),
                    'vod': result.get('vod_count', '?'),
                    'series': result.get('series_count', '?'),
                    'categories': result.get('categories', '')
                }
        except Exception as e:
            print(f"Error en Cloudflare bypass: {e}")
    
    # 2. Intentar con JChecker
    if JCHECKER_AVAILABLE:
        try:
            # Usar c_datos para obtener conteos
            live, vod, series = c_datos(base_url, user, pwd)
            
            # Verificar credenciales
            url = f"{base_url}/player_api.php?username={user}&password={pwd}"
            import requests
            r = requests.get(url, timeout=15, verify=False)
            if r.status_code == 200:
                data = r.json()
                if data.get('user_info', {}).get('auth') == 1:
                    return {
                        'user_info': data['user_info'],
                        'server_info': data.get('server_info', {}),
                        'is_xui': bool(data.get('server_info', {}).get('xui', False)),
                        'live': live,
                        'vod': vod,
                        'series': series,
                        'categories': ''
                    }
        except Exception as e:
            print(f"Error en JChecker: {e}")
    
    # 3. Verificación directa como fallback
    try:
        import requests
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}"
        r = requests.get(url, timeout=10, verify=False)
        if r.status_code == 200:
            data = r.json()
            if data.get('user_info', {}).get('auth') == 1:
                return {
                    'user_info': data['user_info'],
                    'server_info': data.get('server_info', {}),
                    'is_xui': False,
                    'live': '?',
                    'vod': '?',
                    'series': '?',
                    'categories': ''
                }
    except:
        pass
    
    return None

def get_categories_supreme(portal: str, user: str, pwd: str):
    """Obtiene categorías usando Cloudflare Bypass si está disponible"""
    base_url = f"http://{portal}"
    
    if CLOUDFLARE_AVAILABLE and is_cloudflare_protected(portal):
        try:
            categories = get_categories_with_cloudflare_bypass(base_url, user, pwd)
            if categories:
                return categories
        except:
            pass
    
    try:
        import requests
        url = f"{base_url}/player_api.php?username={user}&password={pwd}&action=get_live_categories"
        r = requests.get(url, timeout=10, verify=False)
        if r.status_code == 200:
            cats = r.json()
            if isinstance(cats, list):
                result = []
                for cat in cats[:15]:
                    name = cat.get('category_name', '').replace('\\/', '/').strip()
                    if name:
                        result.append(f"  {ICONS['tv']} {name}")
                if len(cats) > 15:
                    result.append(f"  {ICONS['star']} ...y {len(cats)-15} más")
                return '\n'.join(result)
    except:
        pass
    return ""

# ============================================================
# FORMATEO DE TARJETA
# ============================================================
def format_supreme_card(portal: str, user: str, pwd: str, result: dict, tg_user: str = "") -> str:
    ui = result.get('user_info', {})
    si = result.get('server_info', {})
    
    # Fechas
    expire = ui.get('exp_date', 'No expira')
    expire_str = "No expira"
    if expire and str(expire).isdigit() and int(expire) > 0:
        try:
            expire_str = datetime.fromtimestamp(int(expire)).strftime('%d/%m/%Y')
        except:
            expire_str = str(expire)
    
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
    
    # País (simplificado)
    country = "Desconocido 🌍"
    try:
        import socket
        import requests
        ip = portal.split(':')[0]
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Desconocido')
                code = data.get('countryCode', '')
                flags = {'US': '🇺🇸', 'MX': '🇲🇽', 'ES': '🇪🇸', 'AR': '🇦🇷', 'CO': '🇨🇴', 'CL': '🇨🇱', 'PE': '🇵🇪'}
                country = f"{country} {flags.get(code, '🌍')}"
    except:
        pass
    
    # Conteos
    live = result.get('live', '?')
    vod = result.get('vod', '?')
    series = result.get('series', '?')
    
    # Enlaces
    is_xui = result.get('is_xui', False)
    if is_xui:
        m3u_link = f"http://{portal}/playlist/{user}/{pwd}/m3u_plus"
        epg_link = f"http://{portal}/playlist/{user}/{pwd}/xmltv"
    else:
        m3u_link = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        epg_link = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    
    # Categorías
    categories = get_categories_supreme(portal, user, pwd)
    
    # Construcción
    card = f"""
{S}
🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{S}
✅ 𝐂𝐔𝐄𝐍𝐓𝐀: 🟢 𝐕Á𝐋𝐈𝐃𝐀
📺 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
🔑 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: {pwd}
📅 𝐂𝐫𝐞𝐚𝐝𝐚: {created_str}
⏰ 𝐄𝐱𝐩𝐢𝐫𝐚: {expire_str}
👥 𝐂𝐨𝐧𝐞𝐱𝐢𝐨𝐧𝐞𝐬: {active} / {max_con}
📍 𝐔𝐛𝐢𝐜𝐚𝐜𝐢ó𝐧: {country}
⭐ 𝐓𝐢𝐩𝐨: {is_trial}
{S}
🔥 𝐂𝐎𝐍𝐓𝐄𝐍𝐈𝐃𝐎 𝐃𝐈𝐒𝐏𝐎𝐍𝐈𝐁𝐋𝐄 🔥
{S}
📺 𝐄𝐧 𝐕𝐢𝐯𝐨: {live}
🎬 𝐏𝐞𝐥í𝐜𝐮𝐥𝐚𝐬: {vod}
📹 𝐒𝐞𝐫𝐢𝐞𝐬: {series}
{S}
🔗 𝐄𝐍𝐋𝐀𝐂𝐄𝐒 𝐃𝐈𝐑𝐄𝐂𝐓𝐎𝐒
{S}
📺 <a href="{m3u_link}">𝐋𝐢𝐬𝐭𝐚 𝐌𝟑𝐔</a>
⏰ <a href="{epg_link}">𝐆𝐮í𝐚 𝐄𝐏𝐆</a>
"""
    if categories:
        card += f"""
{S}
🦂 𝐂𝐀𝐓𝐄𝐆𝐎𝐑Í𝐀𝐒 🦂
{S}
{categories}
"""
    card += f"""
{S}
👑 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫 𝐋𝐔𝐈𝐒 𝐑 👑
📅 {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{S}
"""
    return card

def format_invalid_card(portal: str, user: str) -> str:
    return f"""
{S}
🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{S}
❌ 𝐂𝐔𝐄𝐍𝐓𝐀: 🔴 𝐈𝐍𝐕Á𝐋𝐈𝐃𝐀
📺 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{S}
⚠️ 𝐏𝐨𝐬𝐢𝐛𝐥𝐞𝐬 𝐜𝐚𝐮𝐬𝐚𝐬:
⚠️ • Credenciales incorrectas
⚠️ • Servidor caído o lento
⚠️ • Servidor protegido (Cloudflare)
{S}
👑 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫 𝐋𝐔𝐈𝐒 𝐑 👑
📅 {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{S}
"""

# ============================================================
# KEEP-ALIVE
# ============================================================
def keep_alive_loop():
    if RENDER_URL:
        while True:
            try:
                import requests
                requests.get(RENDER_URL, timeout=5)
            except:
                pass
            time.sleep(600)

# ============================================================
# COMANDOS
# ============================================================
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado")
        return
    global bot_active
    bot_active = True
    STATS["users"].add(update.effective_user.id)
    await update.message.reply_text(
        f"🦂 *ＢＯＴ ＩＰＴＶ ＵＬＴＲＡ* 🦂\n\n"
        f"🟢 Bot *ACTIVADO*\n"
        f"🔥 JChecker integrado\n"
        f"🌙 Cloudflare Bypass activado\n\n"
        f"📺 Envía una URL o usa /check\n"
        f"🦂 BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text("🔴 *Bot APAGADO*\n\nUsa /start\n🦂 BY LUIS R", parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado")
        return
    estado = "🟢 ACTIVO" if bot_active else "🔴 APAGADO"
    uptime = datetime.now() - BOT_START_TIME
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    mins, secs = divmod(rem, 60)
    jc = "✅" if JCHECKER_AVAILABLE else "❌"
    cf = "✅" if CLOUDFLARE_AVAILABLE else "❌"
    await update.message.reply_text(
        f"🦂 *ＥＳＴＡＤＯ* 🦂\n\n"
        f"📺 Estado: {estado}\n"
        f"⏰ Activo: {hours:02d}h {mins:02d}m {secs:02d}s\n"
        f"⭐ Checks: {STATS['checks']}\n"
        f"✅ Hits: {STATS['hits']}\n"
        f"👥 Usuarios: {len(STATS['users'])}\n"
        f"📦 JChecker: {jc}\n"
        f"🌙 Cloudflare: {cf}\n\n"
        f"🦂 BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_active
    if not bot_active or not is_admin(update):
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            f"📺 *Uso:* `/check portal:puerto usuario pass`\n"
            f"🔥 *Ejemplo:* `/check latinchannel.tv:8080 user pass`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    portal, user, pwd = args[0], args[1], args[2]
    msg = await update.message.reply_text(f"🦂 *Verificando cuenta...* 🦂", parse_mode=ParseMode.MARKDOWN)
    STATS["checks"] += 1
    result = verify_account_supreme(portal, user, pwd)
    if result:
        STATS["hits"] += 1
        tg_user = update.effective_user.username or update.effective_user.first_name
        card = format_supreme_card(portal, user, pwd, result, tg_user)
        await msg.edit_text(card, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        card = format_invalid_card(portal, user)
        await msg.edit_text(card, parse_mode=ParseMode.MARKDOWN)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or not is_admin(update):
        return
    text = update.message.text.strip()
    portal, user, pwd = extract_from_url(text)
    if portal and user and pwd:
        context.args = [portal, user, pwd]
        await check_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🦂 *ＣＯＭＡＮＤＯＳ* 🦂\n\n"
        f"📺 /start - Encender bot\n"
        f"🔴 /stop - Apagar bot\n"
        f"⭐ /status - Estado del bot\n"
        f"✅ /check - Verificar cuenta\n"
        f"🦂 /help - Esta ayuda\n\n"
        f"🔥 *URLs soportadas:*\n"
        f"• http://portal/get.php?username=user&password=pass\n"
        f"• http://portal/player_api.php?username=user&password=pass\n\n"
        f"🦂 BY LUIS R",
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
    print("🦂 IPTV BOT ULTRA SUPREMO - BY LUIS R")
    print(f"📦 JChecker disponible: {JCHECKER_AVAILABLE}")
    print(f"🌙 Cloudflare disponible: {CLOUDFLARE_AVAILABLE}")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    print("✅ Bot iniciado correctamente")
    app.run_polling()

if __name__ == "__main__":
    main()
