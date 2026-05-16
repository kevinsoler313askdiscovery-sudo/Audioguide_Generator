"""
Módulo de mezcla de audio con música de fondo (vía FFmpeg).

Para cada idioma seleccionado, toma cada '<num>.mp3' generado por TTS
(que vive en 'work_dir/<folder_name>/') y lo mezcla con una pista de
música de fondo, aplicando:
    - Reducción de volumen de la música (configurable, default -9 dB)
    - Fade-out de la música al final (configurable, default 5 s)
    - Limitador final para evitar clipping
    - Exportación a MP3 320 kbps / 48 kHz / estéreo

El archivo final se escribe en la MISMA carpeta:
    'work_dir/<folder_name>/<num>.<titulo>_<suffix>.mp3'

Tras una mezcla exitosa, los archivos intermedios (<num>.txt y <num>.mp3)
se eliminan por defecto, dejando la carpeta limpia con solo los .mp3 finales.
"""

import os
import json
import shutil
import subprocess


# Configuración por defecto (puede sobreescribirse desde la GUI)
DEFAULT_MUSIC_VOLUME_DB = -9
DEFAULT_FADE_SECONDS = 5


def _log(progress_cb, msg):
    print(msg)
    if progress_cb:
        progress_cb(msg)


def _resolve_ffmpeg_binaries(ffmpeg_path=None, ffprobe_path=None):
    """
    Localiza los ejecutables de ffmpeg/ffprobe.

    Orden de búsqueda:
        1. Rutas explícitas (argumentos).
        2. PATH del sistema (shutil.which).
        3. Ubicación típica en Windows: C:\\ffmpeg-master-latest-win64-gpl-shared\\bin\\

    Lanza FileNotFoundError si no los encuentra.
    """
    candidates_ffmpeg = [
        ffmpeg_path,
        shutil.which("ffmpeg"),
        r"C:\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe",
    ]
    candidates_ffprobe = [
        ffprobe_path,
        shutil.which("ffprobe"),
        r"C:\ffmpeg-master-latest-win64-gpl-shared\bin\ffprobe.exe",
    ]

    ffmpeg = next((p for p in candidates_ffmpeg if p and os.path.exists(p)), None)
    ffprobe = next((p for p in candidates_ffprobe if p and os.path.exists(p)), None)

    if not ffmpeg:
        raise FileNotFoundError(
            "No se encontró ffmpeg. Instálalo y añádelo al PATH, o pasa "
            "la ruta explícita en 'ffmpeg_path'."
        )
    if not ffprobe:
        raise FileNotFoundError(
            "No se encontró ffprobe. Suele venir con ffmpeg en la misma carpeta /bin."
        )

    return ffmpeg, ffprobe


def _get_audio_duration(ffprobe: str, file_path: str) -> float:
    """Devuelve la duración del audio en segundos usando ffprobe."""
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(result.stdout)["format"]["duration"])


def _cleanup_intermediates(folder: str, num: str, progress_cb):
    """Elimina '<num>.txt' y '<num>.mp3' dentro de 'folder' si existen."""
    for ext in (".txt", ".mp3"):
        path = os.path.join(folder, f"{num}{ext}")
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                _log(progress_cb, f"  [Aviso] No se pudo borrar {path}: {e}")


