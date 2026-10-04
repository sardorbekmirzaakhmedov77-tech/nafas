import pytest

from nafas.aqi import category_for, combined_aqi, pm10_aqi, pm25_aqi, sky_for


@pytest.mark.parametrize("conc, expected", [
    (0, 0), (9.0, 50), (9.1, 51), (35.4, 100), (35.5, 101),
    (55.4, 150), (125.4, 200), (225.4, 300), (400, 500),
])
def test_pm25_breakpoints(conc, expected):
    assert pm25_aqi(conc) == expected


def test_pm25_truncates_before_lookup():
    # 9.05 truncates to 9.0, which is still "good"
    assert pm25_aqi(9.05) == 50


@pytest.mark.parametrize("conc, expected", [(0, 0), (54, 50), (55, 51), (154, 100), (604, 500)])
def test_pm10_breakpoints(conc, expected):
    assert pm10_aqi(conc) == expected


def test_combined_takes_worst_pollutant():
    assert combined_aqi(pm25=5, pm10=200) == pm10_aqi(200)
    assert combined_aqi(pm25=60, pm10=10) == pm25_aqi(60)
    assert combined_aqi() is None


@pytest.mark.parametrize("aqi, key", [
    (0, "good"), (50, "good"), (51, "moderate"), (101, "sensitive"),
    (151, "unhealthy"), (201, "very-unhealthy"), (301, "hazardous"), (999, "hazardous"),
])
def test_categories(aqi, key):
    assert category_for(aqi).key == key


def test_sky_gets_hazier_as_air_worsens():
    clear, smoggy = sky_for(10), sky_for(250)
    assert clear["sun_blur"] < smoggy["sun_blur"]
    assert clear["haze"] < smoggy["haze"]
    assert clear["top"] != smoggy["top"]
