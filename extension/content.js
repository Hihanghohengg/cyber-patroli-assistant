// Injected content script for Cyber Patrol quick floating action button

(function() {
  // Avoid injecting twice
  if (document.getElementById("cyber-patrol-floating-badge")) return;

  const btn = document.createElement("div");
  btn.id = "cyber-patrol-floating-badge";
  btn.innerHTML = `
    <div class="cp-badge-icon">🛡️</div>
    <span class="cp-badge-text">Triase Patroli</span>
  `;

  btn.addEventListener("click", async () => {
    btn.classList.add("cp-loading");
    btn.querySelector(".cp-badge-text").textContent = "Menganalisis...";

    try {
      const res = await fetch("http://localhost:8000/api/v1/assistant/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: window.location.href,
          source_channel: "BROWSER_EXTENSION",
          reporter_identifier: "In-Page-Floating-Agent",
          notes: "Intake instan via tombol mengambang in-page"
        })
      });

      const data = await res.json();
      if (res.ok) {
        btn.querySelector(".cp-badge-text").textContent = `Tiket: ${data.ticket_number}`;
        btn.classList.remove("cp-loading");
        btn.classList.add("cp-success");
        setTimeout(() => {
          btn.classList.remove("cp-success");
          btn.querySelector(".cp-badge-text").textContent = "Triase Patroli";
        }, 4000);
      } else {
        throw new Error(data.detail || "Error");
      }
    } catch (err) {
      btn.classList.remove("cp-loading");
      btn.classList.add("cp-error");
      btn.querySelector(".cp-badge-text").textContent = "Gagal (Cek Backend)";
      setTimeout(() => {
        btn.classList.remove("cp-error");
        btn.querySelector(".cp-badge-text").textContent = "Triase Patroli";
      }, 3000);
    }
  });

  document.body.appendChild(btn);
})();
