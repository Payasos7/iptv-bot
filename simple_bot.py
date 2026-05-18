#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              🦂 IPTV BOT ULTIMA GENERACIÓN — BY LUIS R 🦂                    ║
║                    CON LÓGICA PERFECTA DE VERIFICACIÓN                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import requests
import json
import time
import threading
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# CONFIGURACIÓN
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL = os.getenv("RENDER_URL", "")

bot_active = True
BOT_START_TIME = datetime.now()
STATS = {"checks": 0, "hits": 0, "retries": 0, "fails": 0, "users": set()}

# Diseño
S = "═" * 55
ICONS = {
    "valid": "✅", "invalid": "❌", "warning": "⚠️", "active": "🟢",
    "inactive": "🔴", "tv": "📺", "movie": "🎬", "series": "📹",
    "user": "👤", "pass": "🔑", "date": "📅", "time": "⏰",
    "connections": "👥", "location": "📍", "link": "🔗",
    "scorpion": "🦂", "crown": "👑", "fire": "🔥", "star": "⭐", "retry": "🔄"
}

# ============================================================
# EXTRACCIÓN DE URLS
# ============================================================

def extract_from_url(url: str):
    """Extrae portal, usuario y contraseña de cualquier URL IPTV"""
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
# VERIFICACIÓN CON LÓGICA PERFECTA
# ============================================================

def verify_account_smart(portal: str, user: str, pwd: str):
    """
    Verifica cuenta IPTV con lógica correcta:
    - Status Active + auth=1 → HIT
    - auth=0 → FAIL
    - Sin respuesta → RETRY
    - JSON inválido → RETRY
    """
    headers = {
        'User-Agent': 'VLC/3.0.16 LibVLC/3.0.16',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}"
        print(f"🔍 Verificando: {url}")
        
        r = requests.get(url, timeout=15, verify=False, headers=headers)
        print(f"📡 Status Code: {r.status_code}")
        
        # Si no hay respuesta exitosa del servidor → RETRY
        if r.status_code != 200:
            print(f"⚠️ Servidor respondió con {r.status_code} → RETRY")
            return "RETRY", None
        
        # Intentar parsear JSON
        try:
            data = r.json()
        except json.JSONDecodeError:
            print("❌ Respuesta no es JSON válido → RETRY")
            return "RETRY", None
        
        # Verificar estructura de datos
        if 'user_info' not in data:
            print("⚠️ Respuesta sin 'user_info' → RETRY")
            return "RETRY", None
        
        user_info = data.get('user_info', {})
        
        # Verificar auth
        auth = user_info.get('auth')
        if auth is None:
            print("⚠️ Campo 'auth' no encontrado → RETRY")
            return "RETRY", None
        
        try:
            auth_int = int(auth)
        except (ValueError, TypeError):
            print("⚠️ 'auth' no es numérico → RETRY")
            return "RETRY", None
        
        # auth = 0 → FAIL (credenciales incorrectas)
        if auth_int == 0:
            print("❌ auth=0 → FAIL (credenciales incorrectas)")
            return "FAIL", None
        
        # auth = 1 → verificar status
        if auth_int == 1:
            status = user_info.get('status', '')
            
            # status = "Active" → HIT (cuenta válida)
            if status == "Active":
                print("✅ auth=1, status=Active → HIT")
                return "HIT", {
                    'user_info': user_info,
                    'server_info': data.get('server_info', {}),
                    'is_xui': bool(data.get('server_info', {}).get('xui', False))
                }
            else:
                # auth=1 pero status no es Active → Custom (cuenta existe pero no activa)
                print(f"⚠️ auth=1 pero status='{status}' → CUSTOM")
                return "CUSTOM", {
                    'user_info': user_info,
                    'server_info': data.get('server_info', {}),
                    'is_xui': bool(data.get('server_info', {}).get('xui', False))
                }
        
        # Cualquier otro valor de auth → RETRY
        print(f"⚠️ auth={auth_int} no reconocido → RETRY")
        return "RETRY", None
        
    except requests.exceptions.Timeout:
        print("⏱️ Timeout → RETRY")
        return "RETRY", None
    except requests.exceptions.ConnectionError:
        print("🔌 Error de conexión → RETRY")
        return "RETRY", None
    except Exception as e:
        print(f"❌ Error inesperado: {e} → RETRY")
        return "RETRY", None

def get_content_counts(portal: str, user: str, pwd: str):
    """Obtiene conteos de canales, películas y series"""
    live = vod = series = "0"
    
    headers = {
        'User-Agent': 'VLC/3.0.16 LibVLC/3.0.16',
        'Accept': '*/*'
    }
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_streams"
        r = requests.get(url, timeout=15, verify=False, headers=headers)
        if r.status_code == 200:
            data = r.json()
            live = str(len(data)) if isinstance(data, list) else "0"
    except:
        pass
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_vod_streams"
        r = requests.get(url, timeout=15, verify=False, headers=headers)
        if r.status_code == 200:
            data = r.json()
            vod = str(len(data)) if isinstance(data, list) else "0"
    except:
        pass
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_series"
        r = requests.get(url, timeout=15, verify=False, headers=headers)
        if r.status_code == 200:
            data = r.json()
            series = str(len(data)) if isinstance(data, list) else "0"
    except:
        pass
    
    return live, vod, series

