/* City page: history chart with 24h / 7d / 30d ranges. */
(function () {
  const canvas = document.getElementById("history-chart");
  if (!canvas || !window.Chart) return;
  const summary = document.getElementById("chart-summary");
  const buttons = document.querySelectorAll(".tabs button");
  const ink = "#17323E", soft = "#546970", line = "#E2E8E6";

  Chart.defaults.font.family = "Onest, system-ui, sans-serif";
  Chart.defaults.color = soft;

  // Faint category bands behind the line, so the chart reads at a glance.
  const bands = {
    id: "aqiBands",
    beforeDatasetsDraw(chart) {
      const { ctx, chartArea: a, scales: { y } } = chart;
      ctx.save();
      Nafas.categories.forEach((c) => {
        const top = y.getPixelForValue(Math.min(c.high + 0.5, y.max));
        const bottom = y.getPixelForValue(Math.max(c.low - 0.5, y.min));
        if (bottom <= a.top || top >= a.bottom) return;
        ctx.fillStyle = c.color + "14";
        ctx.fillRect(a.left, Math.max(top, a.top), a.right - a.left, Math.min(bottom, a.bottom) - Math.max(top, a.top));
      });
      ctx.restore();
    },
  };

  const colorAt = (v) => (Nafas.categoryFor(v) || { color: "#999" }).color;
  let chart;

  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  // Times arrive as local Uzbekistan time ("2026-10-05T14:00"); format them as-is.
  function label(iso, hours) {
    const [date, time] = iso.split("T");
    const day = `${+date.slice(8, 10)} ${MONTHS[+date.slice(5, 7) - 1]}`;
    if (hours <= 24) return time;
    return hours <= 168 ? `${day}, ${time}` : day;
  }

  async function load(hours) {
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.hours === hours)));
    const res = await fetch(`/api/v1/cities/${window.NAFAS_CITY}/history?hours=${hours}`);
    const data = await res.json();
    const rows = data.readings.filter((r) => r.us_aqi !== null);
    const values = rows.map((r) => r.us_aqi);
    const labels = rows.map((r) => label(r.time, hours));
    const yMax = Math.max(100, Math.ceil((Math.max(...values) + 15) / 50) * 50);

    const dataset = {
      data: values,
      borderWidth: hours > 168 ? 1.6 : 2.4,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointHoverBackgroundColor: (ctx) => colorAt(ctx.raw),
      pointHoverBorderColor: "#fff",
      tension: 0.35,
      segment: { borderColor: (ctx) => colorAt((ctx.p0.parsed.y + ctx.p1.parsed.y) / 2) },
      fill: false,
    };

    if (chart) {
      chart.data.labels = labels;
      chart.data.datasets[0] = dataset;
      chart.options.scales.y.max = yMax;
      chart.update();
    } else {
      chart = new Chart(canvas, {
        type: "line",
        data: { labels, datasets: [dataset] },
        plugins: [bands],
        options: {
          maintainAspectRatio: false,
          animation: { duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 500 },
          interaction: { mode: "index", intersect: false },
          scales: {
            x: { grid: { display: false }, ticks: { maxTicksLimit: 8, maxRotation: 0 }, border: { color: line } },
            y: { min: 0, max: yMax, grid: { color: line }, border: { display: false }, ticks: { stepSize: 50 } },
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: ink, padding: 10, displayColors: false,
              titleFont: { weight: "600" },
              callbacks: { label: (ctx) => `AQI ${ctx.raw}, ${Nafas.categoryFor(ctx.raw).name.toLowerCase()}` },
            },
          },
        },
      });
    }

    if (values.length) {
      const avg = Math.round(values.reduce((a, b) => a + b, 0) / values.length);
      const max = Math.max(...values), min = Math.min(...values);
      const badHours = values.filter((v) => v > 100).length;
      summary.innerHTML =
        `<span>Average <strong>${avg}</strong></span>` +
        `<span>Highest <strong>${max}</strong></span>` +
        `<span>Lowest <strong>${min}</strong></span>` +
        `<span>Hours above 100 <strong>${badHours}</strong></span>`;
    }
  }

  buttons.forEach((b) => b.addEventListener("click", () => load(+b.dataset.hours)));
  load(168);
})();
