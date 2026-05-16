"""
Generador del archivo JavaScript audioDatabase.js

Para cada idioma seleccionado:
    1. Traduce el TÍTULO crudo de cada sección al idioma destino vía
       deep-translator (Google).
    2. Construye la URL del audio final con el formato:
           BASE_URL + 'folder/<num>.<slug>_<suffix>.mp3'
    3. Emite un array de objetos { id, title, url } por idioma.

El archivo resultante tiene la estructura:

    const audioDatabase = {
        english: [
            { id: 1, title: '1. INTRODUCTION WELCOME', url: BASE_URL + 'english/1.introduccion_bienvenida_en.mp3' },
            ...
        ],
        persian: [
            { id: 1, title: '1. مقدمه و خوشامدگویی', url: BASE_URL + 'persian/1.introduccion_bienvenida_fa.mp3' },
            ...
        ],
        ...
    };

La constante BASE_URL queda como variable JS — la define el usuario en su
propio código (ej: const BASE_URL = 'https://miservidor.com/audios/').
"""

import os

try:
    from deep_translator import GoogleTranslator
except ImportError as e:
    raise ImportError(
        "Falta la librería 'deep-translator'. Instálala con: "
        "pip install deep-translator"
    ) from e


def _log(progress_cb, msg):
    print(msg)
    if progress_cb:
        progress_cb(msg)


def _escape_js_single(s: str) -> str:
    """
    Escapa una cadena para uso seguro dentro de comillas simples de JavaScript.
    No usa repr() porque queremos preservar Unicode legible (no convertirlo
    a secuencias \\uXXXX).
    """
    return (
        s.replace("\\", "\\\\")
         .replace("'", "\\'")
         .replace("\n", " ")
         .replace("\r", "")
         .strip()
    )


def _translate_title(translator, raw_title: str, progress_cb) -> str:
    """
    Traduce el título crudo. Si falla, devuelve el original.
    Reemplaza '·' por '|' antes de traducir para que el separador
    sobreviva mejor a la traducción.
    """
    # El separador '·' tiende a confundir al traductor. '|' se preserva mejor.
    src = raw_title.replace("·", "|")
    try:
        return translator.translate(src) or raw_title
    except Exception as e:
        _log(progress_cb, f"    [Aviso] No se pudo traducir título '{raw_title}': {e}")
        return raw_title


def generate_database(
    secciones: dict,
    idiomas_seleccionados: list,
    output_path: str,
    base_url_prefix: str = "BASE_URL + ",
    progress_cb=None,
) -> None:
    """
    Genera el archivo audioDatabase.js.

    Args:
        secciones:             dict de text_parser.parse_text_file()
                               (necesita 'titulo' y 'titulo_crudo')
        idiomas_seleccionados: lista de dicts del módulo languages
        output_path:           ruta del archivo .js a escribir
        base_url_prefix:       prefijo para las URLs en el JS. Por defecto
                               'BASE_URL + ' (deja la const BASE_URL para
                               que el usuario la defina en su código).
        progress_cb:           callable(msg) opcional
    """
    if not idiomas_seleccionados:
        _log(progress_cb, "No hay idiomas seleccionados para generar el JS.")
        return

    if not secciones:
        _log(progress_cb, "No hay secciones para generar el JS.")
        return

    _log(progress_cb, f"Generando {output_path}...")
    _log(progress_cb, f"Idiomas: {len(idiomas_seleccionados)}  ·  Secciones: {len(secciones)}")

    # Diccionario ordenado: { folder_name: [ {id, title, url}, ... ] }
    db = {}

    total = len(idiomas_seleccionados)
    for idx, idioma in enumerate(idiomas_seleccionados, start=1):
        folder = idioma["folder_name"]
        suffix = idioma["suffix"]
        code = idioma["lang_code"]
        display = idioma["display_name"]

        _log(progress_cb, f"\n[{idx}/{total}] Traduciendo títulos para {display} ({code})...")

        try:
            translator = GoogleTranslator(source="auto", target=code)
        except Exception as e:
            _log(progress_cb, f"  [Error] No se pudo crear traductor para {display}: {e}")
            continue

        items = []
        for num, info in secciones.items():
            raw_title = info.get("titulo_crudo", info.get("titulo", ""))
            slug = info["titulo"]

            translated = _translate_title(translator, raw_title, progress_cb)

            title_str = f"{num}. {translated}"
            filename = f"{num}.{slug}_{suffix}.mp3"

            items.append({
                "id": int(num),
                "title": _escape_js_single(title_str),
                "url_path": f"{folder}/{filename}",
            })

            _log(progress_cb, f"    [{num}] {title_str}")

        db[folder] = items

    # ----- Construcción del JS -----
    lines = []
    lines.append("// Archivo generado automáticamente por audioguias_app.py")
    lines.append("// Define en otro archivo: const BASE_URL = '...';")
    lines.append("")
    lines.append("const audioDatabase = {")

    folders = list(db.keys())
    for i, folder in enumerate(folders):
        is_last_lang = (i == len(folders) - 1)
        lines.append(f"    {folder}: [")

        items = db[folder]
        for j, item in enumerate(items):
            is_last_item = (j == len(items) - 1)
            comma = "" if is_last_item else ","
            url_js = f"{base_url_prefix}'{item['url_path']}'"
            lines.append(
                f"        {{ id: {item['id']}, "
                f"title: '{item['title']}', "
                f"url: {url_js} }}{comma}"
            )

        closing_comma = "" if is_last_lang else ","
        lines.append(f"    ]{closing_comma}")

    lines.append("};")
    lines.append("")

    content = "\n".join(lines)

    # Asegurar que la carpeta destino exista
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    _log(progress_cb, f"\naudioDatabase.js generado: {output_path}")
    _log(progress_cb, f"  {len(folders)} idioma(s), {sum(len(v) for v in db.values())} entradas totales.")
