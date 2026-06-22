"""Headless smoke test of the load -> build -> export pipeline (no GUI)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from academicfigures import csv_loader, figure_builder, presets

here = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(here, "sample.csv")

data = csv_loader.load(csv_path)
print("Headers:", data.headers)
print("Numeric:", data.numeric_headers())
print("Rows:", data.n_rows)

style = presets.get_style("LineChart")
spec = figure_builder.FigureSpec(
    title="Stress-strain response",
    x_axis_title="Strain (%)",
    y_axis_title="Stress (MPa)",
    lines=[
        figure_builder.LineSpec("Strain", "Stress_A", "Specimen A"),
        figure_builder.LineSpec("Strain", "Stress_B", "Specimen B"),
        figure_builder.LineSpec("Strain", "Stress_C", "Specimen C"),
    ],
)

result = figure_builder.build(data, spec, style)
print("Build warnings:", result.warnings)

for fmt, ext in (("png", "png"), ("jpeg", "jpg")):
    out = os.path.join(here, f"_smoke_output.{ext}")
    figure_builder.export(result.figure, out, fmt, style)
    size = os.path.getsize(out)
    print(f"Exported {fmt}: {out} ({size} bytes)")
    assert size > 0

print("SMOKE TEST PASSED")
