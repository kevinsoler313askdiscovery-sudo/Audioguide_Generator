"""
Interfaz gráfica del pipeline de audioguías.

Permite:
  1. Seleccionar el archivo texto.txt con el guion en español.
  2. Seleccionar la música de fondo (.mp3).
  3. Elegir qué pasos ejecutar (Traducir / TTS / Mezclar).
  4. Marcar qué idiomas procesar (de los 42 soportados).
  5. Ajustar volumen y fade-out de la música.
  6. Decidir si conservar archivos intermedios (.txt y .mp3 sin música).
  7. Ver los logs en vivo.

Ejecuta:
    python audioguias_app.py

Requiere:
    pip install customtkinter deep-translator edge-tts
    + FFmpeg disponible en PATH (o en C:\\ffmpeg-master-latest-win64-gpl-shared\\bin\\)
"""

import os
import queue
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    raise SystemExit(
        "Falta CustomTkinter. Instálalo con:\n    pip install customtkinter"
    )

from languages import as_dicts
from text_parser import parse_text_file
import translator as mod_translator
import tts_generator as mod_tts
import audio_mixer as mod_mixer
import js_generator as mod_js


# =====================================================================
# Apariencia
# =====================================================================
ctk.set_appearance_mode("System")     # "Light" / "Dark" / "System"
ctk.set_default_color_theme("blue")


