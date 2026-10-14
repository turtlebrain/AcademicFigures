"""Build and export a journal-standard figure from user selections.

This module is UI-agnostic: it takes plain data plus a preset and returns a
matplotlib Figure that the UI can both preview and export.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless-safe; the Tk canvas re-uses the same Figure
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator, MaxNLocator

from . import csv_loader
from .presets import FigureStyle


class FigureError(Exception):
    """Raised when a figure cannot be built from the given selections."""


@dataclass
class LineSpec:
    """One line on the chart, as chosen in the UI.

    ``style_index`` selects an entry from the preset's ``line_styles`` palette
    (0-based). ``None`` means "auto": each auto line gets the next unused style
    in order. Two (or more) lines may share the same index so discontinuous
    segments of one conceptual series look identical; the legend then shows
    only one entry for that style.
    """

    x_header: str
    y_header: str
    legend: str
    style_index: Optional[int] = None


@dataclass
class HistogramSpec:
    """One histogram series, drawn behind any lines so both are visible.

    Two input modes are supported:

    * **Raw mode** - ``values_header`` names a column of raw observations that
      are binned into ``bins`` bars, optionally normalised to a probability
      density (``density=True``) so a model PDF line can be overlaid.
    * **Pre-binned mode** - ``bin_centers_header`` and ``heights_header`` name
      columns giving already-computed bar centres and heights. This is what
      lets an existing figure be reproduced when the underlying raw data has
      been lost (heights read straight off the original bars).

    Pre-binned mode takes precedence if its columns are provided.
    """

    legend: str = ""
    # Raw mode
    values_header: Optional[str] = None
    bins: int = 30
    density: bool = True
    # Pre-binned mode
    bin_centers_header: Optional[str] = None
    heights_header: Optional[str] = None

    @property
    def is_prebinned(self) -> bool:
        return bool(self.bin_centers_header and self.heights_header)


@dataclass
class FigureSpec:
    """Everything needed to render a figure.

    The axis-limit fields are optional. A value of ``None`` for any bound
    leaves that side on matplotlib's data-driven autoscale, so the user can
    constrain just one edge (e.g. force the y-axis to start at 0) without
    pinning the rest.

    ``histograms`` and ``lines`` are independent: a figure may contain either,
    or both superimposed (histograms are drawn first, lines on top).
    """

    title: str
    x_axis_title: str
    y_axis_title: str
    lines: list[LineSpec]
    histograms: list[HistogramSpec] = field(default_factory=list)
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


def _plot_histograms(
    ax,
    data: csv_loader.CsvData,
    spec: FigureSpec,
    style: FigureStyle,
    warnings: list[str],
    legend_entries: list,
) -> int:
    """Draw every histogram series behind the lines. Returns the count drawn.

    Any drawn series appends its ``(handle, label)`` to ``legend_entries`` so the
    caller can build a legend whose order matches the source figures (bars
    first, then lines).
    """
    bar_kwargs = dict(
        facecolor=style.hist_facecolor,
        edgecolor=style.hist_edgecolor,
        linewidth=style.hist_edge_width,
        alpha=style.hist_alpha,
        zorder=1,  # keep bars beneath data lines (which default higher)
    )

    plotted = 0
    for idx, hist in enumerate(spec.histograms):
        if hist.is_prebinned:
            if hist.bin_centers_header not in data.headers:
                warnings.append(f"Histogram {idx + 1}: bin-centres column not found; skipped.")
                continue
            if hist.heights_header not in data.headers:
                warnings.append(f"Histogram {idx + 1}: heights column not found; skipped.")
                continue
            series = csv_loader.clean_xy(data, hist.bin_centers_header, hist.heights_header)
            label = hist.legend.strip() or hist.heights_header
            if not series.x:
                warnings.append(
                    f"Histogram {idx + 1} ('{label}'): no numeric bar data; skipped."
                )
                continue
            centers = series.x
            heights = series.y
            ordered = sorted(x for x in centers)
            diffs = [b - a for a, b in zip(ordered, ordered[1:]) if b > a]
            if diffs:
                # Unit bin width on a regular lattice = smallest adjacent gap.
                # Inset slightly so neighbouring edge strokes do not stack into
                # a double-thick line that looks like overlapping bars.
                width = min(diffs) * 0.98
            else:
                width = 1.0
            container = ax.bar(centers, heights, width=width, align="center",
                               label=label, **bar_kwargs)
            legend_entries.append((container, label))
            plotted += 1
        else:
            if not hist.values_header:
                warnings.append(f"Histogram {idx + 1}: no data column selected; skipped.")
                continue
            if hist.values_header not in data.headers:
                warnings.append(f"Histogram {idx + 1}: data column not found; skipped.")
                continue
            cleaned = csv_loader.clean_values(data, hist.values_header)
            label = hist.legend.strip() or hist.values_header
            if not cleaned.values:
                warnings.append(
                    f"Histogram {idx + 1} ('{label}'): no numeric data after cleaning; skipped."
                )
                continue
            if cleaned.skipped:
                warnings.append(
                    f"Histogram {idx + 1} ('{label}'): skipped {cleaned.skipped} "
                    "missing/non-numeric value(s)."
                )
            nbins = hist.bins if hist.bins and hist.bins > 0 else style.default_bins
            _, _, patches = ax.hist(cleaned.values, bins=nbins, density=hist.density,
                                    label=label, **bar_kwargs)
            if len(patches):
                legend_entries.append((patches[0], label))
            plotted += 1

    return plotted


def _resolve_line_styles(lines: list[LineSpec], n_styles: int) -> list[int]:
    """Map each line to a palette index, honouring shared and auto styles.

    Explicit ``style_index`` values are kept (modulo the palette size). Lines
    with ``style_index is None`` receive successive auto indices so they stay
    visually distinct from each other by default.
    """
    if n_styles <= 0:
        return [0] * len(lines)
    resolved: list[Optional[int]] = [None] * len(lines)
    for idx, line in enumerate(lines):
        if line.style_index is not None:
            resolved[idx] = int(line.style_index) % n_styles
    next_auto = 0
    for idx, line in enumerate(lines):
        if resolved[idx] is None:
            resolved[idx] = next_auto % n_styles
            next_auto += 1
    return [int(s) for s in resolved]


def build(data: csv_loader.CsvData, spec: FigureSpec, style: FigureStyle) -> BuildResult:
    """Render a Figure for the given data, spec and preset style.

    Raises:
        FigureError: if there is nothing to plot, or nothing yields plottable
            points.
    """
    if not spec.lines and not spec.histograms:
        raise FigureError("Add at least one line or histogram to plot.")

    warnings: list[str] = []

    with matplotlib.rc_context(rc=style.rc_params()):
        fig = Figure()
        ax = fig.add_subplot(111)

        legend_entries: list = []
        plotted = _plot_histograms(ax, data, spec, style, warnings, legend_entries)

        n_styles = len(style.line_styles)
        # Resolve style indices up front so auto and shared picks stay consistent
        # even when some lines are later skipped for missing data.
        resolved_styles = _resolve_line_styles(spec.lines, n_styles)
        # First handle + preferred legend text per style (for a single legend entry).
        style_handle: dict[int, object] = {}
        style_label: dict[int, str] = {}
        style_label_sources: dict[int, set[str]] = {}

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

            style_idx = resolved_styles[idx]
            ls = style.line_styles[style_idx]
            (handle,) = ax.plot(
                series.x,
                series.y,
                color="black",
                linestyle=ls.linestyle,
                marker=ls.marker,
                fillstyle=ls.fillstyle,
                markevery=_marker_every(len(series.x)),
                label="_nolegend_",
            )
            if style_idx not in style_handle:
                style_handle[style_idx] = handle
                style_label[style_idx] = label
                style_label_sources[style_idx] = {label}
                legend_entries.append((handle, label))
            else:
                style_label_sources[style_idx].add(label)
                # Prefer a non-empty explicit legend if the first segment had none.
                if not style_label[style_idx].strip() and label.strip():
                    style_label[style_idx] = label
                    # Update the already-queued legend entry's label.
                    for i, (h, _) in enumerate(legend_entries):
                        if h is style_handle[style_idx]:
                            legend_entries[i] = (h, label)
                            break
            plotted += 1

        for style_idx, names in style_label_sources.items():
            if len(names) > 1:
                warnings.append(
                    f"Lines sharing style {style_idx + 1} use different legend "
                    f"names ({', '.join(sorted(names))}); only "
                    f"'{style_label[style_idx]}' is shown in the legend."
                )

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
        steps = list(style.tick_steps) if style.tick_steps else None
        ax.xaxis.set_major_locator(
            MaxNLocator(nbins=style.max_x_ticks, prune=None, steps=steps)
        )
        ax.yaxis.set_major_locator(
            MaxNLocator(nbins=style.max_y_ticks, prune=None, steps=steps)
        )
        if style.minor_ticks:
            ax.xaxis.set_minor_locator(AutoMinorLocator())
            ax.yaxis.set_minor_locator(AutoMinorLocator())
        minor_len = style.tick_length_major * style.tick_length_minor_frac
        ax.tick_params(which="major", top=True, right=True,
                       length=style.tick_length_major, width=style.tick_width)
        ax.tick_params(which="minor", top=True, right=True,
                       length=minor_len, width=style.tick_width)

        has_labels = any(line.legend.strip() for line in spec.lines) or any(
            h.legend.strip() for h in spec.histograms
        )
        if has_labels or plotted > 1:
            handles = [h for h, _ in legend_entries]
            labels = [lb for _, lb in legend_entries]
            if handles:
                legend = ax.legend(
                    handles,
                    labels,
                    loc=style.legend_loc,
                    frameon=style.legend_frame,
                    borderaxespad=0.3,
                    handlelength=1.2,
                    handletextpad=0.35,
                    labelspacing=0.35,
                )
                if legend is not None:
                    legend.set_frame_on(style.legend_frame)
                    if style.legend_frame:
                        frame = legend.get_frame()
                        frame.set_linewidth(style.legend_frame_width)
                        frame.set_edgecolor("black")
                        frame.set_boxstyle("square", pad=0.4)

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
