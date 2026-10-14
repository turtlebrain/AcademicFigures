"""CSV reading and validation using only the standard library.

The loader keeps everything as raw strings per column. Numeric coercion happens
later, per selected (X, Y) pair, so a column that is text for one purpose can
still be inspected without forcing the whole table to be numeric.
"""
from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass, field


class CsvError(Exception):
    """Raised when a CSV file cannot be read or is structurally unusable."""


@dataclass
class CsvData:
    """Parsed CSV: headers plus one list of raw string cells per column."""

    headers: list[str]
    columns: list[list[str]]  # columns[i] aligns with headers[i]
    n_rows: int
    warnings: list[str] = field(default_factory=list)

    def column(self, header: str) -> list[str]:
        """Raw cells for a column identified by its header name."""
        return self.columns[self.headers.index(header)]

    def is_numeric_column(self, header: str) -> bool:
        """True if the column has at least one parseable numeric value."""
        return any(_to_float(c) is not None for c in self.column(header))

    def numeric_headers(self) -> list[str]:
        """Headers of columns containing at least one numeric value."""
        return [h for h in self.headers if self.is_numeric_column(h)]


def _to_float(value: str):
    """Parse a single cell to float, tolerating thousands separators.

    Returns None for blank/non-numeric cells.
    """
    if value is None:
        return None
    text = value.strip().replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load(path: str) -> CsvData:
    """Read and validate a CSV file.

    Raises:
        CsvError: if the file is missing, unreadable, empty, has no header,
            or contains no data rows.
    """
    if not path:
        raise CsvError("No file selected.")
    if not os.path.isfile(path):
        raise CsvError(f"File not found: {path}")

    # Read raw text first so we can sniff the dialect and catch decode errors.
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as fh:
            raw = fh.read()
    except UnicodeDecodeError:
        try:
            with open(path, "r", newline="", encoding="latin-1") as fh:
                raw = fh.read()
        except OSError as exc:
            raise CsvError(f"Could not read file: {exc}") from exc
    except OSError as exc:
        raise CsvError(f"Could not read file: {exc}") from exc

    if not raw.strip():
        raise CsvError("The file is empty.")

    dialect: type[csv.Dialect] | csv.Dialect
    try:
        dialect = csv.Sniffer().sniff(raw[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel  # fall back to a comma-delimited dialect

    reader = csv.reader(io.StringIO(raw), dialect)
    try:
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    except csv.Error as exc:
        raise CsvError(f"This does not look like a valid CSV file: {exc}") from exc

    if not rows:
        raise CsvError("The file has no usable rows.")

    header_row = rows[0]
    data_rows = rows[1:]

    headers = _clean_headers(header_row)
    if not headers:
        raise CsvError("Could not detect any column headers in the first row.")
    if not data_rows:
        raise CsvError("The file has headers but no data rows.")

    warnings: list[str] = []
    n_cols = len(headers)

    # Normalise ragged rows so every column has exactly n_rows cells.
    ragged = 0
    normalised: list[list[str]] = []
    for row in data_rows:
        if len(row) != n_cols:
            ragged += 1
        fixed = list(row[:n_cols]) + [""] * (n_cols - len(row))
        normalised.append(fixed)
    if ragged:
        warnings.append(
            f"{ragged} row(s) had a different column count and were padded/truncated."
        )

    columns: list[list[str]] = [
        [normalised[r][c] for r in range(len(normalised))] for c in range(n_cols)
    ]

    data = CsvData(
        headers=headers,
        columns=columns,
        n_rows=len(normalised),
        warnings=warnings,
    )

    if not data.numeric_headers():
        raise CsvError(
            "No numeric columns were found. A LineChart needs at least one "
            "numeric column to plot."
        )

    return data


def _clean_headers(header_row: list[str]) -> list[str]:
    """Strip headers and disambiguate blank/duplicate names."""
    cleaned: list[str] = []
    seen: dict[str, int] = {}
    for idx, name in enumerate(header_row):
        label = name.strip() or f"Column {idx + 1}"
        if label in seen:
            seen[label] += 1
            label = f"{label} ({seen[label]})"
        else:
            seen[label] = 0
        cleaned.append(label)
    return cleaned


@dataclass
class CleanSeries:
    """A numeric (x, y) series cleaned for plotting, with a skip count."""

    x: list[float]
    y: list[float]
    skipped: int


def clean_xy(data: CsvData, x_header: str, y_header: str) -> CleanSeries:
    """Build aligned numeric x/y lists, dropping rows where either is invalid.

    `skipped` reports how many rows were dropped due to non-numeric/missing
    values in either the x or y column.
    """
    x_raw = data.column(x_header)
    y_raw = data.column(y_header)

    xs: list[float] = []
    ys: list[float] = []
    skipped = 0
    for xv, yv in zip(x_raw, y_raw):
        fx = _to_float(xv)
        fy = _to_float(yv)
        if fx is None or fy is None:
            skipped += 1
            continue
        xs.append(fx)
        ys.append(fy)

    return CleanSeries(x=xs, y=ys, skipped=skipped)


@dataclass
class CleanValues:
    """A single numeric column cleaned for plotting, with a skip count."""

    values: list[float]
    skipped: int


def clean_values(data: CsvData, header: str) -> CleanValues:
    """Extract a single numeric column, dropping missing/non-numeric cells.

    Used by histograms, which bin one column of raw observations (unlike lines,
    which need aligned x/y pairs). `skipped` counts dropped cells.
    """
    raw = data.column(header)
    values: list[float] = []
    skipped = 0
    for cell in raw:
        fv = _to_float(cell)
        if fv is None:
            skipped += 1
            continue
        values.append(fv)
    return CleanValues(values=values, skipped=skipped)
