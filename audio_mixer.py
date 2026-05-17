"""
Módulo de mezcla de audio con música de fondo · v2.0

Implementación 100% en Python con Pedalboard (Spotify) + numpy.
Sin dependencias externas: el paquete `pedalboard` trae embebido todo
lo necesario para leer/escribir MP3, WAV, OGG, FLAC.

Para cada idioma seleccionado, toma cada '<num>.mp3' generado por TTS
(que vive en 'work_dir/<folder_name>/') y lo mezcla con la pista de
música de fondo, aplicando:
    - Reducción de volumen de la música (configurable, default -9 dB)
    - Fade-out de la música al final (configurable, default 5 s)
    - Limitador final para evitar clipping (umbral -0.5 dB)
    - Exportación a MP3 320 kbps / 48 kHz / estéreo

El archivo final se escribe en la MISMA carpeta:
    'work_dir/<folder_name>/<num>.<titulo>_<suffix>.mp3'

Tras una mezcla exitosa, los archivos intermedios (<num>.txt y <num>.mp3)
se eliminan por defecto.

OPTIMIZACIONES v2.0:
    - La música se carga UNA sola vez al iniciar el paso (no se relee por sección).
    - El archivo de salida se escribe vía file handle binario, para evitar
      problemas de validación de path string en algunas versiones de Pedalboard
      sobre Windows.
"""

import os
import numpy as np

try:
    from pedalboard import Pedalboard, Limiter
    from pedalboard.io import AudioFile
except ImportError as e:
    raise ImportError(
        "Falta la librería 'pedalboard'. Instálala con: pip install pedalboard"
    ) from e


# Configuración por defecto
DEFAULT_MUSIC_VOLUME_DB = -9
DEFAULT_FADE_SECONDS = 5
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_BITRATE_KBPS = 320
DEFAULT_LIMITER_THRESHOLD_DB = -0.5


def _log(progress_cb, msg):
    print(msg)
    if progress_cb:
        progress_cb(msg)


def _read_audio(path, target_sr):
    """
    Lee un archivo de audio y devuelve ndarray float32 (channels, n_frames)
    resampleado al sample rate destino.
    """
    with AudioFile(path).resampled_to(target_sr) as f:
        data = f.read(f.frames)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return data.astype(np.float32)


def _ensure_stereo(samples):
    """Duplica una pista mono a estéreo si hace falta."""
    if samples.shape[0] == 1:
        return np.vstack([samples, samples])
    return samples


def _pad_or_truncate(samples, total_samples):
    """Ajusta una pista a exactamente `total_samples` rellenando con silencio
    o truncando si fuera más larga."""
    cur = samples.shape[1]
    if cur < total_samples:
        return np.pad(samples, ((0, 0), (0, total_samples - cur)), mode="constant")
    elif cur > total_samples:
        return samples[:, :total_samples]
    return samples


def _apply_fade_out(samples, fade_start_sample, fade_samples):
    """Fade-out lineal entre fade_start_sample y fade_start_sample+fade_samples."""
    end = min(fade_start_sample + fade_samples, samples.shape[1])
    actual_fade = end - fade_start_sample
    if actual_fade <= 0:
        return samples
    ramp = np.linspace(1.0, 0.0, actual_fade, dtype=np.float32)
    samples[:, fade_start_sample:end] *= ramp
    if end < samples.shape[1]:
        samples[:, end:] = 0.0
    return samples


def _write_mp3(output_path, samples, sample_rate, bitrate_kbps):
    """
    Escribe un MP3 usando un file handle binario.
    Workaround para versiones de Pedalboard que en Windows rechazan paths string.
    """
    n_channels = samples.shape[0]
    with open(output_path, "wb") as raw:
        with AudioFile(
            raw,
            "w",
            samplerate=sample_rate,
            num_channels=n_channels,
            format="mp3",
            quality=float(bitrate_kbps),
        ) as f:
            f.write(samples)


