#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              🦂 IPTV BOT ULTRA SUPREMO — BY LUIS R 🦂                        ║
║              CORREGIDO CON LA LÓGICA DE _info_bot_JC.py                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import time
import threading
import socket
import requests
from datetime import datetime
from urllib.parse import urlparse
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
STATS = {"checks": 0, "hits": 0, "fails": 0, "retries": 0, "users": set()}

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
# FUNCIONES DEL SCRIPT QUE FUNCIONA
# ============================================================

def jcinfo(url):
    """Extrae información de cuenta desde URL M3U o Xtream (copia de _info_bot_JC.py)"""
    is_xui = False
    try:
        # Corrección automática protocolo ↔ puerto
        _parsed = urlparse(url)
        _port = str(_parsed.port) if _parsed.port else ""
        _prot = _parsed.scheme or "http"
        HTTPS_PORTS = {"443", "8443", "2053", "2083", "2087", "2096", "8888"}
        HTTP_PORTS = {"80", "8080", "8000", "8008", "25461", "2082", "2086"}
        
        if _port in HTTPS_PORTS and _prot != "https":
            url = url.replace(f"{_prot}://", "https://", 1)
        elif _port in HTTP_PORTS and _prot != "http":
            url = url.replace(f"{_prot}://", "http://", 1)

        if "playlist/" in url:
            base = url.split("playlist/")[0]
            rest = url.split("playlist/")[1]
            parts = [p for p in rest.split("/") if p]
            if len(parts) < 2:
                return "", "", "", "", "", "", "", "", "URL de playlist inválida"
            usr, pas = parts[0], parts[1]
            api_url = f"{base}player_api.php?username={usr}&password={pas}"
            is_xui = True
        else:
            api_url = url.replace('get.php', 'player_api.php').replace('gets.php', 'player_api.php').split("&type")[0]

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Connection': 'close',
        }
        response = requests.get(api_url, headers=headers, verify=False, timeout=(5, 15))

        if response.status_code != 200:
            return "", "", "", "", "", "", "", "", f"Error HTTP {response.status_code}"

        # Detectar respuestas en texto plano
        ct = response.headers.get("Content-Type", "")
        if "json" not in ct and "javascript" not in ct:
            raw = response.text.strip().upper()
            known_errors = {
                "PLAYLIST_DISABLED": "Lista deshabilitada",
                "ACCOUNT_EXPIRED": "Cuenta expirada",
                "ACCOUNT_BANNED": "Cuenta bloqueada",
                "USER_NOT_FOUND": "Usuario no encontrado",
                "INVALID_PASS": "Contraseña incorrecta",
            }
            for key, msg in known_errors.items():
                if key in raw:
                    return "", "", "", "", "", "", "", "", msg
            return "", "", "", "", "", "", "", "", "Respuesta inesperada"

        resp = response.json()
        
        if not is_xui:
            is_xui = bool(resp.get('server_info', {}).get('xui', False))

        if 'user_info' not in resp:
            return "", "", "", "", "", "", "", "", "Respuesta inválida"

        user_info = resp['user_info']
        status = user_info.get('status', '')

        if status.lower() != 'active':
            return "", "", "", "", "", "", "", "", "Cuenta no activa"

        username = user_info.get('username', '')
        password = user_info.get('password', '')
        expira = user_info.get('exp_date')
        prueba = user_info.get('is_trial', '0')
        active_cons = user_info.get('active_cons', '0')
        max_cons = user_info.get('max_connections', '0')

        if expira in (None, 'null', '', 0, '0'):
            expira = "Unlimited"
        else:
            try:
                expira = datetime.fromtimestamp(int(expira)).strftime('%Y-%m-%d')
            except:
                expira = str(expira)

        server_info = resp.get('server_info', {})
        server_url = server_info.get('url', '')
        port = server_info.get('port', '80')
        full_server = f"{server_url}:{port}" if server_url else ''
        timezone = server_info.get('timezone', 'UTC')

        return username, password, expira, active_cons, max_cons, full_server, timezone, prueba, "Vivo"

    except requests.RequestException as e:
        return "", "", "", "", "", "", "", "", f"Error de conexión: {e}"
    except json.JSONDecodeError:
        return "", "", "", "", "", "", "", "", "Error al decodificar JSON"
    except Exception as e:
        return "", "", "", "", "", "", "", "", f"Error: {e}"


