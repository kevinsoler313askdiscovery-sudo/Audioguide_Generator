/* =========================================================
   Audioguías · v2.0 · frontend
   ========================================================= */

const $ = (id) => document.getElementById(id);

const state = {
    languages: [],
    selectedFolders: new Set(),
    jobId: null,
    eventSource: null,
};

// ------------------------------------------------------------------
// 1. Cargar idiomas y renderizar grid
// ------------------------------------------------------------------
async function loadLanguages() {
    try {
        const res = await fetch("/api/languages");
        state.languages = await res.json();
        renderLanguages();
    } catch (e) {
        $("languages-grid").innerHTML =
            `<div class="loading">Error cargando idiomas: ${e}</div>`;
    }
}

function renderLanguages() {
    const grid = $("languages-grid");
    grid.innerHTML = "";
    state.languages.forEach((lang) => {
        const row = document.createElement("label");
        row.className = "lang-row";

        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.dataset.folder = lang.folder_name;
        cb.addEventListener("change", (e) => {
            if (e.target.checked) state.selectedFolders.add(lang.folder_name);
            else state.selectedFolders.delete(lang.folder_name);
        });

        const label = document.createElement("span");
        label.className = "lang-label";
        label.textContent = lang.display_name;

        const folder = document.createElement("span");
        folder.className = "lang-folder";
        folder.textContent = lang.folder_name;

        row.append(cb, label, folder);

        if (!lang.voice) {
            const tag = document.createElement("span");
            tag.className = "no-tts";
            tag.textContent = "sin TTS";
            row.append(tag);
        }

        grid.append(row);
    });
}

// ------------------------------------------------------------------
// 2. Selección masiva
// ------------------------------------------------------------------
$("select-all").addEventListener("click", () => {
    document.querySelectorAll('#languages-grid input[type="checkbox"]').forEach((cb) => {
        cb.checked = true;
        state.selectedFolders.add(cb.dataset.folder);
    });
});

$("select-none").addEventListener("click", () => {
    document.querySelectorAll('#languages-grid input[type="checkbox"]').forEach((cb) => {
        cb.checked = false;
    });
    state.selectedFolders.clear();
});

// ------------------------------------------------------------------
// 3. Logs / status
// ------------------------------------------------------------------
function setStatus(kind, text) {
    const el = $("job-status");
    el.className = `status-pill status-${kind}`;
    el.textContent = text;
}

function appendLog(msg) {
    const el = $("log-output");
    if (el.dataset.fresh !== "1") {
        el.textContent = "";
        el.dataset.fresh = "1";
    }
    el.textContent += msg + "\n";
    el.scrollTop = el.scrollHeight;
}

$("clear-logs").addEventListener("click", () => {
    $("log-output").textContent = "Logs limpiados.\n";
    $("log-output").dataset.fresh = "1";
});

// ------------------------------------------------------------------
// 4. Lanzar pipeline
// ------------------------------------------------------------------
async function runPipeline() {
    const textoFile = $("texto-file").files[0];
    if (!textoFile) { alert("Selecciona un archivo texto.txt"); return; }

    const steps = {
        translate: $("step-translate").checked,
        tts: $("step-tts").checked,
        mix: $("step-mix").checked,
        generate_js: $("step-js").checked,
    };
    if (!Object.values(steps).some(Boolean)) {
        alert("Selecciona al menos un paso."); return;
    }
    if (state.selectedFolders.size === 0) {
        alert("Selecciona al menos un idioma."); return;
    }

    const musicFile = $("music-file").files[0];
    if (steps.mix && !musicFile) {
        alert("Para mezclar con música hace falta un archivo de audio."); return;
    }

    const config = {
        music_volume_db: parseFloat($("music-vol").value),
        fade_seconds: parseFloat($("fade-sec").value),
        skip_existing: $("skip-existing").checked,
        keep_intermediates: $("keep-intermediates").checked,
        js_base_url_prefix: $("js-prefix").value,
    };

    const fd = new FormData();
    fd.append("texto", textoFile);
    if (musicFile) fd.append("music", musicFile);
    fd.append("languages", JSON.stringify([...state.selectedFolders]));
    fd.append("steps", JSON.stringify(steps));
    fd.append("config", JSON.stringify(config));

    $("run-btn").disabled = true;
    $("run-btn").querySelector(".btn-label").textContent = "Procesando...";
    const link = $("download-link");
    link.style.display = "none";
    link.style.pointerEvents = "";
    link.style.opacity = "";
    link.textContent = "Descargar resultado (.zip)";
    link.onclick = null;
    $("log-output").textContent = "";
    $("log-output").dataset.fresh = "1";
    setStatus("running", "En curso");

    let res;
    try {
        res = await fetch("/api/run", { method: "POST", body: fd });
    } catch (e) {
        return finishWithError("Error de red: " + e);
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        return finishWithError("Error: " + err.error);
    }
    const { job_id } = await res.json();
    state.jobId = job_id;
    streamLogs(job_id);
}

function streamLogs(jobId) {
    if (state.eventSource) state.eventSource.close();
    const es = new EventSource(`/api/logs/${jobId}`);
    state.eventSource = es;

    es.onmessage = (e) => {
        let data;
        try { data = JSON.parse(e.data); } catch { return; }
        if (data._final) {
            es.close();
            state.eventSource = null;
            if (data.status === "done") {
                setStatus("done", "Listo para descargar");
                showDownload(jobId);
            } else {
                setStatus("error", "Error");
                if (data.error) appendLog(`\n[ERROR FINAL] ${data.error}`);
            }
            $("run-btn").disabled = false;
            $("run-btn").querySelector(".btn-label").textContent = "▶ EJECUTAR";
            return;
        }
        if (data.msg !== undefined) appendLog(data.msg);
    };

    es.onerror = () => {
        es.close();
        state.eventSource = null;
    };
}

function showDownload(jobId) {
    const link = $("download-link");
    link.href = `/api/download/${jobId}`;
    link.textContent = "⬇ Descargar resultado (.zip)";
    link.style.display = "inline-block";
    link.style.pointerEvents = "";
    link.style.opacity = "";

    // Al descargar: el servidor borra los archivos tras enviar el zip.
    link.onclick = () => {
        appendLog("\nIniciando descarga... el servidor borrara los archivos al terminar.");
        setTimeout(() => {
            link.textContent = "Descarga iniciada — servidor limpio";
            link.style.pointerEvents = "none";
            link.style.opacity = "0.6";
            setStatus("done", "Descargado");
        }, 1000);
    };
}

function finishWithError(msg) {
    setStatus("error", "Error");
    appendLog(msg);
    $("run-btn").disabled = false;
    $("run-btn").querySelector(".btn-label").textContent = "▶ EJECUTAR";
}

$("run-btn").addEventListener("click", runPipeline);

// ------------------------------------------------------------------
// 5. Mostrar nombre del archivo seleccionado
// ------------------------------------------------------------------
$("texto-file").addEventListener("change", (e) => {
    const f = e.target.files[0];
    $("texto-info").textContent = f
        ? `Seleccionado: ${f.name}  (${formatBytes(f.size)})`
        : "Formato esperado: secciones numeradas como 1 – TÍTULO";
});

$("music-file").addEventListener("change", (e) => {
    const f = e.target.files[0];
    $("music-info").textContent = f
        ? `Seleccionado: ${f.name}  (${formatBytes(f.size)})`
        : "Solo necesaria si activas el paso 3";
});

function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

loadLanguages();
