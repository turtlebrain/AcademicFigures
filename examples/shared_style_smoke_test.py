"""Headless test: two discontinuous segments sharing one line style + legend."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from academicfigures import csv_loader, figure_builder, presets

here = os.path.dirname(os.path.abspath(__file__))

# Two x-ranges for the same conceptual series (gap in the middle), plus a
# second distinct series that keeps its own style.
csv_text = """x,y_seg_a,y_seg_b,y_other
0.0,0.0,,1.0
1.0,1.0,,1.1
2.0,2.0,,1.2
3.0,,,1.3
4.0,,4.0,1.4
5.0,,5.0,1.5
6.0,,6.0,1.6
"""

with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "shared_style.csv")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(csv_text)
    data = csv_loader.load(path)

    style = presets.get_style("LineChart")
    spec = figure_builder.FigureSpec(
        title="Shared style segments",
        x_axis_title="x",
        y_axis_title="y",
        lines=[
            # Both segments share style 0 (solid) and the same legend name.
            figure_builder.LineSpec("x", "y_seg_a", "Series A", style_index=0),
            figure_builder.LineSpec("x", "y_seg_b", "Series A", style_index=0),
            figure_builder.LineSpec("x", "y_other", "Series B", style_index=1),
        ],
    )
    result = figure_builder.build(data, spec, style)
    assert not any("different legend" in w for w in result.warnings)

    ax = result.figure.axes[0]
    legend = ax.get_legend()
    assert legend is not None, "legend missing"
    labels = [t.get_text() for t in legend.get_texts()]
    assert labels == ["Series A", "Series B"], f"unexpected legend: {labels}"

    # Three plotted Line2D artists, but only two legend entries.
    assert len(ax.lines) == 3, f"expected 3 line artists, got {len(ax.lines)}"

    out = os.path.join(here, "_shared_style_smoke.png")
    figure_builder.export(result.figure, out, "png", style)
    assert os.path.getsize(out) > 0
    print("Legend labels:", labels)
    print("Exported:", out)
    print("SHARED-STYLE SMOKE TEST PASSED")
