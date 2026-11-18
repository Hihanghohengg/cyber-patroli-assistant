// @ts-nocheck
/* cSpell:disable */
// Popup Controller for TILIK Extension
// Universal 3-Layer Content Acquisition & NIST FIPS 198-1 Verification Display

(() => {
  "use strict";

  let ACTIVE_SERVER_URL = "http://127.0.0.1:8000";
let currentTab = null;
let currentPlatform = "unknown";

function detectPlatform(url) {
  if (!url) return "unknown";
  const lower = url.toLowerCase();
  if (lower.includes("tiktok.com")) return "tiktok";
  if (lower.includes("youtube.com") || lower.includes("youtu.be")) return "youtube";
  if (lower.includes("instagram.com")) return "instagram";
  if (lower.includes("facebook.com")) return "facebook";
  if (lower.includes("threads.net") || lower.includes("threads.com")) return "threads";
  if (lower.includes("twitter.com") || lower.includes("x.com")) return "x";
  return "news";
}

function updatePlatformBadge(platform) {
  const badge = document.getElementById("platform-badge");
  if (!badge) return;
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
  } else if (platform === "facebook") {
    badge.classList.add("platform-news");
    badge.textContent = "Facebook";
  } else if (platform === "threads") {
    badge.classList.add("platform-threads");
    badge.textContent = "Threads";
  } else if (platform === "x") {
    badge.classList.add("platform-x");
    badge.textContent = "X (Twitter)";
  } else if (platform === "news") {
    badge.classList.add("platform-news");
    badge.textContent = "Portal Berita";
  } else {
    badge.classList.add("platform-unknown");
    badge.textContent = platform.toUpperCase();
  }
}

async function checkServerHealth(serverUrl) {
  const indicator = document.getElementById("conn-badge");
  const text = document.getElementById("conn-text");
  const target = (serverUrl || ACTIVE_SERVER_URL).replace(/\/+$/, "");

  try {
    const res = await fetch(`${target}/health`, { method: "GET", signal: AbortSignal.timeout(2500) });
    if (res.ok) {
      ACTIVE_SERVER_URL = target;
      if (indicator) indicator.className = "conn-status";
      if (text) text.textContent = "Terhubung";
      return true;
    }
  } catch (err) {
    // offline
  }

  if (indicator) indicator.className = "conn-status disconnected";
  if (text) text.textContent = "Server Offline";
  return false;
}

document.addEventListener("DOMContentLoaded", async () => {
  const urlDisplayElement = document.getElementById("current-url");
  const btnSubmit = document.getElementById("btn-submit");
  const btnText = document.getElementById("btn-text");
  const resultCard = document.getElementById("result-card");
  const resultTicket = document.getElementById("result-ticket");
  const resultDesc = document.getElementById("result-desc");
  const resultCryptoBadge = document.getElementById("result-crypto-badge");
  const resultCryptoInfo = document.getElementById("result-crypto-info");
  const operatorIdInput = document.getElementById("operator-id");
  const serverUrlInput = document.getElementById("server-url");
  const notesInput = document.getElementById("notes");
  const linkDashboard = document.getElementById("link-dashboard");
  const linkFooter = document.getElementById("link-footer-dashboard");

  // 1. Load saved configuration from chrome.storage.local
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["operator_id", "server_url"], (res) => {
      if (res.operator_id) operatorIdInput.value = res.operator_id;
      if (res.server_url) serverUrlInput.value = res.server_url;
      ACTIVE_SERVER_URL = serverUrlInput.value.trim() || "http://127.0.0.1:8000";
      checkServerHealth(ACTIVE_SERVER_URL);
    });
  } else {
    checkServerHealth(ACTIVE_SERVER_URL);
  }

  // Auto-save configuration on input change
  const saveConfig = () => {
    const op = operatorIdInput.value.trim() || "op_d23_01";
    const srv = serverUrlInput.value.trim() || "http://127.0.0.1:8000";
    ACTIVE_SERVER_URL = srv;
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({ operator_id: op, server_url: srv });
    }
    checkServerHealth(srv);
  };
  operatorIdInput.addEventListener("change", saveConfig);
  serverUrlInput.addEventListener("change", saveConfig);

  // 2. Query active browser tab
  if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url) {
        currentTab = tab;
        urlDisplayElement.textContent = tab.url;
        currentPlatform = detectPlatform(tab.url);
        updatePlatformBadge(currentPlatform);
      } else {
        urlDisplayElement.textContent = "Tidak dapat mendeteksi URL tab aktif.";
      }
    } catch (err) {
      urlDisplayElement.textContent = "Gagal mengambil tab: " + err.message;
    }
  } else {
    urlDisplayElement.textContent = "http://127.0.0.1:8000/dashboard/#/contents (Mode Standalone)";
    currentPlatform = "news";
    updatePlatformBadge("news");
  }

  // 3. Handle Submit Action
  btnSubmit.addEventListener("click", async () => {
    if (btnSubmit.disabled) return;
    btnSubmit.disabled = true;
    saveConfig();
    const targetUrl = currentTab ? currentTab.url : urlDisplayElement.textContent;
    if (!targetUrl || targetUrl.startsWith("chrome://") || targetUrl.startsWith("edge://")) {
      alert("Buka postingan media sosial atau portal berita publik sebelum melakukan triase!");
      return;
    }

    const operatorId = operatorIdInput.value.trim() || "op_d23_01";
    const notes = notesInput.value.trim();

    btnSubmit.disabled = true;
    btnText.textContent = "Mengambil Tangkapan Layar...";

    // Capture tab screenshot (sembunyikan badge floating di halaman terlebih dahulu)
    let screenshotBase64 = null;
    if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.captureVisibleTab) {
      try {
        if (chrome.scripting && currentTab?.id) {
          await chrome.scripting.executeScript({
            target: { tabId: currentTab.id },
            func: () => {
              const b = document.getElementById("cyber-patrol-floating-badge");
              if (b) {
                b.classList.add("cp-capturing");
                b.style.display = "none";
              }
              const m = document.getElementById("cp-triage-modal");
              if (m) {
                m.classList.add("cp-capturing");
                m.style.display = "none";
              }
            }
          }).catch(() => {});
          await new Promise(r => setTimeout(r, 120));
        }

        screenshotBase64 = await new Promise((resolve) => {
          chrome.tabs.captureVisibleTab({ format: "jpeg", quality: 85 }, (dataUrl) => {
            const err = chrome.runtime.lastError;
            if (err || !dataUrl) {
              console.warn("[TILIK Popup] captureVisibleTab warning:", err?.message || "empty dataUrl");
              resolve(null);
            } else {
              resolve(dataUrl);
            }
          });
        });

        // Kembalikan tombol di halaman
        if (chrome.scripting && currentTab?.id) {
          chrome.scripting.executeScript({
            target: { tabId: currentTab.id },
            func: () => {
              const b = document.getElementById("cyber-patrol-floating-badge");
              if (b) {
                b.classList.remove("cp-capturing");
                b.style.display = "";
              }
              const m = document.getElementById("cp-triage-modal");
              if (m) {
                m.classList.remove("cp-capturing");
                m.style.display = "block";
              }
            }
          }).catch(() => {});
        }
      } catch (err) {
        console.warn("Screenshot capture note:", err);
      }
    }

    btnText.textContent = "Ekstraksi Universal 3-Layer...";

    // Execute Universal 3-Layer extraction inside active tab
    let inPageMeta = {};
    if (typeof chrome !== "undefined" && chrome.scripting && currentTab?.id) {
      try {
        const [results] = await chrome.scripting.executeScript({
          target: { tabId: currentTab.id },
          func: () => {
            // Prioritas 0: User Highlight
            const userSelection = window.getSelection() ? window.getSelection().toString().trim() : "";
            if (userSelection && userSelection.length >= 10) {
              return {
                extraction_method: "user_highlight",
                dom_text: userSelection,
                title: userSelection.length > 80 ? (userSelection.slice(0, 80) + "...") : userSelection,
              };
            }

            const url = window.location.href.toLowerCase();
            const host = window.location.hostname.toLowerCase();
            const isSocial = url.includes("twitter.com") || url.includes("x.com") ||
                             url.includes("instagram.com") || url.includes("facebook.com") ||
                             url.includes("threads.net") || url.includes("tiktok.com");

            if (isSocial) {
              // Layer 2: Viewport Center Semantic Article Container
              const cx = window.innerWidth / 2;
              const cy = window.innerHeight / 2;
              const centerEl = document.elementFromPoint(cx, cy);
              const container = document.querySelector("div[role='dialog'] article") ||
                                document.querySelector("div[role='dialog']") ||
                                centerEl?.closest("article, [role='article'], [data-testid='tweet'], div[role='dialog'], main, .x1y1aw1k") ||
                                document.querySelector("article, [role='article'], [data-testid='tweet'], main[role='main']");

              if (container) {
                let clean = "";

                // Prioritaskan elemen teks postingan terisolasi
                if (host.includes("instagram.com")) {
                  const h1El = container.querySelector("h1, h1 span, h1._a9zc");
                  if (h1El && h1El.textContent.trim().length >= 10) {
                    clean = h1El.textContent.trim();
                  }
                  if (!clean) {
                    const firstSpan = container.querySelector("div._a9zs span[dir='auto'], span._ap3a[dir='auto']");
                    if (firstSpan && firstSpan.textContent.trim().length >= 10) {
                      clean = firstSpan.textContent.trim();
                    }
                  }
                } else if (host.includes("twitter.com") || host.includes("x.com")) {
                  clean = container.querySelector('[data-testid="tweetText"]')?.textContent?.trim() || "";
                } else if (host.includes("tiktok.com")) {
                  clean = container.querySelector('[data-e2e="browse-video-desc"], [data-e2e="user-post-item-desc"]')?.textContent?.trim() || "";
                } else if (host.includes("facebook.com")) {
                  clean = container.querySelector('div[data-ad-preview="message"]')?.textContent?.trim() || "";
                }

                // Fallback: Clone node dan buang komentar
                if (!clean || clean.length < 15) {
                  const clone = container.cloneNode(true);
                  clone.querySelectorAll(
                    "script, style, svg, nav, button, iframe, noscript, dialog, ul li, " +
                    "ul div[role='menuitem'], ul > div:nth-child(n+2), section, form, textarea"
                  ).forEach(e => e.remove());
                  clean = clone.innerText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
                }

                // Pembersihan artefak sosial media
                if (clean) {
                  for (const m of ["Lihat terjemahan", "See translation", "View translation", "Lihat semua komentar"]) {
                    if (clean.includes(m)) clean = clean.split(m)[0].trim();
                  }
                  clean = clean.replace(/Disukai oleh.*?lainnya/gi, " ");
                  clean = clean.replace(/Liked by.*?others/gi, " ");

                  // Bersihkan pemutar video (misal: 00:00 / 09:28)
                  clean = clean.replace(/\d{1,2}:\d{2}\s*[\/|\\]\s*\d{1,2}:\d{2}/g, " ");

                  // Bersihkan cap waktu tweet & metrik tayangan/kutipan
                  clean = clean.replace(/\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*[·•\u00b7\u2022]\s*[A-Za-z]{3}\s*\d{1,2},\s*\d{4}/g, " ");
                  clean = clean.replace(/[·•\u00b7\u2022\s]*\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b/g, " ");
                  clean = clean.replace(/[·•\u00b7\u2022\s]*\d+[\d\.,]*[KkMm]?\s*(?:Views|View quotes|views|quotes|suka|likes|Retweets|reposts|Bookmarks|bookmarked)(?=[^a-zA-Z]|$)/gi, " ");

                  // Bersihkan header akun yang menempel di awal (misal: "Sumatera Adil & Federal@indepenSumateraPRABOWO..." -> "PRABOWO...")
                  clean = clean.replace(/^(?:[^\n@]{0,50})?@[a-zA-Z0-9_\.]*?[a-z0-9](?=[A-Z]{2,}|\d+\.)\s*/i, "").trim();
                  clean = clean.replace(/^(?:[A-Z][a-zA-Z0-9\s._-]+)?@([a-zA-Z0-9_]{1,20}?)(?=[A-Z]{2,}|\d+\.|\b)\s*/i, "").trim();
                  clean = clean.replace(/^(?:[A-Z][a-zA-Z0-9\s._-]{0,40})?@[a-zA-Z0-9_]+(?:\s*[·•]\s*[\w\d]+)?(?:\s*(?=\d+\.))?\s*/i, "").trim();
                  clean = clean.replace(/^[A-Z][a-zA-Z0-9\s._-]+@[a-zA-Z0-9_]+\s*/i, "").trim();

                  clean = clean.replace(/\b\d+\s*(?:hari|jam|m|menit|d|detik|w|minggu)\s*(?:yang\s+lalu)?\s*(?:Kirim)?$/gi, "").trim();
                  clean = clean.replace(/\s+/g, " ").trim();
                }

                const permalink = container.querySelector("a[href*='/status/'], a[href*='/p/'], a[href*='/reel/'], a[href*='/posts/'], a[href*='/videos/']")?.href;
                const timeStr = container.querySelector("time[datetime], time")?.getAttribute("datetime");

                return {
                  extraction_method: "semantic_article",
                  dom_text: clean,
                  title: clean.length > 80 ? (clean.slice(0, 80) + "...") : clean,
                  source_url: permalink || window.location.href,
                  posted_at: timeStr || undefined,
                };
              }
            }

            // Layer 1: OpenGraph & JSON-LD (News & YouTube)
            const ogTitle = document.querySelector('meta[property="og:title"]')?.content ||
                            document.querySelector('meta[name="twitter:title"]')?.content || document.title;
            const ogDesc = document.querySelector('meta[property="og:description"]')?.content ||
                           document.querySelector('meta[name="description"]')?.content || "";
            const ogImg = document.querySelector('meta[property="og:image"]')?.content;
            const ogUrl = document.querySelector('meta[property="og:url"]')?.content ||
                          document.querySelector('link[rel="canonical"]')?.href || window.location.href;

            const mainEl = document.querySelector("article, main, .read__content, .detail__body-text, #article-body, .it-detail");
            let bodyText = "";
            if (mainEl) {
              const clone = mainEl.cloneNode(true);
              clone.querySelectorAll("script, style, svg, nav, button, iframe, noscript").forEach(e => e.remove());
              bodyText = clone.innerText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
            }

            return {
              extraction_method: "opengraph_jsonld",
              title: ogTitle,
              dom_text: bodyText || ogDesc || ogTitle,
              source_url: ogUrl,
              media_image_url: ogImg && !ogImg.includes("favicon") ? ogImg : undefined,
            };
          }
        });
        if (results && results.result) inPageMeta = results.result;
      } catch (err) {
        console.warn("Scripting extraction warning:", err);
      }
    }

    btnText.textContent = "Penyegelan HMAC-SHA256...";

    // Strict ISO-8601 UTC timestamp
    const capturedAtUtc = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    const domText = inPageMeta.dom_text || notes || targetUrl;
    const method = inPageMeta.extraction_method || "fallback_dom";

    let targetCleanUrl = inPageMeta.source_url || targetUrl;
    if (targetCleanUrl.includes("instagram.com")) {
      const igMatch = targetCleanUrl.match(/(https?:\/\/(?:www\.)?instagram\.com\/(?:p|reel|reels|tv)\/[A-Za-z0-9_-]+)/i);
      if (igMatch) {
        targetCleanUrl = igMatch[1] + "/";
      }
    }

    const payload = {
      url: targetCleanUrl,
      source_channel: "BROWSER_EXTENSION",
      reporter_identifier: operatorId,
      operator_id: operatorId,
      captured_at_utc: capturedAtUtc,
      ocr_text: "",
      notes: `[AKUISISI: ${method.toUpperCase()}] ${notes ? notes + ' | ' : ''}${domText.slice(0, 150)}...`,
      screenshot_base64: screenshotBase64 || null,
      screenshotBase64: screenshotBase64 || null,
      media_image_url: inPageMeta.media_image_url || undefined,
      title: inPageMeta.title || undefined,
      caption: domText || undefined,
      posted_at: inPageMeta.posted_at || undefined,
    };

    try {
      // Send intake via background service worker
      const responseData = await new Promise((resolve, reject) => {
        if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
          chrome.runtime.sendMessage({ action: "submit_intake", payload }, (bgRes) => {
            if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
            else if (bgRes && bgRes.ok) resolve(bgRes.data);
            else reject(new Error((bgRes && (bgRes.error || bgRes.data?.detail)) || "Gagal mengirim intake ke server."));
          });
        } else {
          // Direct fetch fallback
          fetch(`${ACTIVE_SERVER_URL}/api/v1/assistant/intake`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          })
            .then(res => res.json())
            .then(resolve)
            .catch(reject);
        }
      });

      resultCard.style.display = "block";
      resultTicket.textContent = responseData.ticket_number;

      const isVerified = responseData.verification_status === "VERIFIED";
      resultCryptoBadge.textContent = isVerified ? "🛡️ VERIFIED (NIST FIPS 198-1)" : "⚠️ UNVERIFIED";
      resultCryptoBadge.style.color = isVerified ? "#34d399" : "#f87171";
      resultCryptoBadge.style.borderColor = isVerified ? "#059669" : "#dc2626";

      const hmacShort = responseData.hmac_tag ? `${responseData.hmac_tag.slice(0, 24)}...` : "Tersimpan";
      resultCryptoInfo.innerHTML = `
        <strong>Operator:</strong> ${operatorId}<br/>
        <strong>Metode:</strong> ${method.toUpperCase()}<br/>
        <strong>HMAC-SHA256:</strong> ${hmacShort}
      `;

      resultDesc.textContent = responseData.ai_summary
        ? `[${responseData.ai_status || 'AMAN'} - ${responseData.ai_predicted_label || 'NETRAL'}] ${responseData.ai_summary}`
        : "Bukti digital telah terikat integritasnya dan tercatat di antrean intelijen.";

      const dashUrl = responseData.dashboard_url || `${ACTIVE_SERVER_URL}/dashboard/#/contents/${responseData.content_id}`;
      linkDashboard.href = dashUrl;
      linkFooter.href = `${ACTIVE_SERVER_URL}/dashboard/#/contents`;

      btnText.textContent = "✅ Berhasil Disegel & Dikirim";
      setTimeout(() => {
        btnText.textContent = "⚡ Triase Konten (Universal 3-Layer)";
        btnSubmit.disabled = false;
      }, 4000);
    } catch (err) {
      let msg = err.message || String(err);
      if (msg === "[object Object]") msg = `Pastikan server backend aktif di ${ACTIVE_SERVER_URL}`;
      alert("Gagal memproses triase:\n" + msg);
      btnText.textContent = "⚡ Triase Konten (Universal 3-Layer)";
      btnSubmit.disabled = false;
    }
  });
});
})();
