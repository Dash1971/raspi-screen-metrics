import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dashboard


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.config = {"width": 320, "height": 480, "hosts": []}
        self.fx = {"value": 153.42}
        self.weather = {"temp": 23, "code": 61, "rain": 80}

    def test_render_dimensions(self):
        image = dashboard.render(self.config, self.fx, self.weather, [], True)
        self.assertEqual(image.size, (320, 480))

    def test_rgb565_byte_count(self):
        image = Image.new("RGB", (320, 480), "black")
        self.assertEqual(len(dashboard.rgb565_bytes(image)), 320 * 480 * 2)

    def test_rgb565_asymmetric_pixel_order(self):
        image = Image.new("RGB", (2, 2))
        image.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)])
        self.assertEqual(dashboard.rgb565_bytes(image), bytes.fromhex("00f8e0071f00ffff"))

    def test_weather_precedence(self):
        self.assertEqual(dashboard.weather_kind(self.weather), ("rain", "RAIN LIKELY"))
        self.assertEqual(dashboard.weather_kind({"temp": 32, "code": 0, "rain": 0})[0], "hot")
        self.assertEqual(dashboard.weather_kind({"temp": 10, "code": 0, "rain": 0})[0], "cold")


if __name__ == "__main__":
    unittest.main()
