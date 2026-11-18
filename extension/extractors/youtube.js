// @ts-nocheck
/* cSpell:disable */
// Modular Extractor for YouTube (youtube.com & youtu.be)

(function() {
  window.TilikExtractors = window.TilikExtractors || {};

  function extractYouTube() {
    let title = "";
    const tit = document.querySelector("#title h1 yt-formatted-string") || document.querySelector("meta[name='title']");
    if (tit) title = tit.textContent?.trim() || tit.content || document.title;

    let authorName = "";
    let authorHandle = "";
    const ch = document.querySelector("#channel-name a") || document.querySelector("#owner #text a");
    if (ch) {
      authorName = ch.textContent?.trim() || "";
      const href = ch.getAttribute("href") || "";
      if (href.includes("@")) authorHandle = href.split("@")[1].split("/")[0];
    }

    let transcript = "";
    const tNodes = document.querySelectorAll("ytd-transcript-segment-renderer .segment-text, #segments-container yt-formatted-string");
    if (tNodes && tNodes.length > 0) {
      transcript = Array.from(tNodes).map((n) => n.textContent.trim()).filter(Boolean).join(" ");
    }

    // Ambil deskripsi video
    const descEl = document.querySelector("#description-inline-expander, #description");
    let descText = descEl ? (descEl.innerText || descEl.textContent || "").trim() : "";

    const domText = [title, descText, transcript].filter(Boolean).join("\n\n").trim();

    return {
      platform: "youtube",
      source_url: window.location.href.split("&")[0],
      title: title || document.title,
      dom_text: domText || title,
      extraction_method: "youtube_video",
      username: authorHandle || undefined,
      display_name: authorName || (authorHandle ? `@${authorHandle}` : undefined),
      posted_at: new Date().toISOString(),
      transcript: transcript || undefined,
      has_media: true,
      container: document.querySelector("#player") || document.body,
    };
  }

  window.TilikExtractors.youtube = { extract: extractYouTube };
})();
