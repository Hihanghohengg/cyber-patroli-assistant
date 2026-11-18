// @ts-nocheck
/* cSpell:disable */
// Modular Extractor for News Portals & Generic Web Articles

(function() {
  window.TilikExtractors = window.TilikExtractors || {};

  function extractNewsPortal() {
    // 1. Ekstraksi OpenGraph & JSON-LD
    let title = document.querySelector('meta[property="og:title"]')?.content || document.title;
    let description = document.querySelector('meta[property="og:description"]')?.content ||
                      document.querySelector('meta[name="description"]')?.content || "";
    let author = document.querySelector('meta[name="author"]')?.content ||
                 document.querySelector('meta[property="article:author"]')?.content || "";

    // 2. Ekstraksi Deep Article Body
    const mainEl = document.querySelector("article, main, .read__content, .detail__body-text, #article-body, .it-detail") || document.body;
    let bodyText = "";
    if (mainEl) {
      const clone = mainEl.cloneNode(true);
      clone.querySelectorAll("script, style, svg, nav, button, iframe, noscript, dialog").forEach((el) => el.remove());
      clone.querySelectorAll("p, div.paragraph, div.detail__body-text > div").forEach((p) => {
        p.insertAdjacentText("afterend", "\n\n");
      });
      bodyText = (clone.innerText || clone.textContent || "")
        .replace(/[ \t]+/g, " ")
        .replace(/\n\s*\n\s*\n+/g, "\n\n")
        .trim();

      // Bersihkan noise widget portal berita
      bodyText = bodyText.replace(/\bAdvertisement\b/gi, " ");
      bodyText = bodyText.replace(/\bListen\s+\d+\s*(?:min|mins|menit)\b/gi, " ");
      bodyText = bodyText.replace(/Follow us on[^\n]*/gi, " ");
      bodyText = bodyText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
    }

    const domText = [description, bodyText].filter(Boolean).join("\n\n").trim() || description || title;

    return {
      platform: "web",
      source_url: window.location.href.split("?")[0],
      title: title || document.title,
      dom_text: domText,
      extraction_method: "news_portal_article",
      username: author || window.location.hostname.replace("www.", ""),
      display_name: author || window.location.hostname.replace("www.", ""),
      posted_at: new Date().toISOString(),
      has_media: false,
      container: mainEl,
    };
  }

  window.TilikExtractors.news_portal = { extract: extractNewsPortal };
})();
