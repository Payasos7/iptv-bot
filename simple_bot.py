#!/usr/bin/env python3
import os
import re
import requests
import json
import time
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# CONFIGURACIÓN
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL = os.getenv("RENDER_URL", "")

bot_active = True
BOT_START_TIME = datetime.now()
STATS = {"checks": 0, "hits": 0, "users": set()}

# Diseño
S = "═" * 55
ICONS = {
    "valid": "✅", "invalid": "❌", "warning": "⚠️", "active": "🟢",
    "inactive": "🔴", "tv": "📺", "movie": "🎬", "series": "📹",
    "user": "👤", "pass": "🔑", "date": "📅", "time": "⏰",
    "connections": "👥", "location": "📍", "link": "🔗",
    "scorpion": "🦂", "crown": "👑"
}

# ============================================================
# FUNCIONES PRINCIPALES
# ============================================================

def extract_from_url(url: str):
    """Extrae portal, usuario y contraseña de URLs IPTV"""
    # Formato: http://portal/get.php?username=user&password=pass
    match = re.search(r'//([^/]+)/get\.php\?username=([^&]+)&password=([^&]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    # Formato: http://portal/player_api.php?username=user&password=pass
    match = re.search(r'//([^/]+)/player_api\.php\?username=([^&]+)&password=([^&]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    # Formato: portal|user|pass
    if '|' in url:
        parts = url.split('|')
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
    
    # Formato: portal user pass (separado por espacios)
    parts = url.split()
    if len(parts) == 3 and ':' in parts[0]:
        return parts[0], parts[1], parts[2]
    
    return None, None, None

def verify_account(portal: str, user: str, pwd: str):
    """Verifica cuenta IPTV"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Connection': 'keep-alive'
    }
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}"
        print(f"🔍 Verificando: {url}")
        
        r = requests.get(url, timeout=15, verify=False, headers=headers)
        print(f"📡 Respuesta: {r.status_code}")
        
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
        print("⏱️ Timeout")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def get_content_counts(portal: str, user: str, pwd: str):
    """Obtiene conteos de canales, películas y series"""
    live = vod = series = "?"
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_streams"
        r = requests.get(url, timeout=15, verify=False)
        if r.status_code == 200:
            data = r.json()
            live = str(len(data)) if isinstance(data, list) else "?"
    except:
        pass
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_vod_streams"
        r = requests.get(url, timeout=15, verify=False)
        if r.status_code == 200:
            data = r.json()
            vod = str(len(data)) if isinstance(data, list) else "?"
    except:
        pass
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_series"
        r = requests.get(url, timeout=15, verify=False)
        if r.status_code == 200:
            data = r.json()
            series = str(len(data)) if isinstance(data, list) else "?"
    except:
        pass
    
    return live, vod, series

def get_categories(portal: str, user: str, pwd: str, limit: int = 12):
    """Obtiene categorías de canales"""
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_categories"
        r = requests.get(url, timeout=15, verify=False)
        if r.status_code == 200:
            cats = r.json()
            if isinstance(cats, list):
                result = []
                for cat in cats[:limit]:
                    name = cat.get('category_name', '').replace('\\/', '/').strip()
                    if name:
                        result.append(f"  {ICONS['tv']} {name}")
                if len(cats) > limit:
                    result.append(f"  {ICONS['crown']} ...y {len(cats)-limit} más")
                return '\n'.join(result)
    except:
        pass
    return ""

def get_server_location(portal: str):
    """Obtiene ubicación del servidor"""
    try:
        ip = portal.split(':')[0]
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Desconocido')
                code = data.get('countryCode', '')
                flags = {'US': '🇺🇸', 'MX': '🇲🇽', 'ES': '🇪🇸', 'AR': '🇦🇷', 
                         'CO': '🇨🇴', 'CL': '🇨🇱', 'PE': '🇵🇪', 'VE': '🇻🇪'}
                return f"{country} {flags.get(code, '🌍')}"
    except:
        pass
    return "Desconocido 🌍"

def format_supreme_card(portal: str, user: str, pwd: str, result: dict, live: str, vod: str, series: str) -> str:
    """Formatea la tarjeta de información"""
    ui = result.get('user_info', {})
    
    # Fecha de expiración
    expire = ui.get('exp_date', 'No expira')
    expire_str = "No expira"
    if expire and str(expire).isdigit() and int(expire) > 0:
        try:
            expire_str = datetime.fromtimestamp(int(expire)).strftime('%d/%m/%Y')
        except:
            expire_str = str(expire)
    
    # Fecha de creación
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
    location = get_server_location(portal)
    
    # Enlaces
    m3u_link = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg_link = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    
    # Categorías
    categories = get_categories(portal, user, pwd)
    
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
📍 𝐔𝐛𝐢𝐜𝐚𝐜𝐢ó𝐧: {location}
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
⚠️ • Servidor protegido
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
        await update.message.reply_text("❌ No autorizado")
        return
    global bot_active
    bot_active = True
    STATS["users"].add(update.effective_user.id)
    await update.message.reply_text(
        f"🦂 *ＢＯＴ ＩＰＴＶ ＵＬＴＲＡ* 🦂\n\n"
        f"🟢 Bot *ACTIVADO*\n\n"
        f"📺 *Envía una URL completa:*\n"
        f"`http://portal:8080/get.php?username=user&password=pass`\n\n"
        f"📝 *O usa el comando:*\n"
        f"`/check portal:8080 usuario pass`\n\n"
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
    await update.message.reply_text(
        f"🦂 *ＥＳＴＡＤＯ* 🦂\n\n"
        f"📺 Estado: {estado}\n"
        f"⏰ Activo: {hours:02d}h {mins:02d}m {secs:02d}s\n"
        f"⭐ Checks: {STATS['checks']}\n"
        f"✅ Hits: {STATS['hits']}\n"
        f"👥 Usuarios: {len(STATS['users'])}\n\n"
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
            f"🔥 *Ejemplo:* `/check latinchannel.tv:8080 user pass`\n\n"
            f"📎 *O envía la URL completa:*\n"
            f"`http://portal:8080/get.php?username=user&password=pass`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    portal, user, pwd = args[0], args[1], args[2]
    msg = await update.message.reply_text(f"🦂 *Verificando cuenta...* 🦂", parse_mode=ParseMode.MARKDOWN)
    
    STATS["checks"] += 1
    result = verify_account(portal, user, pwd)
    
    if result:
        STATS["hits"] += 1
        await msg.edit_text(f"📡 *Obteniendo contenido del servidor...*", parse_mode=ParseMode.MARKDOWN)
        live, vod, series = get_content_counts(portal, user, pwd)
        card = format_supreme_card(portal, user, pwd, result, live, vod, series)
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
    else:
        await update.message.reply_text(
            f"🦂 *BY LUIS R* 🦂\n\n"
            f"📺 *Envía una URL en este formato:*\n"
            f"`http://portal:8080/get.php?username=user&password=pass`\n\n"
            f"📝 *O usa:* `/check portal:8080 usuario pass`",
            parse_mode=ParseMode.MARKDOWN
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🦂 *ＣＯＭＡＮＤＯＳ* 🦂\n\n"
        f"📺 /start - Encender bot\n"
        f"🔴 /stop - Apagar bot\n"
        f"⭐ /status - Estado del bot\n"
        f"✅ /check - Verificar cuenta\n"
        f"🦂 /help - Esta ayuda\n\n"
        f"🔥 *EJEMPLOS:*\n"
        f"`/check latinchannel.tv:8080 user pass`\n"
        f"`http://latinchannel.tv:8080/get.php?username=user&password=pass`\n\n"
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
    
    print("🦂 IPTV BOT ULTRA - BY LUIS R")
    print(f"📺 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    print("✅ Bot iniciado correctamente - Esperando mensajes...")
    app.run_polling()

if __name__ == "__main__":
    main()
