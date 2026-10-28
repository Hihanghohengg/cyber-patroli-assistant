// Injected content script for Cyber Patrol Assistant
// Automated In-Page Screen & DOM Metadata Extractor

(function() {
  if (document.getElementById("cyber-patrol-floating-badge")) return;

  // Helper parser: converts "1.2M", "45.3K", "1,200", "50 rb" into clean integer numbers
  function parseMetricNumber(text) {
    if (!text) return 0;
    const clean = text.trim().toLowerCase().replace(/,/g, ".");
    const numMatch = clean.match(/([\d\.]+)/);
    if (!numMatch) return 0;
    let val = parseFloat(numMatch[1]);
    if (clean.includes("m") || clean.includes("jt") || clean.includes("juta")) {
      val = val * 1000000;
    } else if (clean.includes("k") || clean.includes("rb") || clean.includes("ribu")) {
      val = val * 1000;
    }
    return Math.round(val);
  }

  // Smart DOM Parser per platform
  function extractPlatformMetadata() {
    const url = window.location.href;
    const lowerUrl = url.toLowerCase();

    let data = {
      url: url,
      platform: "web",
      username: null,
      display_name: null,
      followers_count: 0,
      title: null,
      caption: null,
      likes_count: 0,
      views_count: 0,
      comments_count: 0,
      shares_count: 0,
    };

    // ───────────────────────────────────────────
    // 1. YOUTUBE (Regular & Shorts)
    // ───────────────────────────────────────────
    if (lowerUrl.includes("youtube.com") || lowerUrl.includes("youtu.be")) {
      data.platform = "youtube";

      // Title
      const titleEl = document.querySelector("#title h1 yt-formatted-string") ||
                      document.querySelector("ytd-watch-metadata #title") ||
                      document.querySelector("h2.ytd-reel-player-header-renderer") ||
                      document.querySelector("meta[name='title']");
      data.title = titleEl?.textContent?.trim() || titleEl?.content || document.title.replace(" - YouTube", "");

      // Channel / Creator Name & Handle
      const channelEl = document.querySelector("#channel-name a") ||
                        document.querySelector("#owner #text a") ||
                        document.querySelector("ytd-channel-name a") ||
                        document.querySelector("ytd-reel-player-header-renderer #channel-name a");
      data.display_name = channelEl?.textContent?.trim();

      const handleEl = document.querySelector("#owner-sub-count") || document.querySelector("#channel-header #subscriber-count");
      if (handleEl) {
        data.followers_count = parseMetricNumber(handleEl.textContent);
      }

      // Username fallback
      const chUrl = channelEl?.getAttribute("href") || "";
      if (chUrl.includes("@")) {
        data.username = chUrl.split("@")[1].split("/")[0];
      } else {
        data.username = data.display_name || "youtube_creator";
      }

      // Views
      const viewEl = document.querySelector("#info-container span") ||
                     document.querySelector("ytd-video-view-count-renderer .view-count") ||
                     document.querySelector(".ytd-watch-info-text #count");
      if (viewEl) {
        data.views_count = parseMetricNumber(viewEl.textContent);
      }

      // Likes
      const likeBtn = document.querySelector("like-button-view-model button") ||
                      document.querySelector("#segmented-like-button button") ||
                      document.querySelector("ytd-toggle-button-renderer yt-button-shape button");
      if (likeBtn) {
        data.likes_count = parseMetricNumber(likeBtn.getAttribute("aria-label") || likeBtn.textContent);
      }

      // Comments
      const commentCountEl = document.querySelector("#comments #count span:first-child");
      if (commentCountEl) {
        data.comments_count = parseMetricNumber(commentCountEl.textContent);
      }

      // Caption / Description with targeted selectors
      const descTextEl = document.querySelector("#description-inline-expander yt-attributed-string") ||
                         document.querySelector("#description-text") ||
                         document.querySelector("ytd-text-inline-expander #plain-snippet-text") ||
                         document.querySelector("#description yt-formatted-string") ||
                         document.querySelector("meta[name='description']");
      
      let rawCaption = descTextEl?.textContent?.trim() || descTextEl?.content;
      if (!rawCaption) {
        const fallbackExpander = document.querySelector("#description-inline-expander");
        rawCaption = fallbackExpander?.textContent?.trim();
      }

      // Filter out YouTube UI button phrases
      if (rawCaption) {
        data.caption = rawCaption
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

      // Check if YouTube Transcript sidebar/panel is active
      const transcriptNodes = document.querySelectorAll("ytd-transcript-segment-renderer .segment-text, #segments-container yt-formatted-string");
      if (transcriptNodes && transcriptNodes.length > 0) {
        const tLines = Array.from(transcriptNodes).map(n => n.textContent.trim()).filter(Boolean);
        if (tLines.length > 0) {
          data.transcript = tLines.join(" ");
        }
      }
    }

    // ───────────────────────────────────────────
    // 2. INSTAGRAM (Posts, Reels, Stories)
    // ───────────────────────────────────────────
    else if (lowerUrl.includes("instagram.com")) {
      data.platform = "instagram";

      // Username & Display Name
      const userEl = document.querySelector("header a[role='link']") ||
                     document.querySelector("article header a") ||
                     document.querySelector("h2") ||
                     document.querySelector("span[dir='auto'] a");
      data.username = userEl?.textContent?.trim()?.replace(/^@/, "");

      // Fallback from URL if in path (e.g. instagram.com/stories/username/123)
      if (!data.username) {
        const storyMatch = url.match(/instagram\.com\/(?:stories\/)?([a-zA-Z0-9_\.]+)/);
        if (storyMatch && !['p', 'reel', 'explore', 'stories'].includes(storyMatch[1])) {
          data.username = storyMatch[1];
        }
      }
      data.display_name = data.username ? `@${data.username}` : "Pengguna Instagram";

      // Caption
      const captionEl = document.querySelector("h1[dir='auto']") ||
                        document.querySelector("article span._a9zs") ||
                        document.querySelector("div[data-ad-preview='message']") ||
                        document.querySelector("meta[property='og:description']");
      data.caption = captionEl?.textContent?.trim() || captionEl?.content;
      data.title = data.caption ? (data.caption.slice(0, 70) + "...") : `Instagram Post (${data.username || 'Media'})`;

      // Likes & Comments
      const likeEl = document.querySelector("section button span:has-text('')") ||
                     document.querySelector("a[href*='/liked_by/'] span");
      if (likeEl) {
        data.likes_count = parseMetricNumber(likeEl.textContent);
      }
    }

    // ───────────────────────────────────────────
    // 3. TIKTOK (Video / Profile)
    // ───────────────────────────────────────────
    else if (lowerUrl.includes("tiktok.com")) {
      data.platform = "tiktok";

      const userEl = document.querySelector("[data-e2e='user-title']") ||
                     document.querySelector("[data-e2e='browse-username']");
      data.username = userEl?.textContent?.trim()?.replace(/^@/, "");
      data.display_name = data.username ? `@${data.username}` : "TikTok Creator";

      const descEl = document.querySelector("[data-e2e='browse-video-desc']") ||
                     document.querySelector("meta[property='og:description']");
      data.caption = descEl?.textContent?.trim() || descEl?.content;
      data.title = data.caption ? (data.caption.slice(0, 70) + "...") : `TikTok Video @${data.username}`;

      const likeEl = document.querySelector("[data-e2e='like-count']");
      if (likeEl) data.likes_count = parseMetricNumber(likeEl.textContent);

      const commentEl = document.querySelector("[data-e2e='comment-count']");
      if (commentEl) data.comments_count = parseMetricNumber(commentEl.textContent);

      const shareEl = document.querySelector("[data-e2e='share-count']");
      if (shareEl) data.shares_count = parseMetricNumber(shareEl.textContent);
    }

    // ───────────────────────────────────────────
    // 4. X / TWITTER (Tweets / Posts)
    // ───────────────────────────────────────────
    else if (lowerUrl.includes("twitter.com") || lowerUrl.includes("x.com")) {
      data.platform = "x";

      const userHeader = document.querySelector("[data-testid='User-Name']");
      if (userHeader) {
        const links = userHeader.querySelectorAll("a");
        data.display_name = links[0]?.textContent?.trim();
        data.username = links[1]?.textContent?.trim()?.replace(/^@/, "");
      }

      const tweetEl = document.querySelector("[data-testid='tweetText']");
      data.caption = tweetEl?.textContent?.trim();
      data.title = data.caption ? (data.caption.slice(0, 70) + "...") : "Postingan X (Twitter)";

      const likeBtn = document.querySelector("[data-testid='like']");
      if (likeBtn) data.likes_count = parseMetricNumber(likeBtn.textContent);

      const replyBtn = document.querySelector("[data-testid='reply']");
      if (replyBtn) data.comments_count = parseMetricNumber(replyBtn.textContent);

      const retweetBtn = document.querySelector("[data-testid='retweet']");
      if (retweetBtn) data.shares_count = parseMetricNumber(retweetBtn.textContent);
    }

    // Generic Fallback
    if (!data.caption) {
      data.caption = document.querySelector("meta[property='og:description']")?.content ||
                     document.querySelector("meta[name='description']")?.content ||
                     document.title;
    }
    if (!data.title) {
      data.title = document.querySelector("meta[property='og:title']")?.content || document.title;
    }

    return data;
  }

  // Build floating badge button
  const btn = document.createElement("div");
  btn.id = "cyber-patrol-floating-badge";
  btn.innerHTML = `
    <div class="cp-badge-icon">🛡</div>
    <span class="cp-badge-text">Triase</span>
  `;

  btn.addEventListener("click", async () => {
    btn.classList.add("cp-loading");
    btn.querySelector(".cp-badge-text").textContent = "Merekam layar...";

    // 1. Ambil screenshot visible tab saat ini persis seperti yang tampil di monitor analis
    let screenshotBase64 = null;
    try {
      const captureRes = await new Promise((resolve) => {
        chrome.runtime.sendMessage({ action: "capture_tab_screenshot" }, (res) => {
          if (chrome.runtime.lastError) {
            console.warn("Background capture warning:", chrome.runtime.lastError.message);
            resolve({ ok: false });
          } else {
            resolve(res || { ok: false });
          }
        });
      });

      if (captureRes && captureRes.ok && captureRes.dataUrl) {
        screenshotBase64 = captureRes.dataUrl;
        console.log("📸 Tangkapan layar monitor berhasil diambil, ukuran:", screenshotBase64.length);
      }
    } catch (err) {
      console.warn("Gagal mengambil tangkapan layar visible tab:", err);
    }

    // 2. Ekstraksi otomatis metadata postingan (username, likes, views, caption, dsb)
    btn.querySelector(".cp-badge-text").textContent = "Mengekstrak DOM...";
    const extracted = extractPlatformMetadata();

    // 3. Ekstraksi visual media thumbnail jika ada
    let mediaImageUrl = null;
    try {
      const ogImg = document.querySelector("meta[property='og:image']")?.content ||
                    document.querySelector("meta[name='twitter:image']")?.content;
      if (ogImg && !ogImg.includes("favicon")) {
        mediaImageUrl = ogImg;
      }
    } catch (e) {}

    btn.querySelector(".cp-badge-text").textContent = "Menganalisis...";

    // 4. Kirim payload lengkap terstruktur ke API
    try {
      const payload = {
        url: window.location.href,
        source_channel: "BROWSER_EXTENSION",
        reporter_identifier: "In-Page-Floating-Agent",
        notes: extracted.caption || "Intake via tombol floating",
        screenshot_base64: screenshotBase64 || undefined,
        media_image_url: mediaImageUrl || undefined,
        username: extracted.username || undefined,
        display_name: extracted.display_name || undefined,
        followers_count: extracted.followers_count || 0,
        title: extracted.title || undefined,
        caption: extracted.caption || undefined,
        likes_count: extracted.likes_count || 0,
        views_count: extracted.views_count || 0,
        comments_count: extracted.comments_count || 0,
        shares_count: extracted.shares_count || 0,
      };

      const res = await fetch("http://localhost:8000/api/v1/assistant/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok) {
        btn.querySelector(".cp-badge-text").textContent = `Tiket: ${data.ticket_number}`;
        btn.classList.remove("cp-loading");
        btn.classList.add("cp-success");

        showTriageResultModal(data, extracted);

        setTimeout(() => {
          btn.classList.remove("cp-success");
          btn.querySelector(".cp-badge-text").textContent = "Triase";
        }, 5000);
      } else {
        throw new Error(data.detail || "Gagal memproses triase");
      }
    } catch (err) {
      btn.classList.remove("cp-loading");
      btn.classList.add("cp-error");
      btn.querySelector(".cp-badge-text").textContent = "Gagal";
      showTriageErrorModal(err.message);
      setTimeout(() => {
        btn.classList.remove("cp-error");
        btn.querySelector(".cp-badge-text").textContent = "Triase";
      }, 4000);
    }
  });

  function showTriageResultModal(data, meta) {
    const oldModal = document.getElementById("cp-triage-modal");
    if (oldModal) oldModal.remove();

    const modal = document.createElement("div");
    modal.id = "cp-triage-modal";
    const dashboardUrl = data.dashboard_url || (data.content_id ? `http://localhost:5173/#/contents/${data.content_id}` : "http://localhost:5173/#/contents");

    modal.innerHTML = `
      <div class="cp-modal-header">
        <div class="cp-modal-title">
          <span class="cp-icon">🛡</span>
          <span>Triase & Ekstraksi Metadata Berhasil</span>
        </div>
        <button class="cp-modal-close" id="cp-close-btn" title="Tutup">&times;</button>
      </div>
      <div class="cp-modal-body">
        <div class="cp-info-row">
          <span class="cp-info-label">Nomor Tiket:</span>
          <span class="cp-info-value cp-ticket-tag">${data.ticket_number}</span>
        </div>
        <div class="cp-info-row">
          <span class="cp-info-label">Akun / Kreator:</span>
          <span class="cp-info-value">${meta?.username ? '@' + meta.username : (data.platform || 'WEB').toUpperCase()}</span>
        </div>
        <div class="cp-info-row">
          <span class="cp-info-label">Metrik:</span>
          <span class="cp-info-value" style="font-size: 11px;">👍 ${meta?.likes_count || 0} | 👁 ${meta?.views_count || 0} | 💬 ${meta?.comments_count || 0}</span>
        </div>
        <div class="cp-action-buttons">
          <a href="${dashboardUrl}" target="_blank" class="cp-btn cp-btn-primary" id="cp-open-dashboard-btn">
            <span>Buka di Dashboard</span>
            <span>↗</span>
          </a>
          <button type="button" class="cp-btn cp-btn-secondary" id="cp-copy-link-btn">
            <span>Salin Link</span>
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    document.getElementById("cp-close-btn").addEventListener("click", () => {
      modal.remove();
    });

    const copyBtn = document.getElementById("cp-copy-link-btn");
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(dashboardUrl).then(() => {
        copyBtn.innerHTML = "<span>Tersalin!</span>";
        setTimeout(() => {
          copyBtn.innerHTML = "<span>Salin Link</span>";
        }, 2000);
      });
    });
  }

  function showTriageErrorModal(errorMsg) {
    const oldModal = document.getElementById("cp-triage-modal");
    if (oldModal) oldModal.remove();

    const modal = document.createElement("div");
    modal.id = "cp-triage-modal";
    modal.innerHTML = `
      <div class="cp-modal-header" style="border-bottom-color: rgba(244,63,94,0.3);">
        <div class="cp-modal-title" style="color: #fda4af;">
          <span class="cp-icon">⚠️</span>
          <span>Triase Gagal</span>
        </div>
        <button class="cp-modal-close" id="cp-close-error-btn">&times;</button>
      </div>
      <div class="cp-modal-body">
        <p style="font-size:12px; color:#cbd5e1; margin-bottom:12px;">${errorMsg}</p>
        <button type="button" class="cp-btn cp-btn-secondary" id="cp-close-error-btn2" style="width:100%;">
          <span>Tutup</span>
        </button>
      </div>
    `;
    document.body.appendChild(modal);
    const close = () => modal.remove();
    document.getElementById("cp-close-error-btn")?.addEventListener("click", close);
    document.getElementById("cp-close-error-btn2")?.addEventListener("click", close);
  }

  document.body.appendChild(btn);
})();
