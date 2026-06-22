"""Figure-style presets.

Each figure style locks in the typographic and line-art parameters so the user
never has to think about font, size, tick style, border weight, etc. The values
below follow conventions shared by high-impact journals' black-and-white line
art (e.g. Nature journals, Elsevier's *Computers and Geotechnics*,
*Computers, Materials & Continua*):

- Single-column figure ~3.5 in wide at 600 dpi (crisp raster line art).
- Sans-serif body text, small point sizes (8-10 pt).
- A full axes box with inward ticks on all four sides.
- Thin spines, modest data-line weight, restrained tick counts.
- Pure black ink on white; lines distinguished only by linestyle + marker.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class LineStyle:
    """A single black-and-white line appearance."""

    linestyle: str
    marker: Optional[str] = None
    fillstyle: str = "none"  # open markers read better in print


# Eight visually distinct black-and-white line styles, used in order.
# Differentiation relies on dash pattern first, then open markers.
BW_LINE_STYLES: tuple[LineStyle, ...] = (
    LineStyle("-"),               # 1: solid
    LineStyle("--"),              # 2: dashed
    LineStyle(":"),               # 3: dotted
    LineStyle("-."),              # 4: dash-dot
    LineStyle("-", marker="o"),   # 5: solid + open circle
    LineStyle("--", marker="s"),  # 6: dashed + open square
    LineStyle(":", marker="^"),   # 7: dotted + open triangle
    LineStyle("-.", marker="D"),  # 8: dash-dot + open diamond
)

MAX_LINES: int = len(BW_LINE_STYLES)


@dataclass(frozen=True)
class FigureStyle:
    """A complete, self-contained figure preset."""

    name: str
    # Canvas
    fig_width_in: float
    fig_height_in: float
    export_dpi: int
    # Lines / markers
    line_width: float
    marker_size: float
    marker_edge_width: float
    marker_every: Optional[int]
    line_styles: tuple[LineStyle, ...]
    # Typography (points)
    font_family: str
    title_size: float
    axis_label_size: float
    tick_label_size: float
    legend_size: float
    # Axes / ticks / border
    axes_line_width: float
    tick_direction: str
    tick_length_major: float
    tick_length_minor: float
    tick_width: float
    max_x_ticks: int
    max_y_ticks: int
    legend_frame: bool
    legend_frame_width: float

    def rc_params(self) -> dict:
        """matplotlib rcParams that encode this preset."""
        return {
            "figure.figsize": (self.fig_width_in, self.fig_height_in),
            "savefig.dpi": self.export_dpi,
            "figure.dpi": 110,  # on-screen preview resolution

            "font.family": "sans-serif",
            "font.sans-serif": [self.font_family, "Arial", "Helvetica", "DejaVu Sans"],
            "axes.titlesize": self.title_size,
            "axes.labelsize": self.axis_label_size,
            "xtick.labelsize": self.tick_label_size,
            "ytick.labelsize": self.tick_label_size,
            "legend.fontsize": self.legend_size,

            "lines.linewidth": self.line_width,
            "lines.markersize": self.marker_size,
            "lines.markeredgewidth": self.marker_edge_width,

            "axes.linewidth": self.axes_line_width,
            "axes.edgecolor": "black",
            "axes.labelcolor": "black",
            "axes.titlecolor": "black",
            "text.color": "black",
            "axes.grid": False,

            "xtick.direction": self.tick_direction,
            "ytick.direction": self.tick_direction,
            "xtick.major.size": self.tick_length_major,
            "ytick.major.size": self.tick_length_major,
            "xtick.minor.size": self.tick_length_minor,
            "ytick.minor.size": self.tick_length_minor,
            "xtick.major.width": self.tick_width,
            "ytick.major.width": self.tick_width,
            "xtick.color": "black",
            "ytick.color": "black",
            "xtick.top": True,
            "ytick.right": True,

            "legend.frameon": self.legend_frame,
            "legend.framealpha": 1.0,
            "legend.edgecolor": "black",
            "legend.fancybox": False,

            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.03,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }


LINE_CHART = FigureStyle(
    name="LineChart",
    fig_width_in=3.5,
    fig_height_in=2.625,  # 4:3 single column
    export_dpi=600,
    line_width=1.2,
    marker_size=4.0,
    marker_edge_width=1.0,
    marker_every=None,  # set dynamically based on point count
    line_styles=BW_LINE_STYLES,
    font_family="Arial",
    title_size=10.0,
    axis_label_size=9.0,
    tick_label_size=8.0,
    legend_size=8.0,
    axes_line_width=0.8,
    tick_direction="in",
    tick_length_major=3.5,
    tick_length_minor=2.0,
    tick_width=0.8,
    max_x_ticks=6,
    max_y_ticks=6,
    legend_frame=False,
    legend_frame_width=0.5,
)


# Registry so the UI can list available styles and grow later.
FIGURE_STYLES: dict[str, FigureStyle] = {
    LINE_CHART.name: LINE_CHART,
}


def get_style(name: str) -> FigureStyle:
    """Return a registered figure style by name."""
    try:
        return FIGURE_STYLES[name]
    except KeyError as exc:  # pragma: no cover - guarded by UI dropdown
        raise ValueError(f"Unknown figure style: {name!r}") from exc


def style_names() -> list[str]:
    """Names of all registered figure styles."""
    return list(FIGURE_STYLES.keys())
