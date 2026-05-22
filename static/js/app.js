// static/js/app.js

// ── Toast ────────────────────────────────────────────────────
function toast(msg, type = "info") {
  const c = document.getElementById("toast-container") || (() => {
    const d = document.createElement("div");
    d.id = "toast-container";
    document.body.appendChild(d);
    return d;
  })();
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  const icons = { ok: "✓", err: "✗", info: "ℹ" };
  t.innerHTML = `<span style="color:var(--${type==='ok'?'green':type==='err'?'red':'blue'})">${icons[type]||"ℹ"}</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; t.style.transform = "translateX(20px)"; t.style.transition = ".3s"; setTimeout(() => t.remove(), 300); }, 3500);
}

// ── HTMX after-swap hook (mostrar toast desde respuesta) ─────
document.addEventListener("htmx:afterSwap", (e) => {
  const hdr = e.detail.xhr.getResponseHeader("X-Toast");
  if (hdr) {
    try { const d = JSON.parse(hdr); toast(d.msg, d.type); } catch {}
  }
});

document.addEventListener("htmx:responseError", () => {
  toast("Error de servidor", "err");
});

// ── Upload zone drag & drop ──────────────────────────────────
function initUploadZone(zoneId, inputId) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;

  ["dragenter","dragover"].forEach(ev =>
    zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add("drag"); })
  );
  ["dragleave","drop"].forEach(ev =>
    zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove("drag"); })
  );
  zone.addEventListener("drop", e => {
    input.files = e.dataTransfer.files;
    input.dispatchEvent(new Event("change"));
  });
  zone.addEventListener("click", () => input.click());
}

// ── Upload PDFs con progreso ─────────────────────────────────
async function uploadPDFs(input, logId, statsId) {
  const files = Array.from(input.files);
  if (!files.length) return;

  const log  = document.getElementById(logId);
  const stat = document.getElementById(statsId);
  let ok = 0, err = 0;

  for (const file of files) {
    const fd = new FormData();
    fd.append("file", file);

    appendLog(log, `Procesando: ${file.name}`, "info");

    try {
      const r = await fetch("/api/procesar-pdf", { method: "POST", body: fd });
      const d = await r.json();
      if (d.ok) {
        ok++;
        appendLog(log, `✓ ${d.mensaje}`, "ok");
        toast(`✓ ${file.name}`, "ok");
        
        // DESCARGA AUTOMÁTICA: Crear enlace temporal para disparar descarga sin recargar página
        const match = d.mensaje.match(/Archivo generado: ([\w\.-]+)/);
        if (match && match[1]) {
          const fileName = match[1];
          const a = document.createElement("a");
          a.href = `/api/descargar/${fileName}`;
          a.setAttribute("download", fileName);
          a.style.display = "none";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
      } else {
        err++;
        appendLog(log, `✗ ${d.mensaje}`, "err");
        toast(`✗ ${file.name}`, "err");
      }
    } catch (ex) {
      err++;
      appendLog(log, `✗ ${file.name}: ${ex}`, "err");
    }

    if (stat) {
      const total = ok + err;
      stat.innerHTML = renderStats(total, ok, err);
    }
  }
  input.value = "";
  // Recargar lista de solicitudes via HTMX
  htmx.trigger("#sol-lista", "reload");
}

function appendLog(el, msg, cls) {
  if (!el) return;
  const ts = new Date().toLocaleTimeString("es-MX", {hour12: false});
  const line = document.createElement("div");
  line.className = `log-${cls}`;
  line.textContent = `[${ts}] ${msg}`;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function renderStats(total, ok, err) {
  return `<span style="color:var(--muted)">Procesados: <b style="color:var(--text)">${total}</b></span>
          <span style="color:var(--muted)">Exitosos: <b style="color:var(--green)">${ok}</b></span>
          <span style="color:var(--muted)">Errores: <b style="color:var(--red)">${err}</b></span>`;
}

// ── Seleccionar/deseleccionar todo ───────────────────────────
function selectAll(name, val) {
  document.querySelectorAll(`input[name="${name}"]`).forEach(c => c.checked = val);
}

// ── Upload BD CSV ────────────────────────────────────────────
async function uploadBD(input, labelId) {
  const file = input.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/api/cargar-bd", { method: "POST", body: fd });
  const d = await r.json();
  const lbl = document.getElementById(labelId);
  if (d.ok) {
    if (lbl) lbl.innerHTML = `<span style="color:var(--green)">✓ ${file.name} — ${d.columnas} columnas</span>`;
    toast(`BD cargada: ${file.name}`, "ok");
    // guardar token de sesión de BD
    window._bdToken = d.token;
  } else {
    toast("Error al leer la BD", "err");
  }
}

// ── Buscar y exportar bajas ──────────────────────────────────
async function buscarYExportar(formId) {
  const form = document.getElementById(formId);
  const data = new FormData(form);

  // Agregar token de BD
  if (window._bdToken) data.append("bd_token", window._bdToken);

  const seleccionados = [...form.querySelectorAll('input[name="solicitudes"]:checked')];
  if (!seleccionados.length) { toast("Selecciona al menos una solicitud", "info"); return; }
  if (!window._bdToken)      { toast("Carga primero la base de datos", "info"); return; }

  const r = await fetch("/api/buscar-bajas", { method: "POST", body: data });
  if (!r.ok) { toast("Error en el servidor", "err"); return; }

  const d = await r.json();
  if (!d.ok) { toast(d.mensaje, "err"); return; }

  // Descargar xlsx
  toast(`${d.encontrados} registro(s) encontrados — descargando...`, "ok");
  window.location.href = `/api/descargar/${d.archivo}`;
}

// ── Generar plantilla de entradas ────────────────────────────
async function generarEntradas(formId) {
  const form = document.getElementById(formId);
  const data = new FormData(form);
  const sel = [...form.querySelectorAll('input[name="solicitudes"]:checked')];
  if (!sel.length) { toast("Selecciona al menos una solicitud", "info"); return; }

  const r = await fetch("/api/generar-entradas", { method: "POST", body: data });
  const d = await r.json();
  if (d.ok) {
    toast(`✓ ${d.registros} registro(s) generados`, "ok");
    window.location.href = `/api/descargar/${d.archivo}`;
  } else {
    toast(d.mensaje, "err");
  }
}