def obtener_datos_streaming(panel, user, password):
    """Obtiene conteos de canales usando streaming (sin timeouts)"""
    base = panel.rstrip('/')
    
    def count_streaming(url, max_mb=15):
        try:
            r = requests.get(url, timeout=(5, 30), verify=False, stream=True)
            if r.status_code != 200:
                r.close()
                return "0"
            depth = 0
            root_objects = 0
            bytes_read = 0
            in_string = False
            escape_next = False
            started = False
            max_bytes = max_mb * 1024 * 1024
            
            for chunk in r.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                bytes_read += len(chunk)
                try:
                    text = chunk.decode('utf-8', errors='ignore')
                except:
                    continue
                for ch in text:
                    if escape_next:
                        escape_next = False
                        continue
                    if ch == '\\' and in_string:
                        escape_next = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if ch == '[' and not started and depth == 0:
                        started = True
                        continue
                    if not started:
                        continue
                    if ch == '{':
                        depth += 1
                        if depth == 1:
                            root_objects += 1
                    elif ch == '}':
                        depth -= 1
                    elif ch == ']' and depth == 0:
                        r.close()
                        return str(root_objects)
                if bytes_read >= max_bytes:
                    r.close()
                    return str(root_objects) if root_objects > 0 else "0"
            r.close()
            return str(root_objects) if root_objects > 0 else "0"
        except:
            return "0"
    
    live_url = f"{base}/player_api.php?username={user}&password={password}&action=get_live_streams"
    vod_url = f"{base}/player_api.php?username={user}&password={password}&action=get_vod_streams"
    series_url = f"{base}/player_api.php?username={user}&password={password}&action=get_series"
    
    live = count_streaming(live_url, 20)
    vod = count_streaming(vod_url, 20)
    series = count_streaming(series_url, 20)
    
    return live, vod, series


