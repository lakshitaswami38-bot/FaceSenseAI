function showLoading(show) {
  const el = document.getElementById("loadingOverlay");
  if (!el) return;
  el.classList.toggle("hidden", !show);
  el.setAttribute("aria-hidden", show ? "false" : "true");
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data && data.error ? data.error : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

function wireMoodSelection() {
  const grid = document.querySelector("[data-mood-grid]");
  if (!grid) return;
  grid.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-emotion]");
    if (!btn) return;
    const emotion = btn.getAttribute("data-emotion");
    try {
      showLoading(true);
      const data = await postJson("/select", { emotion });
      window.location.href = data.redirect || "/result";
    } catch (err) {
      alert(err.message || "Failed to submit mood.");
    } finally {
      showLoading(false);
    }
  });
}

function wireTextForm() {
  const form = document.querySelector("[data-text-form]");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const textarea = form.querySelector("textarea[name='text']");
    const text = textarea ? textarea.value : "";
    try {
      showLoading(true);
      const data = await postJson("/text", { text });
      window.location.href = data.redirect || "/result";
    } catch (err) {
      alert(err.message || "Text analysis failed.");
    } finally {
      showLoading(false);
    }
  });
}

function wireCamera() {
  const btn = document.querySelector("[data-camera-start]");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    try {
      showLoading(true);
      const data = await postJson("/camera", {});
      window.location.href = data.redirect || "/result";
    } catch (err) {
      alert(
        (err && err.message) ||
          "Camera analysis failed. Close other camera apps and try again."
      );
      window.location.href = "/result";
    } finally {
      showLoading(false);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireMoodSelection();
  wireTextForm();
  wireCamera();
});

