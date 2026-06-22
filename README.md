# AcademicFigures

A lite, fast-launching desktop app that turns a CSV into a publication-quality
**black-and-white LineChart** figure meeting high-impact journal standards
(e.g. Nature journals, Elsevier's *Computers and Geotechnics*).

The app is intentionally minimalist: font, font size, line widths, tick style,
border size and so on are **not** exposed. They are locked into a per-figure-style
preset derived from common journal line-art guidelines, so every export looks
consistent and submission-ready.

## Features

- Pick any `.csv` file from disk via a native file dialog.
- Choose a figure style (currently `LineChart`, designed to grow).
- Auto-detects the CSV columns and lets you plot **up to 8 data trends (lines)**.
- Assign any column to the X and Y axis of each line, and name each legend entry.
- Set the figure title and both axis titles.
- Export as **PNG** or **JPEG** at journal-grade resolution.
- Pure black-and-white output: lines are distinguished by 8 distinct
  linestyle + marker combinations (no colour needed).
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
2. Keep **Figure style** on `LineChart`.
3. Set **Number of lines** (1-8). A row appears per line.
4. For each line pick an **X column**, a **Y column**, and type a **Legend** name.
5. Fill in the **Figure title**, **X-axis title**, and **Y-axis title**.
6. Choose the output format (**PNG** or **JPEG**).
7. Click **Preview** to render, then **Export...** to save.

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
    presets.py                 # journal-standard LineChart preset + 8 B/W styles
    figure_builder.py          # build + export the matplotlib figure
```
