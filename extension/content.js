// @ts-nocheck
/* cSpell:disable */
// Injected Universal 3-Layer Content Acquisition Script for TILIK
// Supports: X/Twitter, Instagram, Facebook, YouTube, and National News Portals (Kompas, Detik, Tempo, etc.)
// Deterministic Anti-Noise Extraction, Viewport Isolation, and NIST FIPS 198-1 Integrity Binding

(function() {
  if (document.getElementById("cyber-patrol-floating-badge")) return;

  // Track hovered or focused cards on feed-based social media
  let lastHoveredCard = null;
  document.addEventListener("mouseover", (e) => {
    // Abaikan mutlak area sidebar, widget rekomendasi, trending, dan 'Relevant people'
    if (e.target.closest("aside, [data-testid='sidebarColumn'], [aria-label*='Relevant people'], [aria-label*='Trending'], [aria-label*='Who to follow']")) {
      return;
    }
    const card = e.target.closest(
      "article, [role='article'], [data-testid='tweet'], ytd-rich-item-renderer, ytd-video-renderer, [data-e2e='user-post-item'], .x1y1aw1k"
    );
    if (card) {
      // Pastikan kartu yang disimpan bukan berada di dalam sidebar/aside
      if (!card.closest("aside, [data-testid='sidebarColumn']")) {
        lastHoveredCard = card;
      }
    }
  }, { passive: true });

  // ─────────────────────────────────────────────────────────────
  // DOMAIN CLASSIFIER & ROUTING
  // ─────────────────────────────────────────────────────────────
  function classifyPlatform(url) {
    const u = (url || window.location.href).toLowerCase();
    if (u.includes("twitter.com") || u.includes("x.com")) return "x";
    if (u.includes("instagram.com")) return "instagram";
    if (u.includes("facebook.com")) return "facebook";
    if (u.includes("threads.net")) return "threads";
    if (u.includes("tiktok.com")) return "tiktok";
    if (u.includes("youtube.com") || u.includes("youtu.be")) return "youtube";
    return "news_web"; // National news portal or public website
  }

  // ─────────────────────────────────────────────────────────────
  // NUMBER PARSER UTILITY
  // ─────────────────────────────────────────────────────────────
  function parseMetricNumber(text) {
    if (!text) return 0;
    const clean = text.trim().toLowerCase();
    const match = clean.match(/([\d\.,]+)\s*(rb|k|ribu|jt|m|juta|b|miliar)?/i);
    if (!match) return 0;
    let val = parseFloat(match[1].replace(/,/g, "."));
    if (isNaN(val)) return 0;
    const unit = (match[2] || "").toLowerCase();
    if (unit === "m" || unit === "jt" || unit === "juta") val *= 1000000;
    else if (unit === "b" || unit === "miliar") val *= 1000000000;
    else if (unit === "k" || unit === "rb" || unit === "ribu") val *= 1000;
    const r = Math.round(val);
    return r > 0 && r < 10000000000 ? r : 0;
  }

  // ─────────────────────────────────────────────────────────────
  // LAYER 1: OPENGRAPH & JSON-LD METADATA EXTRACTOR
  // ─────────────────────────────────────────────────────────────
  function extractOpenGraphAndJsonLd() {
    const meta = {
      title: null,
      description: null,
      canonical_url: null,
      published_time: null,
      author: null,
      publisher: null,
      media_image_url: null,
      article_body: null,
    };

    // OpenGraph & Meta Tags
    const ogTitle = document.querySelector('meta[property="og:title"]')?.content ||
                    document.querySelector('meta[name="twitter:title"]')?.content;
    const ogDesc = document.querySelector('meta[property="og:description"]')?.content ||
                   document.querySelector('meta[name="description"]')?.content;
    const ogUrl = document.querySelector('meta[property="og:url"]')?.content ||
                  document.querySelector('link[rel="canonical"]')?.href;
    const ogImg = document.querySelector('meta[property="og:image"]')?.content ||
                  document.querySelector('meta[name="twitter:image"]')?.content;
    const ogTime = document.querySelector('meta[property="article:published_time"]')?.content ||
                   document.querySelector('meta[name="pubdate"]')?.content;

    if (ogTitle) meta.title = ogTitle.trim();
    if (ogDesc) meta.description = ogDesc.trim();
    if (ogUrl) meta.canonical_url = ogUrl.trim();
    if (ogImg && !ogImg.includes("favicon")) meta.media_image_url = ogImg.trim();
    if (ogTime) meta.published_time = ogTime.trim();

    // Parse JSON-LD scripts
    const ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of ldScripts) {
      try {
        const raw = JSON.parse(script.textContent);
        const candidates = Array.isArray(raw) ? raw : (raw["@graph"] ? raw["@graph"] : [raw]);
        for (const item of candidates) {
          if (!item || typeof item !== "object") continue;
          const type = (item["@type"] || "").toLowerCase();
          if (["newsarticle", "article", "report", "blogposting", "socialmediaposting", "videoobject"].includes(type)) {
            if (!meta.title && (item.headline || item.name)) meta.title = (item.headline || item.name).trim();
            if (!meta.description && item.description) meta.description = item.description.trim();
            if (item.articleBody && typeof item.articleBody === "string") {
              meta.article_body = item.articleBody.trim();
            }
            if (!meta.published_time && (item.datePublished || item.uploadDate)) {
              meta.published_time = (item.datePublished || item.uploadDate).trim();
            }
            if (!meta.author && item.author) {
              meta.author = typeof item.author === "string" ? item.author : (item.author.name || null);
            }
            if (!meta.publisher && item.publisher) {
              meta.publisher = typeof item.publisher === "string" ? item.publisher : (item.publisher.name || null);
            }
          }
        }
      } catch (e) {
        // invalid JSON-LD block ignored
      }
    }

    return meta;
  }

  // ─────────────────────────────────────────────────────────────
  // LAYER 2: VIEWPORT SEMANTIC CONTAINER (<article>) EXTRACTOR
  // ─────────────────────────────────────────────────────────────
  function extractSemanticArticleContainer() {
    const host = window.location.hostname.toLowerCase();
    const isTwitter = host.includes("twitter.com") || host.includes("x.com");
    const isInstagram = host.includes("instagram.com");
    const isThreads = host.includes("threads.net");

    // 1. Locate container dengan isolasi platform ketat
    let container = null;

    if (isInstagram) {
      // Jika modal dialog aktif, batasi mutlak di dalam dialog
      const igModal = document.querySelector("div[role='dialog']");
      if (igModal) {
        container = igModal.querySelector("article") || igModal;
      }
    } else if (isTwitter) {
      // Di X/Twitter: Wajib di dalam [data-testid="primaryColumn"] atau <main>, tolak mutlak <aside>
      const primaryCol = document.querySelector('[data-testid="primaryColumn"]') || document.querySelector("main[role='main']") || document.querySelector("main");
      if (primaryCol) {
        if (lastHoveredCard && primaryCol.contains(lastHoveredCard) && !lastHoveredCard.closest("aside, [data-testid='sidebarColumn']")) {
          container = lastHoveredCard;
        } else {
          // Cari tweet utama (tweet pertama di primary column)
          container = primaryCol.querySelector("article[data-testid='tweet']") || primaryCol.querySelector("article");
        }
      }
    } else if (isThreads) {
      container = lastHoveredCard || document.querySelector("div[data-pressable-container='true']") || document.querySelector("article") || document.querySelector("main");
    }

    if (!container) {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      const centerEl = document.elementFromPoint(cx, cy);

      container = (!isTwitter ? lastHoveredCard : null) ||
                  document.querySelector("div[role='dialog'] article") ||
                  document.querySelector("div[role='dialog']") ||
                  centerEl?.closest("article, [role='article'], [data-testid='tweet'], div[role='dialog'], main, .x1y1aw1k") ||
                  document.querySelector("article, [role='article'], [data-testid='tweet'], main[role='main']");
    }

    // Jika container ternyata berada di dalam aside/sidebar, tolak!
    if (container && container.closest("aside, [data-testid='sidebarColumn']")) {
      container = document.querySelector('[data-testid="primaryColumn"] article') || document.querySelector("main article");
    }

    if (!container) return null;

    // Auto-click "Show more" pada X/Twitter jika tweet terpotong
    if (isTwitter) {
      try {
        const buttons = container.querySelectorAll('[role="button"], span');
        for (const btn of buttons) {
          const txt = (btn.textContent || "").trim().toLowerCase();
          if (txt === "show more" || txt === "tampilkan lebih banyak" || txt === "show this thread") {
            btn.click();
            break;
          }
        }
      } catch (e) {}
    }

    // 2. Extract Permalink Anchor & Canonical User
    let permalink = window.location.href;
    const permalinkEl = container.querySelector(
      "a[href*='/status/'], a[href*='/p/'], a[href*='/reel/'], a[href*='/posts/'], a[href*='/post/'], a[href*='/videos/'], a[href*='/photo/']"
    );
    if (permalinkEl) {
      permalink = permalinkEl.href;
    }

    // 3. Extract Published Timestamp
    let publishedAt = null;
    const timeEl = container.querySelector("time[datetime], time");
    if (timeEl) {
      publishedAt = timeEl.getAttribute("datetime") || timeEl.textContent.trim();
    }

    // 4. Extract Author / Handle (Orang)
    let authorName = null;
    let authorHandle = null;

    if (isTwitter) {
      // Prioritas A: Ambil dari URL canonical /status/ jika berada di halaman tweet tunggal
      const statusMatch = window.location.pathname.match(/\/([^\/]+)\/status\/\d+/);
      if (statusMatch && statusMatch[1] && statusMatch[1].toLowerCase() !== "i") {
        authorHandle = statusMatch[1];
      }
      // Prioritas B: Dari blok [data-testid="User-Name"] di dalam tweet container
      const userBlock = container.querySelector('[data-testid="User-Name"]');
      if (userBlock) {
        const fullTxt = userBlock.textContent || "";
        const handleMatch = fullTxt.match(/@([a-zA-Z0-9_]+)/);
        if (handleMatch) {
          authorHandle = handleMatch[1];
        }
        const spl = fullTxt.split("@");
        if (spl[0] && spl[0].trim()) {
          authorName = spl[0].trim();
        }
      }
      if (!authorHandle) {
        const pathSegments = window.location.pathname.split("/").filter(Boolean);
        if (pathSegments.length >= 2 && pathSegments[1] === "status" && !["home", "explore", "notifications", "messages"].includes(pathSegments[0].toLowerCase())) {
          authorHandle = pathSegments[0];
          authorName = `@${pathSegments[0]}`;
        }
      }
    } else if (isInstagram) {
      // Instagram Header: header a[role="link"] or header h2 a
      const nonUserPaths = ["p", "reel", "reels", "tv", "stories", "explore", "direct", "accounts"];
      const igUserAnchors = container.querySelectorAll("header a[role='link'], header h2 a, header a[href^='/'], [data-testid='User-Name'] a, h2 a");
      for (const ua of igUserAnchors) {
        const rawHref = ua.getAttribute("href") || "";
        const pathOnly = rawHref.replace(/^https?:\/\/[^\/]+/, "").split("?")[0];
        const m = pathOnly.match(/^\/([a-zA-Z0-9_\.]+)\/?$/);
        if (m && !nonUserPaths.includes(m[1].toLowerCase())) {
          authorHandle = m[1];
          authorName = ua.textContent.trim() || m[1];
          break;
        }
      }
      if (!authorHandle) {
        const ogTitle = document.querySelector('meta[property="og:title"]')?.content || "";
        const m = ogTitle.match(/\(@([a-zA-Z0-9_\.]+)\)/);
        if (m) authorHandle = m[1];
      }
    } else if (isThreads) {
      const thMatch = window.location.pathname.match(/@([a-zA-Z0-9_\.]+)/);
      if (thMatch) {
        authorHandle = thMatch[1];
        authorName = `@${thMatch[1]}`;
      }
    } else if (host.includes("facebook.com")) {
      const fbAuthorEl = container.querySelector("h2 a, h3 a, strong a, [role='article'] h2, [role='article'] h3, strong span");
      if (fbAuthorEl) {
        authorName = fbAuthorEl.textContent.trim();
        const href = fbAuthorEl.getAttribute("href") || "";
        const m = href.match(/(?:facebook\.com\/|profile\.php\?id=|\/)([a-zA-Z0-9_\.]+)/);
        if (m && !["profile.php", "home.php", "watch", "photo", "groups"].includes(m[1].toLowerCase())) {
          authorHandle = m[1];
        }
      }
    } else {
      const userAnchor = container.querySelector("a[role='link'][href*='/'], header a, [data-testid='User-Name'] a, h2 a");
      if (userAnchor) {
        authorName = userAnchor.textContent.trim();
        const href = userAnchor.getAttribute("href") || "";
        const match = href.match(/\/([a-zA-Z0-9_\.]+)/);
        if (match) authorHandle = match[1];
      }
    }

    // Deteksi media gambar/video pada Instagram untuk pemicu OCR Multimodal
    let hasMedia = false;
    if (isInstagram && container) {
      const mediaEl = container.querySelector("img[srcset], img[src*='cdninstagram'], video");
      if (mediaEl) hasMedia = true;
    }

    // 5. Precision Post Caption Extraction (Anti-Comment & Anti-Noise)
    let cleanText = "";
    let extractedComments = [];
    let likesCount = 0;

    if (host.includes("instagram.com")) {
      // Auto-click "selengkapnya" / "more" button pada caption Instagram
      try {
        const moreButtons = container.querySelectorAll("span[role='button'], div[role='button'], button");
        for (const b of moreButtons) {
          const txt = (b.textContent || "").trim().toLowerCase();
          if (txt === "selengkapnya" || txt === "more" || txt.includes("selengkapnya") || txt.includes("more")) {
            b.click();
            break;
          }
        }
      } catch (e) {}

      // Prioritas 1 DOM: Cari elemen caption spesifik yang bebas dari header profil
      // Instagram menggunakan span._ap3a[dir='auto'] atau div._a9zs untuk caption narasi
      const captionNodes = container.querySelectorAll("div._a9zs span[dir='auto'], div._a9zs, h1 span[dir='auto'], span._ap3a[dir='auto']");
      for (const node of captionNodes) {
        // Abaikan jika node berada di dalam tombol interaksi atau list komentar lain
        if (node.closest("button, header, div[role='button']")) continue;
        const clone = node.cloneNode(true);
        clone.querySelectorAll("button, time, header, a[role='link'], svg").forEach(el => el.remove());
        const raw = (clone.innerText || clone.textContent || "").trim();
        if (raw.length >= 8 && !raw.toLowerCase().startsWith("disukai oleh") && !raw.toLowerCase().startsWith("liked by")) {
          cleanText = raw;
          break;
        }
      }

      // Prioritas 2 DOM: Jika belum ketemu, periksa <h1> tapi bersihkan mutlak tombol Ikuti dan username
      if (!cleanText) {
        const h1El = container.querySelector("h1");
        if (h1El) {
          const clone = h1El.cloneNode(true);
          clone.querySelectorAll("button, time, header, a[role='link'], svg").forEach(el => el.remove());
          const h1Raw = (clone.innerText || clone.textContent || "").trim();
          if (h1Raw.length >= 8) {
            cleanText = h1Raw;
          }
        }
      }

      // Bersihkan Caption Instagram dari sisa-sisa tombol Ikuti, username, atau timestamp
      if (cleanText) {
        // Hapus artefak tombol menempel Instagram (e.g. 'vivacoidIkutivivacoid 21 jam...')
        cleanText = cleanText.replace(/^(?:[a-zA-Z0-9_\.]{2,30})?(?:Ikuti|Mengikuti|Follow|Following)\s*(?:[a-zA-Z0-9_\.]{2,30})?\s*\d+\s*(?:jam|hari|menit|detik|m|h|d|w|minggu)?\s*/i, "").trim();
        cleanText = cleanText.replace(/^(?:[a-zA-Z0-9_\.]{2,30})\s+\d+\s*(?:jam|hari|menit|detik|m|h|d|w|minggu)\s*/i, "").trim();
        // Hapus kata 'Ikuti', 'Mengikuti', 'Follow', 'Following' di depan
        cleanText = cleanText.replace(/^(?:Ikuti|Mengikuti|Follow|Following)\s*/i, "").trim();
        // Hapus authorHandle jika menempel di depan
        if (authorHandle) {
          cleanText = cleanText.replace(new RegExp(`^${authorHandle}\\s*`, "i"), "").trim();
          cleanText = cleanText.replace(/^(?:Ikuti|Mengikuti|Follow|Following)\s*/i, "").trim();
        }
        // Hapus timestamp seperti "49 menit", "2 jam", "3 hari", "49m", "2h", "3d" di depan
        cleanText = cleanText.replace(/^\d+\s*(?:menit|jam|hari|minggu|detik|m|h|d|w)\s*/i, "").trim();
        for (const marker of ["Lihat terjemahan", "See translation", "View translation", "Lihat semua komentar", "View all comments"]) {
          if (cleanText.includes(marker)) {
            cleanText = cleanText.split(marker)[0].trim();
          }
        }
        cleanText = cleanText.replace(/Disukai oleh.*?lainnya/gi, " ");
        cleanText = cleanText.replace(/Liked by.*?others/gi, " ");
        cleanText = cleanText.replace(/\b\d+\s*(?:hari|jam|m|menit|d|detik|w|minggu)\s*(?:yang\s+lalu)?\s*(?:Kirim)?$/gi, "").trim();
        // Pertahankan jeda antar paragraf \n\n, hanya rapikan spasi/tab horizontal
      cleanText = cleanText.replace(/[ \t]+/g, " ");
      cleanText = cleanText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
      }

      // Prioritas 3: Fallback ke OpenGraph HANYA jika DOM benar-benar kosong
      if (!cleanText || cleanText.length < 5) {
        const ogDesc = document.querySelector('meta[property="og:description"]')?.content ||
                       document.querySelector('meta[name="description"]')?.content;
        if (ogDesc && ogDesc.includes(":")) {
          const quoteMatch = ogDesc.match(/(?:on [^:]+:|:\s*)["“]([\s\S]+?)["”]\s*$/);
          if (quoteMatch && quoteMatch[1] && quoteMatch[1].trim().length >= 8) {
            cleanText = quoteMatch[1].trim();
          }
        }
      }

      // Isolasi Komentar Pengikut (Komen) - Tersimpan terpisah agar tidak mengotori caption
      const allCommentNodes = container.querySelectorAll("div._a9zs, span._ap3a[dir='auto']");
      allCommentNodes.forEach((cn, idx) => {
        if (idx === 0 && cleanText) return; // Skip caption item
        const cParent = cn.closest("li, ul > div");
        const cUserEl = cParent?.querySelector("a[role='link']:not([href*='/p/']), h3 a");
        const cUser = cUserEl ? cUserEl.textContent.trim().replace(/^@/, "") : "";
        const cText = cn.textContent.trim();
        if (cUser && cText && cUser !== authorHandle && extractedComments.length < 5) {
          extractedComments.push({ author: cUser, text: cText });
        }
      });

      // Parsing Likes Count
      const sectionEl = container.querySelector("section, div[class*='_ae5q']");
      if (sectionEl) {
        const secText = sectionEl.textContent || "";
        const multiLikes = secText.match(/Disukai oleh\s+([^\s]+)\s+dan\s+([\d\.,]+)\s*(?:rb|jt|ribu|k|m)?\s*lainnya/i);
        if (multiLikes) {
          const numPart = parseMetricNumber(multiLikes[2]);
          likesCount = numPart > 0 ? numPart + 1 : 1;
        } else {
          const simpleLikes = secText.match(/([\d\.,]+)\s*(?:rb|jt|ribu|k|m)?\s*(?:suka|likes)/i);
          if (simpleLikes) {
            likesCount = parseMetricNumber(simpleLikes[1]);
          }
        }
      }
    } else if (host.includes("twitter.com") || host.includes("x.com")) {
      // Prioritas 1 DOM Presisi: Cari [data-testid="tweetText"] resmi
      const tweetEl = container.querySelector('[data-testid="tweetText"]') ||
                      document.querySelector('[data-testid="primaryColumn"] [data-testid="tweetText"]') ||
                      document.querySelector('[data-testid="tweetText"]');
      if (tweetEl) {
        const clone = tweetEl.cloneNode(true);
        clone.querySelectorAll("button, [role='button']").forEach(b => {
          const bt = (b.textContent || "").toLowerCase();
          if (bt.includes("terjemahkan") || bt.includes("translate")) b.remove();
        });
        cleanText = (clone.innerText || clone.textContent || "").trim();
      }

      // Pembersihan teks tweet dari nama pengunggah / handle / middot
      if (cleanText) {
        if (authorHandle) {
          cleanText = cleanText.replace(new RegExp(`^(?:[^\n@]{0,40}@${authorHandle}\\s*(?:·\\s*\\d+[a-zA-Z\\s]*)?)+`, "i"), "").trim();
          cleanText = cleanText.replace(new RegExp(`^@?${authorHandle}\\s*`, "i"), "").trim();
        }
        if (authorName) {
          const escName = authorName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          cleanText = cleanText.replace(new RegExp(`^${escName}\\s*`, "i"), "").trim();
        }
        cleanText = cleanText.replace(/^[·•\s]+\d+\s*[a-zA-Z]+\s*/, "").trim();
        cleanText = cleanText.replace(/Terjemahkan postingan|Translate post/gi, "").trim();

        // Pembersihan header akun yang menempel di awal (misal: "Sumatera Adil & Federal@indepenSumateraPRABOWO..." -> "PRABOWO...")
        if (authorHandle) {
          cleanText = cleanText.replace(new RegExp(`^(?:[^\\n@]{0,50})?@?${authorHandle}\\s*`, "i"), "").trim();
        }
        cleanText = cleanText.replace(/^(?:[^\n@]{0,50})?@[a-zA-Z0-9_\.]*?[a-z0-9](?=[A-Z]{2,}|\d+\.)\s*/i, "").trim();
        cleanText = cleanText.replace(/^(?:[A-Z][a-zA-Z0-9\s._-]+)?@([a-zA-Z0-9_]{1,20}?)(?=[A-Z]{2,}|\d+\.|\b)\s*/i, "").trim();
        cleanText = cleanText.replace(/^(?:[A-Z][a-zA-Z0-9\s._-]{0,40})?@[a-zA-Z0-9_]+(?:\s*[·•]\s*[\w\d]+)?(?:\s*(?=\d+\.))?\s*/i, "").trim();
        cleanText = cleanText.replace(/^[A-Z][a-zA-Z0-9\s._-]+@[a-zA-Z0-9_]+\s*/i, "").trim();

        // Pembersihan kontrol video pemutar X (durasi: 00:00 / 09:28)
        cleanText = cleanText.replace(/\d{1,2}:\d{2}\s*[\/|\\]\s*\d{1,2}:\d{2}/g, " ");

        // Pembersihan cap waktu tweet (misal: 9:14 PM · Oct 20, 2026)
        cleanText = cleanText.replace(/\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*[·•\u00b7\u2022]\s*[A-Za-z]{3}\s*\d{1,2},\s*\d{4}/g, " ");
        cleanText = cleanText.replace(/[·•\u00b7\u2022\s]*\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b/g, " ");

        // Pembersihan metrik tayangan dan kutipan (misal: 767.3KViews, 535View quotes)
        cleanText = cleanText.replace(/[·•\u00b7\u2022\s]*\d+[\d\.,]*[KkMm]?\s*(?:Views|View quotes|views|quotes|suka|likes|Retweets|reposts|Bookmarks|bookmarked)(?=[^a-zA-Z]|$)/gi, " ");
        // Pertahankan jeda antar paragraf \n\n, hanya rapikan spasi/tab horizontal
      cleanText = cleanText.replace(/[ \t]+/g, " ");
      cleanText = cleanText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
      }

      // Prioritas 2: Fallback ke OpenGraph HANYA jika DOM kosong
      if (!cleanText || cleanText.length < 5) {
        const ogDesc = document.querySelector('meta[property="og:description"]')?.content;
        if (ogDesc) {
          const qm = ogDesc.match(/^["“]([\s\S]+?)["”]$/);
          if (qm && qm[1]) cleanText = qm[1].trim();
        }
      }
    } else if (host.includes("tiktok.com")) {
      const ttDesc = container.querySelector('[data-e2e="browse-video-desc"], [data-e2e="user-post-item-desc"]');
      if (ttDesc && ttDesc.textContent.trim().length >= 5) {
        cleanText = ttDesc.textContent.trim();
      }
    } else if (host.includes("facebook.com")) {
      // 1. Selector resmi naskah postingan Facebook Comet UI
      const fbMsg = container.querySelector('div[data-ad-preview="message"], div[data-ad-comet-preview="message"], div[dir="auto"][style*="text-align"]');
      if (fbMsg) {
        // innerText mempertahankan jeda baris alami antar elemen blok
        const msgText = (fbMsg.innerText || fbMsg.textContent || "").trim();
        if (msgText.length >= 15) {
          cleanText = msgText.replace(/\n\s*\n\s*\n+/g, "\n\n");
        }
      }
      
      if (!cleanText || cleanText.length < 15) {
        // 2. Scan div[dir="auto"] dan <p> di dalam container, gabungkan blok paragraf dengan \n\n
        const candidateDivs = container.querySelectorAll('div[dir="auto"], p');
        const paragraphs = [];
        const seenParas = new Set();
        for (const div of candidateDivs) {
          if (div.closest("button, [role='button'], form, ul, ol, nav, header, footer")) continue;
          const txt = (div.innerText || div.textContent || "").trim();
          if (txt.length >= 20 && !seenParas.has(txt)) {
            let isSub = false;
            for (const sp of seenParas) {
              if (sp.includes(txt)) { isSub = true; break; }
            }
            if (!isSub) {
              seenParas.add(txt);
              paragraphs.push(txt);
            }
          }
        }
        if (paragraphs.length > 0) {
          cleanText = paragraphs.join("\n\n");
        }
      }
    }

    // 6. Fallback jika selektor presisi tidak ditemukan: Kloning node dan buang SEMUA komentar, header profil & banner interaksi
    if (!cleanText || cleanText.length < 15) {
      const clone = container.cloneNode(true);
      // Hapus komentar (ul li, ul div), header akun/profil, interaksi likes, footer, form komentar, tombol Ikuti
      clone.querySelectorAll(
        "script, style, svg, nav, button, iframe, noscript, dialog, header, footer, " +
        "[data-testid='User-Name'], [data-testid='socialContext'], [role='group'], [data-testid='caret'], " +
        "ul li, ul div[role='menuitem'], ul > div:nth-child(n+2), section, form, textarea, time, " +
        "div[role='button'], [aria-label*='Komentar'], [aria-label*='Comment'], [aria-label*='Suka'], [aria-label*='Like']"
      ).forEach((el) => el.remove());
      cleanText = clone.innerText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
    }

    // 7. Filter Teks Pembersih (Hapus penanda terjemahan, batas komentar, dan banner 'Disukai oleh')
    if (cleanText) {
      // Potong komentar yang menempel setelah teks "Lihat terjemahan" / "See translation"
      const translationMarkers = ["Lihat terjemahan", "See translation", "View translation", "Lihat semua komentar", "View all comments"];
      for (const m of translationMarkers) {
        if (cleanText.includes(m)) {
          cleanText = cleanText.split(m)[0].trim();
        }
      }

      // Hapus banner likes: "Disukai oleh ... dan ... lainnya"
      cleanText = cleanText.replace(/Disukai oleh.*?lainnya/gi, " ");
      cleanText = cleanText.replace(/Liked by.*?others/gi, " ");

      // Hapus pengulangan handle akun di awal teks jika menempel
      if (authorHandle) {
        const handleRegex = new RegExp(`^(?:${authorHandle}\\s*)+`, "i");
        cleanText = cleanText.replace(handleRegex, "").trim();
      }

      // Bersihkan pemutar video (misal: 00:00 / 09:28)
      cleanText = cleanText.replace(/\d{1,2}:\d{2}\s*[\/|\\]\s*\d{1,2}:\d{2}/g, " ");

      // Bersihkan cap waktu tweet & metrik
      cleanText = cleanText.replace(/\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*[·•\u00b7\u2022]\s*[A-Za-z]{3}\s*\d{1,2},\s*\d{4}/g, " ");
      cleanText = cleanText.replace(/[·•\u00b7\u2022\s]*\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b/g, " ");
      cleanText = cleanText.replace(/[·•\u00b7\u2022\s]*\d+[\d\.,]*[KkMm]?\s*(?:Views|View quotes|views|quotes|suka|likes|Retweets|reposts|Bookmarks|bookmarked)(?=[^a-zA-Z]|$)/gi, " ");

      // Hapus penanda waktu di akhir (misal: "1 hari", "2 jam yang lalu", "Kirim")
      cleanText = cleanText.replace(/\b\d+\s*(?:hari|jam|m|menit|d|detik|w|minggu)\s*(?:yang\s+lalu)?\s*(?:Kirim)?$/gi, "").trim();

      // Hapus mutlak artefak widget sampingan X/Twitter jika sempat lolos
      cleanText = cleanText.replace(/Relevant people.*/gis, "").trim();
      cleanText = cleanText.replace(/What['’]s happening.*/gis, "").trim();
      cleanText = cleanText.replace(/Who to follow.*/gis, "").trim();

      // Pertahankan jeda antar paragraf \n\n, hanya rapikan spasi/tab horizontal
      cleanText = cleanText.replace(/[ \t]+/g, " ");
      cleanText = cleanText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
    }

    return {
      container,
      permalink,
      published_at: publishedAt,
      author_name: authorName,
      author_handle: authorHandle,
      clean_text: cleanText,
      comments: extractedComments,
      likes_count: likesCount,
      has_media: hasMedia,
    };
  }

  // ─────────────────────────────────────────────────────────────
  // UNIVERSAL 3-LAYER ACQUISITION ENGINE (DOMAIN-AWARE)
  // ─────────────────────────────────────────────────────────────
  function acquirePageContent() {
    const currentUrl = window.location.href;
    const platform = classifyPlatform(currentUrl);

    let extractionMethod = "fallback_dom";
    let domText = "";
    let title = "";
    let targetUrl = currentUrl;
    let username = "";
    let displayName = "";
    let postedAt = null;
    let mediaImageUrl = null;
    let transcript = null;
    let likesCount = 0;
    let hasMedia = false;

    // ── PRIORITAS 0: Highlight-to-Capture ──
    const userSelection = window.getSelection() ? window.getSelection().toString().trim() : "";
    if (userSelection && userSelection.length >= 10) {
      extractionMethod = "user_highlight";
      domText = userSelection;
      title = userSelection.length > 80 ? (userSelection.slice(0, 80) + "...") : userSelection;
    }

    // ── DOMAIN-AWARE ROUTING: SOCIAL MEDIA vs NEWS / YOUTUBE ──
    const isSocialMedia = ["x", "instagram", "facebook", "threads", "tiktok"].includes(platform);

    if (isSocialMedia && extractionMethod !== "user_highlight") {
      // ── LAYER 2 (Primary for Social): Semantic <article> Container ──
      const articleData = extractSemanticArticleContainer();
      if (articleData && articleData.clean_text && articleData.clean_text.length >= 15) {
        extractionMethod = "semantic_article";
        domText = articleData.clean_text;
        // Bentuk judul bersih & informatif dari kalimat pertama (bersihkan bullet numbering)
        const firstSentence = domText.split(/[.!?\n]/)[0].trim().replace(/^\d+\.\s*/, "");
        if (firstSentence && firstSentence.length >= 15 && firstSentence.length <= 90) {
          title = firstSentence;
        } else {
          const cleanSnippet = domText.replace(/^\d+\.\s*/, "").trim();
          title = cleanSnippet.length > 80 ? (cleanSnippet.slice(0, 77).trim() + "...") : cleanSnippet;
        }
        if (articleData.permalink) targetUrl = articleData.permalink;
        if (articleData.published_at) postedAt = articleData.published_at;
        if (articleData.author_handle) username = articleData.author_handle;
        if (articleData.author_name) displayName = articleData.author_name;
        if (articleData.likes_count) likesCount = articleData.likes_count;
        if (articleData.has_media) hasMedia = true;
      }
    } else if (!isSocialMedia && extractionMethod !== "user_highlight") {
      // ── LAYER 1 (Primary for News & YouTube): OpenGraph + JSON-LD + Article Main ──
      const ogLd = extractOpenGraphAndJsonLd();
      if (ogLd.title || ogLd.description || ogLd.article_body) {
        extractionMethod = "opengraph_jsonld";
        title = ogLd.title || document.title;
        if (ogLd.canonical_url) targetUrl = ogLd.canonical_url;
        if (ogLd.published_time) postedAt = ogLd.published_time;
        if (ogLd.media_image_url) mediaImageUrl = ogLd.media_image_url;
        if (ogLd.author) displayName = ogLd.author;

        // Extract deep body text from main container
        const mainEl = document.querySelector("article, main, .read__content, .detail__body-text, #article-body, .it-detail");
        let bodyText = "";
        if (mainEl) {
          const clone = mainEl.cloneNode(true);
          clone.querySelectorAll("script, style, svg, nav, button, iframe, noscript, dialog").forEach((el) => el.remove());
          // Pastikan pemisah paragraf <p> tidak menempel tanpa jeda
          clone.querySelectorAll("p, div.paragraph, div.detail__body-text > div").forEach((p) => {
            p.insertAdjacentText("afterend", "\n\n");
          });
          bodyText = (clone.innerText || clone.textContent || "")
            .replace(/[ \t]+/g, " ")
            .replace(/\n\s*\n\s*\n+/g, "\n\n")
            .trim();

          // Bersihkan widget portal berita (Advertisement, audio player, kredit foto)
          bodyText = bodyText.replace(/\bAdvertisement\b/gi, " ");
          bodyText = bodyText.replace(/\bListen\s+\d+\s*(?:min|mins|menit)\b/gi, " ");
          bodyText = bodyText.replace(/New:\s*You can now listen to articles[^\n]*/gi, " ");
          bodyText = bodyText.replace(/\(Photo:[^\)]*\)/gi, " ");
          bodyText = bodyText.replace(/\[Photo:[^\]]*\]/gi, " ");
          bodyText = bodyText.replace(/\(Foto:[^\)]*\)/gi, " ");
          bodyText = bodyText.replace(/\[Foto:[^\]]*\]/gi, " ");
          bodyText = bodyText.replace(/Follow us on[^\n]*/gi, " ");
          bodyText = bodyText.replace(/\n\s*\n\s*\n+/g, "\n\n").trim();
        }

        const combinedParts = [];
        if (ogLd.description) combinedParts.push(ogLd.description);
        if (bodyText && bodyText !== ogLd.description) combinedParts.push(bodyText);
        else if (ogLd.article_body) combinedParts.push(ogLd.article_body);

        domText = combinedParts.join("\n\n").trim() || ogLd.description || title;
      }
    }

    // ── YOUTUBE TRANSCRIPT & EXTRACTION ENRICHMENT ──
    if (platform === "youtube") {
      const tit = document.querySelector("#title h1 yt-formatted-string") || document.querySelector("meta[name='title']");
      if (tit) title = tit.textContent?.trim() || tit.content || title;
      const ch = document.querySelector("#channel-name a") || document.querySelector("#owner #text a");
      if (ch) {
        displayName = ch.textContent?.trim() || displayName;
        const href = ch.getAttribute("href") || "";
        if (href.includes("@")) username = href.split("@")[1].split("/")[0];
      }
      const tNodes = document.querySelectorAll("ytd-transcript-segment-renderer .segment-text, #segments-container yt-formatted-string");
      if (tNodes && tNodes.length > 0) {
        transcript = Array.from(tNodes).map((n) => n.textContent.trim()).filter(Boolean).join(" ");
      }
    }

    // ── FALLBACK IF DOM TEXT STILL EMPTY ──
    if (!domText || domText.length < 5) {
      const ogLd = extractOpenGraphAndJsonLd();
      domText = ogLd.description || document.title || "Tangkapan bukti digital TILIK.";
      title = ogLd.title || document.title;
      extractionMethod = "fallback_dom";
    }

    return {
      platform,
      source_url: targetUrl,
      title: title || document.title,
      dom_text: domText,
      extraction_method: extractionMethod,
      username: username || undefined,
      display_name: displayName || undefined,
      posted_at: postedAt || undefined,
      media_image_url: mediaImageUrl || undefined,
      transcript: transcript || undefined,
      likes_count: likesCount || undefined,
      has_media: hasMedia || undefined,
    };
  }

  // ─────────────────────────────────────────────────────────────
  // FLOATING UI BADGE & INTEGRITY RESULT MODAL (DRAGGABLE & RESILIENT)
  // ─────────────────────────────────────────────────────────────
  const btn = document.createElement("div");
  btn.id = "cyber-patrol-floating-badge";
  btn.title = "Klik untuk Triase. Seret untuk memindahkan posisi.";
  btn.innerHTML = `
    <div class="cp-badge-icon">🛡️</div>
    <span class="cp-badge-text">Triase</span>
  `;

  // Kemampuan Drag-and-Drop agar tidak bertabrakan dengan tombol/widget situs
  let isDragging = false;
  let dragMoved = false;
  let startX = 0;
  let startY = 0;
  let initialLeft = 0;
  let initialTop = 0;

  btn.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    isDragging = true;
    dragMoved = false;
    startX = e.clientX;
    startY = e.clientY;
    const rect = btn.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop = rect.top;
  });

  window.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
      dragMoved = true;
    }
    const maxLeft = Math.max(10, window.innerWidth - btn.offsetWidth - 10);
    const maxTop = Math.max(10, window.innerHeight - btn.offsetHeight - 10);
    const newLeft = Math.min(Math.max(10, initialLeft + dx), maxLeft);
    const newTop = Math.min(Math.max(10, initialTop + dy), maxTop);

    btn.style.left = `${newLeft}px`;
    btn.style.top = `${newTop}px`;
    btn.style.right = "auto";
    btn.style.bottom = "auto";
  });

  window.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
    }
  });

  btn.addEventListener("click", async (e) => {
    if (dragMoved) {
      // Jika digeser/dragged oleh pengguna, jangan picu triase
      return;
    }
    // Guard: Abaikan klik jika proses akuisisi/penyegelan sedang berjalan (anti-double-click)
    if (btn.classList.contains("cp-loading") || btn.classList.contains("cp-capturing")) {
      return;
    }
    btn.classList.add("cp-loading");
    btn.querySelector(".cp-badge-text").textContent = "Akuisisi 3-Layer...";

    // 1. Jalankan Universal 3-Layer Content Acquisition
    const extracted = acquirePageContent();

    // 2. Ambil Operator ID dan Server URL dari chrome.storage.local
    let operatorId = "op_d23_01";
    let serverBaseUrl = "http://127.0.0.1:8000";

    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      const stored = await new Promise((res) => chrome.storage.local.get(["operator_id", "server_url"], res));
      if (stored.operator_id) operatorId = stored.operator_id.trim();
      if (stored.server_url) serverBaseUrl = stored.server_url.trim().replace(/\/+$/, "");
    }

    btn.querySelector(".cp-badge-text").textContent = "Merekam bukti...";

    // 3. Tangkap screenshot layar monitor aktif (Bersih Murni: Sembunyikan Tombol & Modal saat Screenshot)
    let screenshotBase64 = null;
    
    // Sembunyikan badge triase dan seluruh modal secara instan (0ms display none + class cp-capturing) agar tidak terekam pada bukti
    btn.classList.add("cp-capturing");
    btn.style.display = "none";
    btn.style.visibility = "hidden";
    const existingModal = document.getElementById("cp-triage-modal");
    if (existingModal) {
      existingModal.classList.add("cp-capturing");
      existingModal.style.display = "none";
    }

    // Jeda 120ms agar engine render browser selesai menggambar frame bersih tanpa tombol
    await new Promise((r) => setTimeout(r, 120));

    try {
      const captureRes = await new Promise((resolve) => {
        const timer = setTimeout(() => {
          console.warn("[TILIK Content Script] Timeout 8s saat mengambil screenshot, melanjutkan tanpa screenshot.");
          resolve({ ok: false });
        }, 8000);

        try {
          if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
            chrome.runtime.sendMessage({ action: "capture_tab_screenshot" }, (res) => {
              clearTimeout(timer);
              if (chrome.runtime.lastError) {
                console.warn("[TILIK Content Script] Capture error:", chrome.runtime.lastError.message);
                resolve({ ok: false });
              } else {
                resolve(res || { ok: false });
              }
            });
          } else {
            clearTimeout(timer);
            resolve({ ok: false });
          }
        } catch (callErr) {
          clearTimeout(timer);
          console.warn("[TILIK Content Script] Capture call exception:", callErr);
          resolve({ ok: false });
        }
      });

      if (captureRes && captureRes.ok && captureRes.dataUrl) {
        screenshotBase64 = captureRes.dataUrl;
      }
    } catch (e) {
      console.warn("[TILIK Content Script] Capture visible tab error:", e);
    } finally {
      // Tampilkan kembali tombol badge mengambang
      btn.classList.remove("cp-capturing");
      btn.style.display = "";
      btn.style.visibility = "";
      if (existingModal) {
        existingModal.classList.remove("cp-capturing");
        existingModal.style.display = "block";
      }
    }

    // 4. Susun Unified Payload Baku (Layer 3) dengan Strict ISO-8601 UTC
    const capturedAtUtc = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    const payload = {
      url: extracted.source_url || window.location.href,
      source_channel: "BROWSER_EXTENSION",
      reporter_identifier: operatorId,
      operator_id: operatorId,
      captured_at_utc: capturedAtUtc,
      ocr_text: "",
      notes: `[AKUISISI: ${extracted.extraction_method.toUpperCase()}] ${extracted.dom_text.slice(0, 150)}...`,
      screenshot_base64: screenshotBase64 || undefined,
      media_image_url: extracted.media_image_url || undefined,
      username: extracted.username || undefined,
      display_name: extracted.display_name || undefined,
      title: extracted.title || undefined,
      caption: extracted.dom_text || undefined,
      transcript: extracted.transcript || undefined,
      posted_at: extracted.posted_at || undefined,
      likes_count: extracted.likes_count || undefined,
      has_media: extracted.has_media || false,
      platform_hint: extracted.platform || undefined,
    };

    btn.querySelector(".cp-badge-text").textContent = "Penyegelan HMAC...";
    const statusTextTimer = setTimeout(() => {
      if (btn.classList.contains("cp-loading")) {
        btn.querySelector(".cp-badge-text").textContent = "Analisis AI Lokal...";
      }
    }, 3500);

    // 5. Kirim ke Backend API
    const handleResult = (ok, data, errorText) => {
      clearTimeout(statusTextTimer);
      if (ok && data && data.ticket_number) {
        btn.querySelector(".cp-badge-text").textContent = `Tiket: ${data.ticket_number}`;
        btn.classList.remove("cp-loading");
        btn.classList.add("cp-success");

        showTriageResultModal(data, extracted, operatorId);

        setTimeout(() => {
          btn.classList.remove("cp-success");
          btn.querySelector(".cp-badge-text").textContent = "Triase";
        }, 6000);
      } else {
        btn.classList.remove("cp-loading");
        btn.classList.add("cp-error");
        btn.querySelector(".cp-badge-text").textContent = "Gagal";

        let errDetail = errorText || (data && (data.detail || data.message)) || `Server offline di ${serverBaseUrl}`;
        if (typeof errDetail === "string" && errDetail.includes("Extension context invalidated")) {
          errDetail = "⚠️ Ekstensi baru saja diperbarui di Chrome! Silakan REFRESH / MUAT ULANG (F5) tab halaman ini agar terhubung kembali ke ekstensi.";
        }
        showTriageErrorModal(typeof errDetail === "object" ? JSON.stringify(errDetail) : String(errDetail));

        setTimeout(() => {
          btn.classList.remove("cp-error");
          btn.querySelector(".cp-badge-text").textContent = "Triase";
        }, 5000);
      }
    };

    // Kirim via Background Service Worker (dengan batas waktu 180s untuk inferensi AI lokal)
    let messageDispatched = false;
    try {
      if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
        messageDispatched = true;
        const submitTimer = setTimeout(() => {
          handleResult(false, null, "Permintaan triase melampaui batas waktu (timeout 180s). Pastikan server backend sedang aktif.");
        }, 180000);

        chrome.runtime.sendMessage({ action: "submit_intake", payload }, (bgRes) => {
          clearTimeout(submitTimer);
          if (chrome.runtime.lastError) {
            handleResult(false, null, chrome.runtime.lastError.message);
          } else if (bgRes) {
            handleResult(bgRes.ok, bgRes.data, bgRes.error);
          } else {
            handleResult(false, null, "Tidak ada respon dari service worker. Coba buka kembali ekstensi dari toolbar.");
          }
        });
      }
    } catch (sendErr) {
      console.warn("[TILIK Content Script] sendMessage exception:", sendErr);
      messageDispatched = false;
    }

    if (!messageDispatched) {
      try {
        const res = await fetch(`${serverBaseUrl}/api/v1/assistant/intake`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const d = await res.json().catch(() => ({}));
        handleResult(res.ok, d, res.ok ? null : (d.detail || res.statusText));
      } catch (err) {
        handleResult(false, null, err.message);
      }
    }
  });

  document.body.appendChild(btn);

  // ─────────────────────────────────────────────────────────────
  // MODAL HASIL TRIASE & INTEGRITAS KRIPTOGRAFI
  // ─────────────────────────────────────────────────────────────
  function showTriageResultModal(data, extracted, operatorId) {
    const existing = document.getElementById("cp-triage-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "cp-triage-modal";

    const hmacTagShort = data.hmac_tag ? `${data.hmac_tag.slice(0, 16)}...` : "N/A";
    const statusBadge = data.verification_status === "VERIFIED"
      ? `<span style="background:rgba(16,185,129,0.2);color:#34d399;border:1px solid #059669;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;">🛡️ VERIFIED (NIST FIPS 198-1)</span>`
      : `<span style="background:rgba(239,68,68,0.2);color:#f87171;border:1px solid #dc2626;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;">⚠️ UNVERIFIED</span>`;

    modal.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <div style="font-weight:800;font-size:12px;color:#60a5fa;display:flex;align-items:center;gap:5px;">
          <span>TILIK PATROL ASSISTANT</span>
        </div>
        <button id="cp-modal-close" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:16px;">✕</button>
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <span style="font-family:monospace;font-size:11px;font-weight:700;color:#f1f5f9;background:#0f172a;padding:2px 6px;border-radius:4px;border:1px solid #334155;">${data.ticket_number}</span>
        ${statusBadge}
      </div>
      <div style="font-size:11px;color:#cbd5e1;line-height:1.4;margin-bottom:8px;background:#090d16;padding:7px;border-radius:6px;border:1px solid #1e293b;">
        <div><strong>Metode:</strong> <span style="color:#38bdf8;">${extracted.extraction_method.toUpperCase()}</span></div>
        <div><strong>Operator:</strong> <span style="color:#a7f3d0;">${operatorId}</span></div>
        <div><strong>HMAC-SHA256:</strong> <span style="font-family:monospace;color:#fbcfe8;">${hmacTagShort}</span></div>
      </div>
      <div style="font-size:10.5px;color:#94a3b8;margin-bottom:10px;max-height:60px;overflow-y:auto;">
        ${data.ai_summary ? `<strong>Analisis:</strong> ${data.ai_summary}` : 'Bukti digital telah terikat integritasnya dan tercatat di antrean intelijen.'}
      </div>
      <a href="${data.dashboard_url || 'http://localhost:8000/dashboard/#/contents'}" target="_blank" style="display:block;text-align:center;background:#2563eb;color:#fff;text-decoration:none;padding:7px;border-radius:6px;font-size:11px;font-weight:600;">
        Buka di Dashboard →
      </a>
    `;

    document.body.appendChild(modal);
    document.getElementById("cp-modal-close").addEventListener("click", () => modal.remove());
  }

  function showTriageErrorModal(errorDetail) {
    const existing = document.getElementById("cp-triage-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "cp-triage-modal";
    modal.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <span style="font-weight:800;font-size:12px;color:#f43f5e;">⚠️ AKUISISI GAGAL</span>
        <button id="cp-modal-close" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:16px;">✕</button>
      </div>
      <div style="font-size:11px;color:#fecdd3;line-height:1.4;margin-bottom:10px;background:#881337;padding:8px;border-radius:6px;">
        ${errorDetail}
      </div>
      <button id="cp-modal-dismiss" style="width:100%;background:#334155;color:#fff;border:none;padding:6px;border-radius:6px;font-size:11px;cursor:pointer;">
        Tutup
      </button>
    `;

    document.body.appendChild(modal);
    document.getElementById("cp-modal-close").addEventListener("click", () => modal.remove());
    document.getElementById("cp-modal-dismiss").addEventListener("click", () => modal.remove());
  }
})();
