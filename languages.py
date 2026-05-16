"""
Mapeo centralizado de idiomas para todo el pipeline.

Cada idioma define:
    - folder_name : Nombre de la carpeta de salida (siempre en inglés, minúsculas)
    - display_name: Nombre legible para mostrar en la GUI
    - lang_code   : Código que usa deep-translator (Google Translator)
    - voice       : Voz de edge-tts (None si no hay voz disponible)
    - suffix      : Sufijo final del archivo .mp3 editado (sin guion bajo inicial)
                    Ej: 'ko' -> 1.introduccion_bienvenida_ko.mp3

Para añadir un idioma nuevo, solo agrégalo a la lista LANGUAGES.
"""

LANGUAGES = [
    # folder_name,         display_name,         lang_code,  voice,                       suffix
    ("german",             "Alemán",             "de",       "de-DE-KatjaNeural",         "de"),
    ("arabic",             "Árabe",              "ar",       "ar-SA-ZariyahNeural",       "ar"),
    ("bengali",            "Bengalí",            "bn",       "bn-IN-TanishaaNeural",      "bn"),
    ("czech",              "Checo",              "cs",       "cs-CZ-VlastaNeural",        "cs"),
    ("danish",             "Danés",              "da",       "da-DK-ChristelNeural",      "da"),
    ("dutch",              "Neerlandés",         "nl",       "nl-NL-ColetteNeural",       "nl"),
    ("english",            "Inglés",             "en",       "en-US-AriaNeural",          "en"),
    ("spanish_spain",      "Español (España)",   "es",       "es-ES-ElviraNeural",        "es"),
    ("spanish_latam",      "Español (LATAM)",    "es",       "es-MX-DaliaNeural",         "es_latam"),
    ("filipino",           "Filipino",           "tl",       "fil-PH-BlessicaNeural",     "tl"),
    ("french",             "Francés",            "fr",       "fr-FR-DeniseNeural",        "fr"),
    ("greek",              "Griego",             "el",       "el-GR-AthinaNeural",        "el"),
    ("hindi",              "Hindi",              "hi",       "hi-IN-SwaraNeural",         "hi"),
    ("hungarian",          "Húngaro",            "hu",       "hu-HU-NoemiNeural",         "hu"),
    ("indonesian",         "Indonesio",          "id",       "id-ID-GadisNeural",         "id"),
    ("italian",            "Italiano",           "it",       "it-IT-ElsaNeural",          "it"),
    ("japanese",           "Japonés",            "ja",       "ja-JP-NanamiNeural",        "ja"),
    ("korean",             "Coreano",            "ko",       "ko-KR-SunHiNeural",         "ko"),
    ("malay",              "Malayo",             "ms",       "ms-MY-YasminNeural",        "ms"),
    ("mandarin_china",     "Mandarín (China)",   "zh-CN",    "zh-CN-XiaoxiaoNeural",      "zh_cn"),
    ("mandarin_taiwan",    "Mandarín (Taiwán)",  "zh-TW",    "zh-TW-HsiaoChenNeural",     "zh_tw"),
    ("norwegian",          "Noruego",            "no",       "nb-NO-PernilleNeural",      "no"),
    ("persian",            "Persa",              "fa",       "fa-IR-DilaraNeural",        "fa"),
    ("polish",             "Polaco",             "pl",       "pl-PL-ZofiaNeural",         "pl"),
    ("portuguese",         "Portugués",          "pt",       "pt-BR-FranciscaNeural",     "pt"),
    ("russian",            "Ruso",               "ru",       "ru-RU-SvetlanaNeural",      "ru"),
    ("swahili",            "Swahili",            "sw",       "sw-KE-ZuriNeural",          "sw"),
    ("swedish",            "Sueco",              "sv",       "sv-SE-SofieNeural",         "sv"),
    ("tamil",              "Tamil",              "ta",       "ta-IN-PallaviNeural",       "ta"),
    ("thai",               "Tailandés",          "th",       "th-TH-PremwadeeNeural",     "th"),
    ("turkish",            "Turco",              "tr",       "tr-TR-EmelNeural",          "tr"),
    ("ukrainian",          "Ucraniano",          "uk",       "uk-UA-PolinaNeural",        "uk"),
    ("urdu",               "Urdu",               "ur",       "ur-PK-UzmaNeural",          "ur"),
    ("vietnamese",         "Vietnamita",         "vi",       "vi-VN-HoaiMyNeural",        "vi"),
    ("catalan",            "Catalán",            "ca",       "ca-ES-JoanaNeural",         "ca"),
    ("khmer",              "Camboyano (Jemer)",  "km",       "km-KH-SreymomNeural",       "km"),
    ("basque",             "Euskera (Vasco)",    "eu",       None,                        "eu"),
    ("galician",           "Gallego",            "gl",       "gl-ES-SabelaNeural",        "gl"),
    ("nepali",             "Nepalí",             "ne",       "ne-NP-HemkalaNeural",       "ne"),
    ("croatian",           "Croata",             "hr",       "hr-HR-GabrijelaNeural",     "hr"),
    ("serbian",            "Serbio",             "sr",       "sr-RS-SophieNeural",        "sr"),
    ("slovenian",          "Esloveno",           "sl",       "sl-SI-PetraNeural",         "sl"),
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
