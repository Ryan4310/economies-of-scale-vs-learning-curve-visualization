"""Compare two learning curves. Run with: python test.py."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons, Slider, TextBox

A_LIMITS = (1.0, 500.0)
LC_LIMITS = (0.01, 1.0)
X_LIMITS = (1.0, 100.0)
DEFAULTS = ((100.0, 0.85), (140.0, 0.85))
INITIAL_X = 25.0
COLORS = ("#168CB3", "#E77C22")


def calculate_y(x, a, lc):
    """Y_n = a * X ** (log(LC) / log(2))."""
    return a * np.power(x, np.log(lc) / np.log(2))


def calculate_a(x, y, lc):
    """Solve for a while holding LC constant."""
    return y / np.power(x, np.log(lc) / np.log(2))


class LearningCurveComparison:
    def __init__(self):
        self.parameters = [list(pair) for pair in DEFAULTS]
        self.selected_x = [INITIAL_X, INITIAL_X]
        self.active_curve = 0
        self.syncing = False
        self.widgets = []  # Keep Matplotlib widgets alive throughout the session.
        self.fields = {}
        self.sliders = {}
        self.x_values = np.linspace(*X_LIMITS, 1000)
        self.fig, self.ax = plt.subplots(figsize=(13, 10))
        self.fig.subplots_adjust(left=0.09, right=0.96, bottom=0.43, top=0.83)
        self.fig.suptitle("Economies of Scale vs Learning Curve Visualization", fontsize=17, fontweight="bold")
        self.fig.text(0.5, 0.925, r"$Y_n = aX^b,\quad b = \log(LC)/\log(2)$", ha="center", fontsize=14)
        self.fig.text(0.5, 0.89, "Y_n: average unit cost for a batch of n products (e.g., n spacecraft in a satellite constellation)", ha="center", fontsize=10)
        self.fig.text(0.5, 0.866, "a: first-unit cost   |   X: cumulative units produced   |   b: learning index   |   LC: learning curve (%)", ha="center", fontsize=10)
        self.ax.set(xlabel="Cumulative Production Quantity (X)",
                    ylabel="Average Unit Cost (Y_n)", xlim=X_LIMITS)
        self.ax.grid(alpha=0.18)
        self.ax.spines[["top", "right"]].set_visible(False)
        self.curves, self.points = [], []
        for i, color in enumerate(COLORS):
            line, = self.ax.plot([], [], color=color, lw=2.8, label=f"Curve {i + 1}")
            point, = self.ax.plot([], [], "o", color=color, ms=8)
            self.curves.append(line)
            self.points.append(point)
        self.guides = [self.ax.axvline(INITIAL_X, ls=":", color=color, alpha=0.6)
                       for color in COLORS]
        self.ax.legend(frameon=False)
        self.ax.set_ylim(0, max(a for a, _ in DEFAULTS) * 1.15)

        for i, left in enumerate((0.10, 0.57)):
            self.fig.text(left, 0.365, f"Curve {i + 1}", color=COLORS[i], weight="bold", fontsize=12)
            for key, row, limits, initial in (
                ("a", 0.315, A_LIMITS, DEFAULTS[i][0]),
                ("LC", 0.265, (LC_LIMITS[0] * 100, LC_LIMITS[1] * 100), DEFAULTS[i][1] * 100),
                ("X", 0.215, X_LIMITS, INITIAL_X),
            ):
                slider = Slider(self.fig.add_axes([left, row, 0.22, 0.025]), "LC (%)" if key == "LC" else key,
                                *limits, valinit=initial, valfmt="%.3f", color=COLORS[i])
                slider.valtext.set_visible(False)
                self.sliders[i, key] = slider
                self.widgets.append(slider)
                slider.on_changed(lambda value, i=i, key=key: self.edit(i, key, value))
                self.add_field(i, key, [left + 0.255, row - 0.005, 0.105, 0.035], initial)
            self.add_field(i, "Y_n", [left + 0.255, 0.155, 0.105, 0.035], 0)
            self.fig.text(left, 0.166, "Edit Y_n to solve for a", fontsize=9, color="#555555")

        self.comparison = self.fig.text(0.10, 0.10, "", fontsize=11)
        self.status = self.fig.text(0.10, 0.071, "", fontsize=9, color="#555555")
        self.fig.text(0.10, 0.035, "Left-click: fit active curve. Right-click: select active X.", fontsize=9)
        self.radio = RadioButtons(self.fig.add_axes([0.53, 0.012, 0.16, 0.062]), ("Curve 1", "Curve 2"))
        self.radio.on_clicked(self.choose_curve)
        self.widgets.append(self.radio)
        for label, bounds, callback in (
            ("Reset", [0.73, 0.024, 0.09, 0.04], self.reset),
            ("Fit view", [0.84, 0.024, 0.09, 0.04], self.fit_view),
        ):
            widget = Button(self.fig.add_axes(bounds), label)
            widget.on_clicked(callback)
            self.widgets.append(widget)
        self.fig.canvas.mpl_connect("button_press_event", self.on_click)
        self.refresh()

    def add_field(self, index, key, bounds, initial):
        label = "" if key == "LC" else key
        field = TextBox(self.fig.add_axes(bounds), label + " ", initial=str(initial))
        field.on_submit(lambda value: self.edit(index, key, value))
        self.fields[index, key] = field
        self.widgets.append(field)

    def choose_curve(self, label):
        self.active_curve = int(label[-1]) - 1

    def edit(self, index, key, raw_value):
        if self.syncing:
            return
        try:
            value = float(raw_value)
            if not np.isfinite(value):
                raise ValueError("Enter a finite number.")
            if key == "LC":
                value /= 100.0
            if key == "Y_n":
                if value <= 0:
                    raise ValueError("Y_n must be positive.")
                value = float(calculate_a(self.selected_x[index], value, self.parameters[index][1]))
                key = "a"
            limits = {"a": A_LIMITS, "LC": LC_LIMITS, "X": X_LIMITS}[key]
            if not limits[0] <= value <= limits[1]:
                if key == "LC":
                    raise ValueError("LC must be between 1% and 100% (enter 85 for 85%).")
                raise ValueError(f"Required {key}={value:.6g}; allowed range is {limits[0]:g} to {limits[1]:g}.")
            if key == "X":
                self.selected_x[index] = value
            else:
                self.parameters[index][0 if key == "a" else 1] = value
            message = "Updated. Editing Y_n fits a with LC held constant."
        except (ValueError, OverflowError) as error:
            message = str(error)
        self.refresh(message)

    def refresh(self, message="Enter a value and press Enter, or move a slider."):
        self.syncing = True
        try:
            ys = []
            for i, (a, lc) in enumerate(self.parameters):
                self.curves[i].set_data(self.x_values, calculate_y(self.x_values, a, lc))
                y = float(calculate_y(self.selected_x[i], a, lc))
                ys.append(y)
                self.points[i].set_data([self.selected_x[i]], [y])
                self.guides[i].set_xdata([self.selected_x[i], self.selected_x[i]])
                for key, value in (("a", a), ("LC", lc * 100), ("X", self.selected_x[i]), ("Y_n", y)):
                    # Preserve enough precision when an unedited value is submitted again.
                    self.fields[i, key].set_val(f"{value:.12g}")
                    if key != "Y_n":
                        self.sliders[i, key].set_val(value)
            top = max(a for a, _ in self.parameters)
            if top > self.ax.get_ylim()[1]:
                self.ax.set_ylim(0, top * 1.15)
            delta = ys[1] - ys[0]
            percent = 100 * delta / ys[0]
            self.comparison.set_text(
                f"X1 = {self.selected_x[0]:.3f}, Y1 = {ys[0]:.3f}    |    X2 = {self.selected_x[1]:.3f}, Y2 = {ys[1]:.3f}\n"
                f"Selected-point difference (2 - 1) = {delta:+.3f} ({percent:+.2f}% of Curve 1)")
            self.status.set_text(message)
        finally:
            self.syncing = False
        self.fig.canvas.draw_idle()

    def on_click(self, event):
        if event.inaxes is not self.ax or event.button not in (1, 3):
            return
        if self.fig.canvas.toolbar and self.fig.canvas.toolbar.mode:
            return
        if event.xdata is None or event.ydata is None:
            return
        if event.button == 1:
            # Commit the selected X only when the requested fit is valid.
            a = float(calculate_a(event.xdata, event.ydata, self.parameters[self.active_curve][1]))
            if not A_LIMITS[0] <= a <= A_LIMITS[1]:
                self.refresh(f"Cannot fit point: required a={a:.3f}; allowed range is 1 to 500.")
                return
            self.parameters[self.active_curve][0] = a
        self.selected_x[self.active_curve] = float(np.clip(event.xdata, *X_LIMITS))
        self.refresh("Curve fitted with LC held constant." if event.button == 1 else "X selected for active curve.")

    def fit_view(self, event=None):
        self.ax.set_xlim(*X_LIMITS)
        self.ax.set_ylim(0, max(a for a, _ in self.parameters) * 1.15)
        self.fig.canvas.draw_idle()

    def reset(self, event=None):
        self.parameters = [list(pair) for pair in DEFAULTS]
        self.selected_x = [INITIAL_X, INITIAL_X]
        self.radio.set_active(0)
        self.fit_view()
        self.refresh("Both curves reset.")


def main():
    app = LearningCurveComparison()
    plt.show()
    return app


if __name__ == "__main__":
    main()
