"""Rich-text helpers for inserting symbols and sub/superscripts into entries.

matplotlib renders Greek letters, math operators and sub/superscripts out of
the box through its *mathtext* mini-language: anything between ``$...$`` is laid
out as math, so ``$\\alpha$`` becomes alpha, ``$x^{2}$`` raises the 2 and
``$H_{2}O$`` drops the 2. Users should not have to memorise that syntax, so this
module provides a small toolbar plus a categorised symbol palette that inject
the correct tokens into whichever text field the user last touched.

The editor is UI-only and tracks a single "active" entry across every field it
is told about (figure title, axis titles, and the per-line legend entries),
which lets one shared toolbar drive all of them.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# Each entry is (button glyph shown to the user, mathtext token inserted).
# Tokens are inserted already wrapped in ``$...$`` by the editor, so they only
# carry the bare command here.
GREEK_LOWER: tuple[tuple[str, str], ...] = (
    ("\u03b1", r"\alpha"), ("\u03b2", r"\beta"), ("\u03b3", r"\gamma"),
    ("\u03b4", r"\delta"), ("\u03b5", r"\epsilon"), ("\u03b6", r"\zeta"),
    ("\u03b7", r"\eta"), ("\u03b8", r"\theta"), ("\u03b9", r"\iota"),
    ("\u03ba", r"\kappa"), ("\u03bb", r"\lambda"), ("\u03bc", r"\mu"),
    ("\u03bd", r"\nu"), ("\u03be", r"\xi"), ("\u03bf", r"o"),
    ("\u03c0", r"\pi"), ("\u03c1", r"\rho"), ("\u03c3", r"\sigma"),
    ("\u03c4", r"\tau"), ("\u03c5", r"\upsilon"), ("\u03c6", r"\phi"),
    ("\u03c7", r"\chi"), ("\u03c8", r"\psi"), ("\u03c9", r"\omega"),
)

GREEK_UPPER: tuple[tuple[str, str], ...] = (
    ("\u0393", r"\Gamma"), ("\u0394", r"\Delta"), ("\u0398", r"\Theta"),
    ("\u039b", r"\Lambda"), ("\u039e", r"\Xi"), ("\u03a0", r"\Pi"),
    ("\u03a3", r"\Sigma"), ("\u03a6", r"\Phi"), ("\u03a8", r"\Psi"),
    ("\u03a9", r"\Omega"),
)

MATH_OPERATORS: tuple[tuple[str, str], ...] = (
    ("\u00d7", r"\times"), ("\u00f7", r"\div"), ("\u00b1", r"\pm"),
    ("\u2213", r"\mp"), ("\u22c5", r"\cdot"), ("\u2248", r"\approx"),
    ("\u2260", r"\neq"), ("\u2264", r"\leq"), ("\u2265", r"\geq"),
    ("\u221d", r"\propto"), ("\u221e", r"\infty"), ("\u2202", r"\partial"),
    ("\u2207", r"\nabla"), ("\u2211", r"\sum"), ("\u220f", r"\prod"),
    ("\u222b", r"\int"), ("\u00b0", r"^{\circ}"),
)

ARROWS: tuple[tuple[str, str], ...] = (
    ("\u2192", r"\rightarrow"), ("\u2190", r"\leftarrow"),
    ("\u2191", r"\uparrow"), ("\u2193", r"\downarrow"),
    ("\u2194", r"\leftrightarrow"),
)

# (group title, entries) in palette display order.
SYMBOL_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Greek (lower)", GREEK_LOWER),
    ("Greek (upper)", GREEK_UPPER),
    ("Operators", MATH_OPERATORS),
    ("Arrows", ARROWS),
)

# A handful of common symbols surfaced directly on the toolbar.
QUICK_SYMBOLS: tuple[tuple[str, str], ...] = (
    ("\u03b1", r"\alpha"), ("\u03b2", r"\beta"), ("\u03bc", r"\mu"),
    ("\u03a9", r"\Omega"), ("\u00b0", r"^{\circ}"), ("\u00d7", r"\times"),
    ("\u00b1", r"\pm"),
)


class MathTextEditor:
    """Tracks the active text entry and inserts symbols / scripts into it.

    Bind every editable field with :meth:`track`; the most recently focused one
    becomes the target for :meth:`insert_symbol`, :meth:`superscript` and
    :meth:`subscript`. This keeps a single toolbar usable for all fields,
    including legend entries that are created and destroyed dynamically.
    """

    def __init__(self, root: tk.Misc, colors: dict[str, str]) -> None:
        self._root = root
        self._colors = colors
        self._target: tk.Entry | None = None
        self._palette: tk.Toplevel | None = None

    # ------------------------------------------------------------ tracking
    def track(self, entry: tk.Entry) -> None:
        """Make ``entry`` eligible to receive insertions when it has focus."""
        entry.bind("<FocusIn>", lambda _e: self._set_target(entry), add="+")

    def _set_target(self, entry: tk.Entry) -> None:
        self._target = entry

    def _active(self) -> tk.Entry | None:
        """The current target, or ``None`` if it no longer exists."""
        if self._target is not None and self._target.winfo_exists():
            return self._target
        self._target = None
        return None

    # ------------------------------------------------------------ inserts
    def insert_symbol(self, token: str) -> None:
        """Insert a mathtext ``token`` (e.g. ``\\alpha``) at the cursor."""
        cursor_back = 1 if token.endswith("{}") else 0
        self._insert(f"${token}$", cursor_back=cursor_back)

    def superscript(self) -> None:
        """Raise the selected text, or open an empty superscript group."""
        self._wrap_script("^")

    def subscript(self) -> None:
        """Lower the selected text, or open an empty subscript group."""
        self._wrap_script("_")

    def _wrap_script(self, kind: str) -> None:
        entry = self._active()
        if entry is None:
            return
        selected = self._pop_selection(entry)
        if selected:
            entry.insert("insert", f"${kind}{{{selected}}}$")
        else:
            entry.insert("insert", f"${kind}{{}}$")
            entry.icursor(entry.index("insert") - 2)  # land inside the braces
        entry.focus_set()

    def _insert(self, text: str, cursor_back: int = 0) -> None:
        entry = self._active()
        if entry is None:
            return
        self._pop_selection(entry)
        entry.insert("insert", text)
        if cursor_back:
            entry.icursor(entry.index("insert") - cursor_back)
        entry.focus_set()

    @staticmethod
    def _pop_selection(entry: tk.Entry) -> str:
        """Return and delete the current selection, if any."""
        if entry.selection_present():
            start = entry.index("sel.first")
            end = entry.index("sel.last")
            text = entry.get()[start:end]
            entry.delete("sel.first", "sel.last")
            return text
        return ""

    # ------------------------------------------------------------- toolbar
    def build_toolbar(self, parent: tk.Misc) -> ttk.Frame:
        """Create the compact insert toolbar (scripts + quick symbols)."""
        bar = ttk.Frame(parent, style="Panel.TFrame")
        bar.columnconfigure(99, weight=1)

        def chip(col: int, text: str, command, width: int = 3) -> None:
            tk.Button(
                bar,
                text=text,
                command=command,
                width=width,
                relief="flat",
                bg=self._colors["panel"],
                fg=self._colors["ink"],
                activebackground=self._colors["border_soft"],
                highlightbackground=self._colors["border"],
                highlightthickness=1,
                bd=0,
                font=("Segoe UI", 10),
                cursor="hand2",
            ).grid(row=0, column=col, padx=(0, 4), pady=2)

        chip(0, "x\u00b2", self.superscript)
        chip(1, "x\u2082", self.subscript)
        sep = tk.Frame(bar, bg=self._colors["border_soft"], width=1)
        sep.grid(row=0, column=2, sticky="ns", padx=(2, 6), pady=2)

        for i, (glyph, token) in enumerate(QUICK_SYMBOLS):
            chip(3 + i, glyph, lambda t=token: self.insert_symbol(t))

        tk.Button(
            bar,
            text="\u03a9 More\u2026",
            command=lambda: self.open_palette(parent),
            relief="flat",
            bg=self._colors["panel"],
            fg=self._colors["accent"],
            activebackground=self._colors["border_soft"],
            activeforeground=self._colors["accent"],
            highlightbackground=self._colors["border"],
            highlightthickness=1,
            bd=0,
            font=("Segoe UI Semibold", 9),
            cursor="hand2",
            padx=8,
        ).grid(row=0, column=3 + len(QUICK_SYMBOLS), padx=(6, 0), pady=2)

        return bar

    # ------------------------------------------------------------- palette
    def open_palette(self, parent: tk.Misc) -> None:
        """Open (or focus) the full categorised symbol palette window."""
        if self._palette is not None and self._palette.winfo_exists():
            self._palette.deiconify()
            self._palette.lift()
            return

        win = tk.Toplevel(parent)
        win.title("Insert symbol")
        win.configure(bg=self._colors["panel"])
        win.resizable(False, False)
        win.transient(parent.winfo_toplevel())
        self._palette = win

        wrap = tk.Frame(win, bg=self._colors["panel"])
        wrap.pack(fill="both", expand=True, padx=14, pady=12)

        tk.Label(
            wrap,
            text="Click a field, then a symbol. Select text first to make it "
                 "super/subscript.",
            bg=self._colors["panel"],
            fg=self._colors["muted"],
            font=("Segoe UI", 9),
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        for title, entries in SYMBOL_GROUPS:
            tk.Label(
                wrap,
                text=title.upper(),
                bg=self._colors["panel"],
                fg=self._colors["muted"],
                font=("Segoe UI Semibold", 8),
            ).pack(anchor="w", pady=(6, 4))
            grid = tk.Frame(wrap, bg=self._colors["panel"])
            grid.pack(anchor="w")
            cols = 12
            for i, (glyph, token) in enumerate(entries):
                tk.Button(
                    grid,
                    text=glyph,
                    width=2,
                    command=lambda t=token: self.insert_symbol(t),
                    relief="flat",
                    bg=self._colors["panel"],
                    fg=self._colors["ink"],
                    activebackground=self._colors["border_soft"],
                    highlightbackground=self._colors["border"],
                    highlightthickness=1,
                    bd=0,
                    font=("Segoe UI", 11),
                    cursor="hand2",
                ).grid(row=i // cols, column=i % cols, padx=2, pady=2)

        win.protocol("WM_DELETE_WINDOW", win.withdraw)
