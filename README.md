# AcademicFigures

A lite, fast-launching desktop app that turns a CSV into a publication-quality
**black-and-white** figure meeting high-impact journal standards
(e.g. Nature journals, Elsevier's *Computers and Geotechnics*). It supports
**line charts** and **histograms**, including a histogram and a line
**superimposed** in one figure (e.g. a Monte-Carlo distribution with an
overlaid model PDF).

The app is intentionally minimalist: font, font size, line widths, tick style,
border size and so on are **not** exposed. They are locked into a per-figure-style
preset derived from common journal line-art guidelines, so every export looks
consistent and submission-ready.

## Features

- Pick any `.csv` file from disk via a native file dialog.
- Choose a figure style (`LineChart` or `Histogram`).
- Auto-detects the CSV columns and lets you plot **up to 16 data trends (lines)**.
- Add **up to 4 histograms**, superimposed behind the lines so a distribution
  and a model curve can share one figure.
  - **Raw mode:** bin one column of raw observations (choose bin count and
    whether to normalise to a probability density).
  - **Binned mode:** draw already-computed bars from a *bin centre* column and a
    *bar height* column (handy when the raw data is unavailable).
- Assign any column to the X and Y axis of each line, name each legend entry, and
  optionally pick a **line style**. Two lines may share the same style (e.g.
  discontinuous segments of one series); the legend then shows **one entry per
  style**.
- Set the figure title and both axis titles.
- Export as **PNG** or **JPEG** at journal-grade resolution.
- Print-safe output: lines are pure black, distinguished by 8 distinct
  linestyle + marker combinations (shareable across lines); histogram bars use
  a neutral grey fill.
- Inline preview plus clear errors and warnings (bad file, non-numeric data,
  missing values, mismatched lengths, etc.).

## Requirements

- Python 3.9+ (tested on 3.13)
- [`matplotlib`](https://matplotlib.org/) (only third-party dependency)

Tkinter ships with the standard CPython installer on Windows and macOS. On some
Linux distros install it via your package manager (e.g. `sudo apt install python3-tk`).

## Install

```bash
cd AcademicFigures
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python run.py
```

## Usage

1. Click **Browse...** and select a CSV file (first row is treated as headers).
2. Choose a **Figure style** (`LineChart` or `Histogram`).
3. Set **Number of lines** (0-16). A row appears per line; pick an **X column**, a
   **Y column**, a **Legend** name, and a **Style** (`Auto` or one of the 8
   palette styles). Use the same Style on multiple lines when the data is
   discontinuous but should read as one series — only one legend entry is shown
   for that style.
4. Set **Number of histograms** (0-4). For each histogram choose:
   - **Raw values** - a data column, a bin count, and whether to normalise to a
     density (PDF); or
   - **Binned (centre+height)** - a bin-centre column and a bar-height column.
5. Fill in the **Figure title**, **X-axis title**, and **Y-axis title**.
6. Choose the output format (**PNG** or **JPEG**).
7. Click **Preview** to render, then **Export...** to save.

> Tip: to overlay a distribution with a model curve, add one histogram and one
> line. Bars are always drawn behind the lines.

## CSV format

- The first row must be column headers.
- Plotted columns must be numeric. Non-numeric or empty cells in a plotted
  column are skipped for that line (you'll get a warning telling you how many).

## Project layout

```
AcademicFigures/
  run.py                       # entry point
  requirements.txt
  README.md
  academicfigures/
    __init__.py
    app.py                     # Tkinter UI + workflow
    csv_loader.py              # CSV read / validation
    presets.py                 # LineChart + Histogram presets, 8 B/W line styles
    figure_builder.py          # build + export the matplotlib figure (lines + histograms)
    mathtext.py                # symbol palette + toolbar for math in text entries
  examples/
    sample.csv                 # tiny dataset used by the smoke tests
    smoke_test.py              # headless line-chart pipeline test
    histogram_smoke_test.py    # headless histogram (raw + binned) pipeline test
    shared_style_smoke_test.py # two segments sharing one style -> one legend entry
```
