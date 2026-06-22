"""Minimalist Tkinter UI for AcademicFigures.

The window is a single vertical column of controls with a live preview on the
right. Styling is deliberately restrained: a clean light theme, generous
whitespace, and a single status line that turns red for errors and amber for
warnings.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import csv_loader, figure_builder, presets

# --- palette: light, low-distraction, high-contrast text ---------------------
BG = "#fbfbfd"
PANEL = "#ffffff"
INK = "#1b1b1f"
MUTED = "#6b6b70"
ACCENT = "#2563eb"
ERROR = "#c0392b"
WARNING = "#b7791f"
OK = "#1f7a4d"


class AcademicFiguresApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.data: csv_loader.CsvData | None = None
        self.current_figure = None
        self.canvas: FigureCanvasTkAgg | None = None
        self.line_rows: list[dict] = []

        self._configure_root()
        self._build_style()
        self._build_layout()
        self._set_status("Select a CSV file to begin.", MUTED)

    # ------------------------------------------------------------------ setup
    def _configure_root(self) -> None:
        self.root.title("AcademicFigures")
        self.root.configure(bg=BG)
        self.root.geometry("960x680")
        self.root.minsize(820, 560)

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        base_font = ("Segoe UI", 10)
        style.configure(".", background=BG, foreground=INK, font=base_font)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=INK, font=base_font)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("Heading.TLabel", background=BG, foreground=INK,
                        font=("Segoe UI Semibold", 15))
        style.configure("Section.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI Semibold", 9))
        style.configure("TButton", font=base_font, padding=(10, 5))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10),
                        padding=(12, 6))
        style.map("Accent.TButton",
                  background=[("!disabled", ACCENT), ("active", "#1d4ed8")],
                  foreground=[("!disabled", "#ffffff")])
        style.configure("TEntry", padding=4)
        style.configure("TSpinbox", padding=4)
        style.configure("TRadiobutton", background=BG, font=base_font)
        style.configure("TCombobox", padding=4)

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=0, minsize=380)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(1, weight=1)

        header = ttk.Label(outer, text="AcademicFigures", style="Heading.TLabel")
        header.grid(row=0, column=0, columnspan=2, sticky="w")
        sub = ttk.Label(
            outer,
            text="CSV to journal-standard black & white figures.",
            style="Muted.TLabel",
        )
        sub.grid(row=0, column=0, columnspan=2, sticky="w", pady=(24, 0))

        # ---- left: controls (scrollable) -----------------------------------
        left = ttk.Frame(outer)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 16), pady=(16, 0))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self._build_controls(left)

        # ---- right: preview --------------------------------------------------
        right = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        right.grid(row=1, column=1, sticky="nsew", pady=(16, 0))
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="PREVIEW", style="Section.TLabel",
                  background=PANEL).grid(row=0, column=0, sticky="w")
        self.preview_holder = tk.Frame(right, bg=PANEL,
                                       highlightbackground="#e3e3e8",
                                       highlightthickness=1)
        self.preview_holder.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.preview_holder.rowconfigure(0, weight=1)
        self.preview_holder.columnconfigure(0, weight=1)
        self.preview_placeholder = tk.Label(
            self.preview_holder,
            text="Your figure preview will appear here.",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 10),
        )
        self.preview_placeholder.grid(row=0, column=0)

        # ---- bottom: status bar ---------------------------------------------
        self.status = ttk.Label(outer, text="", style="Muted.TLabel", anchor="w")
        self.status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _build_controls(self, parent: ttk.Frame) -> None:
        # Scrollable canvas so many lines never overflow the window.
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas)
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        def _wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _wheel)

        body.columnconfigure(0, weight=1)
        r = 0

        # 1) CSV file
        ttk.Label(body, text="1 · DATA FILE", style="Section.TLabel").grid(
            row=r, column=0, sticky="w", pady=(0, 4)); r += 1
        file_row = ttk.Frame(body)
        file_row.grid(row=r, column=0, sticky="ew", pady=(0, 12)); r += 1
        file_row.columnconfigure(0, weight=1)
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(file_row, textvariable=self.path_var, state="readonly")
        path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(file_row, text="Browse...", command=self._on_browse).grid(
            row=0, column=1)

        # 2) Figure style
        ttk.Label(body, text="2 · FIGURE STYLE", style="Section.TLabel").grid(
            row=r, column=0, sticky="w", pady=(0, 4)); r += 1
        self.style_var = tk.StringVar(value=presets.style_names()[0])
        style_box = ttk.Combobox(body, textvariable=self.style_var,
                                 values=presets.style_names(), state="readonly")
        style_box.grid(row=r, column=0, sticky="ew", pady=(0, 12)); r += 1
        style_box.bind("<<ComboboxSelected>>", lambda e: self._rebuild_line_rows())

        # 3) Number of lines
        ttk.Label(body, text="3 · DATA TRENDS (LINES)", style="Section.TLabel").grid(
            row=r, column=0, sticky="w", pady=(0, 4)); r += 1
        nlines_row = ttk.Frame(body)
        nlines_row.grid(row=r, column=0, sticky="ew", pady=(0, 8)); r += 1
        ttk.Label(nlines_row, text="Number of lines").grid(row=0, column=0, sticky="w")
        self.nlines_var = tk.IntVar(value=1)
        self.nlines_spin = ttk.Spinbox(
            nlines_row, from_=1, to=presets.MAX_LINES, width=5,
            textvariable=self.nlines_var, command=self._rebuild_line_rows,
            state="disabled",
        )
        self.nlines_spin.grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(nlines_row, text=f"(1-{presets.MAX_LINES})",
                  style="Muted.TLabel").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.nlines_var.trace_add("write", lambda *a: self._rebuild_line_rows())

        # 4) Per-line assignment container
        self.lines_container = ttk.Frame(body)
        self.lines_container.grid(row=r, column=0, sticky="ew", pady=(0, 12)); r += 1
        self.lines_container.columnconfigure(0, weight=1)

        # 5) Labels
        ttk.Label(body, text="4 · LABELS", style="Section.TLabel").grid(
            row=r, column=0, sticky="w", pady=(0, 4)); r += 1
        self.title_var = tk.StringVar()
        self.xtitle_var = tk.StringVar()
        self.ytitle_var = tk.StringVar()
        for label, var in (
            ("Figure title", self.title_var),
            ("X-axis title", self.xtitle_var),
            ("Y-axis title", self.ytitle_var),
        ):
            row = ttk.Frame(body)
            row.grid(row=r, column=0, sticky="ew", pady=(0, 6)); r += 1
            row.columnconfigure(1, weight=1)
            ttk.Label(row, text=label, width=14).grid(row=0, column=0, sticky="w")
            ttk.Entry(row, textvariable=var).grid(row=0, column=1, sticky="ew")

        # 6) Output format
        ttk.Label(body, text="5 · OUTPUT FORMAT", style="Section.TLabel").grid(
            row=r, column=0, sticky="w", pady=(8, 4)); r += 1
        fmt_row = ttk.Frame(body)
        fmt_row.grid(row=r, column=0, sticky="ew", pady=(0, 12)); r += 1
        self.fmt_var = tk.StringVar(value="png")
        ttk.Radiobutton(fmt_row, text="PNG", value="png",
                        variable=self.fmt_var).grid(row=0, column=0, padx=(0, 16))
        ttk.Radiobutton(fmt_row, text="JPEG", value="jpeg",
                        variable=self.fmt_var).grid(row=0, column=1)

        # 7) Actions
        actions = ttk.Frame(body)
        actions.grid(row=r, column=0, sticky="ew", pady=(4, 0)); r += 1
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.preview_btn = ttk.Button(actions, text="Preview",
                                      command=self._on_preview, state="disabled")
        self.preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.export_btn = ttk.Button(actions, text="Export...", style="Accent.TButton",
                                     command=self._on_export, state="disabled")
        self.export_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    # ----------------------------------------------------------- line rows UI
    def _rebuild_line_rows(self) -> None:
        for child in self.lines_container.winfo_children():
            child.destroy()
        self.line_rows = []

        if not self.data:
            ttk.Label(self.lines_container,
                      text="Load a CSV to assign columns.",
                      style="Muted.TLabel").grid(row=0, column=0, sticky="w")
            return

        try:
            n = int(self.nlines_var.get())
        except (tk.TclError, ValueError):
            return
        n = max(1, min(presets.MAX_LINES, n))

        headers = self.data.headers
        numeric = self.data.numeric_headers()
        default_x = headers[0]
        default_y = numeric[0] if numeric else headers[0]

        for i in range(n):
            frame = ttk.Frame(self.lines_container, style="Panel.TFrame", padding=8)
            frame.grid(row=i, column=0, sticky="ew", pady=(0, 6))
            frame.columnconfigure(1, weight=1)

            ttk.Label(frame, text=f"Line {i + 1}", style="Section.TLabel",
                      background=PANEL).grid(row=0, column=0, columnspan=2, sticky="w")

            ttk.Label(frame, text="X", background=PANEL, width=8).grid(
                row=1, column=0, sticky="w", pady=(4, 0))
            x_var = tk.StringVar(value=default_x)
            x_box = ttk.Combobox(frame, textvariable=x_var, values=headers,
                                 state="readonly")
            x_box.grid(row=1, column=1, sticky="ew", pady=(4, 0))

            ttk.Label(frame, text="Y", background=PANEL, width=8).grid(
                row=2, column=0, sticky="w", pady=(4, 0))
            y_default = numeric[(i + 1) % len(numeric)] if len(numeric) > 1 else default_y
            y_var = tk.StringVar(value=y_default)
            y_box = ttk.Combobox(frame, textvariable=y_var, values=headers,
                                 state="readonly")
            y_box.grid(row=2, column=1, sticky="ew", pady=(4, 0))

            ttk.Label(frame, text="Legend", background=PANEL, width=8).grid(
                row=3, column=0, sticky="w", pady=(4, 0))
            legend_var = tk.StringVar(value=y_default)
            ttk.Entry(frame, textvariable=legend_var).grid(
                row=3, column=1, sticky="ew", pady=(4, 0))

            self.line_rows.append({"x": x_var, "y": y_var, "legend": legend_var})

    # ---------------------------------------------------------------- actions
    def _on_browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.path_var.set(path)
        self._load_csv(path)

    def _load_csv(self, path: str) -> None:
        try:
            data = csv_loader.load(path)
        except csv_loader.CsvError as exc:
            self.data = None
            self.nlines_spin.configure(state="disabled")
            self.preview_btn.configure(state="disabled")
            self.export_btn.configure(state="disabled")
            self._rebuild_line_rows()
            self._set_status(f"Error: {exc}", ERROR)
            return

        self.data = data
        self.nlines_spin.configure(state="normal")
        self.preview_btn.configure(state="normal")
        self.export_btn.configure(state="disabled")  # require a preview first
        self._rebuild_line_rows()

        msg = (f"Loaded {len(data.headers)} columns, {data.n_rows} rows. "
               f"Numeric columns: {len(data.numeric_headers())}.")
        if data.warnings:
            self._set_status(msg + "  " + "  ".join(data.warnings), WARNING)
        else:
            self._set_status(msg, OK)

    def _collect_spec(self) -> figure_builder.FigureSpec:
        lines = [
            figure_builder.LineSpec(
                x_header=row["x"].get(),
                y_header=row["y"].get(),
                legend=row["legend"].get(),
            )
            for row in self.line_rows
        ]
        return figure_builder.FigureSpec(
            title=self.title_var.get(),
            x_axis_title=self.xtitle_var.get(),
            y_axis_title=self.ytitle_var.get(),
            lines=lines,
        )

    def _on_preview(self) -> None:
        if not self.data:
            self._set_status("Load a CSV file first.", ERROR)
            return
        style = presets.get_style(self.style_var.get())
        spec = self._collect_spec()
        try:
            result = figure_builder.build(self.data, spec, style)
        except figure_builder.FigureError as exc:
            self.export_btn.configure(state="disabled")
            self._set_status(f"Error: {exc}", ERROR)
            return

        self.current_figure = result.figure
        self._render_preview(result.figure)
        self.export_btn.configure(state="normal")

        if result.warnings:
            self._set_status("Warning: " + "  ".join(result.warnings), WARNING)
        else:
            self._set_status("Preview ready. Click Export... to save.", OK)

    def _render_preview(self, figure) -> None:
        self.preview_placeholder.grid_forget()
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(figure, master=self.preview_holder)
        self.canvas.draw()
        widget = self.canvas.get_tk_widget()
        widget.configure(bg=PANEL)
        widget.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def _on_export(self) -> None:
        if self.current_figure is None:
            self._set_status("Generate a preview before exporting.", ERROR)
            return
        fmt = self.fmt_var.get()
        ext = "jpg" if fmt == "jpeg" else "png"
        default_name = self._default_export_name(ext)
        path = filedialog.asksaveasfilename(
            title="Export figure",
            defaultextension=f".{ext}",
            initialfile=default_name,
            filetypes=[("PNG image", "*.png")] if ext == "png"
            else [("JPEG image", "*.jpg *.jpeg")],
        )
        if not path:
            return
        style = presets.get_style(self.style_var.get())
        try:
            figure_builder.export(self.current_figure, path, fmt, style)
        except figure_builder.FigureError as exc:
            self._set_status(f"Error: {exc}", ERROR)
            return
        self._set_status(f"Saved: {path}", OK)

    def _default_export_name(self, ext: str) -> str:
        title = self.title_var.get().strip()
        if title:
            safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
            return f"{safe.strip().replace(' ', '_')}.{ext}"
        if self.path_var.get():
            stem = os.path.splitext(os.path.basename(self.path_var.get()))[0]
            return f"{stem}_figure.{ext}"
        return f"figure.{ext}"

    # ----------------------------------------------------------------- status
    def _set_status(self, message: str, color: str) -> None:
        self.status.configure(text=message, foreground=color)


def main() -> None:
    root = tk.Tk()
    AcademicFiguresApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
