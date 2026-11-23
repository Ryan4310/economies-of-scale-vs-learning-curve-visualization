import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

spec = importlib.util.spec_from_file_location('comparison', Path(__file__).resolve().parents[1] / 'test.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.app = module.LearningCurveComparison()

    def tearDown(self):
        plt.close(self.app.fig)

    def test_independent_parameters_and_quantities(self):
        app = self.app
        second = app.curves[1].get_ydata().copy()
        app.sliders[0, 'a'].set_val(160)
        app.fields[0, 'LC'].set_val('75')
        np.testing.assert_allclose(app.curves[0].get_ydata(), module.calculate_y(app.x_values, 160, .75))
        np.testing.assert_array_equal(app.curves[1].get_ydata(), second)
        app.fields[0, 'X'].set_val('40')
        app.sliders[1, 'X'].set_val(60)
        self.assertEqual(app.selected_x, [40, 60])
        for i, (a, lc) in enumerate(app.parameters):
            np.testing.assert_allclose(app.points[i].get_data(), ([app.selected_x[i]], [module.calculate_y(app.selected_x[i], a, lc)]))
        self.assertEqual(sum(len(line.get_xdata()) == 1000 for line in app.ax.lines), 2)

    def test_edit_cost_and_invalid_inputs(self):
        app = self.app
        app.fields[1, 'X'].set_val('60')
        app.fields[1, 'Y_n'].set_val('30')
        self.assertAlmostEqual(module.calculate_y(app.selected_x[1], app.parameters[1][0], .85), 30)
        before = [pair[:] for pair in app.parameters]
        for key, value in [('a', 'nan'), ('LC', '0'), ('LC', '101'), ('Y_n', '-1'), ('a', 'abc'), ('Y_n', '999999')]:
            app.fields[1, key].set_val(value)
            self.assertEqual(app.parameters, before)
        app.fields[1, 'X'].set_val('0')
        self.assertEqual(app.selected_x, [25, 60])

    def test_click_fit_selection_reset_and_scale(self):
        app = self.app
        app.radio.set_active(1)
        app.on_click(SimpleNamespace(inaxes=app.ax, button=1, xdata=20., ydata=40.))
        self.assertAlmostEqual(module.calculate_y(20, *app.parameters[1]), 40)
        self.assertEqual(app.parameters[0], list(module.DEFAULTS[0]))
        app.on_click(SimpleNamespace(inaxes=app.ax, button=3, xdata=50., ydata=20.))
        self.assertEqual(app.selected_x, [25, 50])
        app.edit(0, 'a', 500)
        top = app.ax.get_ylim()[1]
        app.edit(0, 'a', 50)
        self.assertEqual(app.ax.get_ylim()[1], top)
        app.reset()
        self.assertEqual(app.parameters, [list(pair) for pair in module.DEFAULTS])
        self.assertEqual(app.selected_x, [25, 25])
        self.assertEqual(app.active_curve, 0)
        self.assertAlmostEqual(app.ax.get_ylim()[1], 140 * 1.15)
        self.assertAlmostEqual(module.calculate_y(20, 100, .85) / module.calculate_y(10, 100, .85), .85)


if __name__ == '__main__':
    unittest.main()