# =====================================================================
# Aplicación principal
# =====================================================================
class AudioguiasApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Audioguías · Pipeline multilenguaje")
        self.geometry("1100x740")
        self.minsize(950, 600)

        # Estado interno
        self.texto_path = ctk.StringVar(value="")
        self.music_path = ctk.StringVar(value="")
        self.work_dir = ctk.StringVar(value="audios_finales")

        self.step_translate = ctk.BooleanVar(value=True)
        self.step_tts = ctk.BooleanVar(value=True)
        self.step_mix = ctk.BooleanVar(value=True)
        self.step_generate_js = ctk.BooleanVar(value=True)
        self.skip_existing = ctk.BooleanVar(value=True)
        self.keep_intermediates = ctk.BooleanVar(value=False)

        self.js_output_path = ctk.StringVar(value="")  # vacío = <work_dir>/audioDatabase.js
        self.js_base_url_prefix = ctk.StringVar(value="BASE_URL + ")

        self.music_volume_db = ctk.StringVar(value="-9")
        self.fade_seconds = ctk.StringVar(value="5")

        self.lang_data = as_dicts()
        self.lang_vars: list = []   # tuplas (BooleanVar, dict)

        self.log_queue: queue.Queue = queue.Queue()
        self.worker_thread = None

        self._build_layout()
        self._poll_log_queue()

    # -----------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------
    def _build_layout(self):
        # Configuración del grid raíz: 2 columnas
        self.grid_columnconfigure(0, weight=0, minsize=520)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----- Columna izquierda: controles -----
        left = ctk.CTkScrollableFrame(self, label_text="Configuración")
        left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        self._build_files_section(left)
        self._build_steps_section(left)
        self._build_mix_section(left)
        self._build_js_section(left)
        self._build_languages_section(left)
        self._build_execute_section(left)

        # ----- Columna derecha: logs -----
        right = ctk.CTkFrame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(right, text="Registro", font=ctk.CTkFont(size=14, weight="bold"))\
            .grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        self.log_text = ctk.CTkTextbox(right, wrap="word", font=("Consolas", 11))
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.log_text.configure(state="disabled")

    # ----- Secciones -----
    def _build_files_section(self, parent):
        box = ctk.CTkFrame(parent)
        box.pack(fill="x", padx=4, pady=(4, 8))
        box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(box, text="texto.txt:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkEntry(box, textvariable=self.texto_path).grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkButton(box, text="Examinar", width=90,
                      command=self._pick_texto).grid(row=0, column=2, padx=8, pady=6)

        ctk.CTkLabel(box, text="Música:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkEntry(box, textvariable=self.music_path).grid(row=1, column=1, sticky="ew", padx=4)
        ctk.CTkButton(box, text="Examinar", width=90,
                      command=self._pick_music).grid(row=1, column=2, padx=8, pady=6)

        ctk.CTkLabel(box, text="Carpeta de trabajo:").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkEntry(box, textvariable=self.work_dir).grid(row=2, column=1, sticky="ew", padx=4)
        ctk.CTkButton(box, text="Examinar", width=90,
                      command=lambda: self._pick_folder(self.work_dir))\
            .grid(row=2, column=2, padx=8, pady=6)

        ctk.CTkLabel(
            box,
            text=("Dentro de la carpeta de trabajo se creará una subcarpeta por idioma\n"
                  "(german/, english/, korean/, ...) con los .mp3 finales con música."),
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

    def _build_steps_section(self, parent):
        box = ctk.CTkFrame(parent)
        box.pack(fill="x", padx=4, pady=(4, 8))
        ctk.CTkLabel(box, text="Pasos a ejecutar",
                     font=ctk.CTkFont(size=13, weight="bold"))\
            .grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 2))

        ctk.CTkCheckBox(box, text="1. Traducir", variable=self.step_translate)\
            .grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkCheckBox(box, text="2. Generar TTS", variable=self.step_tts)\
            .grid(row=1, column=1, sticky="w", padx=8, pady=4)
        ctk.CTkCheckBox(box, text="3. Mezclar con música", variable=self.step_mix)\
            .grid(row=1, column=2, sticky="w", padx=8, pady=4)
        ctk.CTkCheckBox(box, text="4. Generar audioDatabase.js",
                        variable=self.step_generate_js)\
            .grid(row=1, column=3, sticky="w", padx=8, pady=4)

        ctk.CTkCheckBox(box, text="Omitir archivos ya existentes (más rápido)",
                        variable=self.skip_existing)\
            .grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 2))

        ctk.CTkCheckBox(
            box,
            text="Conservar archivos intermedios (.txt y .mp3 sin música)",
            variable=self.keep_intermediates,
        ).grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 8))

    def _build_mix_section(self, parent):
        box = ctk.CTkFrame(parent)
        box.pack(fill="x", padx=4, pady=(4, 8))
        ctk.CTkLabel(box, text="Configuración de mezcla",
                     font=ctk.CTkFont(size=13, weight="bold"))\
            .grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 2))

        ctk.CTkLabel(box, text="Volumen música (dB):").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(box, textvariable=self.music_volume_db, width=80)\
            .grid(row=1, column=1, sticky="w", padx=4)

        ctk.CTkLabel(box, text="Fade-out (segundos):").grid(row=1, column=2, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(box, textvariable=self.fade_seconds, width=80)\
            .grid(row=1, column=3, sticky="w", padx=4, pady=(0, 8))

    def _build_js_section(self, parent):
        box = ctk.CTkFrame(parent)
        box.pack(fill="x", padx=4, pady=(4, 8))
        box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(box, text="audioDatabase.js (paso 4)",
                     font=ctk.CTkFont(size=13, weight="bold"))\
            .grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 2))

        ctk.CTkLabel(box, text="Archivo .js:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(box, textvariable=self.js_output_path,
                     placeholder_text="(vacío → <work_dir>/audioDatabase.js)")\
            .grid(row=1, column=1, sticky="ew", padx=4)
        ctk.CTkButton(box, text="Examinar", width=90,
                      command=self._pick_js_output).grid(row=1, column=2, padx=8, pady=4)

        ctk.CTkLabel(box, text="Prefijo URL:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        ctk.CTkEntry(box, textvariable=self.js_base_url_prefix)\
            .grid(row=2, column=1, columnspan=2, sticky="ew", padx=4, pady=(0, 4))

        ctk.CTkLabel(
            box,
            text=("'BASE_URL + ' deja la variable JS sin tocar (recomendado).\n"
                  "Reemplázalo por '\"https://miservidor.com/\" + ' si quieres URLs absolutas."),
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 6))

    def _build_languages_section(self, parent):
        box = ctk.CTkFrame(parent)
        box.pack(fill="both", expand=True, padx=4, pady=(4, 8))

        header = ctk.CTkFrame(box, fg_color="transparent")
        header.pack(fill="x", padx=4, pady=(6, 2))
        ctk.CTkLabel(header, text="Idiomas",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=4)
        ctk.CTkButton(header, text="Todos", width=70,
                      command=self._select_all_langs).pack(side="right", padx=2)
        ctk.CTkButton(header, text="Ninguno", width=70,
                      command=self._select_no_langs).pack(side="right", padx=2)

        # Grid de checkboxes en 2 columnas
        grid = ctk.CTkFrame(box, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=4, pady=4)
        cols = 2
        for idx, lang in enumerate(self.lang_data):
            var = ctk.BooleanVar(value=False)
            row, col = divmod(idx, cols)
            label = f"{lang['display_name']}  ·  {lang['folder_name']}"
            if lang["voice"] is None:
                label += "  (sin TTS)"
            cb = ctk.CTkCheckBox(grid, text=label, variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=8, pady=2)
            self.lang_vars.append((var, lang))

        for c in range(cols):
            grid.grid_columnconfigure(c, weight=1)

    def _build_execute_section(self, parent):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", padx=4, pady=(8, 4))
        self.run_button = ctk.CTkButton(
            box, text="▶  EJECUTAR", height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_run_clicked,
        )
        self.run_button.pack(fill="x", padx=4, pady=4)

    # -----------------------------------------------------------------
    # Acciones de UI
    # -----------------------------------------------------------------
    def _pick_texto(self):
        path = filedialog.askopenfilename(
            title="Selecciona el texto.txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
        )
        if path:
            self.texto_path.set(path)

    def _pick_music(self):
        path = filedialog.askopenfilename(
            title="Selecciona la música de fondo",
            filetypes=[("Audio MP3", "*.mp3"), ("Audio", "*.mp3 *.wav *.m4a"), ("Todos", "*.*")],
        )
        if path:
            self.music_path.set(path)

    def _pick_folder(self, var: ctk.StringVar):
        path = filedialog.askdirectory(title="Selecciona la carpeta")
        if path:
            var.set(path)

    def _pick_js_output(self):
        path = filedialog.asksaveasfilename(
            title="Guardar audioDatabase.js como...",
            defaultextension=".js",
            initialfile="audioDatabase.js",
            filetypes=[("JavaScript", "*.js"), ("Todos", "*.*")],
        )
        if path:
            self.js_output_path.set(path)

    def _select_all_langs(self):
        for var, _ in self.lang_vars:
            var.set(True)

    def _select_no_langs(self):
        for var, _ in self.lang_vars:
            var.set(False)

    # -----------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------
    def _log(self, msg: str):
        """Encola un mensaje para que se muestre en el textbox desde el hilo principal."""
        self.log_queue.put(msg)

    def _poll_log_queue(self):
        """Vuelca la cola al widget cada 100 ms."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    # -----------------------------------------------------------------
    # Ejecución del pipeline
    # -----------------------------------------------------------------
    def _on_run_clicked(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("En curso", "Ya hay un proceso ejecutándose.")
            return

        # Validaciones
        idiomas_sel = [lang for var, lang in self.lang_vars if var.get()]
        if not idiomas_sel:
            messagebox.showerror("Sin idiomas", "Selecciona al menos un idioma.")
            return

        if not (self.step_translate.get() or self.step_tts.get()
                or self.step_mix.get() or self.step_generate_js.get()):
            messagebox.showerror("Sin pasos", "Selecciona al menos un paso a ejecutar.")
            return

        texto = self.texto_path.get().strip()
        # Cualquier paso necesita texto.txt (para títulos)
        if not texto or not os.path.exists(texto):
            messagebox.showerror(
                "Falta texto.txt",
                "Selecciona un texto.txt válido (se usa para obtener los títulos "
                "y nombrar los archivos finales)."
            )
            return

        music = self.music_path.get().strip()
        if self.step_mix.get():
            if not music or not os.path.exists(music):
                messagebox.showerror("Falta música",
                                     "Selecciona el archivo de música para la mezcla.")
                return

        try:
            music_db = float(self.music_volume_db.get())
            fade_s = float(self.fade_seconds.get())
        except ValueError:
            messagebox.showerror("Configuración inválida",
                                 "Volumen y fade deben ser números.")
            return

        # Lanzar el worker
        self.run_button.configure(state="disabled", text="Procesando...")
        params = dict(
            idiomas=idiomas_sel,
            texto=texto,
            music=music,
            work_dir=self.work_dir.get().strip() or "audios_finales",
            music_db=music_db,
            fade_s=fade_s,
            do_translate=self.step_translate.get(),
            do_tts=self.step_tts.get(),
            do_mix=self.step_mix.get(),
            do_generate_js=self.step_generate_js.get(),
            js_output_path=self.js_output_path.get().strip(),
            js_base_url_prefix=self.js_base_url_prefix.get(),
            skip_existing=self.skip_existing.get(),
            cleanup_intermediates=not self.keep_intermediates.get(),
        )
        self.worker_thread = threading.Thread(
            target=self._run_pipeline, args=(params,), daemon=True
        )
        self.worker_thread.start()

    def _run_pipeline(self, p):
        try:
            self._log("=" * 60)
            self._log(f"Idiomas seleccionados: {len(p['idiomas'])}")
            self._log(
                f"Pasos: traducir={p['do_translate']} tts={p['do_tts']} "
                f"mezcla={p['do_mix']} js={p['do_generate_js']}"
            )
            self._log(f"Carpeta de trabajo: {p['work_dir']}")
            self._log(f"Conservar intermedios: {not p['cleanup_intermediates']}")
            self._log("=" * 60)

            # Parsear texto.txt: siempre lo necesitamos (para títulos finales)
            self._log(f"\nParseando {p['texto']}...")
            secciones = parse_text_file(p["texto"])
            self._log(f"Secciones detectadas: {len(secciones)}")
            for num, info in secciones.items():
                self._log(f"  [{num}] {info['titulo']}")

            # 1. Traducir
            if p["do_translate"]:
                self._log("\n--- PASO 1: Traducción ---")
                mod_translator.translate_sections(
                    secciones=secciones,
                    idiomas_seleccionados=p["idiomas"],
                    work_dir=p["work_dir"],
                    progress_cb=self._log,
                    skip_existing=p["skip_existing"],
                )

            # 2. TTS
            if p["do_tts"]:
                self._log("\n--- PASO 2: Generación TTS ---")
                tts_idiomas = [i for i in p["idiomas"] if i["voice"]]
                omitidos = [i["display_name"] for i in p["idiomas"] if not i["voice"]]
                if omitidos:
                    self._log(f"  Sin voz TTS, se omiten: {', '.join(omitidos)}")
                mod_tts.generate_tts(
                    idiomas_seleccionados=tts_idiomas,
                    secciones=secciones,
                    work_dir=p["work_dir"],
                    progress_cb=self._log,
                    skip_existing=p["skip_existing"],
                )

            # 3. Mezcla
            if p["do_mix"]:
                self._log("\n--- PASO 3: Mezcla con música ---")
                mod_mixer.mix_with_music(
                    idiomas_seleccionados=p["idiomas"],
                    secciones=secciones,
                    music_path=p["music"],
                    work_dir=p["work_dir"],
                    music_volume_db=p["music_db"],
                    fade_seconds=p["fade_s"],
                    progress_cb=self._log,
                    skip_existing=p["skip_existing"],
                    cleanup_intermediates=p["cleanup_intermediates"],
                )

            # 4. Generar audioDatabase.js
            if p["do_generate_js"]:
                self._log("\n--- PASO 4: Generación audioDatabase.js ---")
                js_path = p["js_output_path"] or os.path.join(
                    p["work_dir"], "audioDatabase.js"
                )
                mod_js.generate_database(
                    secciones=secciones,
                    idiomas_seleccionados=p["idiomas"],
                    output_path=js_path,
                    base_url_prefix=p["js_base_url_prefix"],
                    progress_cb=self._log,
                )

            self._log("\n" + "=" * 60)
            self._log("PROCESO COMPLETADO")
            self._log("=" * 60)
        except Exception as e:
            self._log(f"\n[ERROR] {e}")
            self._log(traceback.format_exc())
        finally:
            self.after(0, lambda: self.run_button.configure(
                state="normal", text="▶  EJECUTAR"))


# =====================================================================
# Entry point
# =====================================================================
def main():
    app = AudioguiasApp()
    app.mainloop()


if __name__ == "__main__":
    main()
