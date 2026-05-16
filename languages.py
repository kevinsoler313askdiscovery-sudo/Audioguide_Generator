"""
Mapeo centralizado de idiomas para todo el pipeline.

El orden, los nombres de carpeta (folder_name) y los display_name están
alineados con el archivo del proyecto: translationsGB.js
(misma clave y misma etiqueta nativa).

Cada idioma define:
    - folder_name : Nombre de la carpeta y clave en audioDatabase.js
                    (siempre en inglés, minúsculas) — coincide con
                    las claves de translationsGB.js
    - display_name: Etiqueta nativa del idioma (English, Deutsch,
                    日本語, العربية...) — coincide con el campo
                    'label' de translationsGB.js
    - lang_code   : Código que usa deep-translator (Google Translator)
    - voice       : Voz de edge-tts (None si no hay voz disponible)
    - suffix      : Sufijo final del archivo .mp3 editado (sin guion bajo inicial)
                    Ej: 'ko' -> 1.introduccion_bienvenida_ko.mp3
"""

LANGUAGES = [
    # folder_name,        display_name,         lang_code,  voice,                       suffix
    ("english",           "English",            "en",       "en-US-AriaNeural",          "en"),
    ("arabic",            "العربية",            "ar",       "ar-SA-ZariyahNeural",       "ar"),
    ("basque",            "Euskara",            "eu",       None,                        "eu"),
    ("bengali",           "বাংলা",              "bn",       "bn-IN-TanishaaNeural",      "bn"),
    ("catalan",           "Català",             "ca",       "ca-ES-JoanaNeural",         "ca"),
    ("croatian",          "Hrvatski",           "hr",       "hr-HR-GabrijelaNeural",     "hr"),
    ("czech",             "Čeština",            "cs",       "cs-CZ-VlastaNeural",        "cs"),
    ("danish",            "Dansk",              "da",       "da-DK-ChristelNeural",      "da"),
    ("dutch",             "Nederlands",         "nl",       "nl-NL-ColetteNeural",       "nl"),
    ("filipino",          "Filipino",           "tl",       "fil-PH-BlessicaNeural",     "tl"),
    ("french",            "Français",           "fr",       "fr-FR-DeniseNeural",        "fr"),
    ("galician",          "Galego",             "gl",       "gl-ES-SabelaNeural",        "gl"),
    ("german",            "Deutsch",            "de",       "de-DE-KatjaNeural",         "de"),
    ("greek",             "Ελληνικά",           "el",       "el-GR-AthinaNeural",        "el"),
    ("hindi",             "हिन्दी",              "hi",       "hi-IN-SwaraNeural",         "hi"),
    ("hungarian",         "Magyar",             "hu",       "hu-HU-NoemiNeural",         "hu"),
    ("indonesian",        "Bahasa Indonesia",   "id",       "id-ID-GadisNeural",         "id"),
    ("italian",           "Italiano",           "it",       "it-IT-ElsaNeural",          "it"),
    ("japanese",          "日本語",              "ja",       "ja-JP-NanamiNeural",        "ja"),
    ("khmer",             "ភាសាខ្មែរ",          "km",       "km-KH-SreymomNeural",       "km"),
    ("korean",            "한국어",              "ko",       "ko-KR-SunHiNeural",         "ko"),
    ("malay",             "Bahasa Melayu",      "ms",       "ms-MY-YasminNeural",        "ms"),
    ("mandarin_china",    "简体中文",            "zh-CN",    "zh-CN-XiaoxiaoNeural",      "zh_cn"),
    ("mandarin_taiwan",   "繁體中文",            "zh-TW",    "zh-TW-HsiaoChenNeural",     "zh_tw"),
    ("nepali",            "नेपाली",              "ne",       "ne-NP-HemkalaNeural",       "ne"),
    ("norwegian",         "Norsk",              "no",       "nb-NO-PernilleNeural",      "no"),
    ("persian",           "فارسی",              "fa",       "fa-IR-DilaraNeural",        "fa"),
    ("polish",            "Polski",             "pl",       "pl-PL-ZofiaNeural",         "pl"),
    ("portuguese",        "Português",          "pt",       "pt-BR-FranciscaNeural",     "pt"),
    ("russian",           "Русский",            "ru",       "ru-RU-SvetlanaNeural",      "ru"),
    ("serbian",           "Српски",             "sr",       "sr-RS-SophieNeural",        "sr"),
    ("slovenian",         "Slovenščina",        "sl",       "sl-SI-PetraNeural",         "sl"),
    ("spanish_spain",     "Español (España)",   "es",       "es-ES-ElviraNeural",        "es"),
    ("spanish_latam",     "Español (Latam)",    "es",       "es-MX-DaliaNeural",         "es_latam"),
    ("swahili",           "Kiswahili",          "sw",       "sw-KE-ZuriNeural",          "sw"),
    ("swedish",           "Svenska",            "sv",       "sv-SE-SofieNeural",         "sv"),
    ("tamil",             "தமிழ்",              "ta",       "ta-IN-PallaviNeural",       "ta"),
    ("thai",              "ไทย",                "th",       "th-TH-PremwadeeNeural",     "th"),
    ("turkish",           "Türkçe",             "tr",       "tr-TR-EmelNeural",          "tr"),
    ("ukrainian",         "Українська",         "uk",       "uk-UA-PolinaNeural",        "uk"),
    ("urdu",              "اردو",               "ur",       "ur-PK-UzmaNeural",          "ur"),
    ("vietnamese",        "Tiếng Việt",         "vi",       "vi-VN-HoaiMyNeural",        "vi"),
]


def as_dicts():
    """Devuelve LANGUAGES como lista de diccionarios (más cómodo para consumir)."""
    keys = ("folder_name", "display_name", "lang_code", "voice", "suffix")
    return [dict(zip(keys, row)) for row in LANGUAGES]


def by_folder(folder_name):
    """Busca un idioma por nombre de carpeta. Devuelve dict o None."""
    for d in as_dicts():
        if d["folder_name"] == folder_name:
            return d
    return None


# Lista de carpetas que tienen voz TTS disponible (excluye Basque)
TTS_AVAILABLE = [d["folder_name"] for d in as_dicts() if d["voice"] is not None]
