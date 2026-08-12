(() => {
  "use strict";

  const active = new Map();
  let sequence = 0;

  function render() {
    const overlay = document.getElementById("globalLoadingOverlay");
    if (!overlay) return;
    overlay.hidden = active.size === 0;
    const label = overlay.querySelector("[data-loading-label]");
    if (label) label.textContent = Array.from(active.values()).at(-1) || "Загрузка…";
  }

  function start(label = "Загрузка…") {
    const token = `ui-${++sequence}`;
    active.set(token, String(label));
    render();
    return token;
  }

  function stop(token) {
    active.delete(token);
    render();
  }

  async function run(label, operation) {
    const token = start(label);
    try { return await operation(); }
    catch (error) { showError(error); throw error; }
    finally { stop(token); }
  }

  function showError(error) {
    const banner = document.getElementById("appErrorBanner");
    if (!banner) return;
    const message = error instanceof Error ? error.message : String(error || "Неизвестная ошибка");
    banner.querySelector("[data-error-message]").textContent = `Ошибка: ${message}`;
    banner.hidden = false;
  }

  function initialize() {
    document.getElementById("closeAppErrorBanner")?.addEventListener("click", () => { document.getElementById("appErrorBanner").hidden = true; });
    window.addEventListener("unhandledrejection", (event) => showError(event.reason));
    window.addEventListener("error", (event) => showError(event.error || event.message));
  }

  window.MacAnalyzerUiFeedback = Object.freeze({ initialize, start, stop, run, showError });
  initialize();
})();
