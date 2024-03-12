import numpy as np
from hyp3_sdk.stac import load


def test_incidence_angle2slant_range_distance():
    incidence_angles = np.array([1, 10, 30, 45])
    earth_radius = 10_000
    orbit_altitude = 500
    slant_range_distances = load.incidence_angle2slant_range_distance(orbit_altitude, earth_radius, incidence_angles)
    assert np.allclose(slant_range_distances, np.array([500.07253639, 507.33801148, 572.83861847, 691.01953626]))


def test_utm2latlon():
    # Coordinates near Ridgecrest, CA
    utm_x = 677962
    utm_y = 4096742
    epsg = 32610
    lat, lon = load.utm2latlon(epsg, utm_x, utm_y)
    assert np.allclose([lat, lon], [37, -121])


def test_wrap():
    unwrapped = np.array([0, np.pi * 0.5, np.pi, np.pi * 1.5, np.pi * 2])
    wrapped = load.wrap(unwrapped)
    assert np.allclose(wrapped, [0, np.pi * 0.5, -np.pi, -np.pi * 0.5, 0])
