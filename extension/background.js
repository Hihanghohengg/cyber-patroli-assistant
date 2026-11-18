// @ts-nocheck
/* cSpell:disable */
// Background Service Worker for TILIK Extension
// Compliant with Manifest V3 and Multi-User LAN Dynamic Configuration

const DEFAULT_SERVER = "http://127.0.0.1:8000";

async function getServerHosts() {
  return new Promise((resolve) => {
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.get(["server_url"], (res) => {
        const configured = (res.server_url || "").trim().replace(/\/+$/, "");
        const hosts = [];
        if (configured) hosts.push(configured);
        if (!hosts.includes("http://127.0.0.1:8000")) hosts.push("http://127.0.0.1:8000");
        if (!hosts.includes("http://localhost:8000")) hosts.push("http://localhost:8000");
        resolve(hosts);
      });
    } else {
      resolve(["http://127.0.0.1:8000", "http://localhost:8000"]);
    }
  });
}

async function fetchWithFallback(endpoint, options = {}) {
  const hosts = await getServerHosts();
  let lastError = null;

  // 1. Identifikasi host yang aktif secara cepat (1200ms ping) untuk mencegah penundaan pada host mati
  let activeHost = null;
  for (const host of hosts) {
    try {
      const pingRes = await fetch(`${host}/health`, { method: "GET", signal: AbortSignal.timeout(1200) });
      if (pingRes.ok) {
        activeHost = host;
        break;
      }
    } catch (_) {
      // Host tidak merespon, lanjutkan cek host berikutnya
    }
  }

  // Jika tidak ada host yang merespon ping health, prioritaskan host terkonfigurasi atau localhost
  const targetHosts = activeHost ? [activeHost] : hosts;

  for (const host of targetHosts) {
    try {
      const url = `${host}${endpoint}`;
      const res = await fetch(url, { ...options, signal: AbortSignal.timeout(240000) }); // 240s timeout for local AI inference
      return res;
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error(`Gagal terhubung ke backend server (${hosts.join(" / ")})`);
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "patrol_analyze_link",
    title: "🛡️ Kirim Tautan ke TILIK (AI Triage)",
    contexts: ["link", "page"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "patrol_analyze_link") {
    const targetUrl = info.linkUrl || info.pageUrl;
    if (!targetUrl) return;

    let screenshotBase64 = undefined;
    const winId = typeof tab?.windowId === "number" ? tab.windowId : null;
    try {
      screenshotBase64 = await new Promise((resolve) => {
        chrome.tabs.captureVisibleTab(winId, { format: "jpeg", quality: 85 }, (dataUrl) => {
          if (!chrome.runtime.lastError && dataUrl) {
            resolve(dataUrl);
          } else {
            chrome.tabs.captureVisibleTab(null, { format: "jpeg", quality: 85 }, (dataUrl2) => {
              resolve((!chrome.runtime.lastError && dataUrl2) ? dataUrl2 : undefined);
            });
          }
        });
      });
    } catch (_) {}

    chrome.storage.local.get(["operator_id"], async (res) => {
      const operatorId = (res.operator_id || "op_d23_01").trim();
      const capturedAtUtc = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");

      try {
        const response = await fetchWithFallback("/api/v1/assistant/intake", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: targetUrl,
            source_channel: "BROWSER_EXTENSION",
            reporter_identifier: operatorId,
            operator_id: operatorId,
            captured_at_utc: capturedAtUtc,
            screenshot_base64: screenshotBase64,
            notes: "Pelaporan cepat via klik kanan (Context Menu)"
          })
        });

        const data = await response.json().catch(() => ({}));
        if (response.ok) {
          chrome.notifications.create({
            type: "basic",
            iconUrl: "icons/icon48.png",
            title: "TILIK — Laporan Diterima",
            message: `Tiket ${data.ticket_number} [HMAC: ${data.verification_status || 'VERIFIED'}] berhasil dicatat oleh ${operatorId}.`
          });
        } else {
          const errorMsg = typeof data.detail === "string" ? data.detail : (data.detail ? JSON.stringify(data.detail) : "URL tidak didukung atau server sibuk.");
          chrome.notifications.create({
            type: "basic",
            iconUrl: "icons/icon48.png",
            title: "TILIK — Gagal",
            message: errorMsg
          });
        }
      } catch (err) {
        console.error("Gagal mengirim intake via context menu:", err);
      }
    });
  }
});

// Handler for tab screenshot capture and background API proxy
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "submit_intake") {
    fetchWithFallback("/api/v1/assistant/intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload)
    })
      .then(async (res) => {
        let data = {};
        try {
          data = await res.json();
        } catch (jsonErr) {
          const rawText = await res.text().catch(() => "");
          data = { detail: rawText || `Server HTTP ${res.status}: ${res.statusText || "Internal Error"}` };
        }
        sendResponse({ ok: res.ok, status: res.status, data: data });
      })
      .catch((err) => {
        console.error("Background submit_intake fetch failed:", err);
        let msg = "Gagal menghubungi server TILIK. Pastikan server backend sedang aktif di IP/Port yang sesuai.";
        if (err.name === "AbortError") {
          msg = "Batas waktu permintaan habis (timeout). Pipeline AI lokal membutuhkan waktu lebih lama.";
        }
        sendResponse({ ok: false, error: msg });
      });
    return true; // Keep asynchronous message channel open
  }

  if (request.action === "check_health") {
    fetchWithFallback("/health")
      .then((res) => sendResponse({ ok: res.ok }))
      .catch((err) => sendResponse({ ok: false, error: err.message || "Offline" }));
    return true;
  }

  if (request.action === "capture_tab_screenshot") {
    const options = { format: "jpeg", quality: 85 };
    const winId = typeof sender?.tab?.windowId === "number" ? sender.tab.windowId : null;

    const tryCapture = (targetWinId, fallback) => {
      chrome.tabs.captureVisibleTab(targetWinId, options, (dataUrl) => {
        if (!chrome.runtime.lastError && dataUrl) {
          sendResponse({ ok: true, dataUrl: dataUrl });
        } else if (fallback) {
          fallback();
        } else {
          const err = chrome.runtime.lastError?.message || "Capture visible tab failed";
          console.warn("[TILIK Service Worker] Capture error:", err);
          sendResponse({ ok: false, error: err });
        }
      });
    };

    // Prioritas 1: Gunakan windowId tab pengirim jika tersedia, lalu fallback ke active window (null)
    if (typeof winId === "number") {
      tryCapture(winId, () => tryCapture(null, null));
    } else {
      tryCapture(null, null);
    }
    return true; // Keep asynchronous message channel open
  }
});
