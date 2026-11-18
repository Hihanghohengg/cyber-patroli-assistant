// @ts-nocheck
/* cSpell:disable */
// Modular Extractor for X / Twitter (x.com & twitter.com)

(function() {
  window.TilikExtractors = window.TilikExtractors || {};

  function extractTwitterX() {
    const primaryCol = document.querySelector('[data-testid="primaryColumn"]') || document.querySelector("main") || document.body;
    const container = primaryCol.querySelector("article[data-testid='tweet']") || primaryCol.querySelector("article") || primaryCol;

    let authorHandle = "";
    let authorName = "";

    const userAnchor = container.querySelector("[data-testid='User-Name'] a, header a[role='link']");
    if (userAnchor) {
      authorName = userAnchor.textContent.trim();
      const href = userAnchor.getAttribute("href") || "";
      const m = href.match(/\/([a-zA-Z0-9_]+)/);
      if (m && !["home", "explore", "notifications", "messages"].includes(m[1].toLowerCase())) {
        authorHandle = m[1];
      }
    }

    // Auto-click "Show more"
    try {
      const buttons = container.querySelectorAll('[role="button"], span');
      for (const btn of buttons) {
        const txt = (btn.textContent || "").trim().toLowerCase();
        if (txt === "show more" || txt === "tampilkan lebih banyak") {
          btn.click();
          break;
        }
      }
    } catch (_) {}

    // Ekstraksi Teks Tweet
    let cleanText = "";
    const tweetEl = container.querySelector('[data-testid="tweetText"]') || container;
    if (tweetEl) {
      const clone = tweetEl.cloneNode(true);
      clone.querySelectorAll("button, [role='button']").forEach(b => {
        const bt = (b.textContent || "").toLowerCase();
        if (bt.includes("terjemahkan") || bt.includes("translate")) b.remove();
      });
      cleanText = (clone.innerText || clone.textContent || "").trim();
    }

    if (cleanText) {
      if (authorHandle) {
        cleanText = cleanText.replace(new RegExp(`^(?:[^\n@]{0,40}@${authorHandle}\\s*(?:·\\s*\\d+[a-zA-Z\\s]*)?)+`, "i"), "").trim();
        cleanText = cleanText.replace(new RegExp(`^@?${authorHandle}\\s*`, "i"), "").trim();
      }
      cleanText = cleanText.replace(/Terjemahkan postingan|Translate post/gi, "").trim();
      cleanText = cleanText.replace(/\d{1,2}:\d{2}\s*[\/|\\]\s*\d{1,2}:\d{2}/g, " ");
      cleanText = cleanText.replace(/\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*[·•\u00b7\u2022]\s*[A-Za-z]{3}\s*\d{1,2},\s*\d{4}/g, " ");
      cleanText = cleanText.replace(/[·•\u00b7\u2022\s]*\d+[\d\.,]*[KkMm]?\s*(?:Views|View quotes|views|quotes|suka|likes|Retweets|reposts|Bookmarks|bookmarked)(?=[^a-zA-Z]|$)/gi, " ");
      cleanText = cleanText.replace(/[ \t]+/g, " ");
      cleanText = cleanText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
    }

    const hasMedia = Boolean(container.querySelector("[data-testid='tweetPhoto'], video"));
    const title = cleanText ? (cleanText.slice(0, 77) + (cleanText.length > 77 ? "..." : "")) : "Postingan X (Twitter)";

    return {
      platform: "x",
      source_url: window.location.href.split("?")[0],
      title: title,
      dom_text: cleanText,
      extraction_method: "twitter_tweet",
      username: authorHandle || undefined,
      display_name: authorName || (authorHandle ? `@${authorHandle}` : undefined),
      posted_at: new Date().toISOString(),
      likes_count: 0,
      has_media: hasMedia,
      container: container,
    };
  }

  window.TilikExtractors.x = { extract: extractTwitterX };
})();
