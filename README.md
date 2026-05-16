# Audioguías · Pipeline multilenguaje

Aplicación de escritorio con interfaz gráfica que automatiza la producción de audioguías turísticas en 42 idiomas a partir de un único guion en español.

El pipeline consta de cuatro pasos encadenados:

1. **Traducción** del guion (`texto.txt`) a los idiomas seleccionados (Google Translate vía `deep-translator`).
2. **Síntesis de voz** (TTS) con voces neuronales femeninas (Microsoft Edge TTS).
3. **Mezcla con música de fondo** vía FFmpeg, con control de volumen, fade-out y limitador.
4. **Generación de `audioDatabase.js`** con URLs y títulos traducidos al idioma nativo, listo para integrar en la app web/móvil de la audioguía.

Todo se controla desde una interfaz con CustomTkinter: eliges idiomas con checkboxes, marcas los pasos a ejecutar y pulsas un botón. Cero edición manual de archivos por idioma.

## Requisitos

- **Python 3.10+**
- **FFmpeg** en el PATH (o en `C:\ffmpeg-master-latest-win64-gpl-shared\bin\` por defecto en Windows). Descarga en [ffmpeg.org](https://ffmpeg.org/download.html).
- **Conexión a internet** (Google Translate y Microsoft Edge TTS son servicios online).

## Instalación

```bash
git clone <url-del-repo>
cd audioguias
pip install -r requirements.txt
```

## Uso

1. Prepara un archivo `texto.txt` con el guion en español, dividido en secciones numeradas con este formato:

   ```
   1 – INTRODUCCIÓN · BIENVENIDA
   Hola y bienvenidos al tour...

   2 – CAMINO HACIA AYUTTHAYA
   El paisaje empieza a cambiar...
   ```

2. Consigue un archivo `.mp3` con la música de fondo del tour.

3. Lanza la aplicación:

   ```bash
   python audioguias_app.py
   ```

4. En la interfaz:
   - Selecciona `texto.txt` y la música de fondo.
   - Elige la **carpeta de trabajo** (donde se guardarán los audios finales).
   - Marca los pasos a ejecutar (los 4 por defecto).
   - Marca los idiomas que quieres procesar (botón **Todos** para los 42).
   - Ajusta volumen de la música (dB) y duración del fade-out si lo necesitas.
   - Pulsa **EJECUTAR**.

Al terminar, dentro de la carpeta de trabajo encontrarás:

```
carpeta_de_trabajo/
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

Cada subcarpeta lleva como nombre la clave en inglés del idioma (alineada con `translationsGB.js` y `audioDatabase.js` del proyecto de la audioguía).

## Estructura del proyecto

| Archivo | Propósito |
|---------|-----------|
| `audioguias_app.py` | Aplicación principal con la GUI (CustomTkinter). Entry point. |
| `languages.py` | Mapeo centralizado de los 42 idiomas: carpeta, etiqueta nativa, código Google, voz edge-tts, sufijo. |
| `text_parser.py` | Lee `texto.txt` y extrae secciones numeradas con sus títulos normalizados a slug. |
| `translator.py` | Paso 1: traduce el guion a cada idioma seleccionado. |
| `tts_generator.py` | Paso 2: genera audios `.mp3` con voz neuronal. |
| `audio_mixer.py` | Paso 3: mezcla voz + música con FFmpeg y limpia los intermedios. |
| `js_generator.py` | Paso 4: emite `audioDatabase.js` con URLs y títulos por idioma. |
| `requirements.txt` | Dependencias de Python. |

## Idiomas soportados (42)

English, Arabic (العربية), Basque (Euskara, *sin TTS*), Bengali (বাংলা), Catalan (Català), Croatian (Hrvatski), Czech (Čeština), Danish (Dansk), Dutch (Nederlands), Filipino, French (Français), Galician (Galego), German (Deutsch), Greek (Ελληνικά), Hindi (हिन्दी), Hungarian (Magyar), Indonesian (Bahasa Indonesia), Italian (Italiano), Japanese (日本語), Khmer (ភាសាខ្មែរ), Korean (한국어), Malay (Bahasa Melayu), Mandarin China (简体中文), Mandarin Taiwan (繁體中文), Nepali (नेपाली), Norwegian (Norsk), Persian (فارسی), Polish (Polski), Portuguese (Português), Russian (Русский), Serbian (Српски), Slovenian (Slovenščina), Spanish Spain (Español), Spanish LATAM (Español), Swahili (Kiswahili), Swedish (Svenska), Tamil (தமிழ்), Thai (ไทย), Turkish (Türkçe), Ukrainian (Українська), Urdu (اردو), Vietnamese (Tiếng Việt).

> Euskera (Vasco) se traduce pero **no se genera audio TTS** porque Microsoft Edge no ofrece voz neuronal para ese idioma.

## Opciones útiles

- **Omitir archivos ya existentes**: si el proceso se interrumpe, vuelves a pulsar EJECUTAR y solo se genera lo que falta.
- **Conservar archivos intermedios**: por defecto los `.txt` y `.mp3` sin música se borran tras la mezcla. Marca esta casilla si quieres conservarlos (útil para probar varias músicas sin regenerar TTS).
- **Pasos independientes**: puedes ejecutar solo el paso 4 para regenerar el `audioDatabase.js` sin tocar los audios.

## Personalizar voces o sufijos

Edita `languages.py`. Cada entrada es una tupla con los 5 campos:

```python
("folder_name", "Display Native", "lang_code", "voice-edge-tts", "suffix")
```

Para añadir un idioma nuevo, agrégalo a la lista `LANGUAGES`. Para cambiar la voz de un idioma, sustituye el campo `voice` por otra voz neuronal de Microsoft Edge (lista completa: `edge-tts --list-voices`).
