import requests
import json
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

def extraer_datos_desde_url(url):
    """
    Extrae portal, usuario y password desde cualquier formato de URL IPTV
    """
    # Formato 1: get.php?username=xxx&password=xxx
    if 'get.php' in url or 'player_api.php' in url:
        parsed = urlparse(url)
        portal = parsed.netloc
        query = parse_qs(parsed.query)
        usuario = query.get('username', [None])[0]
        password = query.get('password', [None])[0]
        return portal, usuario, password
    
    # Formato 2: portal:8080/live/usuario/password/index.m3u
    match = re.search(r'//([^/]+)/live/([^/]+)/([^/]+)', url)
    if match:
        portal = match.group(1)
        usuario = match.group(2)
        password = match.group(3)
        return portal, usuario, password
    
    # Formato 3: solo la URL del portal
    return None, None, None


def verificar_cuenta_con_api(portal, usuario, password):
    """
    Verifica la cuenta usando la API correcta (player_api.php)
    """
    # ✅ URL CORRECTA para obtener JSON
    url_api = f"http://{portal}/player_api.php?username={usuario}&password={password}"
    
    try:
        response = requests.get(url_api, timeout=15)
        
        # Verificar si es JSON válido
        try:
            datos = response.json()
        except:
            return 'RETRY', {'motivo': 'No devuelve JSON - Servidor bloqueado o caído'}
        
        # Buscar user_info en la respuesta
        user_info = datos.get('user_info', {})
        
        if not user_info:
            return 'RETRY', {'motivo': 'Respuesta sin user_info'}
        
        auth = user_info.get('auth', 0)
        status = user_info.get('status', '')
        
        # Cuenta ACTIVA
        if auth == 1 or status == 'Active':
            # Convertir fecha de expiración
            exp_date = user_info.get('exp_date', 0)
            if exp_date and exp_date > 0:
                fecha = datetime.fromtimestamp(exp_date).strftime('%d/%m/%Y %H:%M')
            else:
                fecha = 'No especificada'
            
            info = {
                'usuario': usuario,
                'password': password,
                'portal': portal,
                'status': status,
                'activa': True,
                'vence': fecha,
                'conexiones': f"{user_info.get('active_cons', 0)} / {user_info.get('max_cons', 0)}",
                'trial': '✅ Sí' if user_info.get('is_trial', '0') == '1' else '❌ No',
                'canales': datos.get('available_channels', '?'),
                'vod': datos.get('available_vod', '?'),
                'series': datos.get('available_series', '?')
            }
            return 'ACTIVA', info
        
        # Cuenta FALLIDA
        elif auth == 0:
            return 'FALLIDA', {'motivo': 'Usuario o contraseña incorrectos'}
        
        elif status == 'Expired':
            return 'FALLIDA', {'motivo': 'Cuenta EXPIRADA'}
        
        elif status == 'Disabled':
            return 'FALLIDA', {'motivo': 'Cuenta DESHABILITADA'}
        
        else:
            return 'RETRY', {'motivo': f'Estado desconocido: {status}'}
            
    except requests.exceptions.Timeout:
        return 'RETRY', {'motivo': 'Timeout - El servidor no responde'}
    except requests.exceptions.ConnectionError:
        return 'RETRY', {'motivo': 'Error de conexión - Servidor caído'}
    except Exception as e:
        return 'RETRY', {'motivo': f'Error: {str(e)}'}


def obtener_categorias(portal, usuario, password, limite=15):
    """
    Obtiene las categorías del servicio
    """
    url = f"http://{portal}/player_api.php?username={usuario}&password={password}&action=get_live_categories"
    
    try:
        response = requests.get(url, timeout=10)
        categorias = response.json()
        
        if isinstance(categorias, list):
            resultado = []
            for cat in categorias[:limite]:
                nombre = cat.get('category_name', 'Sin nombre')
                cantidad = cat.get('num', 0)
                resultado.append(f"  ➠ • {nombre} • [{cantidad}]")
            
            if len(categorias) > limite:
                resultado.append(f"  ➕ ...y {len(categorias) - limite} categorías más")
            return resultado
        return []
    except:
        return []


def formatear_mensaje(estado, info, categorias=None, usuario_telegram="smile5678"):
    """
    Formatea el mensaje bonito
    """
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if estado == 'ACTIVA':
        mensaje = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🦂 LUIS R 🦂
  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➥ 🟢 CUENTA VÁLIDA
➥ 🆙 Estado: ✅ ACTIVA
➥ 🧪 Trial: {info.get('trial', '❌ No')}
➥ 🌐 Portal: {info.get('portal', '?')}
➥ 👤 Usuario: {info.get('usuario', '?')}
➥ 🔑 Contraseña: {info.get('password', '?')}
➥ ⏲ Vence: {info.get('vence', '?')}
➥ 👁 Conexiones: {info.get('conexiones', '?')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       ★彡ᴄᴏɴᴛᴇɴɪᴅᴏ彡★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➥ 📺 En Vivo: {info.get('canales', '?')}
➥ 🎥 VOD: {info.get('vod', '?')}
➥ 📹 Series: {info.get('series', '?')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ★彡ᴄᴀᴛᴇɢᴏʀíᴀs彡★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        if categorias:
            for cat in categorias[:12]:
                mensaje += f"\n{cat}"
        
        mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ✔️ Verificado para @{usuario_telegram}
   🕐 {ahora}
   🦂 @Luishits_bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return mensaje
    
    elif estado == 'FALLIDA':
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🦂 LUIS R 🦂
  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➥ ❌ CUENTA INVÁLIDA
➥ 📛 Estado: FALLIDA
➥ 🌐 Portal: {info.get('portal', '?')}
➥ 👤 Usuario: {info.get('usuario', '?')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠️ {info.get('motivo', 'Credenciales incorrectas')}
   ✔️ Verificado para @{usuario_telegram}
   🕐 {ahora}
   🦂 @Luishits_bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    else:  # RETRY
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🦂 LUIS R 🦂
  ★彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡★
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
➥ 🔄 SIN RESPUESTA / RETRY
➥ 🌐 Portal: {info.get('portal', '?')}
➥ 👤 Usuario: {info.get('usuario', '?')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠️ {info.get('motivo', 'Servidor bloqueado o sin respuesta')}
  💡 Intenta más tarde
   ✔️ Verificado para @{usuario_telegram}
   🕐 {ahora}
   🦂 @Luishits_bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


def procesar_lista(url, usuario_telegram="smile5678"):
    """
    Función principal - llamar desde el bot
    """
    # Extraer datos de la URL
    portal, usuario, password = extraer_datos_desde_url(url)
    
    if not portal or not usuario or not password:
        return "❌ Error: No se pudo extraer portal/usuario/contraseña de la URL"
    
    # Verificar la cuenta
    estado, info = verificar_cuenta_con_api(portal, usuario, password)
    info['portal'] = portal
    info['usuario'] = usuario
    info['password'] = password
    
    # Obtener categorías si está activa
    categorias = None
    if estado == 'ACTIVA':
        categorias = obtener_categorias(portal, usuario, password)
    
    # Formatear y retornar
    return formatear_mensaje(estado, info, categorias, usuario_telegram)
