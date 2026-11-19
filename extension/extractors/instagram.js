// @ts-nocheck
/* cSpell:disable */
// Modular Extractor for Instagram (instagram.com)

(function() {
  window.TilikExtractors = window.TilikExtractors || {};

  function extractInstagram() {
    // 1. Isolasi container modal jika aktif
    const igModal = document.querySelector("div[role='dialog']");
    const container = igModal ? (igModal.querySelector("article") || igModal) : (document.querySelector("article") || document.body);

    let authorHandle = "";
    let authorName = "";

    // Deteksi akun pengunggah
    const userAnchor = container.querySelector("header a[role='link'], h2 a, a[role='link'][href*='/']");
    if (userAnchor) {
      authorName = userAnchor.textContent.trim();
      const href = userAnchor.getAttribute("href") || "";
      const match = href.match(/\/([a-zA-Z0-9_\.]+)/);
      if (match && !["explore", "direct", "stories"].includes(match[1])) {
        authorHandle = match[1];
      }
    }

    // Auto-click 'selengkapnya' jika ada
    try {
      const moreButtons = container.querySelectorAll("span[role='button'], div[role='button'], button");
      for (const b of moreButtons) {
        const txt = (b.textContent || "").trim().toLowerCase();
        if (txt.includes("selengkapnya") || txt.includes("more")) {
          b.click();
          break;
        }
      }
    } catch (_) {}

    // Ekstraksi Caption
    let cleanText = "";
    const captionNodes = container.querySelectorAll("div._a9zs span[dir='auto'], div._a9zs, h1 span[dir='auto'], span._ap3a[dir='auto']");
    for (const node of captionNodes) {
      if (node.closest("button, header, div[role='button']")) continue;
      const clone = node.cloneNode(true);
      clone.querySelectorAll("button, time, header, a[role='link'], svg").forEach(el => el.remove());
      const raw = (clone.innerText || clone.textContent || "").trim();
      if (raw.length >= 8 && !raw.toLowerCase().startsWith("disukai oleh") && !raw.toLowerCase().startsWith("liked by")) {
        cleanText = raw;
        break;
      }
    }

    if (!cleanText) {
      const h1El = container.querySelector("h1");
      if (h1El) {
        cleanText = (h1El.innerText || h1El.textContent || "").trim();
      }
    }

    // Bersihkan artefak Instagram
    if (cleanText) {
      cleanText = cleanText.replace(/[\u00a0\u200b]/g, " ");
      cleanText = cleanText.replace(/^(?:[a-zA-Z0-9_\.]{2,30})?(?:Ikuti|Mengikuti|Follow|Following)\s*(?:[a-zA-Z0-9_\.]{2,30})?\s*\d+\s*(?:jam|hari|menit|detik|m|h|d|w|minggu)?\s*/i, "").trim();
      cleanText = cleanText.replace(/^(?:Ikuti|Mengikuti|Follow|Following)\s*/i, "").trim();
      if (authorHandle) {
        cleanText = cleanText.replace(new RegExp(`^${authorHandle}\\s*`, "i"), "").trim();
      }
      cleanText = cleanText.replace(/^\d+\s*(?:menit|jam|hari|minggu|detik|m|h|d|w)\s*/i, "").trim();
      for (const marker of ["Lihat terjemahan", "See translation", "View translation", "Terjemahkan", "Translate", "Lihat semua komentar", "View all comments"]) {
        if (cleanText.includes(marker)) cleanText = cleanText.split(marker)[0].trim();
      }
      for (let i = 0; i < 3; i++) {
        cleanText = cleanText.replace(/[\s·•\-_|/]*\b(?:Translate|Terjemahkan|Lihat terjemahan|See translation|View translation|Suka|Like|Balas|Reply|Bagikan|Share|Komentar|Comment)\b[\s]*$/gi, "").trim();
      }
      cleanText = cleanText.replace(/Disukai oleh.*?lainnya/gi, " ");
      cleanText = cleanText.replace(/Liked by.*?others/gi, " ");
      cleanText = cleanText.replace(/[ \t]+/g, " ");
      cleanText = cleanText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
    }

    // Pembersihan URL modal Instagram (/liked_by, /comments)
    let permalink = window.location.href;
    const igMatch = permalink.match(/(https?:\/\/(?:www\.)?instagram\.com\/(?:p|reel|reels|tv)\/[A-Za-z0-9_-]+)/i);
    if (igMatch) {
      permalink = igMatch[1] + "/";
    }

    const hasMedia = Boolean(container.querySelector("img, video"));
    const title = cleanText ? (cleanText.slice(0, 77) + (cleanText.length > 77 ? "..." : "")) : "Postingan Instagram";

    return {
      platform: "instagram",
      source_url: permalink,
      title: title,
      dom_text: cleanText,
      extraction_method: "instagram_article",
      username: authorHandle || undefined,
      display_name: authorName || (authorHandle ? `@${authorHandle}` : undefined),
      posted_at: new Date().toISOString(),
      likes_count: 0,
      has_media: hasMedia,
      container: container,
    };
  }

  window.TilikExtractors.instagram = { extract: extractInstagram };
})();