def get_categories(portal: str, user: str, pwd: str, limit: int = 12):
    """Obtiene categorías de canales"""
    headers = {
        'User-Agent': 'VLC/3.0.16 LibVLC/3.0.16',
        'Accept': '*/*'
    }
    
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_categories"
        r = requests.get(url, timeout=15, verify=False, headers=headers)
        if r.status_code == 200:
            cats = r.json()
            if isinstance(cats, list):
                result = []
                for cat in cats[:limit]:
                    name = cat.get('category_name', '').replace('\\/', '/').strip()
                    if name:
                        result.append(f"  {ICONS['tv']} {name}")
                if len(cats) > limit:
                    result.append(f"  {ICONS['star']} ...y {len(cats)-limit} más")
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

# ============================================================
# FORMATEO DE TARJETAS
# ============================================================

def format_hit_card(portal: str, user: str, pwd: str, result: dict, live: str, vod: str, series: str) -> str:
    """Tarjeta para cuentas HIT (válidas)"""
    ui = result.get('user_info', {})
    
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
    
    active = ui.get('active_cons', '0')
    max_con = ui.get('max_connections', '0')
    status = ui.get('status', 'Active')
    is_trial = "Trial" if "trial" in user.lower() else "No Trial"
    location = get_server_location(portal)
    
    m3u_link = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg_link = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    categories = get_categories(portal, user, pwd)
    
    card = f"""
{S}
🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{S}
✅ 𝐂𝐔𝐄𝐍𝐓𝐀: 🟢 𝐇𝐈𝐓 (𝐕Á𝐋𝐈𝐃𝐀)
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

def format_fail_card(portal: str, user: str) -> str:
    """Tarjeta para cuentas FAIL"""
    return f"""
{S}
🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{S}
❌ 𝐂𝐔𝐄𝐍𝐓𝐀: 🔴 𝐅𝐀𝐈𝐋 (𝐈𝐍𝐕Á𝐋𝐈𝐃𝐀)
📺 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{S}
⚠️ 𝐂𝐫𝐞𝐝𝐞𝐧𝐜𝐢𝐚𝐥𝐞𝐬 𝐢𝐧𝐜𝐨𝐫𝐫𝐞𝐜𝐭𝐚𝐬
{S}
👑 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫 𝐋𝐔𝐈𝐒 𝐑 👑
📅 {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{S}
"""

def format_retry_card(portal: str, user: str) -> str:
    """Tarjeta para cuentas RETRY"""
    return f"""
{S}
🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{S}
🔄 𝐂𝐔𝐄𝐍𝐓𝐀: 🟡 𝐑𝐄𝐓𝐑𝐘
📺 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{S}
⚠️ 𝐄𝐥 𝐬𝐞𝐫𝐯𝐢𝐝𝐨𝐫 𝐧𝐨 𝐫𝐞𝐬𝐩𝐨𝐧𝐝𝐢ó
⚠️ 𝐏𝐨𝐬𝐢𝐛𝐥𝐞 𝐩𝐫𝐨𝐭𝐞𝐜𝐜𝐢ó𝐧 𝐂𝐥𝐨𝐮𝐝𝐟𝐥𝐚𝐫𝐞
⚠️ 𝐑𝐞𝐢𝐧𝐭𝐞𝐧𝐭𝐚 𝐦á𝐬 𝐭𝐚𝐫𝐝𝐞
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
        f"🦂 *ＢＯＴ ＩＰＴＶ ＵＬＴＩＭＡ ＧＥＮＥＲＡＣＩÓＮ* 🦂\n\n"
        f"🟢 Bot *ACTIVADO*\n"
        f"✅ Lógica HIT/FAIL/RETRY implementada\n\n"
        f"📺 *Envía una URL:*\n"
        f"`http://portal:8080/get.php?username=user&password=pass`\n\n"
        f"🦂 BY LUIS R",
        parse_mode=ParseMode.MARKDOWN
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ No autorizado")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(f"🔴 *Bot APAGADO*\n🦂 BY LUIS R", parse_mode=ParseMode.MARKDOWN)

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
        f"✅ Hits: {STATS['hits']}\n"
        f"❌ Fails: {STATS['fails']}\n"
        f"🔄 Retries: {STATS['retries']}\n"
        f"⭐ Checks: {STATS['checks']}\n"
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
            f"🔥 *Ejemplo:* `/check latinchannel.tv:8080 usuario pass`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    portal, user, pwd = args[0], args[1], args[2]
    msg = await update.message.reply_text(f"🦂 *Verificando cuenta...* 🦂", parse_mode=ParseMode.MARKDOWN)
    
    STATS["checks"] += 1
    status, result = verify_account_smart(portal, user, pwd)
    
    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text(f"📡 *Obteniendo contenido...*", parse_mode=ParseMode.MARKDOWN)
        live, vod, series = get_content_counts(portal, user, pwd)
        card = format_hit_card(portal, user, pwd, result, live, vod, series)
        await msg.edit_text(card, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    elif status == "FAIL":
        STATS["fails"] += 1
        card = format_fail_card(portal, user)
        await msg.edit_text(card, parse_mode=ParseMode.MARKDOWN)
    else:  # RETRY
        STATS["retries"] += 1
        card = format_retry_card(portal, user)
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
    
    print("🦂" * 20)
    print("IPTV BOT ULTIMA GENERACION - BY LUIS R")
    print("CON LÓGICA HIT/FAIL/RETRY")
    print("🦂" * 20)
    
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
