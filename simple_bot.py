#!/usr/bin/env python3
import requests
import re
import socket
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8708803857:AAHsIF_AbBuM_GPam1MWYBBRFycRSWAA4Cs"
ADMIN_ID = 1183299436

bot_active = True

def get_country_flag(country_code):
    flags = {
        'US': '🇺🇸', 'MX': '🇲🇽', 'CA': '🇨🇦', 'GB': '🇬🇧', 'ES': '🇪🇸',
        'FR': '🇫🇷', 'DE': '🇩🇪', 'IT': '🇮🇹', 'BR': '🇧🇷', 'AR': '🇦🇷',
        'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'CL': '🇨🇱', 'EC': '🇪🇨',
    }
    return flags.get(country_code.upper(), '🌍')

def get_server_location(host):
    try:
        ip = socket.gethostbyname(host.split(':')[0])
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'success':
                country = data.get('country', 'Desconocido')
                code = data.get('countryCode', '')
                return f"{country} {get_country_flag(code)}"
    except:
        pass
    return "Desconocido 🌍"

def get_content_counts(portal, user, pwd):
    try:
        # Canales en vivo
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_streams"
        r = requests.get(url, timeout=10)
        live = len(r.json()) if r.status_code == 200 else '?'
        
        # Películas VOD
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_vod_streams"
        r = requests.get(url, timeout=10)
        vod = len(r.json()) if r.status_code == 200 else '?'
        
        # Series
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_series"
        r = requests.get(url, timeout=10)
        series = len(r.json()) if r.status_code == 200 else '?'
        
        return str(live), str(vod), str(series)
    except:
        return '?', '?', '?'

def get_categories(portal, user, pwd):
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_categories"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            cats = r.json()
            result = ""
            for cat in cats[:10]:
                name = cat.get('category_name', 'Sin nombre')
                result += f"  ➠ • {name}\n"
            if len(cats) > 10:
                result += f"  ➕ ...y {len(cats)-10} categorías más"
            return result
    except:
        pass
    return ""

def extract_data(url):
    match = re.search(r'//([^/]+)/(?:player_api|get)\.php\?username=([^&]+)&password=([^&]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    match = re.search(r'//([^/]+)/playlist/([^/]+)/([^/]+)', url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None, None, None

def verify_account(portal, user, pwd):
    try:
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return False, None
        data = r.json()
        if data.get('user_info', {}).get('auth') == 1:
            return True, data['user_info']
        return False, None
    except:
        return False, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ No autorizado")
        return
    global bot_active
    bot_active = True
    await update.message.reply_text("✅ Bot ACTIVADO - BY LUIS R\n\nEnvía un enlace Xtream o M3U para verificar.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ No autorizado")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text("🛑 Bot APAGADO - BY LUIS R")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ No autorizado")
        return
    estado = "🟢 ACTIVO" if bot_active else "🔴 APAGADO"
    await update.message.reply_text(f"📊 Estado: {estado}\nBY LUIS R")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_active
    if not bot_active:
        await update.message.reply_text("🔴 Bot apagado. Usa /start")
        return
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    
    url = update.message.text.strip()
    if not url.startswith('http'):
        await update.message.reply_text("❌ Enlace inválido")
        return
    
    msg = await update.message.reply_text("⏳ Verificando cuenta...")
    
    portal, user, pwd = extract_data(url)
    if not portal:
        await msg.edit_text("❌ No se pudo extraer datos del enlace")
        return
    
    success, info = verify_account(portal, user, pwd)
    
    if success:
        # Datos de la cuenta
        expire = info.get('exp_date', 'No expira')
        if str(expire).isdigit() and int(expire) > 0:
            expire = datetime.fromtimestamp(int(expire)).strftime('%d/%m/%Y %H:%M')
        active = info.get('active_cons', '0')
        max_con = info.get('max_connections', '0')
        status_text = info.get('status', 'Active')
        is_trial = "Trial" if "trial" in user.lower() or "test" in user.lower() else "No Trial"
        
        # Ubicación del servidor
        country = get_server_location(portal)
        
        # Obtener conteos de contenido
        await msg.edit_text("⏳ Obteniendo información del servidor...")
        live, vod, series = get_content_counts(portal, user, pwd)
        
        # Obtener categorías
        await msg.edit_text("⏳ Obteniendo categorías...")
        categories = get_categories(portal, user, pwd)
        
        # Construir enlaces
        m3u_link = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        epg_link = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
        
        # Formato del mensaje
        separator = "━━━━━━━━━━━━━━━━━━━━━━"
        result = f"""
{separator}
     ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★
{separator}
➥ 🟢 CUENTA VÁLIDA
➥🆙 Estado: ✅ {status_text}
➥🧪 {is_trial}
➥🌐 Portal: {portal}
➥👤 Usuario: {user}
➥🔑 Contraseña: {pwd}
➥⏲ Vence: {expire}
➥👁 Conexiones: {active} / {max_con}
➥📍 País: {country}
{separator}
       ★彡ᴄᴏɴᴛᴇɴᴛ彡★
{separator}
➥📺 En Vivo: {live}
➥🎥 VOD: {vod}
➥📹 Series: {series}
{separator}
➥🔗 <a href="{m3u_link}">M3U Link</a>   |   <a href="{epg_link}">EPG Link</a>
"""
        if categories:
            result += f"""
{separator}
    ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★
{separator}
{categories}
"""
        result += f"""
{separator}
   ✔️ Verificado por BY LUIS R
   🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{separator}"""
        
        await msg.edit_text(result, parse_mode='HTML')
    else:
        await msg.edit_text(f"❌ CUENTA INVÁLIDA\n\n@{update.effective_user.first_name}, las credenciales no son válidas.\n\nBY LUIS R")

def main():
    print("🚀 Bot IPTV Universal - BY LUIS R")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    print("✅ Bot iniciado correctamente - BY LUIS R")
    app.run_polling()

if __name__ == "__main__":
    main()
