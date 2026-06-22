"""Build and export a journal-standard figure from user selections.

This module is UI-agnostic: it takes plain data plus a preset and returns a
matplotlib Figure that the UI can both preview and export.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless-safe; the Tk canvas re-uses the same Figure
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from . import csv_loader
from .presets import FigureStyle


class FigureError(Exception):
    """Raised when a figure cannot be built from the given selections."""


@dataclass
class LineSpec:
    """One line on the chart, as chosen in the UI."""

    x_header: str
    y_header: str
    legend: str


@dataclass
class FigureSpec:
    """Everything needed to render a figure.

    The axis-limit fields are optional. A value of ``None`` for any bound
    leaves that side on matplotlib's data-driven autoscale, so the user can
    constrain just one edge (e.g. force the y-axis to start at 0) without
    pinning the rest.
    """

    title: str
    x_axis_title: str
    y_axis_title: str
    lines: list[LineSpec]
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    y_min: Optional[float] = None
    y_max: Optional[float] = None


@dataclass
class BuildResult:
    """A rendered figure plus any non-fatal warnings to surface to the user."""

    figure: Figure
    warnings: list[str]


def _marker_every(n_points: int) -> int | None:
    """Thin markers so dense series stay readable in print."""
    if n_points <= 25:
        return None
    return max(1, n_points // 20)


def _apply_axis_limits(ax, spec: FigureSpec, warnings: list[str]) -> None:
    """Apply user axis limits, ignoring (with a warning) inverted ranges.

    Only the bounds the user supplied are pinned; the others stay on the
    autoscaled data extent. Limits are set *before* the tick locators run so
    that ``MaxNLocator`` recomputes journal-standard "nice" tick positions and
    labels for the new view interval.
    """
    for axis_name, lo, hi, setter in (
        ("X", spec.x_min, spec.x_max, ax.set_xlim),
        ("Y", spec.y_min, spec.y_max, ax.set_ylim),
    ):
        if lo is not None and hi is not None and lo >= hi:
            warnings.append(
                f"{axis_name}-axis: minimum ({lo:g}) must be less than maximum "
                f"({hi:g}); limit ignored."
            )
            continue
        if lo is not None or hi is not None:
            setter(left=lo, right=hi) if axis_name == "X" else setter(bottom=lo, top=hi)


def build(data: csv_loader.CsvData, spec: FigureSpec, style: FigureStyle) -> BuildResult:
    """Render a Figure for the given data, spec and preset style.

    Raises:
        FigureError: if there are no lines or no line yields plottable points.
    """
    if not spec.lines:
        raise FigureError("Add at least one line to plot.")

    warnings: list[str] = []

    with matplotlib.rc_context(rc=style.rc_params()):
        fig = Figure()
        ax = fig.add_subplot(111)

        plotted = 0
        for idx, line in enumerate(spec.lines):
            if line.x_header not in data.headers:
                warnings.append(f"Line {idx + 1}: X column not found; skipped.")
                continue
            if line.y_header not in data.headers:
                warnings.append(f"Line {idx + 1}: Y column not found; skipped.")
                continue

            series = csv_loader.clean_xy(data, line.x_header, line.y_header)
            label = line.legend.strip() or f"{line.y_header}"

            if not series.x:
                warnings.append(
                    f"Line {idx + 1} ('{label}'): no numeric data after cleaning; skipped."
                )
                continue
            if series.skipped:
                warnings.append(
                    f"Line {idx + 1} ('{label}'): skipped {series.skipped} row(s) "
                    "with missing/non-numeric values."
                )

            ls = style.line_styles[idx % len(style.line_styles)]
            ax.plot(
                series.x,
                series.y,
                color="black",
                linestyle=ls.linestyle,
                marker=ls.marker,
                fillstyle=ls.fillstyle,
                markevery=_marker_every(len(series.x)),
                label=label,
            )
            plotted += 1

        if plotted == 0:
            raise FigureError(
                "Nothing could be plotted. Check that the selected columns "
                "contain numeric data."
            )

        if spec.title.strip():
            ax.set_title(spec.title.strip())
        if spec.x_axis_title.strip():
            ax.set_xlabel(spec.x_axis_title.strip())
        if spec.y_axis_title.strip():
            ax.set_ylabel(spec.y_axis_title.strip())

        _apply_axis_limits(ax, spec, warnings)

        # Recompute ticks *after* limits so labels stay journal-standard for
        # whatever view interval the user pinned.
        ax.xaxis.set_major_locator(MaxNLocator(nbins=style.max_x_ticks, prune=None))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=style.max_y_ticks, prune=None))
        ax.tick_params(which="both", top=True, right=True)

        if any(line.legend.strip() for line in spec.lines) or plotted > 1:
            legend = ax.legend(loc="best")
            if legend is not None and not style.legend_frame:
                legend.set_frame_on(False)

        fig.tight_layout()

    return BuildResult(figure=fig, warnings=warnings)


def export(figure: Figure, path: str, fmt: str, style: FigureStyle) -> None:
    """Save the figure to disk as PNG or JPEG at the preset DPI.

    Raises:
        FigureError: for an unsupported format or a write failure.
    """
    fmt_norm = fmt.strip().lower()
    if fmt_norm in ("jpg", "jpeg"):
        save_format = "jpg"
    elif fmt_norm == "png":
        save_format = "png"
    else:
        raise FigureError(f"Unsupported output format: {fmt!r}")

    save_kwargs: dict = {
        "format": save_format,
        "dpi": style.export_dpi,
        "bbox_inches": "tight",
        "pad_inches": 0.03,
        "facecolor": "white",
    }
    if save_format == "jpg":
        # JPEG has no alpha; matplotlib needs quality via pil_kwargs.
        save_kwargs["pil_kwargs"] = {"quality": 95}

    try:
        figure.savefig(path, **save_kwargs)
    except (OSError, ValueError) as exc:
        raise FigureError(f"Could not save figure: {exc}") from exc
