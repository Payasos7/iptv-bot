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
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_live_streams"
        r = requests.get(url, timeout=10)
        live = len(r.json()) if r.status_code == 200 else '?'
        
        url = f"http://{portal}/player_api.php?username={user}&password={pwd}&action=get_vod_streams"
        r = requests.get(url, timeout=10)
        vod = len(r.json()) if r.status_code == 200 else '?'
        
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
            for cat in cats[:15]:
                name = cat.get('category_name', 'Sin nombre')
                result += f"  ➠ • {name}\n"
            if len(cats) > 15:
                result += f"  ➕ ...y {len(cats)-15} categorías más"
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
    await update.message.reply_text(
        "🦂 *ＢＯＴ ＡＣＴＩＶＡＤＯ* 🦂\n\n"
        "┌─────────────────────────────────┐\n"
        "│     📡 ＥＸＴＲＡＣＴＯＲ ＩＰＴＶ     │\n"
        "│     🦂 ＢＹ ＬＵＩＳ Ｒ 🦂           │\n"
        "│     🌐 ＵＮＩＶＥＲＳＡＬ ｖ２.０     │\n"
        "└─────────────────────────────────┘\n\n"
        "🎯 *Comandos:*\n"
        "▸ /start  → Activar bot\n"
        "▸ /stop   → Desactivar bot\n"
        "▸ /status → Estado\n\n"
        "📎 *Envía un enlace Xtream o M3U*\n\n"
        "🦂 *ＢＹ ＬＵＩＳ Ｒ* 🦂",
        parse_mode='Markdown'
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ No autorizado")
        return
    global bot_active
    bot_active = False
    await update.message.reply_text(
        "🦂 *ＢＯＴ ＡＰＡＧＡＤＯ* 🦂\n\n"
        "Usa /start para encenderlo nuevamente.\n\n"
        "🦂 *ＢＹ ＬＵＩＳ Ｒ* 🦂",
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ No autorizado")
        return
    estado = "🟢 *ＡＣＴＩＶＯ*" if bot_active else "🔴 *ＡＰＡＧＡＤＯ*"
    await update.message.reply_text(
        f"┌─────────────────────────────────┐\n"
        f"│       📊 *ＥＳＴＡＤＯ ＤＥＬ ＢＯＴ*       │\n"
        f"└─────────────────────────────────┘\n\n"
        f"▸ Estado: {estado}\n"
        f"▸ Modo: Extractor Universal\n"
        f"▸ Versión: 2.0\n\n"
        f"🦂 *ＢＹ ＬＵＩＳ Ｒ* 🦂",
        parse_mode='Markdown'
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_active
    if not bot_active:
        await update.message.reply_text("🦂 Bot apagado. Usa /start 🦂")
        return
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    
    url = update.message.text.strip()
    if not url.startswith('http'):
        await update.message.reply_text("❌ Enlace inválido")
        return
    
    msg = await update.message.reply_text("🦂 *Extrayendo información...* 🦂", parse_mode='Markdown')
    
    portal, user, pwd = extract_data(url)
    if not portal:
        await msg.edit_text("❌ No se pudo extraer datos del enlace")
        return
    
    success, info = verify_account(portal, user, pwd)
    
    if success:
        # Fecha de creación (cuando se creó la cuenta en el panel)
        created = info.get('created_at', None)
        created_str = "No disponible"
        if created and str(created).isdigit() and int(created) > 0:
            created_str = datetime.fromtimestamp(int(created)).strftime('%d/%m/%Y')
        
        # Fecha de expiración
        expire = info.get('exp_date', None)
        expire_str = "No expira"
        if expire and str(expire).isdigit() and int(expire) > 0:
            expire_str = datetime.fromtimestamp(int(expire)).strftime('%d/%m/%Y')
        
        active = info.get('active_cons', '0')
        max_con = info.get('max_connections', '0')
        status_text = info.get('status', 'Active')
        is_trial = "Trial" if "trial" in user.lower() else "No Trial"
        
        country = get_server_location(portal)
        
        await msg.edit_text("📡 *Obteniendo contenido...*", parse_mode='Markdown')
        live, vod, series = get_content_counts(portal, user, pwd)
        
        await msg.edit_text("📺 *Obteniendo categorías...*", parse_mode='Markdown')
        categories = get_categories(portal, user, pwd)
        
        m3u_link = f"http://{portal}/get.php?username={user}&password={pwd}&type=m3u_plus"
        epg_link = f"http://{portal}/xmltv.php?username={user}&password={pwd}"
        
        # Diseño ULTRA ELEGANTE con 🦂
        result = f"""
╔══════════════════════════════════════════════════════════════╗
║            🦂 ＩＮＦＯＲＭＡＣＩÓＮ ＤＥ ＬＡ ＣＵＥＮＴＡ 🦂            ║
║                       🦂 ＢＹ ＬＵＩＳ Ｒ 🦂                        ║
╠══════════════════════════════════════════════════════════════╣
║  🟢 Ｅｓｔａｄｏ        : ✅ {status_text}                             ║
║  🧪 Ｔｒｉａｌ         : {is_trial}                                      ║
║  🌐 Ｐｏｒｔａｌ        : {portal}                             ║
║  👤 Ｕｓｕａｒｉｏ       : {user}                           ║
║  🔑 Ｃｏｎｔｒａｓｅñａ   : {pwd}                            ║
║  📅 Ｆｅｃｈａ ｃｒｅａｃｉóｎ : {created_str}                               ║
║  ⏰ Ｆｅｃｈａ ｅｘｐｉｒａｃｉóｎ : {expire_str}                               ║
║  👥 Ｃｏｎｅｘｉｏｎｅｓ   : {active} / {max_con}                               ║
║  📍 Ｐａíｓ          : {country}                                ║
╠══════════════════════════════════════════════════════════════╣
║                      📺 ＣＯＮＴＥＮＩＤＯ 📺                      ║
╠══════════════════════════════════════════════════════════════╣
║  📡 Ｅｎ Ｖｉｖｏ      : {live}                                            ║
║  🎬 Ｐｅｌíｃｕｌａｓ     : {vod}                                            ║
║  📹 Ｓｅｒｉｅｓ       : {series}                                           ║
╠══════════════════════════════════════════════════════════════╣
║                      🔗 ＥＮＬＡＣＥＳ 🔗                      ║
╠══════════════════════════════════════════════════════════════╣
║  📺 <a href="{m3u_link}">▶ Ｍ３Ｕ Ｐｌａｙｌｉｓｔ</a>                                ║
║  📡 <a href="{epg_link}">▶ ＥＰＧ Ｇｕｉｄｅ</a>                                   ║
"""
        if categories:
            result += f"""
╠══════════════════════════════════════════════════════════════╣
║                   🏷️ ＣＡＴＥＧＯＲÍＡＳ 🏷️                   ║
╠══════════════════════════════════════════════════════════════╣
"""
            for line in categories.split('\n')[:12]:
                if line.strip():
                    result += f"║  {line:<58} ║\n"
        
        result += f"""
╠══════════════════════════════════════════════════════════════╣
║  🦂 Ｖｅｒｉｆｉｃａｄｏ ｐｏｒ ＬＵＩＳ Ｒ 🦂                            ║
║  🕐 {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}                               ║
╚══════════════════════════════════════════════════════════════╝
"""
        await msg.edit_text(result, parse_mode='HTML')
    else:
        await msg.edit_text(
            f"╔══════════════════════════════════════════════════════════════╗\n"
            f"║                    ❌ ＣＵＥＮＴＡ ＩＮＶÁＬＩＤＡ ❌                    ║\n"
            f"╠══════════════════════════════════════════════════════════════╣\n"
            f"║  ▸ Las credenciales no son válidas                            ║\n"
            f"║  ▸ Usuario: {user}                                    ║\n"
            f"║  ▸ Portal: {portal}                                    ║\n"
            f"╠══════════════════════════════════════════════════════════════╣\n"
            f"║  🦂 ＢＹ ＬＵＩＳ Ｒ 🦂                                            ║\n"
            f"╚══════════════════════════════════════════════════════════════╝",
            parse_mode='HTML'
        )

def main():
    print("🦂 IPTV UNIVERSAL EXTRACTOR - BY LUIS R 🦂")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    print("✅ Bot Ultra Elegante 🦂 iniciado - BY LUIS R")
    app.run_polling()

if __name__ == "__main__":
    main()
