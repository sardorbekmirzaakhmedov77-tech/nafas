/* Home page: switch the sky between cities without reloading. */
(function () {
  const sky = document.getElementById("sky");
  if (!sky || !window.fetch) return;
  const select = document.getElementById("switch-city");
  const field = (name) => sky.querySelector(`[data-field="${name}"]`);
  const hour = (iso) => iso.slice(11, 16);
  const round = (v) => (v === null || v === undefined ? "–" : Math.round(v));

  async function show(slug, push) {
    let city, fc;
    try {
      [city, fc] = await Promise.all([
        fetch(`/api/v1/cities/${slug}`).then((r) => r.json()),
        fetch(`/api/v1/cities/${slug}/forecast`).then((r) => r.json()),
      ]);
    } catch (e) {
      window.location.href = `/?city=${slug}`;   // fall back to a normal page load
      return;
    }
    const now = city.current;
    if (!now) return;
    const cat = Nafas.categoryFor(now.us_aqi);

    Nafas.applySky(sky, now.us_aqi);
    field("name").textContent = city.name;
    field("aqi").textContent = now.us_aqi;
    field("category").textContent = cat.name;
    field("dot").style.color = cat.color;
    field("advice").textContent = cat.advice;
    field("updated").textContent = `updated ${hour(now.time)}`;
    ["pm2_5", "pm10", "nitrogen_dioxide", "ozone"].forEach((k) => {
      const el = field(k);
      if (el) el.textContent = round(now[k]);
    });

    const next = fc.hourly.slice(0, 24);
    const bars = field("bars");
    if (bars) {
      // Reuse existing bars so heights animate instead of jumping
      while (bars.children.length < next.length) bars.appendChild(document.createElement("span"));
      [...bars.children].forEach((bar, i) => {
        const r = next[i];
        if (!r) { bar.remove(); return; }
        const c = Nafas.categoryFor(r.us_aqi);
        bar.style.height = Math.min((r.us_aqi || 0) / 200 * 100, 100).toFixed(1) + "%";
        bar.style.setProperty("--c", c ? c.color : "#ccc");
        bar.title = `${hour(r.time)}: AQI ${r.us_aqi}`;
      });
      field("axis").innerHTML = next.filter((_, i) => i % 3 === 0)
        .map((r) => `<span>${hour(r.time)}</span>`).join("");
    }

    const details = document.querySelector('[data-field="details"]');
    details.href = `/city/${slug}`;
    details.textContent = `See ${city.name} in detail`;

    document.querySelectorAll(".pin").forEach((p) => p.classList.toggle("is-current", p.dataset.city === slug));
    document.querySelectorAll(".rank a").forEach((a) =>
      a.dataset.city === slug ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current"));
    if (select) select.value = slug;
    document.title = `${city.name}: AQI ${now.us_aqi}, ${cat.name.toLowerCase()} | Nafas`;
    if (push) history.pushState({ slug }, "", `/?city=${slug}`);
  }

  document.addEventListener("click", (e) => {
    const link = e.target.closest("[data-city]");
    if (!link || e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    show(link.dataset.city, true);
    sky.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });

  if (select) select.addEventListener("change", () => show(select.value, true));
  window.addEventListener("popstate", (e) => {
    const slug = (e.state && e.state.slug) || new URLSearchParams(location.search).get("city") || "tashkent";
    show(slug, false);
  });
})();
