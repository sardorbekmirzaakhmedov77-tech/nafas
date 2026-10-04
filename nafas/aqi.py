"""US EPA Air Quality Index: categories, colours, advice and calculation.

Breakpoints follow the EPA's 2024 revision of the PM2.5 standard.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    name: str
    low: int
    high: int
    color: str
    advice: str
    text: str = "#17323E"  # readable text colour on top of `color`


CATEGORIES = [
    Category("good", "Good", 0, 50, "#45A766",
             "Air is clean. A good day to be outside."),
    Category("moderate", "Moderate", 51, 100, "#D9B531",
             "Acceptable for most people. If you're unusually sensitive, "
             "take it easier outdoors."),
    Category("sensitive", "Unhealthy for sensitive groups", 101, 150, "#E5832F",
             "Children, older adults and people with heart or lung conditions "
             "should cut back on long or intense outdoor activity."),
    Category("unhealthy", "Unhealthy", 151, 200, "#D2453D",
             "Everyone should limit time outdoors. Keep windows closed and "
             "consider a mask if you have to go out.", "#FFFFFF"),
    Category("very-unhealthy", "Very unhealthy", 201, 300, "#8B4799",
             "Health alert. Avoid outdoor activity and run an air purifier "
             "indoors if you can.", "#FFFFFF"),
    Category("hazardous", "Hazardous", 301, 500, "#74213A",
             "Emergency conditions. Stay indoors with windows shut.", "#FFFFFF"),
]


def category_for(aqi):
    """Return the Category for an AQI value (None-safe)."""
    if aqi is None:
        return None
    aqi = max(0, round(aqi))
    for cat in CATEGORIES:
        if aqi <= cat.high:
            return cat
    return CATEGORIES[-1]


# (concentration low, concentration high, index low, index high)
PM25_BREAKPOINTS = [
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
]

PM10_BREAKPOINTS = [
    (0, 54, 0, 50),
    (55, 154, 51, 100),
    (155, 254, 101, 150),
    (255, 354, 151, 200),
    (355, 424, 201, 300),
    (425, 604, 301, 500),
]


def _sub_index(conc, breakpoints, decimals):
    if conc is None:
        return None
    conc = max(0.0, float(conc))
    # EPA truncates concentrations before looking up the breakpoint
    factor = 10 ** decimals
    conc = int(conc * factor) / factor
    for c_lo, c_hi, i_lo, i_hi in breakpoints:
        if conc <= c_hi:
            return round((i_hi - i_lo) / (c_hi - c_lo) * (conc - c_lo) + i_lo)
    return 500


def pm25_aqi(conc):
    return _sub_index(conc, PM25_BREAKPOINTS, 1)


def pm10_aqi(conc):
    return _sub_index(conc, PM10_BREAKPOINTS, 0)


def combined_aqi(pm25=None, pm10=None):
    """The overall AQI is the highest sub-index among the pollutants."""
    values = [v for v in (pm25_aqi(pm25), pm10_aqi(pm10)) if v is not None]
    return max(values) if values else None


# --------------------------------------------------------------------------- #
#  The sky: hero colours that turn from clear blue to dusty haze with the AQI
# --------------------------------------------------------------------------- #
# (aqi, sky top, sky horizon, ink colour, sun blur in px)
SKY_STOPS = [
    (0, "#7FB6DE", "#E4F0F6", "#14303F", 2),
    (50, "#9CC2DA", "#ECF0EC", "#14303F", 6),
    (100, "#B8C2BE", "#F0E6CF", "#2A2A22", 18),
    (150, "#BFAE8C", "#EBD3A6", "#2E2418", 34),
    (200, "#A98E6A", "#D9B987", "#22180F", 52),
    (300, "#7A6550", "#B4946E", "#FBF3E6", 70),
    (500, "#4E3F36", "#86705A", "#FBF3E6", 90),
]


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    ra, rb = _hex_to_rgb(a), _hex_to_rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ra, rb))


def sky_for(aqi):
    """CSS colours for the hero sky at a given AQI."""
    aqi = 0 if aqi is None else max(0, min(500, aqi))
    for (a0, top0, hor0, ink0, blur0), (a1, top1, hor1, ink1, blur1) in zip(SKY_STOPS, SKY_STOPS[1:]):
        if aqi <= a1:
            t = (aqi - a0) / (a1 - a0)
            return {
                "top": _mix(top0, top1, t),
                "horizon": _mix(hor0, hor1, t),
                "ink": ink1 if t > 0.5 else ink0,
                "sun_blur": round(blur0 + (blur1 - blur0) * t),
                "haze": round(min(aqi / 300, 1) * 0.55, 3),
            }
    return {"top": SKY_STOPS[-1][1], "horizon": SKY_STOPS[-1][2],
            "ink": SKY_STOPS[-1][3], "sun_blur": SKY_STOPS[-1][4], "haze": 0.55}
