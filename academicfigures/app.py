"""Minimalist Tkinter UI for AcademicFigures.

Two-column layout: a card-style control panel on the left and a live preview
on the right. Styling stays lightweight (pure Tk/ttk) for fast startup while
using clear hierarchy, soft borders, and a dedicated header band.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import csv_loader, figure_builder, mathtext, presets

# --- palette: calm neutrals with one accent ----------------------------------
BG = "#f4f4f6"
PANEL = "#ffffff"
BORDER = "#e2e2e8"
BORDER_SOFT = "#ececf0"
INK = "#18181b"
MUTED = "#71717a"
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
ERROR = "#dc2626"
WARNING = "#b45309"
OK = "#15803d"


class AcademicFiguresApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.data: csv_loader.CsvData | None = None
        self.current_figure = None
        self.canvas: FigureCanvasTkAgg | None = None
        self.line_rows: list[dict] = []
        self.hist_rows: list[dict] = []
        self.mathtext = mathtext.MathTextEditor(
            root,
            colors={
                "panel": PANEL,
                "ink": INK,
                "muted": MUTED,
                "border": BORDER,
                "border_soft": BORDER_SOFT,
                "accent": ACCENT,
            },
        )

        self._configure_root()
        self._build_style()
        self._build_layout()
        self._set_status("Select a CSV file to begin.", MUTED)

    # ------------------------------------------------------------------ setup
    def _configure_root(self) -> None:
        self.root.title("AcademicFigures")
        self.root.configure(bg=BG)
        self.root.geometry("1024x720")
        self.root.minsize(880, 600)

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
        style.configure("Card.TFrame", background=PANEL, relief="flat")
        style.configure("TLabel", background=BG, foreground=INK, font=base_font)
        style.configure("Panel.TLabel", background=PANEL, foreground=INK, font=base_font)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("Section.TLabel", background=PANEL, foreground=MUTED,
                        font=("Segoe UI Semibold", 8))
        style.configure("Field.TLabel", background=PANEL, foreground=INK,
                        font=("Segoe UI", 9))
        style.configure("TButton", font=base_font, padding=(12, 6))
        style.configure("Secondary.TButton", font=base_font, padding=(12, 6))
        style.map("Secondary.TButton",
                  background=[("!disabled", PANEL), ("active", BORDER_SOFT)],
                  foreground=[("!disabled", INK)])
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10),
                        padding=(12, 7))
        style.map("Accent.TButton",
                  background=[("!disabled", ACCENT), ("active", ACCENT_HOVER),
                              ("disabled", BORDER_SOFT)],
                  foreground=[("!disabled", "#ffffff"), ("disabled", MUTED)])
        style.configure("TEntry", padding=6, fieldbackground=PANEL)
        style.configure("TSpinbox", padding=6, fieldbackground=PANEL)
        style.configure("TRadiobutton", background=PANEL, font=base_font)
        style.configure("Panel.TCheckbutton", background=PANEL,
                        font=("Segoe UI", 9))
        style.map("Panel.TCheckbutton", background=[("active", PANEL)])
        style.configure("TCombobox", padding=6, fieldbackground=PANEL)
        style.configure("Vertical.TScrollbar", background=BG, troughcolor=BG,
                        borderwidth=0, arrowsize=12)

    def _card(self, parent: tk.Misc, **grid_kw) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        frame.grid(**grid_kw)
        return frame

    def _build_layout(self) -> None:
        header_band = tk.Frame(self.root, bg=PANEL,
                               highlightbackground=BORDER, highlightthickness=1)
        header_band.pack(fill="x", side="top")
        header_inner = tk.Frame(header_band, bg=PANEL)
        header_inner.pack(fill="x", padx=24, pady=(18, 16))
        tk.Label(
            header_inner,
            text="AcademicFigures",
            bg=PANEL,
            fg=INK,
            font=("Segoe UI Semibold", 22),
        ).pack(anchor="w")
        tk.Label(
            header_inner,
            text="CSV to journal-standard black & white figures.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(6, 0))

        outer = ttk.Frame(self.root, padding=(20, 16, 20, 0))
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=0, minsize=360)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        left_card = self._card(outer, row=0, column=0, sticky="nsew", padx=(0, 14))
        left_card.rowconfigure(0, weight=1)
        left_card.columnconfigure(0, weight=1)
        self._build_controls(left_card)

        right_card = self._card(outer, row=0, column=1, sticky="nsew")
        right_card.rowconfigure(0, weight=1)
        right_card.columnconfigure(0, weight=1)
        right_inner = ttk.Frame(right_card, style="Panel.TFrame", padding=(16, 14))
        right_inner.grid(row=0, column=0, sticky="nsew")
        right_inner.rowconfigure(1, weight=1)
        right_inner.columnconfigure(0, weight=1)
        ttk.Label(right_inner, text="PREVIEW", style="Section.TLabel").grid(
            row=0, column=0, sticky="w")
        self.preview_holder = tk.Frame(
            right_inner,
            bg=BORDER_SOFT,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.preview_holder.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.preview_holder.rowconfigure(0, weight=1)
        self.preview_holder.columnconfigure(0, weight=1)
        self.preview_placeholder = tk.Label(
            self.preview_holder,
            text="Your figure preview will appear here.",
            bg=BORDER_SOFT,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        self.preview_placeholder.grid(row=0, column=0)

        status_bar = tk.Frame(self.root, bg=PANEL,
                              highlightbackground=BORDER, highlightthickness=1)
        status_bar.pack(fill="x", side="bottom")
        self.status = tk.Label(
            status_bar,
            text="",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            padx=24,
            pady=10,
        )
        self.status.pack(fill="x")

    def _build_controls(self, parent: tk.Frame) -> None:
        canvas = tk.Canvas(parent, bg=PANEL, highlightthickness=0, borderwidth=0)
        self._controls_scroll = ttk.Scrollbar(
            parent, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar",
        )
        body = ttk.Frame(canvas, style="Panel.TFrame", padding=(16, 14))
        body.bind("<Configure>", lambda e: self._sync_controls_scroll(canvas))
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>",
                    lambda e: (canvas.itemconfigure(window, width=e.width),
                               self._sync_controls_scroll(canvas)))
        canvas.configure(yscrollcommand=self._controls_scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        self._controls_scroll.grid(row=0, column=1, sticky="ns")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        def _wheel(event):
            if canvas.winfo_height() >= body.winfo_reqheight():
                return
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._controls_canvas = canvas
        self._controls_body = body
        body.columnconfigure(0, weight=1)
        r = 0

        def section(title: str) -> None:
            nonlocal r
            if r:
                sep = tk.Frame(body, bg=BORDER_SOFT, height=1)
                sep.grid(row=r, column=0, sticky="ew", pady=(14, 12))
                r += 1
            ttk.Label(body, text=title, style="Section.TLabel").grid(
                row=r, column=0, sticky="w", pady=(0, 8))
            r += 1

        section("1 · DATA FILE")
        file_row = ttk.Frame(body, style="Panel.TFrame")
        file_row.grid(row=r, column=0, sticky="ew", pady=(0, 0))
        r += 1
        file_row.columnconfigure(0, weight=1)
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(file_row, textvariable=self.path_var, state="readonly")
        path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(file_row, text="Browse...", style="Secondary.TButton",
                   command=self._on_browse).grid(row=0, column=1)

        section("2 · FIGURE STYLE")
        self.style_var = tk.StringVar(value=presets.style_names()[0])
        style_box = ttk.Combobox(body, textvariable=self.style_var,
                                 values=presets.style_names(), state="readonly")
        style_box.grid(row=r, column=0, sticky="ew")
        r += 1
        style_box.bind("<<ComboboxSelected>>",
                       lambda e: (self._rebuild_line_rows(), self._rebuild_hist_rows()))

        section("3 · LINES")
        nlines_row = ttk.Frame(body, style="Panel.TFrame")
        nlines_row.grid(row=r, column=0, sticky="ew", pady=(0, 8))
        r += 1
        ttk.Label(nlines_row, text="Number of lines", style="Field.TLabel").grid(
            row=0, column=0, sticky="w")
        self.nlines_var = tk.IntVar(value=1)
        self.nlines_spin = ttk.Spinbox(
            nlines_row, from_=0, to=presets.MAX_LINES, width=5,
            textvariable=self.nlines_var, command=self._rebuild_line_rows,
            state="disabled",
        )
        self.nlines_spin.grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Label(nlines_row, text=f"(0–{presets.MAX_LINES})", style="PanelMuted.TLabel").grid(
            row=0, column=2, sticky="w", padx=(8, 0))
        self.nlines_var.trace_add("write", lambda *a: self._rebuild_line_rows())

        self.lines_container = ttk.Frame(body, style="Panel.TFrame")
        self.lines_container.grid(row=r, column=0, sticky="ew", pady=(0, 0))
        r += 1
        self.lines_container.columnconfigure(0, weight=1)

        section("4 · HISTOGRAMS")
        ttk.Label(
            body,
            text="Bars are drawn behind the lines, so a distribution and a "
                 "model curve can be superimposed.",
            style="PanelMuted.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=r, column=0, sticky="w", pady=(0, 8))
        r += 1
        nhist_row = ttk.Frame(body, style="Panel.TFrame")
        nhist_row.grid(row=r, column=0, sticky="ew", pady=(0, 8))
        r += 1
        ttk.Label(nhist_row, text="Number of histograms", style="Field.TLabel").grid(
            row=0, column=0, sticky="w")
        self.nhist_var = tk.IntVar(value=0)
        self.nhist_spin = ttk.Spinbox(
            nhist_row, from_=0, to=presets.MAX_HISTOGRAMS, width=5,
            textvariable=self.nhist_var, command=self._rebuild_hist_rows,
            state="disabled",
        )
        self.nhist_spin.grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Label(nhist_row, text=f"(0–{presets.MAX_HISTOGRAMS})",
                  style="PanelMuted.TLabel").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.nhist_var.trace_add("write", lambda *a: self._rebuild_hist_rows())

        self.hist_container = ttk.Frame(body, style="Panel.TFrame")
        self.hist_container.grid(row=r, column=0, sticky="ew", pady=(0, 0))
        r += 1
        self.hist_container.columnconfigure(0, weight=1)

        section("5 · LABELS")
        self.title_var = tk.StringVar()
        self.xtitle_var = tk.StringVar()
        self.ytitle_var = tk.StringVar()
        for label, var in (
            ("Figure title", self.title_var),
            ("X-axis title", self.xtitle_var),
            ("Y-axis title", self.ytitle_var),
        ):
            row = ttk.Frame(body, style="Panel.TFrame")
            row.grid(row=r, column=0, sticky="ew", pady=(0, 8))
            r += 1
            row.columnconfigure(1, weight=1)
            ttk.Label(row, text=label, style="Field.TLabel", width=14).grid(
                row=0, column=0, sticky="w")
            entry = ttk.Entry(row, textvariable=var)
            entry.grid(row=0, column=1, sticky="ew")
            self.mathtext.track(entry)

        self.mathtext.build_toolbar(body).grid(
            row=r, column=0, sticky="ew", pady=(2, 2))
        r += 1
        ttk.Label(
            body,
            text="Click a field, then insert. Select text first to make it "
                 "super/subscript.",
            style="PanelMuted.TLabel",
            wraplength=320,
            justify="left",
        ).grid(row=r, column=0, sticky="w", pady=(0, 4))
        r += 1

        section("6 · AXIS LIMITS")
        ttk.Label(
            body,
            text="Leave blank to auto-fit. Ticks restyle to match.",
            style="PanelMuted.TLabel",
        ).grid(row=r, column=0, sticky="w", pady=(0, 8))
        r += 1
        self.xmin_var = tk.StringVar()
        self.xmax_var = tk.StringVar()
        self.ymin_var = tk.StringVar()
        self.ymax_var = tk.StringVar()
        for axis_label, min_var, max_var in (
            ("X-axis", self.xmin_var, self.xmax_var),
            ("Y-axis", self.ymin_var, self.ymax_var),
        ):
            row = ttk.Frame(body, style="Panel.TFrame")
            row.grid(row=r, column=0, sticky="ew", pady=(0, 8))
            r += 1
            row.columnconfigure(2, weight=1)
            row.columnconfigure(4, weight=1)
            ttk.Label(row, text=axis_label, style="Field.TLabel", width=8).grid(
                row=0, column=0, sticky="w")
            ttk.Label(row, text="min", style="PanelMuted.TLabel").grid(
                row=0, column=1, sticky="w", padx=(4, 4))
            ttk.Entry(row, textvariable=min_var, width=8).grid(
                row=0, column=2, sticky="ew", padx=(0, 8))
            ttk.Label(row, text="max", style="PanelMuted.TLabel").grid(
                row=0, column=3, sticky="w", padx=(0, 4))
            ttk.Entry(row, textvariable=max_var, width=8).grid(
                row=0, column=4, sticky="ew")

        section("7 · OUTPUT FORMAT")
        fmt_row = ttk.Frame(body, style="Panel.TFrame")
        fmt_row.grid(row=r, column=0, sticky="ew", pady=(0, 0))
        r += 1
        self.fmt_var = tk.StringVar(value="png")
        ttk.Radiobutton(fmt_row, text="PNG", value="png",
                        variable=self.fmt_var).grid(row=0, column=0, padx=(0, 18))
        ttk.Radiobutton(fmt_row, text="JPEG", value="jpeg",
                        variable=self.fmt_var).grid(row=0, column=1)

        actions = ttk.Frame(body, style="Panel.TFrame")
        actions.grid(row=r, column=0, sticky="ew", pady=(18, 4))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.preview_btn = ttk.Button(
            actions, text="Preview", style="Secondary.TButton",
            command=self._on_preview, state="disabled",
        )
        self.preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.export_btn = ttk.Button(
            actions, text="Export...", style="Accent.TButton",
            command=self._on_export, state="disabled",
        )
        self.export_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self._sync_controls_scroll(canvas)

    def _sync_controls_scroll(self, canvas: tk.Canvas) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        needs_scroll = canvas.winfo_height() < self._controls_body.winfo_reqheight()
        if needs_scroll:
            self._controls_scroll.grid()
        else:
            self._controls_scroll.grid_remove()
            canvas.yview_moveto(0)

    # ----------------------------------------------------------- line rows UI
    def _rebuild_line_rows(self) -> None:
        for child in self.lines_container.winfo_children():
            child.destroy()
        self.line_rows = []

        if not self.data:
            ttk.Label(
                self.lines_container,
                text="Load a CSV to assign columns.",
                style="PanelMuted.TLabel",
            ).grid(row=0, column=0, sticky="w", pady=(0, 4))
            self._sync_controls_scroll(self._controls_canvas)
            return

        try:
            n = int(self.nlines_var.get())
        except (tk.TclError, ValueError):
            return
        n = max(0, min(presets.MAX_LINES, n))

        headers = self.data.headers
        numeric = self.data.numeric_headers()
        default_x = headers[0]
        default_y = numeric[0] if numeric else headers[0]

        for i in range(n):
            frame = tk.Frame(
                self.lines_container,
                bg=BORDER_SOFT,
                highlightbackground=BORDER,
                highlightthickness=1,
            )
            frame.grid(row=i, column=0, sticky="ew", pady=(0, 8))
            frame.columnconfigure(0, weight=1)
            inner = ttk.Frame(frame, style="Panel.TFrame", padding=(10, 8))
            inner.grid(row=0, column=0, sticky="ew")
            inner.columnconfigure(1, weight=1)

            ttk.Label(inner, text=f"Line {i + 1}", style="Section.TLabel").grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

            ttk.Label(inner, text="X", style="Field.TLabel", width=8).grid(
                row=1, column=0, sticky="w", pady=(2, 0))
            x_var = tk.StringVar(value=default_x)
            x_box = ttk.Combobox(inner, textvariable=x_var, values=headers,
                                 state="readonly")
            x_box.grid(row=1, column=1, sticky="ew", pady=(2, 0))

            ttk.Label(inner, text="Y", style="Field.TLabel", width=8).grid(
                row=2, column=0, sticky="w", pady=(6, 0))
            y_default = numeric[(i + 1) % len(numeric)] if len(numeric) > 1 else default_y
            y_var = tk.StringVar(value=y_default)
            y_box = ttk.Combobox(inner, textvariable=y_var, values=headers,
                                 state="readonly")
            y_box.grid(row=2, column=1, sticky="ew", pady=(6, 0))

            ttk.Label(inner, text="Legend", style="Field.TLabel", width=8).grid(
                row=3, column=0, sticky="w", pady=(6, 0))
            legend_var = tk.StringVar(value=y_default)
            legend_entry = ttk.Entry(inner, textvariable=legend_var)
            legend_entry.grid(row=3, column=1, sticky="ew", pady=(6, 0))
            self.mathtext.track(legend_entry)

            ttk.Label(inner, text="Style", style="Field.TLabel", width=8).grid(
                row=4, column=0, sticky="w", pady=(6, 0))
            style_choices = ["Auto"] + [
                f"{j + 1}: {self._line_style_label(ls)}"
                for j, ls in enumerate(self._current_line_styles())
            ]
            style_var = tk.StringVar(value="Auto")
            style_box = ttk.Combobox(
                inner, textvariable=style_var, values=style_choices, state="readonly"
            )
            style_box.grid(row=4, column=1, sticky="ew", pady=(6, 0))

            self.line_rows.append({
                "x": x_var,
                "y": y_var,
                "legend": legend_var,
                "style": style_var,
            })

        self._sync_controls_scroll(self._controls_canvas)

    def _rebuild_hist_rows(self) -> None:
        for child in self.hist_container.winfo_children():
            child.destroy()
        self.hist_rows = []

        if not self.data:
            self._sync_controls_scroll(self._controls_canvas)
            return

        try:
            n = int(self.nhist_var.get())
        except (tk.TclError, ValueError):
            return
        n = max(0, min(presets.MAX_HISTOGRAMS, n))

        headers = self.data.headers
        numeric = self.data.numeric_headers()
        default_col = numeric[0] if numeric else headers[0]

        for i in range(n):
            frame = tk.Frame(
                self.hist_container,
                bg=BORDER_SOFT,
                highlightbackground=BORDER,
                highlightthickness=1,
            )
            frame.grid(row=i, column=0, sticky="ew", pady=(0, 8))
            frame.columnconfigure(0, weight=1)
            inner = ttk.Frame(frame, style="Panel.TFrame", padding=(10, 8))
            inner.grid(row=0, column=0, sticky="ew")
            inner.columnconfigure(1, weight=1)

            ttk.Label(inner, text=f"Histogram {i + 1}", style="Section.TLabel").grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

            ttk.Label(inner, text="Type", style="Field.TLabel", width=8).grid(
                row=1, column=0, sticky="w", pady=(2, 0))
            type_var = tk.StringVar(value="Raw values")
            type_box = ttk.Combobox(
                inner, textvariable=type_var, state="readonly",
                values=["Raw values", "Binned (centre+height)"],
            )
            type_box.grid(row=1, column=1, sticky="ew", pady=(2, 0))

            ttk.Label(inner, text="Legend", style="Field.TLabel", width=8).grid(
                row=2, column=0, sticky="w", pady=(6, 0))
            legend_var = tk.StringVar(value=default_col)
            legend_entry = ttk.Entry(inner, textvariable=legend_var)
            legend_entry.grid(row=2, column=1, sticky="ew", pady=(6, 0))
            self.mathtext.track(legend_entry)

            # --- Raw-values widgets (rows 3-5) ---
            lbl_data = ttk.Label(inner, text="Data", style="Field.TLabel", width=8)
            values_var = tk.StringVar(value=default_col)
            values_box = ttk.Combobox(inner, textvariable=values_var,
                                      values=headers, state="readonly")
            lbl_bins = ttk.Label(inner, text="Bins", style="Field.TLabel", width=8)
            bins_var = tk.IntVar(value=presets.get_style(self.style_var.get()).default_bins)
            bins_spin = ttk.Spinbox(inner, from_=1, to=500, width=6,
                                    textvariable=bins_var)
            density_var = tk.BooleanVar(value=True)
            density_chk = ttk.Checkbutton(
                inner, text="Normalise to density (PDF)",
                variable=density_var, style="Panel.TCheckbutton",
            )

            # --- Binned widgets (rows 3-4) ---
            lbl_centres = ttk.Label(inner, text="Centres", style="Field.TLabel", width=8)
            centers_var = tk.StringVar(value=default_col)
            centers_box = ttk.Combobox(inner, textvariable=centers_var,
                                       values=headers, state="readonly")
            lbl_heights = ttk.Label(inner, text="Heights", style="Field.TLabel", width=8)
            heights_var = tk.StringVar(
                value=numeric[1] if len(numeric) > 1 else default_col)
            heights_box = ttk.Combobox(inner, textvariable=heights_var,
                                       values=headers, state="readonly")

            raw_widgets = (
                (lbl_data, 3, 0), (values_box, 3, 1),
                (lbl_bins, 4, 0), (bins_spin, 4, 1),
                (density_chk, 5, 1),
            )
            binned_widgets = (
                (lbl_centres, 3, 0), (centers_box, 3, 1),
                (lbl_heights, 4, 0), (heights_box, 4, 1),
            )

            def apply_type(*_a, type_var=type_var, raw_widgets=raw_widgets,
                           binned_widgets=binned_widgets):
                show_raw = type_var.get().startswith("Raw")
                active = raw_widgets if show_raw else binned_widgets
                inactive = binned_widgets if show_raw else raw_widgets
                for widget, _row, _col in inactive:
                    widget.grid_remove()
                for widget, row_i, col_i in active:
                    sticky = "w" if widget is density_chk else "ew"
                    pady = (6, 0)
                    widget.grid(row=row_i, column=col_i, sticky=sticky, pady=pady)
                self._sync_controls_scroll(self._controls_canvas)

            type_box.bind("<<ComboboxSelected>>", apply_type)
            apply_type()

            self.hist_rows.append({
                "type": type_var,
                "legend": legend_var,
                "values": values_var,
                "bins": bins_var,
                "density": density_var,
                "centers": centers_var,
                "heights": heights_var,
            })

        self._sync_controls_scroll(self._controls_canvas)

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
            self.nhist_spin.configure(state="disabled")
            self.preview_btn.configure(state="disabled")
            self.export_btn.configure(state="disabled")
            self._rebuild_line_rows()
            self._rebuild_hist_rows()
            self._set_status(f"Error: {exc}", ERROR)
            return

        self.data = data
        self.nlines_spin.configure(state="normal")
        self.nhist_spin.configure(state="normal")
        self.preview_btn.configure(state="normal")
        self.export_btn.configure(state="disabled")  # require a preview first
        self._rebuild_line_rows()
        self._rebuild_hist_rows()

        msg = (f"Loaded {len(data.headers)} columns, {data.n_rows} rows. "
               f"Numeric columns: {len(data.numeric_headers())}.")
        if data.warnings:
            self._set_status(msg + "  " + "  ".join(data.warnings), WARNING)
        else:
            self._set_status(msg, OK)

    def _current_line_styles(self) -> tuple:
        """Line-style palette for the currently selected figure style."""
        try:
            return presets.get_style(self.style_var.get()).line_styles
        except Exception:
            return presets.BW_LINE_STYLES

    @staticmethod
    def _line_style_label(ls) -> str:
        """Short human-readable name for a palette entry (UI combobox)."""
        dash = {
            "-": "solid",
            "--": "dashed",
            ":": "dotted",
            "-.": "dash-dot",
        }.get(ls.linestyle, ls.linestyle)
        if ls.marker:
            return f"{dash} + {ls.marker}"
        return dash

    @staticmethod
    def _parse_style_index(value: str) -> int | None:
        """Map a Style combobox value to a 0-based palette index, or None=Auto."""
        text = (value or "").strip()
        if not text or text == "Auto":
            return None
        # Values look like "3: dotted" — take the leading integer.
        head = text.split(":", 1)[0].strip()
        try:
            n = int(head)
        except ValueError:
            return None
        return max(0, n - 1)

    def _collect_spec(self) -> figure_builder.FigureSpec:
        lines = [
            figure_builder.LineSpec(
                x_header=row["x"].get(),
                y_header=row["y"].get(),
                legend=row["legend"].get(),
                style_index=self._parse_style_index(row["style"].get()),
            )
            for row in self.line_rows
        ]
        histograms = [self._hist_spec_from_row(row) for row in self.hist_rows]
        return figure_builder.FigureSpec(
            title=self.title_var.get(),
            x_axis_title=self.xtitle_var.get(),
            y_axis_title=self.ytitle_var.get(),
            lines=lines,
            histograms=histograms,
            x_min=self._parse_limit(self.xmin_var.get()),
            x_max=self._parse_limit(self.xmax_var.get()),
            y_min=self._parse_limit(self.ymin_var.get()),
            y_max=self._parse_limit(self.ymax_var.get()),
        )

    @staticmethod
    def _hist_spec_from_row(row: dict) -> figure_builder.HistogramSpec:
        """Translate one histogram UI row into a HistogramSpec."""
        legend = row["legend"].get()
        if row["type"].get().startswith("Raw"):
            try:
                bins = int(row["bins"].get())
            except (tk.TclError, ValueError):
                bins = 0  # builder falls back to the style default
            return figure_builder.HistogramSpec(
                legend=legend,
                values_header=row["values"].get(),
                bins=bins,
                density=bool(row["density"].get()),
            )
        return figure_builder.HistogramSpec(
            legend=legend,
            bin_centers_header=row["centers"].get(),
            heights_header=row["heights"].get(),
        )

    @staticmethod
    def _parse_limit(text: str) -> float | None:
        """Blank stays auto (None); otherwise coerce to float, tolerating commas."""
        cleaned = text.strip().replace(",", "")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _invalid_limit_fields(self) -> list[str]:
        """Names of axis-limit fields holding non-blank, non-numeric text."""
        bad: list[str] = []
        for name, var in (
            ("X min", self.xmin_var),
            ("X max", self.xmax_var),
            ("Y min", self.ymin_var),
            ("Y max", self.ymax_var),
        ):
            text = var.get().strip()
            if text and self._parse_limit(text) is None:
                bad.append(name)
        return bad

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

        warnings = list(result.warnings)
        bad = self._invalid_limit_fields()
        if bad:
            warnings.append(
                f"Ignored non-numeric axis limit(s): {', '.join(bad)}."
            )
        if warnings:
            self._set_status("Warning: " + "  ".join(warnings), WARNING)
        else:
            self._set_status("Preview ready. Click Export... to save.", OK)

    def _render_preview(self, figure) -> None:
        self.preview_placeholder.grid_forget()
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(figure, master=self.preview_holder)
        self.canvas.draw()
        widget = self.canvas.get_tk_widget()
        widget.configure(bg=BORDER_SOFT)
        widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

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
