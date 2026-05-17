#!/usr/bin/env python3
import requests
import re
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8708803857:AAHsIF_AbBuM_GPam1MWYBBRFycRSWAA4Cs"
ADMIN_ID = 1183299436

bot_active = True

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
    await update.message.reply_text("✅ Bot ACTIVADO - BY LUIS R")

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
    msg = await update.message.reply_text("⏳ Verificando...")
    portal, user, pwd = extract_data(url)
    if not portal:
        await msg.edit_text("❌ No se pudo extraer datos")
        return
    success, info = verify_account(portal, user, pwd)
    if success:
        expire = info.get('exp_date', 'No expira')
        if str(expire).isdigit():
            expire = datetime.fromtimestamp(int(expire)).strftime('%Y-%m-%d')
        active = info.get('active_cons', '0')
        max_con = info.get('max_connections', '0')
        result = f"""
━━━━━━━━━━━━━━━━━━━━━━
     ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★
━━━━━━━━━━━━━━━━━━━━━━
➥ 🟢 CUENTA VÁLIDA
➥🌐 Portal: {portal}
➥👤 User: {user}
➥🔑 Pass: {pwd}
➥⏲ Expira: {expire}
➥👁 Conexiones: {active}/{max_con}
━━━━━━━━━━━━━━━━━━━━━━
   ✔️ BY LUIS R
   🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━
"""
        await msg.edit_text(result)
    else:
        await msg.edit_text(f"❌ Cuenta INVÁLIDA\n@{update.effective_user.first_name}\nBY LUIS R")

def main():
    print("✅ Bot iniciado - BY LUIS R")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.run_polling()

if __name__ == "__main__":
    main()
