/* ═══════════════════════════════════════════════════════════════════════════
  YT Downloader — Client Logic
  Uses a direct serverless response for file download.
  ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  // ── DOM refs ──────────────────────────────────────────────────────────
  const form        = document.getElementById("download-form");
  const urlInput    = document.getElementById("url-input");
  const resSel      = document.getElementById("resolution-select");
  const fpsSel      = document.getElementById("fps-select");
  const btn         = document.getElementById("download-btn");
  const statusArea  = document.getElementById("status-area");
  const spinner     = document.getElementById("spinner");
  const statusText  = document.getElementById("status-text");
  const progressBar = document.getElementById("progress-fill");
  const downloadLink = document.getElementById("download-link");

  // ── Helpers ───────────────────────────────────────────────────────────
  function showStatus(msg, pct) {
    statusArea.classList.remove("hidden");
    statusText.textContent = msg || "Working…";
    if (typeof pct === "number") {
      progressBar.style.width = Math.min(pct, 100) + "%";
    }
  }

  function setSpinnerState(state) {
    spinner.classList.remove("done", "error");
    if (state === "done")  spinner.classList.add("done");
    if (state === "error") spinner.classList.add("error");
  }

  function resetUI() {
    statusArea.classList.add("hidden");
    downloadLink.classList.add("hidden");
    downloadLink.href = "#";
    progressBar.style.width = "0%";
    setSpinnerState("running");
    btn.disabled = false;
    btn.querySelector("span").textContent = "Download";
  }

  // ── Submit ────────────────────────────────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const url        = urlInput.value.trim();
    const resolution = resSel.value;
    const fps        = fpsSel.value;

    if (!url) return;

    // Reset previous state
    resetUI();
    btn.disabled = true;
    btn.querySelector("span").textContent = "Processing…";
    showStatus("Starting download…", 8);

    try {
      const res = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, resolution, fps }),
      });
      showStatus("Downloading…", 70);

      if (!res.ok) {
        let msg = "Server error";
        try {
          const errData = await res.json();
          msg = errData.error || msg;
        } catch (_) {
          // Keep generic message if non-JSON error response.
        }
        throw new Error(msg);
      }

      const blob = await res.blob();
      const cd = res.headers.get("Content-Disposition") || "";
      const match = cd.match(/filename="?([^";]+)"?/i);
      const name = match && match[1] ? match[1] : "download.mp4";

      const blobUrl = URL.createObjectURL(blob);
      downloadLink.href = blobUrl;
      downloadLink.setAttribute("download", name);
      downloadLink.classList.remove("hidden");

      showStatus("Done. Click Save Video.", 100);
      setSpinnerState("done");
      btn.disabled = false;
      btn.querySelector("span").textContent = "Download Another";

      // Trigger save automatically, and leave button as manual fallback.
      downloadLink.click();
    } catch (err) {
      showStatus("❌ " + err.message, 0);
      setSpinnerState("error");
      btn.disabled = false;
      btn.querySelector("span").textContent = "Retry";
    }
  });
})();
