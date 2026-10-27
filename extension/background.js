// Background Service Worker for Cyber Patrol Assistant Extension

const API_BASE = "http://localhost:8000";

chrome.runtime.onInstalled.addListener(() => {
  // Create context menu for right-clicking links
  chrome.contextMenus.create({
    id: "patrol_analyze_link",
    title: "🛡️ Kirim Tautan ke Cyber Patrol Assistant (AI Triage)",
    contexts: ["link", "page"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "patrol_analyze_link") {
    const targetUrl = info.linkUrl || info.pageUrl;
    if (!targetUrl) return;

    try {
      const response = await fetch(`${API_BASE}/api/v1/assistant/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: targetUrl,
          source_channel: "BROWSER_EXTENSION",
          reporter_identifier: "Context-Menu-Analyst",
          notes: "Pelaporan cepat via klik kanan (Context Menu)"
        })
      });

      const data = await response.json();
      if (response.ok) {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon48.png",
          title: "Patroli Siber — Laporan Diterima",
          message: `Tiket ${data.ticket_number} untuk ${data.platform.toUpperCase()} berhasil dikirim ke antrean AI.`
        });
      } else {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon48.png",
          title: "Patroli Siber — Gagal",
          message: data.detail || "URL tidak didukung."
        });
      }
    } catch (err) {
      console.error("Gagal mengirim intake via context menu:", err);
    }
  }
});

// Handler for tab screenshot capture requested by content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "capture_tab_screenshot") {
    const targetWinId = sender?.tab?.windowId || null;
    chrome.tabs.captureVisibleTab(targetWinId, { format: "png" }, (dataUrl) => {
      if (!chrome.runtime.lastError && dataUrl) {
        sendResponse({ ok: true, dataUrl: dataUrl });
      } else {
        // Fallback: try capturing without specific windowId
        chrome.tabs.captureVisibleTab(null, { format: "png" }, (fallbackUrl) => {
          if (!chrome.runtime.lastError && fallbackUrl) {
            sendResponse({ ok: true, dataUrl: fallbackUrl });
          } else {
            console.error("Capture visible tab failed:", chrome.runtime.lastError?.message);
            sendResponse({ ok: false, error: chrome.runtime.lastError?.message || "Capture failed" });
          }
        });
      }
    });
    return true; // Keep asynchronous message channel open
  }
});
