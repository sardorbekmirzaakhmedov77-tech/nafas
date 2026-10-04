/* Shared helpers: AQI categories and sky colours (mirrors nafas/aqi.py). */
(function () {
  const data = JSON.parse(document.getElementById("aqi-data").textContent);

  function categoryFor(aqi) {
    if (aqi === null || aqi === undefined) return null;
    const v = Math.max(0, Math.round(aqi));
    return data.categories.find((c) => v <= c.high) || data.categories[data.categories.length - 1];
  }

  function hexToRgb(h) {
    h = h.replace("#", "");
    return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  }
  function mix(a, b, t) {
    const ra = hexToRgb(a), rb = hexToRgb(b);
    return "#" + ra.map((x, i) => Math.round(x + (rb[i] - x) * t).toString(16).padStart(2, "0")).join("");
  }

  function skyFor(aqi) {
    const stops = data.sky;
    aqi = Math.max(0, Math.min(500, aqi || 0));
    for (let i = 0; i < stops.length - 1; i++) {
      const [a0, top0, hor0, ink0, blur0] = stops[i];
      const [a1, top1, hor1, ink1, blur1] = stops[i + 1];
      if (aqi <= a1) {
        const t = (aqi - a0) / (a1 - a0);
        return {
          top: mix(top0, top1, t), horizon: mix(hor0, hor1, t),
          ink: t > 0.5 ? ink1 : ink0,
          sunBlur: Math.round(blur0 + (blur1 - blur0) * t),
          haze: Math.min(aqi / 300, 1) * 0.55,
        };
      }
    }
    const last = stops[stops.length - 1];
    return { top: last[1], horizon: last[2], ink: last[3], sunBlur: last[4], haze: 0.55 };
  }

  function applySky(el, aqi) {
    const s = skyFor(aqi);
    el.style.setProperty("--sky-top", s.top);
    el.style.setProperty("--sky-horizon", s.horizon);
    el.style.setProperty("--sky-ink", s.ink);
    document.body.style.setProperty("--sky-ink", s.ink);  // top bar sits outside the sky
    el.style.setProperty("--sun-blur", s.sunBlur + "px");
    el.style.setProperty("--haze", s.haze.toFixed(3));
  }

  window.Nafas = { categoryFor, skyFor, applySky, categories: data.categories };
})();
