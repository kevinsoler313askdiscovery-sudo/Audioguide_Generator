"""
Servidor Flask para el pipeline de audioguías · v2.0

Sirve una interfaz web (HTML/CSS/JS) y expone endpoints REST para:
    - Listar los 42 idiomas soportados
    - Subir texto.txt y música de fondo
    - Lanzar el pipeline en un hilo (worker)
    - Streaming de logs en vivo (Server-Sent Events)
    - Descarga del resultado como .zip (auto-borrado tras la descarga)

Ejecuta:
    python audioguias_server.py
    → abre el navegador en http://127.0.0.1:8000

Requiere:
    pip install -r requirements.txt
"""

import json
import os
import queue
import shutil
import threading
import time
import traceback
import uuid
import webbrowser
import zipfile
from datetime import datetime, timedelta

try:
    from flask import Flask, Response, abort, jsonify, render_template, request
except ImportError:
    raise SystemExit(
        "Falta Flask. Instálalo con:\n    pip install -r requirements.txt"
    )

from languages import as_dicts
from text_parser import parse_text_file
import translator as mod_translator
import tts_generator as mod_tts
import audio_mixer as mod_mixer
import js_generator as mod_js


# =====================================================================
# Configuración
# =====================================================================
APP_HOST = os.environ.get("AUDIOGUIAS_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("AUDIOGUIAS_PORT", "8000"))
WORK_ROOT = os.path.abspath(os.environ.get("AUDIOGUIAS_WORK_ROOT", "./_workspace"))

os.makedirs(WORK_ROOT, exist_ok=True)


app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB por upload


# =====================================================================
# Estado en memoria de los trabajos
# =====================================================================
jobs = {}
jobs_lock = threading.Lock()


# =====================================================================
# Utilidades
# =====================================================================
def _new_job():
    job_id = uuid.uuid4().hex[:12]
    output_dir = os.path.join(WORK_ROOT, job_id)
    os.makedirs(output_dir, exist_ok=True)
    with jobs_lock:
        jobs[job_id] = {
            "status": "pending",
            "log_queue": queue.Queue(),
            "output_dir": output_dir,
            "created_at": datetime.now().isoformat(),
            "error": None,
            "zip_path": None,
            "zip_filename": None,
            "zip_size": None,
        }
    return job_id


def _push_log(job_id, msg):
    if job_id in jobs:
        jobs[job_id]["log_queue"].put(msg)


def _close_log(job_id):
    if job_id in jobs:
        jobs[job_id]["log_queue"].put(None)


def _allowed_text(filename):
    return filename.lower().endswith(".txt")


def _allowed_audio(filename):
    return filename.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac"))


def _build_zip(work_dir, zip_path):
    """Empaqueta todo work_dir EXCEPTO el propio zip, texto.txt y music.*"""
    base_zip_name = os.path.basename(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(work_dir):
            for name in files:
                if name == base_zip_name:
                    continue
                if name == "texto.txt":
                    continue
                if name.startswith("music."):
                    continue
                full = os.path.join(root, name)
                arcname = os.path.relpath(full, work_dir)
                zf.write(full, arcname)


def _cleanup_work_dir_keep_zip(work_dir, zip_path):
    """Borra todo en work_dir excepto el zip."""
    base_zip_name = os.path.basename(zip_path)
    for item in os.listdir(work_dir):
        if item == base_zip_name:
            continue
        p = os.path.join(work_dir, item)
        try:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            else:
                os.remove(p)
        except OSError:
            pass


def _delete_job(job_id):
    """Borra la carpeta entera del job + quita del diccionario."""
    with jobs_lock:
        info = jobs.pop(job_id, None)
    if not info:
        return
    work_dir = info.get("output_dir")
    if work_dir and os.path.isdir(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)


def _periodic_cleanup(max_age_hours=2.0, interval_seconds=1800):
    """Daemon que cada interval_seconds elimina jobs > max_age_hours."""
    while True:
        try:
            time.sleep(interval_seconds)
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            stale = []
            with jobs_lock:
                for jid, info in list(jobs.items()):
                    try:
                        created = datetime.fromisoformat(info["created_at"])
                    except Exception:
                        continue
                    if created < cutoff:
                        stale.append(jid)
            for jid in stale:
                _delete_job(jid)
                print(f"[cleanup] Job {jid} eliminado por antiguedad")
        except Exception as e:
            print(f"[cleanup] Error: {e}")


# =====================================================================
# Endpoints
# =====================================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/languages")
def api_languages():
    return jsonify(as_dicts())


@app.route("/api/run", methods=["POST"])
def api_run():
    if "texto" not in request.files:
        return jsonify({"error": "Falta el archivo de texto."}), 400
    texto_file = request.files["texto"]
    if not texto_file or not _allowed_text(texto_file.filename or ""):
        return jsonify({"error": "El archivo de texto debe ser .txt"}), 400

    try:
        languages = json.loads(request.form.get("languages", "[]"))
        steps = json.loads(request.form.get("steps", "{}"))
        config = json.loads(request.form.get("config", "{}"))
    except json.JSONDecodeError as e:
        return jsonify({"error": f"JSON invalido: {e}"}), 400

    if not languages:
        return jsonify({"error": "Selecciona al menos un idioma."}), 400
    if not any(steps.values()):
        return jsonify({"error": "Selecciona al menos un paso."}), 400

    job_id = _new_job()
    job = jobs[job_id]
    work_dir = job["output_dir"]

    texto_path = os.path.join(work_dir, "texto.txt")
    texto_file.save(texto_path)

    music_path = None
    if steps.get("mix"):
        if "music" not in request.files:
            return jsonify({"error": "Falta el archivo de musica para la mezcla."}), 400
        music_file = request.files["music"]
        if not music_file or not _allowed_audio(music_file.filename or ""):
            return jsonify({"error": "La musica debe ser .mp3/.wav/.m4a/.ogg/.flac"}), 400
        music_path = os.path.join(work_dir, "music" + os.path.splitext(music_file.filename)[1])
        music_file.save(music_path)

    all_langs = as_dicts()
    folder_to_lang = {d["folder_name"]: d for d in all_langs}
    idiomas_sel = [folder_to_lang[f] for f in languages if f in folder_to_lang]

    job["status"] = "running"
    threading.Thread(
        target=_pipeline_worker,
        args=(job_id, texto_path, music_path, idiomas_sel, steps, config, work_dir),
        daemon=True,
    ).start()

    return jsonify({"job_id": job_id})


@app.route("/api/logs/<job_id>")
def api_logs(job_id):
    if job_id not in jobs:
        return jsonify({"error": "job no encontrado"}), 404

    def gen():
        q = jobs[job_id]["log_queue"]
        while True:
            try:
                msg = q.get(timeout=15)
            except queue.Empty:
                yield ": heartbeat\n\n"
                continue
            if msg is None:
                status = jobs[job_id]["status"]
                err = jobs[job_id]["error"]
                payload = {"_final": True, "status": status, "error": err}
                yield f"data: {json.dumps(payload)}\n\n"
                return
            yield f"data: {json.dumps({'msg': msg})}\n\n"

    return Response(
        gen(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/download/<job_id>")
def api_download(job_id):
    """Stream del .zip + borrado tras enviar."""
    if job_id not in jobs:
        abort(404)
    job = jobs[job_id]
    zip_path = job.get("zip_path")
    if not zip_path or not os.path.exists(zip_path):
        return jsonify({"error": "El zip aun no esta listo o ya fue descargado"}), 404

    fname = job.get("zip_filename") or f"audioguias_{job_id}.zip"
    total_size = os.path.getsize(zip_path)
    job["status"] = "downloading"

    def stream_and_delete():
        try:
            with open(zip_path, "rb") as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
        finally:
            _delete_job(job_id)

    return Response(
        stream_and_delete(),
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Content-Length": str(total_size),
            "Cache-Control": "no-store",
        },
    )


@app.route("/api/status/<job_id>")
def api_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "job no encontrado"}), 404
    j = jobs[job_id]
    return jsonify({
        "status": j["status"],
        "error": j["error"],
        "zip_size": j.get("zip_size"),
    })


# =====================================================================
# Worker del pipeline
# =====================================================================
def _pipeline_worker(job_id, texto_path, music_path, idiomas_sel,
                     steps, config, work_dir):
    log = lambda m: _push_log(job_id, m)
    try:
        log("=" * 60)
        log(f"Idiomas: {len(idiomas_sel)}  ·  Carpeta: {work_dir}")
        log(f"Pasos: {steps}")
        log("=" * 60)

        log("\nParseando texto.txt...")
        secciones = parse_text_file(texto_path)
        log(f"Secciones detectadas: {len(secciones)}")
        for num, info in secciones.items():
            log(f"  [{num}] {info['titulo']}")

        skip = bool(config.get("skip_existing", True))
        cleanup = not bool(config.get("keep_intermediates", False))

        # 1. Traducción
        if steps.get("translate"):
            log("\n--- PASO 1: Traduccion ---")
            mod_translator.translate_sections(
                secciones=secciones,
                idiomas_seleccionados=idiomas_sel,
                work_dir=work_dir,
                progress_cb=log,
                skip_existing=skip,
            )

        # 2. TTS
        if steps.get("tts"):
            log("\n--- PASO 2: Generacion TTS ---")
            tts_idiomas = [i for i in idiomas_sel if i["voice"]]
            omitidos = [i["display_name"] for i in idiomas_sel if not i["voice"]]
            if omitidos:
                log(f"  Sin voz TTS, se omiten: {', '.join(omitidos)}")
            mod_tts.generate_tts(
                idiomas_seleccionados=tts_idiomas,
                secciones=secciones,
                work_dir=work_dir,
                progress_cb=log,
                skip_existing=skip,
            )

        # 3. Mezcla con música
        if steps.get("mix"):
            log("\n--- PASO 3: Mezcla con musica (Pedalboard) ---")
            mod_mixer.mix_with_music(
                idiomas_seleccionados=idiomas_sel,
                secciones=secciones,
                music_path=music_path,
                work_dir=work_dir,
                music_volume_db=float(config.get("music_volume_db", -9)),
                fade_seconds=float(config.get("fade_seconds", 5)),
                progress_cb=log,
                skip_existing=skip,
                cleanup_intermediates=cleanup,
            )

        # 4. audioDatabase.js
        if steps.get("generate_js"):
            log("\n--- PASO 4: Generacion audioDatabase.js ---")
            js_path = os.path.join(work_dir, "audioDatabase.js")
            mod_js.generate_database(
                secciones=secciones,
                idiomas_seleccionados=idiomas_sel,
                output_path=js_path,
                base_url_prefix=config.get("js_base_url_prefix", "BASE_URL + "),
                progress_cb=log,
            )

        # 5. Empaquetar resultado y limpiar intermedios
        log("\n--- EMPAQUETANDO RESULTADO ---")
        zip_filename = f"audioguias_{job_id}.zip"
        zip_path = os.path.join(work_dir, zip_filename)
        _build_zip(work_dir, zip_path)
        zip_size = os.path.getsize(zip_path)
        log(f"  Creado: {zip_filename}  ({zip_size / (1024*1024):.1f} MB)")

        log("  Limpiando archivos intermedios del servidor...")
        _cleanup_work_dir_keep_zip(work_dir, zip_path)
        log("  Solo se conserva el .zip hasta que lo descargues.")

        jobs[job_id]["zip_path"] = zip_path
        jobs[job_id]["zip_filename"] = zip_filename
        jobs[job_id]["zip_size"] = zip_size

        log("\n" + "=" * 60)
        log("PROCESO COMPLETADO")
        log("=" * 60)
        jobs[job_id]["status"] = "done"
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        log(f"\n[ERROR] {e}")
        log(traceback.format_exc())
    finally:
        _close_log(job_id)


# =====================================================================
# Entry point
# =====================================================================
def main():
    print(f"\n[Audioguias v2.0] servidor en http://{APP_HOST}:{APP_PORT}")
    print(f"   Workspace: {WORK_ROOT}")
    print(f"   Limpieza automatica de jobs > 4h cada 90 minutos.")
    print(f"   Pulsa Ctrl+C para detener.\n")

    threading.Thread(
        target=_periodic_cleanup,
        kwargs={"max_age_hours": 4.0, "interval_seconds": 5400},
        daemon=True,
    ).start()

    if APP_HOST in ("127.0.0.1", "localhost"):
        try:
            webbrowser.open(f"http://{APP_HOST}:{APP_PORT}")
        except Exception:
            pass
    app.run(host=APP_HOST, port=APP_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