def extract_from_url(url):
    """Extrae portal, usuario y contraseña de cualquier URL"""
    # Formato Xtream
    match = re.search(r'//([^/]+)/get\.php\?username=([^&]+)&password=([^&]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    match = re.search(r'//([^/]+)/player_api\.php\?username=([^&]+)&password=([^&]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    # Formato XUI
    match = re.search(r'//([^/]+)/playlist/([^/]+)/([^/]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    # Formato manual
    if '|' in url:
        parts = url.split('|')
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
    
    parts = url.split()
    if len(parts) == 3 and ':' in parts[0]:
        return parts[0], parts[1], parts[2]
    
    return None, None, None


def verify_account_smart(portal, user, pwd):
    """Verificación usando la lógica de jcinfo"""
    # Construir URL
    base_url = f"http://{portal}"
    test_url = f"{base_url}/player_api.php?username={user}&password={pwd}"
    
    try:
        # Intentar obtener información de la cuenta
        username, password, expira, active, max_conn, full_server, timezone, prueba, estado = jcinfo(test_url)
        
        if estado == "Vivo" and username and password:
            return "HIT", {
                'username': username,
                'password': password,
                'expira': expira,
                'active_cons': active,
                'max_connections': max_conn,
                'full_server': full_server,
                'timezone': timezone,
                'is_trial': prueba,
                'status': 'Active'
            }
        elif "Cuenta no activa" in estado:
            return "FAIL", None
        elif any(x in estado.lower() for x in ["invalida", "expired", "banned", "not found"]):
            return "FAIL", None
        else:
            return "RETRY", None
            
    except Exception as e:
        print(f"Error en verify_account_smart: {e}")
        return "RETRY", None


def get_content_counts(portal, user, pwd):
    """Obtiene conteos usando streaming"""
    base = f"http://{portal}"
    return obtener_datos_streaming(base, user, pwd)


def get_server_location(portal):
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


def format_hit_card(portal, user, pwd, info, live, vod, series):
    """Formatea tarjeta de cuenta válida"""
    ui = info
    
    expire = ui.get('expira', 'No expira')
    active = ui.get('active_cons', '0')
    max_con = ui.get('max_connections', '0')
    status = ui.get('status', 'Active')
    is_trial = "Trial" if ui.get('is_trial') == '1' else "No Trial"
    location = get_server_location(portal)
    
    m3u_link = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
    epg_link = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
    
    card = f"""
{S}
🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{S}
✅ 𝐂𝐔𝐄𝐍𝐓𝐀: 🟢 𝐕Á𝐋𝐈𝐃𝐀 (𝐇𝐈𝐓)
📺 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
🔑 𝐂𝐨𝐧𝐭𝐫𝐚𝐬𝐞ñ𝐚: {pwd}
⏰ 𝐄𝐱𝐩𝐢𝐫𝐚: {expire}
👥 𝐂𝐨𝐧𝐞𝐱𝐢𝐨𝐧𝐞𝐬: {active} / {max_con}
📍 𝐔𝐛𝐢𝐜𝐚𝐜𝐢ó𝐧: {location}
⭐ 𝐓𝐢𝐩𝐨: {is_trial}
{S}
🔥 𝐂𝐎𝐍𝐓𝐄𝐍𝐈𝐃𝐎 🔥
{S}
📺 𝐄𝐧 𝐕𝐢𝐯𝐨: {live}
🎬 𝐏𝐞𝐥í𝐜𝐮𝐥𝐚𝐬: {vod}
📹 𝐒𝐞𝐫𝐢𝐞𝐬: {series}
{S}
🔗 <a href="{m3u_link}">𝐌𝟑𝐔 𝐋𝐢𝐧𝐤</a> | <a href="{epg_link}">𝐄𝐏𝐆 𝐋𝐢𝐧𝐤</a>
{S}
👑 𝐕𝐞𝐫𝐢𝐟𝐢𝐜𝐚𝐝𝐨 𝐩𝐨𝐫 𝐋𝐔𝐈𝐒 𝐑 👑
📅 {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{S}
"""
    return card


def format_fail_card(portal, user):
    return f"""
{S}
🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{S}
❌ 𝐂𝐔𝐄𝐍𝐓𝐀: 🔴 𝐈𝐍𝐕Á𝐋𝐈𝐃𝐀 (𝐅𝐀𝐈𝐋)
📺 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{S}
⚠️ 𝐂𝐫𝐞𝐝𝐞𝐧𝐜𝐢𝐚𝐥𝐞𝐬 𝐢𝐧𝐜𝐨𝐫𝐫𝐞𝐜𝐭𝐚𝐬
{S}
👑 𝐁𝐘 𝐋𝐔𝐈𝐒 𝐑 👑
📅 {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}
{S}
"""


def format_retry_card(portal, user):
    return f"""
{S}
🦂 𝐈𝐍𝐅𝐎𝐑𝐌𝐀𝐂𝐈Ó𝐍 𝐃𝐄 𝐋𝐀 𝐂𝐔𝐄𝐍𝐓𝐀 🦂
{S}
🔄 𝐂𝐔𝐄𝐍𝐓𝐀: 🟡 𝐑𝐄𝐓𝐑𝐘
📺 𝐏𝐨𝐫𝐭𝐚𝐥: {portal}
👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {user}
{S}
⚠️ 𝐄𝐥 𝐬𝐞𝐫𝐯𝐢𝐝𝐨𝐫 𝐧𝐨 𝐫𝐞𝐬𝐩𝐨𝐧𝐝𝐢ó
⚠️ 𝐑𝐞𝐢𝐧𝐭𝐞𝐧𝐭𝐚 𝐦á𝐬 𝐭𝐚𝐫𝐝𝐞
{S}
👑 𝐁𝐘 𝐋𝐔𝐈𝐒 𝐑 👑
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
        f"🟢 Bot *ACTIVADO*\n"
        f"✅ Lógica corregida con jcinfo()\n\n"
        f"📺 *Envía una URL:*\n"
        f"`http://portal:8080/get.php?username=user&password=pass`\n"
        f"`http://portal:8080/playlist/user/pass/m3u_plus`\n\n"
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
    status, info = verify_account_smart(portal, user, pwd)
    
    if status == "HIT":
        STATS["hits"] += 1
        await msg.edit_text(f"📡 *Obteniendo contenido...*", parse_mode=ParseMode.MARKDOWN)
        live, vod, series = get_content_counts(portal, user, pwd)
        card = format_hit_card(portal, user, pwd, info, live, vod, series)
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
    print("IPTV BOT ULTRA SUPREMO - BY LUIS R")
    print("CORREGIDO CON LA LÓGICA DE _info_bot_JC.py")
    print("🦂" * 20)
    
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
