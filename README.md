# Audioguías · Pipeline multilenguaje v2.0

Aplicación web que automatiza la producción de audioguías turísticas en 42 idiomas a partir de un único guion en español. **100% Python, sin dependencias externas:** un solo `pip install -r requirements.txt` y listo.

## Novedades v2.0

- **Interfaz web** (HTML/CSS/JS) servida por Flask en vez de la antigua GUI de escritorio.
- **Sin FFmpeg externo**: la mezcla de audio se hace con [Pedalboard](https://github.com/spotify/pedalboard) de Spotify (pure-Python con binarios embebidos en el wheel de pip).
- **Lista para web**: se puede ejecutar localmente o desplegarse en cualquier servidor con Python.

## Pipeline (4 pasos)

1. **Traducción** del guion (`texto.txt`) a los idiomas seleccionados (Google Translate vía `deep-translator`).
2. **Síntesis de voz** (TTS) con voces neuronales femeninas (Microsoft Edge TTS).
3. **Mezcla con música de fondo** (Pedalboard + numpy): atenuación, fade-out y limitador.
4. **Generación de `audioDatabase.js`** con URLs y títulos traducidos al idioma nativo, listo para integrar en la app web/móvil de la audioguía.

## Requisitos

- **Python 3.10+**
- **Conexión a internet** (Google Translate y Microsoft Edge TTS son servicios online).

No necesitas FFmpeg ni ningún otro binario externo. Todo se instala con pip.

## Instalación

```bash
git clone <url-del-repo>
cd audioguias
pip install -r requirements.txt
```

## Uso

Lanza el servidor:

```bash
python audioguias_server.py
```

Se abrirá automáticamente el navegador en `http://127.0.0.1:8000`.

En la interfaz:

1. Sube el guion `texto.txt` (formato `1 – TÍTULO`, una sección por bloque).
2. Sube la música de fondo (.mp3, .wav, .m4a, .ogg o .flac).
3. Marca los pasos a ejecutar (los 4 por defecto).
4. Ajusta volumen de la música (dB) y fade-out si lo necesitas.
5. Marca los idiomas (botón **Todos** para los 42).
6. Pulsa **EJECUTAR**.

Los logs se muestran en tiempo real en la columna derecha. Al terminar aparece un botón **Descargar resultado (.zip)** con todas las carpetas por idioma y el `audioDatabase.js`.

Estructura del .zip resultante:

```
audioguias_<job_id>.zip
├── audioDatabase.js
├── english/
│   ├── 1.introduccion_bienvenida_en.mp3
│   ├── 2.camino_hacia_ayutthaya_en.mp3
│   └── ...
├── japanese/
│   ├── 1.introduccion_bienvenida_ja.mp3
│   └── ...
└── ...
```

## Despliegue en servidor

El servidor Flask se puede desplegar tal cual con un WSGI/ASGI como `gunicorn` o `waitress`:

```bash
# Linux
pip install gunicorn
gunicorn -w 1 --threads 4 -b 0.0.0.0:8000 audioguias_server:app

# Windows
pip install waitress
waitress-serve --listen=0.0.0.0:8000 audioguias_server:app
```

Variables de entorno opcionales:

| Variable | Default | Descripción |
|---|---|---|
| `AUDIOGUIAS_HOST` | `127.0.0.1` | Interfaz donde escucha |
| `AUDIOGUIAS_PORT` | `8000` | Puerto |
| `AUDIOGUIAS_WORK_ROOT` | `./_workspace` | Carpeta donde se guardan los archivos por job |

## Estructura del proyecto

| Archivo | Propósito |
|---|---|
| `audioguias_server.py` | Servidor Flask · entry point. Endpoints REST + SSE para logs. |
| `templates/index.html` | UI web (estructura). |
| `static/style.css` | Estilos con gradiente corporativo `#F200C6 → #971EE8`. |
| `static/app.js` | Lógica del frontend: upload, lanzamiento, streaming de logs, descarga. |
| `languages.py` | Mapeo centralizado de los 42 idiomas alineado con `translationsGB.js`. |
| `text_parser.py` | Lee `texto.txt` y extrae secciones numeradas con sus títulos. |
| `translator.py` | Paso 1: traduce el guion a cada idioma. |
| `tts_generator.py` | Paso 2: genera audios `.mp3` con voz neuronal. |
| `audio_mixer.py` | Paso 3: mezcla voz + música con Pedalboard. |
| `js_generator.py` | Paso 4: emite `audioDatabase.js` con URLs y títulos por idioma. |
| `requirements.txt` | Dependencias de Python (5 paquetes). |

## Idiomas soportados (42)

English, Arabic (العربية), Basque (Euskara, *sin TTS*), Bengali (বাংলা), Catalan (Català), Croatian (Hrvatski), Czech (Čeština), Danish (Dansk), Dutch (Nederlands), Filipino, French (Français), Galician (Galego), German (Deutsch), Greek (Ελληνικά), Hindi (हिन्दी), Hungarian (Magyar), Indonesian (Bahasa Indonesia), Italian (Italiano), Japanese (日本語), Khmer (ភាសាខ្មែរ), Korean (한국어), Malay (Bahasa Melayu), Mandarin China (简体中文), Mandarin Taiwan (繁體中文), Nepali (नेपाली), Norwegian (Norsk), Persian (فارسی), Polish (Polski), Portuguese (Português), Russian (Русский), Serbian (Српски), Slovenian (Slovenščina), Spanish Spain (Español), Spanish LATAM (Español), Swahili (Kiswahili), Swedish (Svenska), Tamil (தமிழ்), Thai (ไทย), Turkish (Türkçe), Ukrainian (Українська), Urdu (اردو), Vietnamese (Tiếng Việt).

> Euskera (Vasco) se traduce pero **no se genera audio TTS** porque Microsoft Edge no ofrece voz neuronal para ese idioma.

## Opciones útiles en la UI

- **Omitir archivos ya existentes**: si el proceso se interrumpe, vuelves a pulsar EJECUTAR y solo se genera lo que falta.
- **Conservar archivos intermedios**: por defecto los `.txt` y `.mp3` sin música se borran tras la mezcla. Marca esta casilla si quieres conservarlos.
- **Pasos independientes**: puedes ejecutar solo el paso 4 para regenerar el `audioDatabase.js` sin tocar los audios.

## Personalizar voces o sufijos

Edita `languages.py`. Cada entrada es una tupla con los 5 campos:

```python
("folder_name", "Display Native", "lang_code", "voice-edge-tts", "suffix")
```

Para añadir un idioma nuevo, agrégalo a `LANGUAGES`. Para cambiar la voz, sustituye el campo `voice` por otra voz neuronal de Microsoft Edge (lista completa: `edge-tts --list-voices`).