def _mix_one_section(voice_path, music_full, output_path,
                     music_volume_db, fade_seconds, sample_rate,
                     bitrate_kbps, limiter_threshold_db):
    """
    Mezcla una pista de voz con la música ya cargada en memoria
    y exporta el resultado a MP3.
    """
    # 1. Leer voz (resampleando si hace falta)
    voice = _read_audio(voice_path, sample_rate)
    voice = _ensure_stereo(voice)

    # 2. Calcular duraciones
    voice_samples = voice.shape[1]
    fade_samples = int(fade_seconds * sample_rate)
    total_samples = voice_samples + fade_samples

    # 3. Voz: padding con silencio al final hasta total_samples
    voice_padded = _pad_or_truncate(voice, total_samples)

    # 4. Música: copia, ajuste a total_samples, gain, fade-out
    music = _pad_or_truncate(music_full, total_samples).copy()
    gain_factor = 10 ** (music_volume_db / 20.0)
    music = music * gain_factor
    music = _apply_fade_out(music, voice_samples, fade_samples)

    # 5. Mezcla
    mixed = voice_padded + music

    # 6. Limitador
    board = Pedalboard([Limiter(threshold_db=limiter_threshold_db, release_ms=100)])
    mixed = board(mixed, sample_rate)

    # 7. Exportar MP3
    _write_mp3(output_path, mixed, sample_rate, bitrate_kbps)


def _cleanup_intermediates(folder, num, progress_cb):
    """Elimina '<num>.txt' y '<num>.mp3' dentro de 'folder' si existen."""
    for ext in (".txt", ".mp3"):
        path = os.path.join(folder, f"{num}{ext}")
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                _log(progress_cb, f"  [Aviso] No se pudo borrar {path}: {e}")


def mix_with_music(idiomas_seleccionados, secciones, music_path,
                   work_dir="audios_finales",
                   music_volume_db=DEFAULT_MUSIC_VOLUME_DB,
                   fade_seconds=DEFAULT_FADE_SECONDS,
                   sample_rate=DEFAULT_SAMPLE_RATE,
                   bitrate_kbps=DEFAULT_BITRATE_KBPS,
                   progress_cb=None,
                   skip_existing=True,
                   cleanup_intermediates=True):
    """
    Mezcla los audios TTS con música de fondo (Pedalboard, sin FFmpeg externo).
    """
    if not idiomas_seleccionados:
        _log(progress_cb, "No hay idiomas seleccionados para mezclar.")
        return

    if not os.path.exists(music_path):
        raise FileNotFoundError(f"No existe el archivo de música: {music_path}")

    _log(progress_cb, f"Música: {music_path}")
    _log(progress_cb, f"Volumen música: {music_volume_db} dB · Fade: {fade_seconds}s")
    _log(progress_cb, f"Sample rate: {sample_rate} Hz · MP3: {bitrate_kbps} kbps")
    _log(progress_cb, f"Limpiar intermedios tras mezclar: {cleanup_intermediates}")

    # ---- Cargar la música UNA sola vez (optimización clave) ----
    _log(progress_cb, "Cargando música de fondo en memoria...")
    music_full = _read_audio(music_path, sample_rate)
    music_full = _ensure_stereo(music_full)
    music_dur = music_full.shape[1] / sample_rate
    _log(progress_cb, f"  Duración música: {music_dur:.1f}s · canales: {music_full.shape[0]}")

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

        seccion_ok = []

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
                seccion_ok.append(num)
                continue

            _log(progress_cb, f"  Generando {output_filename}...")
            try:
                _mix_one_section(
                    voice_path=voice_path,
                    music_full=music_full,
                    output_path=output_path,
                    music_volume_db=music_volume_db,
                    fade_seconds=fade_seconds,
                    sample_rate=sample_rate,
                    bitrate_kbps=bitrate_kbps,
                    limiter_threshold_db=DEFAULT_LIMITER_THRESHOLD_DB,
                )
                seccion_ok.append(num)
            except Exception as e:
                _log(progress_cb, f"  [Error] {output_filename}: {e}")

        if cleanup_intermediates and seccion_ok:
            _log(progress_cb, f"  Limpiando intermedios de {display}...")
            for num in seccion_ok:
                _cleanup_intermediates(lang_folder, num, progress_cb)

    _log(progress_cb, "\nMezcla con música completada.")
