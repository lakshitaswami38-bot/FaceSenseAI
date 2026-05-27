function parseJsonScript(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  try {
    return JSON.parse(el.textContent || "null");
  } catch (err) {
    return null;
  }
}

function setupSidebarSections() {
  const navButtons = Array.from(document.querySelectorAll(".nav-item[data-section]"));
  const allSectionTriggers = Array.from(document.querySelectorAll("[data-section]"));
  const sections = Array.from(document.querySelectorAll(".dash-section"));
  if (!sections.length) return;

  const activateSection = (target) => {
    navButtons.forEach((x) => x.classList.toggle("active", x.getAttribute("data-section") === target));
    sections.forEach((section) => {
      section.classList.toggle("active", section.id === target);
    });
    if (target === "journeySection") {
      window.dispatchEvent(new CustomEvent("facesense:open-journey"));
    }
  };

  allSectionTriggers.forEach((btn) => {
    btn.addEventListener("click", () => activateSection(btn.getAttribute("data-section")));
  });

  const quickOpenButtons = Array.from(document.querySelectorAll("[data-open-section]"));
  quickOpenButtons.forEach((btn) => {
    btn.addEventListener("click", () => activateSection(btn.getAttribute("data-open-section")));
  });
}

function setupThemeToggle() {
  const toggle = document.getElementById("themeToggle");
  if (!toggle) return;
  const savedTheme = localStorage.getItem("facesense-theme") || "dark";
  document.body.setAttribute("data-theme", savedTheme);
  toggle.checked = savedTheme === "light";

  toggle.addEventListener("change", () => {
    const nextTheme = toggle.checked ? "light" : "dark";
    document.body.setAttribute("data-theme", nextTheme);
    localStorage.setItem("facesense-theme", nextTheme);
  });
}

function setupSidebarToggle() {
  const btn = document.getElementById("sidebarToggleBtn");
  if (!btn) return;

  const key = "facesense-sidebar-collapsed";
  const saved = localStorage.getItem(key);
  if (saved === "1") {
    document.body.classList.add("sidebar-collapsed");
  }

  btn.addEventListener("click", () => {
    document.body.classList.toggle("sidebar-collapsed");
    localStorage.setItem(key, document.body.classList.contains("sidebar-collapsed") ? "1" : "0");
  });
}

function createMoodJourneyChart() {
  const canvas = document.getElementById("moodJourneyChart");
  if (!canvas || canvas.dataset.ready === "1") return;

  const labels = parseJsonScript("journey-labels") || [];
  const counts = parseJsonScript("journey-counts") || [];
  if (!labels.length || !counts.length) return;

  const emotionEmoji = {
    happy: "😊",
    sad: "😢",
    angry: "😡",
    fear: "😨",
    surprise: "😲",
    neutral: "😐",
  };

  const barColors = {
    happy: "#facc15",
    sad: "#9ca3af",
    angry: "#ef4444",
    fear: "#a855f7",
    surprise: "#60a5fa",
    neutral: "#ffffff",
  };

  const css = getComputedStyle(document.body);
  const yTickColor = css.getPropertyValue("--muted").trim() || "#93a4c6";
  const gridColor = css.getPropertyValue("--border").trim() || "rgba(148, 163, 184, 0.22)";

  const moodEmojiPlugin = {
    id: "moodEmojiPlugin",
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      const datasetMeta = chart.getDatasetMeta(0);
      if (!datasetMeta || !datasetMeta.data) return;

      const drawRoundedRect = (x, y, w, h, r) => {
        const radius = Math.min(r, w / 2, h / 2);
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + w - radius, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
        ctx.lineTo(x + w, y + h - radius);
        ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
        ctx.lineTo(x + radius, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
      };

      ctx.save();
      ctx.textAlign = "center";
      ctx.font = "18px Segoe UI Emoji, sans-serif";
      datasetMeta.data.forEach((bar, idx) => {
        const emotion = labels[idx];
        const emoji = emotionEmoji[emotion] || "😐";
        const bubbleW = 28;
        const bubbleH = 22;
        const bubbleX = bar.x - bubbleW / 2;
        const bubbleY = bar.y - 28;
        drawRoundedRect(bubbleX, bubbleY, bubbleW, bubbleH, 7);
        ctx.fillStyle = "rgba(15, 23, 42, 0.88)";
        ctx.fill();
        ctx.fillStyle = "#ffffff";
        ctx.fillText(emoji, bar.x, bar.y - 10);
      });
      ctx.restore();
    },
  };

  new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: counts,
          backgroundColor: labels.map((emotion) => barColors[emotion] || "#94a3b8"),
          borderColor: labels.map((emotion) => (emotion === "neutral" ? "#64748b" : "transparent")),
          borderWidth: labels.map((emotion) => (emotion === "neutral" ? 1 : 0)),
          borderRadius: 8,
          maxBarThickness: 62,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 1000,
        easing: "easeOutQuart",
      },
      layout: {
        padding: {
          top: 28,
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: yTickColor, font: { size: 12 } },
        },
        y: {
          beginAtZero: true,
          ticks: { precision: 0, color: yTickColor },
          title: {
            display: true,
            text: "Frequency",
            color: yTickColor,
          },
          grid: { color: gridColor },
        },
      },
    },
    plugins: [moodEmojiPlugin],
  });

  canvas.dataset.ready = "1";
}

document.addEventListener("DOMContentLoaded", () => {
  setupSidebarSections();
  setupThemeToggle();
  setupSidebarToggle();
  createMoodJourneyChart();
});

window.addEventListener("facesense:open-journey", createMoodJourneyChart);
