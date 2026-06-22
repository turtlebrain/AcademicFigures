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

from . import csv_loader, figure_builder, presets

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
        style_box.bind("<<ComboboxSelected>>", lambda e: self._rebuild_line_rows())

        section("3 · DATA TRENDS")
        nlines_row = ttk.Frame(body, style="Panel.TFrame")
        nlines_row.grid(row=r, column=0, sticky="ew", pady=(0, 8))
        r += 1
        ttk.Label(nlines_row, text="Number of lines", style="Field.TLabel").grid(
            row=0, column=0, sticky="w")
        self.nlines_var = tk.IntVar(value=1)
        self.nlines_spin = ttk.Spinbox(
            nlines_row, from_=1, to=presets.MAX_LINES, width=5,
            textvariable=self.nlines_var, command=self._rebuild_line_rows,
            state="disabled",
        )
        self.nlines_spin.grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Label(nlines_row, text=f"(1–{presets.MAX_LINES})", style="PanelMuted.TLabel").grid(
            row=0, column=2, sticky="w", padx=(8, 0))
        self.nlines_var.trace_add("write", lambda *a: self._rebuild_line_rows())

        self.lines_container = ttk.Frame(body, style="Panel.TFrame")
        self.lines_container.grid(row=r, column=0, sticky="ew", pady=(0, 0))
        r += 1
        self.lines_container.columnconfigure(0, weight=1)

        section("4 · LABELS")
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
            ttk.Entry(row, textvariable=var).grid(row=0, column=1, sticky="ew")

        section("5 · OUTPUT FORMAT")
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
        n = max(1, min(presets.MAX_LINES, n))

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
            ttk.Entry(inner, textvariable=legend_var).grid(
                row=3, column=1, sticky="ew", pady=(6, 0))

            self.line_rows.append({"x": x_var, "y": y_var, "legend": legend_var})

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
