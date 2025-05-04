import schedule
import os
from datetime import datetime, time
#import pyttsx3
import pychromecast
from gtts import gTTS

# Configuración básica
GOOGLE_HOME_NAME = "Google nest salon"  # <-- CAMBIA esto por el nombre real de tu dispositivo
SERVER_URL = "http://192.168.68.104:5000/static/mensajes/"  # Donde sirves los audios

def programar_tarea_cronica(tarea):
    if not tarea.dias_semana:
        return
    hora = datetime.fromisoformat(tarea.fecha).strftime("%H:%M")
    texto = f"Tarea repetitiva: {tarea.descripcion}"

    for dia in tarea.dias_semana:
        dia_nombre = {
            'MO': 'monday',
            'TU': 'tuesday',
            'WE': 'wednesday',
            'TH': 'thursday',
            'FR': 'friday',
            'SA': 'saturday',
            'SU': 'sunday'
        }.get(dia.upper())

        enviar_a_google_home(texto)

        ##if hasattr(schedule.every(), dia_nombre):
        ##    getattr(schedule.every(), dia_nombre).at(hora).do(recordar_cronica, texto)


def generar_mp3(texto: str, nombre_archivo: str) -> str:
    """Genera el MP3 usando pyttsx3 y espera que se complete."""
    ruta = os.path.join('static', 'mensajes', nombre_archivo)
    tts = gTTS(text=texto, lang='es')
    tts.save(ruta)
    #engine = pyttsx3.init()
    #engine.setProperty('rate', 140)  # ✅ Velocidad más natural (default suele ser 200)
    #engine.save_to_file(texto, ruta)
    #engine.runAndWait()  # 🔥 Aquí garantiza que el archivo ya esté escrito
    while not os.path.exists(ruta):
        time.sleep(0.1)  # Espera a que realmente esté creado
    print(f"[INFO] MP3 generado en {ruta}")
    return ruta


def enviar_a_google_home(texto):
    chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=["Google nest salon"])
    cast = chromecasts[0]
    cast.wait()

    tts_url = f"http://api.voicerss.org/?key=TU_API_KEY&hl=es-es&src={texto.replace(' ', '+')}"
    
    mc = cast.media_controller
    mc.play_media(tts_url, 'audio/mp3')
    mc.block_until_active()
    browser.stop_discovery()

def enviar_mensaje_a_google_home(nombre_archivo: str):
    """Envía el mensaje MP3 al Google Home para reproducirlo."""
    chromecasts, browser = pychromecast.get_chromecasts()
    print("nombre de archivo enviar en google: ", nombre_archivo)
    cast = next(cc for cc in chromecasts if GOOGLE_HOME_NAME in cc.name)
    cast.wait()
    mc = cast.media_controller

    url_mp3 = f"https://hagente-ia-iscq.onrender.com/static/mensajes/{nombre_archivo}"
    mc.play_media(url_mp3, 'audio/mp3')
    mc.block_until_active()
     # 🧠 Leer duración del MP3
    #audio = url_mp3(f'static/mensajes/{nombre_archivo}')
    #duracion = audio.info.length

    # 💤 Esperar a que termine
    #print(f"Esperando {duracion:.2f} segundos para completar reproducción...")
    #time.sleep(duracion + 1)  # Añadimos un segundo extra de margen

    #browser.stop_discovery()
    print(f"[INFO] Mensaje enviado al Google Home: {url_mp3}")
