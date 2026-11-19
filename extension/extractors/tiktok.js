// @ts-nocheck
/* cSpell:disable */
// Modular Extractor for TikTok (tiktok.com)
// Robust client-side DOM extraction for feeds, full-screen player, and modal video overlays

(function() {
  window.TilikExtractors = window.TilikExtractors || {};

  function parseCount(str) {
    if (!str || typeof str !== "string") return 0;
    const clean = str.trim().toLowerCase();
    let mult = 1;
    if (clean.endsWith("k") || clean.endsWith("rb")) mult = 1000;
    else if (clean.endsWith("m") || clean.endsWith("jt")) mult = 1000000;
    else if (clean.endsWith("b")) mult = 1000000000;
    const num = parseFloat(clean.replace(/[^0-9.]/g, ""));
    return isNaN(num) ? 0 : Math.round(num * mult);
  }

  function extractTikTok() {
    const pathname = window.location.pathname;
    const href = window.location.href;

    // 1. Ekstraksi Username & Video ID dari URL aktif
    const userMatch = pathname.match(/\/@([a-zA-Z0-9_\.]+)/);
    const videoMatch = pathname.match(/\/(?:video|photo)\/(\d+)/);

    let authorHandle = userMatch ? userMatch[1] : "";
    let videoId = videoMatch ? videoMatch[1] : "";

    // 2. Tentukan Container Utama (Modal / Detail Player / Feed Item aktif)
    const modalContainer = document.querySelector('[data-e2e="browse-video-container"]') ||
                           document.querySelector('[data-e2e="modal-content"]') ||
                           document.querySelector('div[role="dialog"]');
    const container = modalContainer || document.querySelector("main") || document.body;

    // 3. Auto-expand teks caption jika terpotong ('selengkapnya' / 'more')
    try {
      const expandBtn = container.querySelector(
        '[data-e2e="video-desc-expand"], button[class*="ButtonMore"], span[role="button"][class*="more"]'
      );
      if (expandBtn) expandBtn.click();
    } catch (_) {}

    // 4. Deteksi Akun Kreator dari DOM jika belum dari URL
    let authorName = "";
    const nicknameEl = container.querySelector(
      '[data-e2e="browser-nickname"], [data-e2e="user-title"], a[data-e2e="user-avatar"] + div a, a[href*="/@"] h3, h2[data-e2e="user-info-title"]'
    );
    if (nicknameEl) {
      authorName = (nicknameEl.innerText || nicknameEl.textContent || "").trim();
    }

    if (!authorHandle) {
      const userAnchor = container.querySelector('a[data-e2e="user-avatar"], a[href*="/@"]');
      if (userAnchor) {
        const uHref = userAnchor.getAttribute("href") || "";
        const uM = uHref.match(/\/@([a-zA-Z0-9_\.]+)/);
        if (uM) authorHandle = uM[1];
      }
    }

    // 5. Ekstraksi Naskah Caption / Deskripsi Video & Hashtag
    let cleanText = "";
    const descSelectors = [
      '[data-e2e="browse-video-desc"]',
      'h1[data-e2e="video-desc"]',
      '[data-e2e="user-post-item-desc"]',
      'div[data-e2e="video-desc"]',
      'h1[class*="H1VideoDesc"]',
      'div[class*="DivDescriptionContainer"]'
    ];

    for (const sel of descSelectors) {
      const descEl = container.querySelector(sel);
      if (descEl) {
        const raw = (descEl.innerText || descEl.textContent || "").trim();
        if (raw.length >= 3) {
          cleanText = raw;
          break;
        }
      }
    }

    // Fallback: meta tag description jika DOM kosong
    if (!cleanText || cleanText.length < 5) {
      const metaOg = document.querySelector('meta[property="og:description"], meta[name="description"]');
      if (metaOg) {
        cleanText = (metaOg.getAttribute("content") || "").trim();
      }
    }

    // Bersihkan spasi berlebih
    if (cleanText) {
      cleanText = cleanText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
    }

    // 6. Ekstraksi Metrik Interaksi (Likes, Comments, Shares)
    let likesCount = 0;
    let commentsCount = 0;
    let sharesCount = 0;

    const likeEl = container.querySelector('[data-e2e="like-count"], strong[data-e2e="browse-like-count"]');
    if (likeEl) likesCount = parseCount(likeEl.textContent);

    const commentEl = container.querySelector('[data-e2e="comment-count"], strong[data-e2e="browse-comment-count"]');
    if (commentEl) commentsCount = parseCount(commentEl.textContent);

    const shareEl = container.querySelector('[data-e2e="share-count"], strong[data-e2e="browse-share-count"]');
    if (shareEl) sharesCount = parseCount(shareEl.textContent);

    // 7. Bentuk Canonical URL
    let canonicalUrl = href.split("?")[0].replace(/\/+$/, "");
    if (videoId && authorHandle) {
      canonicalUrl = `https://www.tiktok.com/@${authorHandle}/video/${videoId}`;
    }

    // 8. Bentuk Judul Informatif
    let title = "";
    if (cleanText) {
      const firstLine = cleanText.split("\n")[0].split(/[.!?]/)[0].trim();
      title = firstLine.length > 80 ? (firstLine.slice(0, 77) + "...") : firstLine;
    } else {
      title = authorHandle ? `TikTok Video oleh @${authorHandle}` : "TikTok Post Video";
    }

    return {
      platform: "tiktok",
      source_url: canonicalUrl,
      dom_text: cleanText,
      title: title,
      username: authorHandle || "tiktok_user",
      display_name: authorName || (authorHandle ? `@${authorHandle}` : "Pengguna TikTok"),
      likes_count: likesCount,
      comments_count: commentsCount,
      shares_count: sharesCount,
      has_media: true,
      extraction_method: "tiktok_dom_post",
      container: container
    };
  }

  window.TilikExtractors.tiktok = {
    extract: extractTikTok
  };
})();
