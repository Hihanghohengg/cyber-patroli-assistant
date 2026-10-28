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

    // Extract in-depth structured metadata and direct media image url from active tab
    let inPageMeta = {};
    if (typeof chrome !== "undefined" && chrome.scripting && currentTab?.id) {
      try {
        const [results] = await chrome.scripting.executeScript({
          target: { tabId: currentTab.id },
          func: () => {
            function parseNum(text) {
              if (!text) return 0;
              const clean = text.trim().toLowerCase().replace(/,/g, ".");
              const m = clean.match(/([\d\.]+)/);
              if (!m) return 0;
              let v = parseFloat(m[1]);
              if (clean.includes("m") || clean.includes("jt")) v *= 1000000;
              else if (clean.includes("k") || clean.includes("rb")) v *= 1000;
              return Math.round(v);
            }

            const url = window.location.href.toLowerCase();
            const res = {
              username: null,
              display_name: null,
              followers_count: 0,
              title: null,
              caption: null,
              likes_count: 0,
              views_count: 0,
              comments_count: 0,
              shares_count: 0,
              media_image_url: null,
            };

            // Image
            const og = document.querySelector('meta[property="og:image"]')?.content ||
                       document.querySelector('meta[name="twitter:image"]')?.content;
            if (og && !og.includes('favicon')) res.media_image_url = og;

            // YouTube
            if (url.includes("youtube.com") || url.includes("youtu.be")) {
              const ch = document.querySelector("#channel-name a") || document.querySelector("#owner #text a");
              res.display_name = ch?.textContent?.trim();
              const chHref = ch?.getAttribute("href") || "";
              res.username = chHref.includes("@") ? chHref.split("@")[1].split("/")[0] : res.display_name;
              const subEl = document.querySelector("#owner-sub-count") || document.querySelector("#subscriber-count");
              if (subEl) res.followers_count = parseNum(subEl.textContent);
              const tit = document.querySelector("#title h1 yt-formatted-string") || document.querySelector("h2.ytd-reel-player-header-renderer");
              res.title = tit?.textContent?.trim() || document.title.replace(" - YouTube", "");
              const descText = document.querySelector("#description-inline-expander yt-attributed-string") ||
                               document.querySelector("#description-text") ||
                               document.querySelector("ytd-text-inline-expander #plain-snippet-text") ||
                               document.querySelector("#description yt-formatted-string") ||
                               document.querySelector("meta[name='description']");
              let rawDesc = descText?.textContent?.trim() || descText?.content || document.querySelector("#description-inline-expander")?.textContent?.trim();
              if (rawDesc) {
                res.caption = rawDesc
                  .replace(/\.\.\.selengkapnya/gi, "")
                  .replace(/Lebih sedikit/gi, "")
                  .replace(/Ikuti menggunakan transkrip\./gi, "")
                  .replace(/Tampilkan transkrip/gi, "")
                  .replace(/Cara konten ini dibuat/gi, "")
                  .replace(/Disulih suara otomatis/gi, "")
                  .replace(/Trek audio untuk beberapa bahasa dibuat secara otomatis\./gi, "")
                  .replace(/Pelajari lebih lanjut/gi, "")
                  .replace(/\d+([,\.]\d+)?\s*(rb|jt|k|m)?\s*subscriber/gi, "")
                  .replace(/VideoTentangInstagram\S*/gi, "")
                  .replace(/\n\s*\n\s*\n/g, "\n\n")
                  .trim();
              }
              const tNodes = document.querySelectorAll("ytd-transcript-segment-renderer .segment-text, #segments-container yt-formatted-string");
              if (tNodes && tNodes.length > 0) {
                const tLines = Array.from(tNodes).map(n => n.textContent.trim()).filter(Boolean);
                if (tLines.length > 0) res.transcript = tLines.join(" ");
              }
              const view = document.querySelector("#info-container span");
              if (view) res.views_count = parseNum(view.textContent);
              const like = document.querySelector("like-button-view-model button");
              if (like) res.likes_count = parseNum(like.getAttribute("aria-label") || like.textContent);
              const comm = document.querySelector("#comments #count span");
              if (comm) res.comments_count = parseNum(comm.textContent);
            }
            // Instagram
            else if (url.includes("instagram.com")) {
              const u = document.querySelector("header a[role='link']") || document.querySelector("article header a") || document.querySelector("h2");
              res.username = u?.textContent?.trim()?.replace(/^@/, "");
              if (!res.username) {
                const sm = window.location.href.match(/instagram\.com\/(?:stories\/)?([a-zA-Z0-9_\.]+)/);
                if (sm && !['p', 'reel', 'explore', 'stories'].includes(sm[1])) res.username = sm[1];
              }
              res.display_name = res.username ? `@${res.username}` : "Pengguna Instagram";
              const cap = document.querySelector("h1[dir='auto']") || document.querySelector("article span._a9zs") || document.querySelector("meta[property='og:description']");
              res.caption = cap?.textContent?.trim() || cap?.content;
              res.title = res.caption ? (res.caption.slice(0, 70) + "...") : `Instagram Post (${res.username || 'Media'})`;
              const lk = document.querySelector("section button span") || document.querySelector("a[href*='/liked_by/'] span");
              if (lk) res.likes_count = parseNum(lk.textContent);
            }
            // TikTok
            else if (url.includes("tiktok.com")) {
              const tu = document.querySelector("[data-e2e='user-title']");
              res.username = tu?.textContent?.trim()?.replace(/^@/, "");
              res.display_name = res.username ? `@${res.username}` : "TikTok Creator";
              const tc = document.querySelector("[data-e2e='browse-video-desc']");
              res.caption = tc?.textContent?.trim();
              res.title = res.caption ? (res.caption.slice(0, 70) + "...") : `TikTok Video @${res.username}`;
              const tlk = document.querySelector("[data-e2e='like-count']");
              if (tlk) res.likes_count = parseNum(tlk.textContent);
              const tcm = document.querySelector("[data-e2e='comment-count']");
              if (tcm) res.comments_count = parseNum(tcm.textContent);
              const tsh = document.querySelector("[data-e2e='share-count']");
              if (tsh) res.shares_count = parseNum(tsh.textContent);
            }
            // X / Twitter
            else if (url.includes("twitter.com") || url.includes("x.com")) {
              const xu = document.querySelector("[data-testid='User-Name']");
              if (xu) {
                const links = xu.querySelectorAll("a");
                res.display_name = links[0]?.textContent?.trim();
                res.username = links[1]?.textContent?.trim()?.replace(/^@/, "");
              }
              const xt = document.querySelector("[data-testid='tweetText']");
              res.caption = xt?.textContent?.trim();
              res.title = res.caption ? (res.caption.slice(0, 70) + "...") : "Postingan X (Twitter)";
              const xlk = document.querySelector("[data-testid='like']");
              if (xlk) res.likes_count = parseNum(xlk.textContent);
              const xcm = document.querySelector("[data-testid='reply']");
              if (xcm) res.comments_count = parseNum(xcm.textContent);
            }

            return res;
          }
        });
        if (results && results.result) {
          inPageMeta = results.result;
        }
      } catch (err) {
        console.warn("Scripting extraction error in popup:", err);
      }
    }

    btnText.textContent = "Mengirim ke Pipeline AI...";

    try {
      const payload = {
        url: targetUrl,
        source_channel: "BROWSER_EXTENSION",
        reporter_identifier: analystId,
        notes: notes || inPageMeta.caption || undefined,
        screenshot_base64: screenshotBase64 || undefined,
        media_image_url: inPageMeta.media_image_url || undefined,
        username: inPageMeta.username || undefined,
        display_name: inPageMeta.display_name || undefined,
        followers_count: inPageMeta.followers_count || 0,
        title: inPageMeta.title || undefined,
        caption: inPageMeta.caption || undefined,
        transcript: inPageMeta.transcript || undefined,
        likes_count: inPageMeta.likes_count || 0,
        views_count: inPageMeta.views_count || 0,
        comments_count: inPageMeta.comments_count || 0,
        shares_count: inPageMeta.shares_count || 0,
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
      resultDesc.textContent = `Konten ${data.platform ? data.platform.toUpperCase() : ''} berhasil dicatat ke antrean validasi bukti digital.`;
      if (data.content_id) {
        const link = document.getElementById("link-dashboard");
        if (link) link.href = `http://localhost:5173/#/contents/${data.content_id}`;
      }
      btnText.textContent = "✅ Berhasil Diproses";
    } catch (err) {
      alert("Gagal memproses triase: " + err.message);
      btnText.textContent = "⚡ Triase Konten";
      btnSubmit.disabled = false;
    }
  });
});
