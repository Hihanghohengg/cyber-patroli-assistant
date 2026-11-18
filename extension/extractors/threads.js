// @ts-nocheck
/* cSpell:disable */
// Modular Extractor for Threads (threads.net & threads.com)
// Single Page Application (SPA) Real-Time Viewport Aware & Anti-Stale DOM

(function() {
  window.TilikExtractors = window.TilikExtractors || {};

  function isVisibleInViewport(el) {
    if (!el) return false;
    if (el.offsetParent === null) return false;
    if (el.getAttribute("aria-hidden") === "true") return false;
    try {
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || parseFloat(style.opacity) === 0) return false;
    } catch (_) {}
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    return rect.bottom > 50 && rect.top < (window.innerHeight - 30);
  }

  function isLoginBoilerplate(text) {
    if (!text || typeof text !== "string") return false;
    const lower = text.toLowerCase();
    return (
      lower.includes("log in with your instagram") ||
      lower.includes("masuk dengan akun instagram") ||
      lower.includes("log in to see photos and videos") ||
      lower.includes("login to see photos and videos") ||
      lower.includes("masuk untuk melihat foto dan video") ||
      lower.includes("create an account or log in") ||
      lower.includes("buat akun atau masuk") ||
      lower.includes("log in to threads") ||
      lower.includes("masuk ke threads") ||
      lower.includes("join groups, ask questions") ||
      lower.includes("lihat lainnya dari threads") ||
      lower.includes("see more from threads")
    );
  }

  function extractThreads() {
    // 1. Baca pathname & URL secara real-time saat dipicu (anti-stale React SPA)
    const pathname = window.location.pathname;
    const urlPostMatch = pathname.match(/\/@([a-zA-Z0-9_\.]+)\/post\/([A-Za-z0-9_-]+)/i);
    const postOnlyMatch = pathname.match(/\/post\/([A-Za-z0-9_-]+)/i);
    const authorFromUrl = urlPostMatch ? urlPostMatch[1] : null;
    const postIdFromUrl = urlPostMatch ? urlPostMatch[2] : (postOnlyMatch ? postOnlyMatch[1] : null);

    const mainEl = document.querySelector("[role='main']") || document.querySelector("main") || document.body;
    let container = null;

    // Skenario A: Halaman Detail Postingan (/@username/post/<id>)
    if (postIdFromUrl) {
      if (authorFromUrl) {
        const userAnchors = mainEl.querySelectorAll(`a[href*="/@${authorFromUrl}"]`);
        for (const ua of userAnchors) {
          if (!isVisibleInViewport(ua)) continue;
          const cardCandidate = ua.closest("div[data-pressable-container='true']") ||
                                ua.closest("article") ||
                                ua.closest("div[role='article']") ||
                                ua.closest(".x1y1aw1k") ||
                                ua.parentElement?.parentElement?.parentElement;
          if (cardCandidate && isVisibleInViewport(cardCandidate) && !cardCandidate.closest("aside, nav, header, [role='navigation']")) {
            container = cardCandidate;
            break;
          }
        }
      }

      if (!container) {
        const postAnchor = mainEl.querySelector(`a[href*="/post/${postIdFromUrl}"]`);
        if (postAnchor && isVisibleInViewport(postAnchor)) {
          container = postAnchor.closest("div[data-pressable-container='true']") ||
                      postAnchor.closest("article") ||
                      postAnchor.closest("div[role='article']");
        }
      }

      if (!container) {
        const candidateDivs = mainEl.querySelectorAll("div[data-pressable-container='true'], article, div[role='article']");
        for (const cd of candidateDivs) {
          if (isVisibleInViewport(cd) && !cd.closest("aside, nav, header, [role='navigation']")) {
            container = cd;
            break;
          }
        }
      }
    }

    // Skenario B: Feed / Beranda Threads
    if (!container) {
      const allCards = mainEl.querySelectorAll("div[data-pressable-container='true'], article, div[role='article']");
      const visibleCards = [];
      for (const card of allCards) {
        if (isVisibleInViewport(card) && !card.closest("aside, nav, header, [role='navigation']")) {
          visibleCards.push(card);
        }
      }

      if (visibleCards.length > 0) {
        const viewportCenter = window.innerHeight / 2;
        let closestCard = visibleCards[0];
        let minDistance = Infinity;
        for (const card of visibleCards) {
          const rect = card.getBoundingClientRect();
          const cardCenter = rect.top + rect.height / 2;
          const dist = Math.abs(cardCenter - viewportCenter);
          if (dist < minDistance) {
            minDistance = dist;
            closestCard = card;
          }
        }
        container = closestCard;
      }
    }

    if (!container) {
      container = mainEl;
    }

    // Ekstraksi Username & Nama Pengunggah
    let authorHandle = authorFromUrl || "";
    let authorName = authorHandle ? `@${authorHandle}` : "";

    const userAnchors = container.querySelectorAll("a[href*='/@']");
    for (const ua of userAnchors) {
      const href = ua.getAttribute("href") || "";
      const m = href.match(/@([a-zA-Z0-9_\.]+)/);
      if (m && !["post", "activity", "search"].includes(m[1].toLowerCase())) {
        authorHandle = m[1];
        let cleanDisp = (ua.textContent || "").trim();
        cleanDisp = cleanDisp.replace(/\s*[·•\s]+\d+\s*(?:j|jam|h|m|menit|d|hari|w|minggu|detik)$/i, "").trim();
        cleanDisp = cleanDisp.replace(/\b(?:Verified|Threads)\b/gi, "").trim();
        authorName = cleanDisp || `@${m[1]}`;
        break;
      }
    }

    // Ekstraksi Naskah Teks Postingan (Presisi Anti-Comment & Anti-Button)
    const textNodes = container.querySelectorAll('span[dir="auto"], div[dir="auto"], p');
    const textParts = [];
    const seenTexts = new Set();

    for (const node of textNodes) {
      if (node.closest("button, [role='button'], nav, header, footer, a[role='link'], form")) continue;
      if (node.querySelector("a[href*='/@']")) continue;

      const clone = node.cloneNode(true);
      clone.querySelectorAll("button, time, svg, a[role='link']").forEach(el => el.remove());
      const raw = (clone.innerText || clone.textContent || "").trim();

      if (
        raw.length >= 3 &&
        !isLoginBoilerplate(raw) &&
        !/^(?:Suka|Balas|Posting ulang|Bagikan|Like|Reply|Repost|Share|Ikuti|Follow|Mengikuti|Following|Terjemahkan|Translate|Komentar|Comment|Quotes|See more|Thread)$/i.test(raw) &&
        !/^\d+[\d\.,]*\s*(?:suka|likes|balasan|replies|reposts|shares|tayangan|views|quotes)?$/i.test(raw) &&
        !/^\d+\s*(?:j|jam|h|m|menit|d|hari|w|minggu|detik)$/i.test(raw) &&
        !seenTexts.has(raw)
      ) {
        let isSub = false;
        for (const st of seenTexts) {
          if (st.includes(raw)) { isSub = true; break; }
        }
        if (!isSub) {
          seenTexts.add(raw);
          textParts.push(raw);
        }
      }
    }

    let cleanText = textParts.join("\n\n").trim();
    if (cleanText) {
      cleanText = cleanText.replace(/^(?:Ikuti|Mengikuti|Follow|Following)\s*/i, "").trim();
      if (authorHandle) {
        cleanText = cleanText.replace(new RegExp(`^@?${authorHandle}\\s*`, "i"), "").trim();
      }
      cleanText = cleanText.replace(/^\d+\s*(?:j|jam|h|m|menit|d|hari|w|minggu|detik)\s*/i, "").trim();
      cleanText = cleanText.replace(/\b(?:Suka|Balas|Posting ulang|Bagikan|Like|Reply|Repost|Share)\b.*$/gi, "").trim();
      cleanText = cleanText.replace(/[ \t]+/g, " ");
      cleanText = cleanText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
    }

    // Deteksi Media Gambar/Video (Pemicu Multimodal RapidOCR)
    const hasMedia = Boolean(container.querySelector("img[srcset], img[src*='threads'], img[src*='cdninstagram'], video"));

    let permalink = window.location.href.split("?")[0].replace(/\/+$/, "");
    if (authorHandle && postIdFromUrl) {
      permalink = `https://www.threads.net/@${authorHandle}/post/${postIdFromUrl}`;
    }

    const firstSentence = cleanText.split(/[.!?\n]/)[0].trim().replace(/^\d+\.\s*/, "");
    const title = firstSentence && firstSentence.length >= 15 && firstSentence.length <= 90
      ? firstSentence
      : (cleanText.slice(0, 77).trim() + (cleanText.length > 77 ? "..." : "") || "Postingan Threads");

    return {
      platform: "threads",
      source_url: permalink,
      title: title,
      dom_text: cleanText,
      extraction_method: "threads_spa_post",
      username: authorHandle || undefined,
      display_name: authorName || undefined,
      posted_at: new Date().toISOString(),
      likes_count: 0,
      has_media: hasMedia,
      container: container,
    };
  }

  window.TilikExtractors.threads = { extract: extractThreads };
})();
