// @ts-nocheck
/* cSpell:disable */
// Modular Extractor for Facebook (facebook.com & fb.watch)

(function() {
  window.TilikExtractors = window.TilikExtractors || {};

  function extractFacebook() {
    const container = document.querySelector("[role='article']") ||
                      document.querySelector("div[data-pagelet*='FeedUnit']") ||
                      document.body;

    let authorName = "";
    let authorHandle = "";

    const authorEl = container.querySelector("h2 a, h3 a, strong a, [role='article'] h2, strong span");
    if (authorEl) {
      authorName = authorEl.textContent.trim();
      const href = authorEl.getAttribute("href") || "";
      const m = href.match(/(?:facebook\.com\/|profile\.php\?id=|\/)([a-zA-Z0-9_\.]+)/);
      if (m && !["profile.php", "home.php", "watch", "photo", "groups"].includes(m[1].toLowerCase())) {
        authorHandle = m[1];
      }
    }

    let cleanText = "";
    const fbMsg = container.querySelector('div[data-ad-preview="message"], div[data-ad-comet-preview="message"], div[dir="auto"][style*="text-align"]');
    if (fbMsg) {
      cleanText = (fbMsg.innerText || fbMsg.textContent || "").trim();
    } else {
      const candidateDivs = container.querySelectorAll('div[dir="auto"], p');
      const paragraphs = [];
      const seenParas = new Set();
      for (const div of candidateDivs) {
        if (div.closest("button, [role='button'], form, ul, ol, nav, header, footer")) continue;
        const txt = (div.innerText || div.textContent || "").trim();
        if (txt.length >= 20 && !seenParas.has(txt)) {
          seenParas.add(txt);
          paragraphs.push(txt);
        }
      }
      cleanText = paragraphs.join("\n\n").trim();
    }

    if (cleanText) {
      cleanText = cleanText.replace(/[ \t]+/g, " ");
      cleanText = cleanText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
    }

    const hasMedia = Boolean(container.querySelector("img, video"));
    const title = cleanText ? (cleanText.slice(0, 77) + (cleanText.length > 77 ? "..." : "")) : "Postingan Facebook";

    return {
      platform: "facebook",
      source_url: window.location.href.split("?")[0],
      title: title,
      dom_text: cleanText,
      extraction_method: "facebook_post",
      username: authorHandle || undefined,
      display_name: authorName || (authorHandle ? `@${authorHandle}` : undefined),
      posted_at: new Date().toISOString(),
      likes_count: 0,
      has_media: hasMedia,
      container: container,
    };
  }

  window.TilikExtractors.facebook = { extract: extractFacebook };
})();
