"""
Módulo de generación de voz (Text-to-Speech) con edge-tts.

Para cada idioma seleccionado, lee los archivos '<num>.txt' de
'work_dir/<folder_name>/' y genera el correspondiente '<num>.mp3'.

Idiomas sin voz disponible (ej: Vasco/Basque) se omiten con un warning.
"""

import os
import asyncio

try:
    import edge_tts
except ImportError as e:
    raise ImportError(
        "Falta la librería 'edge-tts'. Instálala con: pip install edge-tts"
    ) from e


# Configuración de la voz (ajustable)
RATE = "+0%"     # Velocidad
VOLUME = "+0%"   # Volumen
PITCH = "+0Hz"   # Tono


def _log(progress_cb, msg):
    print(msg)
    if progress_cb:
        progress_cb(msg)


def _final_filename(num: str, titulo: str, suffix: str) -> str:
    """Construye el nombre del archivo final con música. Sirve para 'skip_existing'."""
    return f"{num}.{titulo}_{suffix}.mp3"


async def _generate_audio(text: str, voice: str, output_path: str):
    """Genera un .mp3 a partir de texto usando edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate=RATE, volume=VOLUME, pitch=PITCH)
    await communicate.save(output_path)


async def _process_language(idioma: dict, secciones: dict, work_dir: str,
                            progress_cb, skip_existing: bool):
    """Procesa todos los .txt de un idioma generando los .mp3."""
    folder = idioma["folder_name"]
    voice = idioma["voice"]
    suffix = idioma["suffix"]
    display = idioma["display_name"]

    folder_path = os.path.join(work_dir, folder)
    if not os.path.isdir(folder_path):
        _log(progress_cb, f"  [Aviso] Carpeta no existe: {folder_path}. Saltando {display}.")
        return

    if not voice:
        _log(progress_cb, f"  [Aviso] {display} no tiene voz TTS disponible. Saltando.")
        return

    _log(progress_cb, f"\n=== TTS · {display}  (voz: {voice}) ===")

    # Si tenemos secciones, iteramos por número para usarlo en el skip
    if secciones:
        items = list(secciones.items())
    else:
        # Fallback: leer del disco si no se pasaron secciones
        txt_files = [f for f in os.listdir(folder_path) if f.endswith(".txt")]
        txt_files.sort(
            key=lambda x: int(os.path.splitext(x)[0])
            if os.path.splitext(x)[0].isdigit()
            else 0
        )
        items = [(os.path.splitext(f)[0], None) for f in txt_files]

    for num, info in items:
        file_path = os.path.join(folder_path, f"{num}.txt")
        output_path = os.path.join(folder_path, f"{num}.mp3")

        # Si ya existe el audio FINAL con música, saltamos todo
        if info and skip_existing:
            final_audio = os.path.join(
                folder_path, _final_filename(num, info["titulo"], suffix)
            )
            if os.path.exists(final_audio):
                _log(progress_cb, f"  Sección {num}: audio final ya existe, se omite")
                continue

        if skip_existing and os.path.exists(output_path):
            _log(progress_cb, f"  {num}.mp3: ya existe, se omite")
            continue

        if not os.path.exists(file_path):
            _log(progress_cb, f"  [Aviso] No existe {file_path}. Saltando.")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().strip()

        if not text:
            _log(progress_cb, f"  {num}.txt: vacío, se omite")
            continue

        _log(progress_cb, f"  Generando {num}.mp3...")
        try:
            await _generate_audio(text, voice, output_path)
        except Exception as e:
            _log(progress_cb, f"  [Error] {num}.txt: {e}")


async def _run(idiomas_seleccionados, secciones, work_dir, progress_cb, skip_existing):
    for idioma in idiomas_seleccionados:
        await _process_language(idioma, secciones, work_dir, progress_cb, skip_existing)


def generate_tts(
    idiomas_seleccionados: list,
    secciones: dict = None,
    work_dir: str = "audios_finales",
    progress_cb=None,
    skip_existing: bool = True,
) -> None:
    """
    Punto de entrada síncrono para usar desde la GUI.

    Args:
        idiomas_seleccionados: lista de dicts del módulo languages
        secciones:             dict de text_parser.parse_text_file() (opcional)
                               Si se pasa, se usa para detectar si el audio final
                               ya existe y omitir TTS.
        work_dir:              carpeta raíz donde están las subcarpetas con los .txt
        progress_cb:           callable(msg) opcional
        skip_existing:         si True, no regenera .mp3 que ya existen
    """
    if not idiomas_seleccionados:
        _log(progress_cb, "No hay idiomas seleccionados para TTS.")
        return

    _log(progress_cb, f"Iniciando TTS para {len(idiomas_seleccionados)} idioma(s)...")
    asyncio.run(_run(
        idiomas_seleccionados, secciones, work_dir, progress_cb, skip_existing
    ))
    _log(progress_cb, "\nGeneración de TTS completada.")
