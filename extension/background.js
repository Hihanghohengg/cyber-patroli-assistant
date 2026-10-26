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
