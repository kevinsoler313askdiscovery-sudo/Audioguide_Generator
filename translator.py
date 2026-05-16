"""
Módulo de traducción.

Traduce las secciones del guion a los idiomas seleccionados y guarda
cada sección como '<numero>.txt' dentro de 'work_dir/<folder_name>/'.

Uso desde la GUI:
    translate_sections(
        secciones={'1': {...}, '2': {...}},
        idiomas_seleccionados=[lang_dict, lang_dict, ...],
        work_dir='audios_finales',
        progress_cb=lambda msg: print(msg),
    )

`secciones` es la salida de text_parser.parse_text_file().
`idiomas_seleccionados` es una lista de dicts del módulo languages.
`progress_cb(msg)` es una función opcional para reportar progreso a la GUI.
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
    """Reporta progreso al callback si existe, también a stdout."""
    print(msg)
    if progress_cb:
        progress_cb(msg)


def _final_filename(num: str, titulo: str, suffix: str) -> str:
    """Construye el nombre del archivo final con música. Sirve para 'skip_existing'."""
    return f"{num}.{titulo}_{suffix}.mp3"


def translate_sections(
    secciones: dict,
    idiomas_seleccionados: list,
    work_dir: str = "audios_finales",
    progress_cb=None,
    skip_existing: bool = True,
) -> None:
    """
    Traduce todas las secciones a todos los idiomas seleccionados.

    Args:
        secciones:             dict {numero: {'titulo': ..., 'contenido': ...}}
        idiomas_seleccionados: list de dicts con keys folder_name, lang_code, ...
        work_dir:              carpeta raíz donde se crean las subcarpetas por idioma
        progress_cb:           callable(msg) opcional para reportar progreso
        skip_existing:         si True, no retraduce secciones cuyo archivo final
                               (con música) ya existe; también omite los .txt que
                               ya existan
    """
    os.makedirs(work_dir, exist_ok=True)

    total_idiomas = len(idiomas_seleccionados)
    _log(progress_cb, f"Iniciando traducción a {total_idiomas} idioma(s)...")

    for idx, idioma in enumerate(idiomas_seleccionados, start=1):
        folder = idioma["folder_name"]
        code = idioma["lang_code"]
        suffix = idioma["suffix"]
        display = idioma["display_name"]

        lang_dir = os.path.join(work_dir, folder)
        os.makedirs(lang_dir, exist_ok=True)

        _log(progress_cb, f"\n[{idx}/{total_idiomas}] Traduciendo a {display} ({code})...")

        try:
            translator = GoogleTranslator(source="auto", target=code)
        except Exception as e:
            _log(progress_cb, f"  [Error] No se pudo inicializar el traductor para {display}: {e}")
            continue

        for num, info in secciones.items():
            texto = info["contenido"]
            if not texto:
                continue

            output_file = os.path.join(lang_dir, f"{num}.txt")
            final_audio = os.path.join(lang_dir, _final_filename(num, info["titulo"], suffix))

            if skip_existing and os.path.exists(final_audio):
                _log(progress_cb, f"  Sección {num}: el audio final ya existe, se omite")
                continue
            if skip_existing and os.path.exists(output_file):
                _log(progress_cb, f"  Sección {num}: .txt ya existe, se omite")
                continue

            _log(progress_cb, f"  Traduciendo sección {num}...")
            try:
                texto_traducido = translator.translate(texto)
            except Exception as e:
                _log(progress_cb, f"  [Error] Sección {num}: {e}")
                texto_traducido = texto  # fallback: guardar original

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(texto_traducido or "")

    _log(progress_cb, "\nTraducción completada.")