def mix_with_music(
    idiomas_seleccionados: list,
    secciones: dict,
    music_path: str,
    work_dir: str = "audios_finales",
    music_volume_db: float = DEFAULT_MUSIC_VOLUME_DB,
    fade_seconds: float = DEFAULT_FADE_SECONDS,
    ffmpeg_path: str = None,
    ffprobe_path: str = None,
    progress_cb=None,
    skip_existing: bool = True,
    cleanup_intermediates: bool = True,
) -> None:
    """
    Mezcla los audios TTS con música de fondo y los exporta con nombres descriptivos
    en la MISMA carpeta del idioma. Tras éxito, opcionalmente elimina los archivos
    intermedios (.txt y .mp3 sin música).

    Args:
        idiomas_seleccionados:  lista de dicts del módulo languages
        secciones:              dict de text_parser.parse_text_file()
        music_path:             ruta al .mp3 de música de fondo
        work_dir:               carpeta raíz donde están work_dir/<folder_name>/
                                con los .txt y .mp3 intermedios
        music_volume_db:        volumen relativo de la música (dB, negativo = más bajo)
        fade_seconds:           duración del fade-out final de la música
        ffmpeg_path / ffprobe_path: rutas explícitas (opcional)
        progress_cb:            callable(msg) opcional
        skip_existing:          si True, no rehace archivos finales ya presentes
        cleanup_intermediates:  si True, borra '<num>.txt' y '<num>.mp3' tras
                                generar el final con música
    """
    if not idiomas_seleccionados:
        _log(progress_cb, "No hay idiomas seleccionados para mezclar.")
        return

    if not os.path.exists(music_path):
        raise FileNotFoundError(f"No existe el archivo de música: {music_path}")

    ffmpeg, ffprobe = _resolve_ffmpeg_binaries(ffmpeg_path, ffprobe_path)
    _log(progress_cb, f"FFmpeg: {ffmpeg}")
    _log(progress_cb, f"FFprobe: {ffprobe}")
    _log(progress_cb, f"Música: {music_path}")
    _log(progress_cb, f"Volumen música: {music_volume_db} dB · Fade: {fade_seconds}s")
    _log(progress_cb, f"Limpiar intermedios tras mezclar: {cleanup_intermediates}")

    os.makedirs(work_dir, exist_ok=True)
    total = len(idiomas_seleccionados)

    for idx, idioma in enumerate(idiomas_seleccionados, start=1):
        folder = idioma["folder_name"]
        suffix = idioma["suffix"]
        display = idioma["display_name"]

        lang_folder = os.path.join(work_dir, folder)
        _log(progress_cb, f"\n[{idx}/{total}] Mezclando · {display} (sufijo: _{suffix})")

        if not os.path.isdir(lang_folder):
            _log(progress_cb, f"  [Aviso] Carpeta inexistente: {lang_folder}. Saltando.")
            continue

        seccion_ok = []  # números de sección que se mezclaron correctamente

        for num, info in secciones.items():
            voice_path = os.path.join(lang_folder, f"{num}.mp3")
            if not os.path.exists(voice_path):
                _log(progress_cb, f"  [Aviso] No existe {voice_path}. Saltando sección {num}.")
                continue

            titulo = info["titulo"]
            output_filename = f"{num}.{titulo}_{suffix}.mp3"
            output_path = os.path.join(lang_folder, output_filename)

            if skip_existing and os.path.exists(output_path):
                _log(progress_cb, f"  {output_filename}: ya existe, se omite")
                seccion_ok.append(num)  # también marcamos para limpieza
                continue

            try:
                duration_voice = _get_audio_duration(ffprobe, voice_path)
            except Exception as e:
                _log(progress_cb, f"  [Error] No se pudo medir duración de {voice_path}: {e}")
                continue

            fade_start = duration_voice

            filter_complex = (
                f"[1:a]"
                f"aresample=resampler=soxr:precision=28:dither_method=triangular,"
                f"volume={music_volume_db}dB,"
                f"apad,"
                f"afade=t=out:st={fade_start}:d={fade_seconds},"
                f"volume={music_volume_db}dB"
                f"[music];"
                f"[0:a]aresample=resampler=soxr:precision=28:dither_method=triangular[voice];"
                f"[voice][music]"
                f"amix=inputs=2:dropout_transition=0:duration=longest,"
                f"alimiter=limit=0.95"
            )

            ffmpeg_cmd = [
                ffmpeg,
                "-i", voice_path,
                "-i", music_path,
                "-filter_complex", filter_complex,
                "-t", str(duration_voice + fade_seconds),
                "-c:a", "libmp3lame",
                "-b:a", "320k",
                "-ar", "48000",
                "-ac", "2",
                "-compression_level", "0",
                "-y",
                output_path,
            ]

            _log(progress_cb, f"  Generando {output_filename}...")
            try:
                subprocess.run(
                    ffmpeg_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                seccion_ok.append(num)
            except subprocess.CalledProcessError as e:
                _log(progress_cb, f"  [Error] ffmpeg falló en {output_filename}:")
                _log(progress_cb, e.stderr[-400:] if e.stderr else str(e))

        # Limpieza de intermedios tras éxito
        if cleanup_intermediates and seccion_ok:
            _log(progress_cb, f"  Limpiando intermedios de {display}...")
            for num in seccion_ok:
                _cleanup_intermediates(lang_folder, num, progress_cb)

    _log(progress_cb, "\nMezcla con música completada.")
