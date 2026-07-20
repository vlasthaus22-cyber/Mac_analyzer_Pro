(() => {
  "use strict";

  const tabNames = ["overview", "user", "engineer", "large-files"];

  function normalizeTab(name) {
    return tabNames.includes(String(name || "")) ? String(name) : "overview";
  }

  function modePresentation(engineeringActive, expiresAt = "") {
    if (!engineeringActive) {
      return {
        mode: "user",
        label: "Пользовательский режим",
        summary: "Доступны поиск, история MAC, аналитика и просмотр сохранённых данных.",
      };
    }
    const parsed = Date.parse(expiresAt || "");
    const expires = Number.isFinite(parsed) ? new Date(parsed).toLocaleString("ru-RU") : "без ограничения";
    return {
      mode: "engineering",
      label: "Инженерный режим",
      summary: `Полный доступ к импорту, обогащению, сравнению и данным до ${expires}.`,
    };
  }

  function activateTab(name, scope = document) {
    const selected = normalizeTab(name);
    scope.querySelectorAll("[data-guide-tab]").forEach((button) => {
      const active = button.dataset.guideTab === selected;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
      button.tabIndex = active ? 0 : -1;
    });
    scope.querySelectorAll("[data-guide-panel]").forEach((panel) => {
      const active = panel.dataset.guidePanel === selected;
      panel.hidden = !active;
      panel.classList.toggle("active", active);
    });
    return selected;
  }

  function syncMode(engineeringActive, expiresAt = "", scope = document) {
    const presentation = modePresentation(engineeringActive, expiresAt);
    const strip = scope.querySelector("#guideModeStrip");
    if (strip) {
      strip.dataset.guideMode = presentation.mode;
      strip.classList.toggle("engineering-mode", presentation.mode === "engineering");
      strip.classList.toggle("user-mode", presentation.mode === "user");
    }
    const label = scope.querySelector("#guideCurrentMode");
    if (label) label.textContent = presentation.label;
    const summary = scope.querySelector("#guideModeSummary");
    if (summary) summary.textContent = presentation.summary;
    scope.querySelectorAll("[data-guide-requires-engineering]").forEach((button) => {
      button.disabled = !engineeringActive;
      button.title = engineeringActive ? "" : "Сначала войдите в инженерный режим";
    });
    const loginButton = scope.querySelector("#guideEngineeringLoginButton");
    if (loginButton) loginButton.textContent = engineeringActive ? "Перейти к анализу" : "Войти в инженерный режим";
    return presentation;
  }

  const api = {activateTab, modePresentation, normalizeTab, syncMode, tabNames: [...tabNames]};
  if (typeof window !== "undefined") window.MacAnalyzerGuide = api;
  else globalThis.MacAnalyzerGuide = api;
  if (typeof document !== "undefined" && document.documentElement) document.documentElement.dataset.guideModule = "ready";
})();
