from __future__ import annotations

import math
import unittest
from types import SimpleNamespace

from poker_engine import calculate_equity
from theme_helpers import plotly_palette, resolve_theme_type


def _luminance(hex_color):
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground, background):
    first, second = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


class _FakeStreamlit:
    def __init__(self, theme_type=None, config_base=None):
        if theme_type is not None:
            self.context = SimpleNamespace(theme=SimpleNamespace(type=theme_type))
        if config_base is not None:
            self._config_base = config_base

    def get_option(self, name):
        if name == "theme.base":
            return getattr(self, "_config_base", None)
        return None


class TestThemeResolution(unittest.TestCase):
    def test_reads_active_dark_theme_from_context(self):
        self.assertEqual(resolve_theme_type(_FakeStreamlit("dark")), "dark")

    def test_reads_active_light_theme_from_context(self):
        self.assertEqual(resolve_theme_type(_FakeStreamlit("light")), "light")

    def test_falls_back_to_configured_theme(self):
        self.assertEqual(resolve_theme_type(_FakeStreamlit(config_base="dark")), "dark")

    def test_unknown_theme_safely_falls_back_to_light(self):
        self.assertEqual(resolve_theme_type(_FakeStreamlit("custom")), "light")

    def test_plotly_palettes_have_contrast_and_distinct_templates(self):
        light = plotly_palette("light")
        dark = plotly_palette("dark")
        self.assertEqual(light["template"], "plotly_white")
        self.assertEqual(dark["template"], "plotly_dark")
        self.assertNotEqual(light["text"], light["surface"])
        self.assertNotEqual(dark["text"], dark["surface"])
        self.assertNotEqual(light["grid"], dark["grid"])


class TestTwentyFiveThousandSampleError(unittest.TestCase):
    def test_25000_uses_conservative_95_percent_hoeffding_half_width(self):
        result = calculate_equity(
            [("A", "♠"), ("K", "♠")],
            [("Q", "♠"), ("J", "♠"), ("3", "♦")],
            1,
            method="monte_carlo",
            samples=25_000,
            seed=2026,
            opponent_range="typical",
        )
        expected = math.sqrt(math.log(2 / 0.05) / (2 * 25_000))
        ci = result["confidence_interval"]
        self.assertAlmostEqual(ci["half_width"], expected, places=7)
        self.assertAlmostEqual(ci["half_width"] * 100, 0.85894, places=4)
        self.assertEqual(result["samples"], 25_000)
        self.assertGreaterEqual(ci["equity_low"], 0.0)
        self.assertLessEqual(ci["equity_high"], 1.0)

    def test_clipping_at_probability_boundaries_does_not_shrink_reported_margin(self):
        from poker_engine import _stats_result
        result = _stats_result(25_000, 0, 0, 25_000.0, 25_000.0, 25_000, "monte_carlo", "typical")
        expected = math.sqrt(math.log(2 / 0.05) / (2 * 25_000))
        self.assertAlmostEqual(result["confidence_interval"]["half_width"], expected, places=7)
        self.assertEqual(result["confidence_interval"]["equity_high"], 1.0)


if __name__ == "__main__":
    unittest.main()
