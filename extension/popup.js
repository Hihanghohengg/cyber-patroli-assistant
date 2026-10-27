const DEFAULT_API_BASE = "http://localhost:8000";

let currentTab = null;
let currentPlatform = "unknown";

function detectPlatform(url) {
  if (!url) return "unknown";
  const lower = url.toLowerCase();
  if (lower.includes("tiktok.com")) return "tiktok";
  if (lower.includes("youtube.com") || lower.includes("youtu.be")) return "youtube";
  if (lower.includes("instagram.com")) return "instagram";
  if (lower.includes("twitter.com") || lower.includes("x.com")) return "x";
  return "web";
}

function updatePlatformBadge(platform) {
  const badge = document.getElementById("platform-badge");
  badge.className = "platform-badge";
  if (platform === "tiktok") {
    badge.classList.add("platform-tiktok");
    badge.textContent = "TikTok";
  } else if (platform === "youtube") {
    badge.classList.add("platform-youtube");
    badge.textContent = "YouTube";
  } else if (platform === "instagram") {
    badge.classList.add("platform-instagram");
    badge.textContent = "Instagram";
  } else if (platform === "x") {
    badge.classList.add("platform-x");
    badge.textContent = "X / Twitter";
  } else {
    badge.classList.add("platform-unknown");
    badge.textContent = platform.toUpperCase();
  }
}

async function checkServerHealth(apiBase) {
  const indicator = document.getElementById("conn-indicator");
  const text = document.getElementById("conn-text");
  try {
    const res = await fetch(`${apiBase}/health`, { method: "GET" });
    if (res.ok) {
      indicator.className = "conn-status";
      text.textContent = "Terhubung";
      return true;
    }
  } catch (err) {
    // offline
  }
  indicator.className = "conn-status disconnected";
  text.textContent = "API Offline";
  return false;
}

document.addEventListener("DOMContentLoaded", async () => {
  const tabUrlElem = document.getElementById("tab-url");
  const btnSubmit = document.getElementById("btn-submit");
  const btnText = document.getElementById("btn-text");
  const resultCard = document.getElementById("result-card");
  const resultTicket = document.getElementById("result-ticket");
  const resultDesc = document.getElementById("result-desc");
  const analystIdInput = document.getElementById("analyst-id");
  const notesInput = document.getElementById("notes");

  // Load saved analyst ID if available
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["analystId"], (result) => {
      if (result.analystId) {
        analystIdInput.value = result.analystId;
      }
    });
  }

  // Check health
  await checkServerHealth(DEFAULT_API_BASE);

  // Get active tab URL
  if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url) {
        currentTab = tab;
        tabUrlElem.textContent = tab.url;
        currentPlatform = detectPlatform(tab.url);
        updatePlatformBadge(currentPlatform);
      } else {
        tabUrlElem.textContent = "Tidak dapat mendeteksi URL tab aktif.";
      }
    } catch (err) {
      tabUrlElem.textContent = "Gagal mengambil tab: " + err.message;
    }
  } else {
    tabUrlElem.textContent = "http://localhost:5173/#/contents (Mode Standalone)";
    currentPlatform = "web";
    updatePlatformBadge("web");
  }

  // Handle Submit
  btnSubmit.addEventListener("click", async () => {
    const targetUrl = currentTab ? currentTab.url : tabUrlElem.textContent;
    if (!targetUrl || targetUrl.startsWith("chrome://") || targetUrl.startsWith("edge://")) {
      alert("Hanya tautan media sosial publik (TikTok, YouTube, Instagram) yang dapat diproses!");
      return;
    }

    const analystId = analystIdInput.value.trim() || "Analyst-Extension";
    const notes = notesInput.value.trim();

    // Save analyst ID
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({ analystId: analystId });
    }

    btnSubmit.disabled = true;
    btnText.textContent = "Mengambil Tangkapan Layar...";

    let screenshotBase64 = null;
    if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.captureVisibleTab) {
      try {
        screenshotBase64 = await new Promise((resolve) => {
          chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
            if (chrome.runtime.lastError || !dataUrl) {
              resolve(null);
            } else {
              resolve(dataUrl);
            }
          });
        });
      } catch (err) {
        console.warn("Popup tab screenshot capture failed:", err);
      }
    }

    btnText.textContent = "Mengirim ke Pipeline AI...";

    try {
      const payload = {
        url: targetUrl,
        source_channel: "BROWSER_EXTENSION",
        reporter_identifier: analystId,
        notes: notes || undefined,
        screenshot_base64: screenshotBase64 || undefined,
      };

      const res = await fetch(`${DEFAULT_API_BASE}/api/v1/assistant/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Gagal mengirim laporan intake");
      }

      resultCard.style.display = "block";
      resultTicket.textContent = data.ticket_number;
      resultDesc.textContent = `Konten ${data.platform.toUpperCase()} berhasil dimasukkan ke antrean triase AI & preseden RAG. Buka dashboard untuk meninjau hasil.`;
      btnText.textContent = "✅ Laporan Berhasil Dikirim";
    } catch (err) {
      alert("Gagal memproses triase: " + err.message);
      btnText.textContent = "⚡ Triase & Kirim ke AI (1-Click)";
      btnSubmit.disabled = false;
    }
  });
});
