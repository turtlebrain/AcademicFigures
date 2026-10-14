"""Headless smoke test for the histogram feature (raw + pre-binned, with line).

Builds an in-memory CSV rather than touching disk, so it runs anywhere.
"""
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from academicfigures import csv_loader, figure_builder, presets


def _write_temp_csv(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="") as fh:
        fh.write(text)
    return path


# One column of raw samples, plus a pre-binned (centre, height) pair and a line.
raw = io.StringIO()
raw.write("samples,bin_center,bar_height,line_x,line_y\n")
data_rows = [
    "1.2,0.5,0.10,0.0,0.02", "2.3,1.5,0.25,1.0,0.20",
    "2.9,2.5,0.40,2.0,0.38", "3.1,3.5,0.20,3.0,0.30",
    "3.8,4.5,0.05,4.0,0.10", "4.2,,,5.0,0.02",
    "2.7,,,,", "3.3,,,,", "2.1,,,,", "3.6,,,,",
]
for r in data_rows:
    raw.write(r + "\n")

csv_path = _write_temp_csv(raw.getvalue())
try:
    data = csv_loader.load(csv_path)
    print("Headers:", data.headers)

    style = presets.get_style("Histogram")

    # 1) raw-values histogram + overlaid line
    spec_raw = figure_builder.FigureSpec(
        title="Raw histogram + line",
        x_axis_title=r"$u_{max}$ [m]",
        y_axis_title="",
        lines=[figure_builder.LineSpec("line_x", "line_y", "Model")],
        histograms=[figure_builder.HistogramSpec(
            legend="Samples", values_header="samples", bins=6, density=True)],
    )
    res_raw = figure_builder.build(data, spec_raw, style)
    print("raw warnings:", res_raw.warnings)

    # 2) pre-binned histogram + line (the reproduction path)
    spec_bin = figure_builder.FigureSpec(
        title="Pre-binned histogram + line",
        x_axis_title=r"$u_{max}$ [m]",
        y_axis_title="",
        lines=[figure_builder.LineSpec("line_x", "line_y", "Model")],
        histograms=[figure_builder.HistogramSpec(
            legend="Samples",
            bin_centers_header="bin_center", heights_header="bar_height")],
    )
    res_bin = figure_builder.build(data, spec_bin, style)
    print("prebinned warnings:", res_bin.warnings)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "_hist_smoke_output.png")
    figure_builder.export(res_bin.figure, out, "png", style)
    assert os.path.getsize(out) > 0
    print(f"Exported: {out} ({os.path.getsize(out)} bytes)")
    print("HISTOGRAM SMOKE TEST PASSED")
finally:
    os.remove(csv_path)
