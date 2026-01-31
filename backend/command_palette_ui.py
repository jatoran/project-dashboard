"""
Ultra-Fast Command Palette using CustomTkinter.
Optimized for instant show/hide and smooth typing.
"""
import customtkinter as ctk
import threading
from typing import List, Dict, Optional
import time
import ctypes

# Direct store import for speed (bypasses HTTP)
from .services.launcher import Launcher
from .services.store import ProjectStore

# Windows API for forcing focus
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Singleton instances for direct calls
_launcher = Launcher()
_store = ProjectStore()

# How many items to show max (fits in 380px height with 56px items + padding)
MAX_VISIBLE_ITEMS = 6


class ProjectItem(ctk.CTkFrame):
    """Reusable project item widget."""

    def __init__(self, master, on_launch):
        super().__init__(master, fg_color="#1e293b", corner_radius=8, height=56)
        self.pack_propagate(False)

        self._on_launch = on_launch
        self._project = None
        self._selected = False

        # Simple layout: name on left, path below
        self._name_label = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI Semibold", 15),
            text_color="#f1f5f9",
            anchor="w",
        )
        self._name_label.place(x=14, y=6)

        self._path_label = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 11),
            text_color="#64748b",
            anchor="w",
        )
        self._path_label.place(x=14, y=30)

        # Buttons frame (shown when selected)
        self._btn_frame = ctk.CTkFrame(self, fg_color="transparent")

        btn_style = {"width": 65, "height": 26, "font": ("Segoe UI", 10),
                     "fg_color": "#475569", "hover_color": "#6366f1"}

        self._btn_code = ctk.CTkButton(self._btn_frame, text="Code",
            command=lambda: self._do_launch('vscode'), **btn_style)
        self._btn_code.pack(side="left", padx=2)

        self._btn_term = ctk.CTkButton(self._btn_frame, text="Terminal",
            command=lambda: self._do_launch('terminal'), **btn_style)
        self._btn_term.pack(side="left", padx=2)

        self._btn_folder = ctk.CTkButton(self._btn_frame, text="Folder",
            command=lambda: self._do_launch('explorer'), **btn_style)
        self._btn_folder.pack(side="left", padx=2)

        self._btn_claude = ctk.CTkButton(self._btn_frame, text="Claude",
            command=lambda: self._do_launch('claude'), **btn_style)
        self._btn_claude.pack(side="left", padx=2)

        self._btn_codex = ctk.CTkButton(self._btn_frame, text="Codex",
            command=lambda: self._do_launch('codex'), **btn_style)
        self._btn_codex.pack(side="left", padx=2)

        self._btn_opencode = ctk.CTkButton(self._btn_frame, text="OpenCode",
            command=lambda: self._do_launch('opencode'), **btn_style)
        self._btn_opencode.pack(side="left", padx=2)

        # Bind clicks
        self.bind('<Button-1>', self._on_click)
        self._name_label.bind('<Button-1>', self._on_click)
        self._path_label.bind('<Button-1>', self._on_click)

        # Right-click for terminal
        self.bind('<Button-3>', self._on_right_click)
        self._name_label.bind('<Button-3>', self._on_right_click)
        self._path_label.bind('<Button-3>', self._on_right_click)

    def _do_launch(self, launch_type: str):
        if self._project:
            self._on_launch(self._project, launch_type)

    def set_project(self, project: Dict):
        """Update this item with project data."""
        self._project = project
        self._name_label.configure(text=project['name'])

        # Truncate path
        path = project['path']
        if len(path) > 65:
            path = "..." + path[-62:]
        self._path_label.configure(text=path)

    def set_selected(self, selected: bool):
        """Update selection state."""
        self._selected = selected
        if selected:
            self.configure(fg_color="#334155", border_width=2, border_color="#6366f1")
            self._btn_frame.place(relx=1.0, y=14, anchor="ne", x=-10)
        else:
            self.configure(fg_color="#1e293b", border_width=0)
            self._btn_frame.place_forget()

    def _on_click(self, event=None):
        if self._project:
            self._on_launch(self._project, 'vscode')

    def _on_right_click(self, event=None):
        if self._project:
            self._on_launch(self._project, 'terminal')


class CommandPaletteUI:
    """Fast, lightweight command palette window."""

    def __init__(self):
        # Data
        self.projects: List[Dict] = []
        self.filtered_projects: List[Dict] = []
        self.selected_index = 0
        self._last_query = ""
        self._projects_loaded = False

        # Window reference
        self.window = None
        self.search_entry = None
        self.results_frame = None

        # Pre-created item widgets for reuse
        self._items: List[ProjectItem] = []

        # Thread-safe flag
        self._initialized = False
        self._first_show = True

        # Start Tkinter in its own thread
        self._ui_thread = threading.Thread(target=self._run_ui_thread, daemon=True)
        self._ui_thread.start()

        # Wait for UI to initialize
        timeout = 5
        start = time.time()
        while not self._initialized and (time.time() - start) < timeout:
            time.sleep(0.05)

        if not self._initialized:
            raise RuntimeError("Failed to initialize command palette UI")

    def _run_ui_thread(self):
        """Run Tkinter in its own thread."""
        self.window = ctk.CTk()
        self.window.title("Command Palette")
        self.window.geometry("750x550")
        self.window.resizable(False, False)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._setup_ui()

        # Start off-screen
        self.window.geometry("750x550-10000-10000")
        self.window.update()

        # Bind focus loss
        self.window.bind('<FocusOut>', lambda e: self._schedule_hide_check())

        self._initialized = True

        # Pre-load projects
        self._load_projects_sync()

        self.window.mainloop()

    def _setup_ui(self):
        """Create the UI elements."""
        # Main container
        container = ctk.CTkFrame(self.window, fg_color="#0f172a", corner_radius=10)
        container.pack(fill="both", expand=True, padx=2, pady=2)

        # Search box
        self.search_entry = ctk.CTkEntry(
            container,
            placeholder_text="Search projects...",
            height=50,
            font=("Segoe UI", 17),
            fg_color="#1e293b",
            border_color="#334155",
            border_width=2,
        )
        self.search_entry.pack(fill="x", padx=20, pady=(20, 12))

        # Bind keys
        self.search_entry.bind('<KeyRelease>', self._on_key)
        self.search_entry.bind('<Return>', lambda e: self._launch_selected('vscode'))
        self.search_entry.bind('<Control-Return>', lambda e: self._launch_selected('terminal'))
        self.search_entry.bind('<Shift-Return>', lambda e: self._launch_selected('explorer'))
        self.search_entry.bind('<Control-c>', lambda e: self._launch_selected('claude') or "break")
        self.search_entry.bind('<Control-x>', lambda e: self._launch_selected('codex') or "break")
        self.search_entry.bind('<Control-z>', lambda e: self._launch_selected('opencode') or "break")
        self.search_entry.bind('<Escape>', lambda e: self.hide())
        self.search_entry.bind('<Up>', self._on_up)
        self.search_entry.bind('<Down>', self._on_down)

        # Results frame with fixed height so it doesn't cover hints
        self.results_frame = ctk.CTkFrame(container, fg_color="transparent", height=380)
        self.results_frame.pack(fill="x", padx=20, pady=(0, 8))
        self.results_frame.pack_propagate(False)

        # Pre-create item widgets
        for _ in range(MAX_VISIBLE_ITEMS):
            item = ProjectItem(self.results_frame, self._launch_project)
            self._items.append(item)

        # Hints frame
        hints_frame = ctk.CTkFrame(container, fg_color="transparent")
        hints_frame.pack(pady=(0, 15))

        hint_style = {"font": ("Segoe UI", 11), "text_color": "#64748b"}
        key_style = {"font": ("Consolas", 11), "text_color": "#94a3b8"}

        # Row 1: Basic actions
        row1 = ctk.CTkFrame(hints_frame, fg_color="transparent")
        row1.pack()
        ctk.CTkLabel(row1, text="Enter", **key_style).pack(side="left")
        ctk.CTkLabel(row1, text=" Code   ", **hint_style).pack(side="left")
        ctk.CTkLabel(row1, text="Ctrl+Enter", **key_style).pack(side="left")
        ctk.CTkLabel(row1, text=" Terminal   ", **hint_style).pack(side="left")
        ctk.CTkLabel(row1, text="Shift+Enter", **key_style).pack(side="left")
        ctk.CTkLabel(row1, text=" Folder   ", **hint_style).pack(side="left")
        ctk.CTkLabel(row1, text="Esc", **key_style).pack(side="left")
        ctk.CTkLabel(row1, text=" Close", **hint_style).pack(side="left")

        # Row 2: AI tools
        row2 = ctk.CTkFrame(hints_frame, fg_color="transparent")
        row2.pack(pady=(4, 0))
        ctk.CTkLabel(row2, text="Ctrl+C", **key_style).pack(side="left")
        ctk.CTkLabel(row2, text=" Claude   ", **hint_style).pack(side="left")
        ctk.CTkLabel(row2, text="Ctrl+X", **key_style).pack(side="left")
        ctk.CTkLabel(row2, text=" Codex   ", **hint_style).pack(side="left")
        ctk.CTkLabel(row2, text="Ctrl+Z", **key_style).pack(side="left")
        ctk.CTkLabel(row2, text=" OpenCode", **hint_style).pack(side="left")

    def _load_projects_sync(self):
        """Load projects directly from store (fast, no HTTP)."""
        try:
            projects = _store.get_all(sort_by_palette_recency=True)
            self.projects = [p.dict() for p in projects]
            self.filtered_projects = self.projects
            self._projects_loaded = True

            # Update UI
            if self.window:
                self.window.after(0, self._render)
        except Exception as e:
            print(f"Failed to load projects: {e}")

    def _on_key(self, event):
        """Handle key press in search."""
        # Ignore navigation keys
        if event.keysym in ('Up', 'Down', 'Return', 'Escape', 'Shift_L', 'Shift_R',
                           'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Tab'):
            return "break"

        query = self.search_entry.get()
        if query == self._last_query:
            return

        self._last_query = query
        self._filter(query)
        self.selected_index = 0
        self._render()

    def _filter(self, query: str):
        """Filter projects by query."""
        if not query.strip():
            self.filtered_projects = self.projects
            return

        query_lower = query.lower()
        scored = []

        for project in self.projects:
            name = project['name'].lower()

            # Exact prefix match scores highest
            if name.startswith(query_lower):
                scored.append((project, 100 + len(query)))
            # Contains match
            elif query_lower in name:
                scored.append((project, 50))
            # Fuzzy match on name
            elif self._fuzzy_match(name, query_lower):
                scored.append((project, 25))
            # Path contains
            elif query_lower in project['path'].lower():
                scored.append((project, 10))

        scored.sort(key=lambda x: x[1], reverse=True)
        self.filtered_projects = [p for p, _ in scored]

    def _fuzzy_match(self, text: str, query: str) -> bool:
        """Simple fuzzy match - all query chars must appear in order."""
        text_idx = 0
        for char in query:
            found = False
            while text_idx < len(text):
                if text[text_idx] == char:
                    found = True
                    text_idx += 1
                    break
                text_idx += 1
            if not found:
                return False
        return True

    def _render(self):
        """Update visible items (no widget destruction)."""
        # Hide all items first
        for item in self._items:
            item.pack_forget()

        # Show items for filtered projects
        for i, project in enumerate(self.filtered_projects[:MAX_VISIBLE_ITEMS]):
            item = self._items[i]
            item.set_project(project)
            item.set_selected(i == self.selected_index)
            item.pack(fill="x", pady=2)

    def _on_up(self, event):
        """Move selection up."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._update_selection()
        return "break"

    def _on_down(self, event):
        """Move selection down."""
        max_idx = min(len(self.filtered_projects), MAX_VISIBLE_ITEMS) - 1
        if self.selected_index < max_idx:
            self.selected_index += 1
            self._update_selection()
        return "break"

    def _update_selection(self):
        """Update selection highlighting without full re-render."""
        for i, item in enumerate(self._items):
            if i < len(self.filtered_projects):
                item.set_selected(i == self.selected_index)

    def _launch_selected(self, launch_type: str):
        """Launch the selected project."""
        if self.filtered_projects and self.selected_index < len(self.filtered_projects):
            project = self.filtered_projects[self.selected_index]
            self._launch_project(project, launch_type)
        return "break"

    def _launch_project(self, project: Dict, launch_type: str):
        """Launch a project and hide palette."""
        self.hide()

        def do_launch():
            try:
                _launcher.launch(project['path'], launch_type)
                _store.mark_palette_open(project['path'])
            except Exception as e:
                print(f"Launch failed: {e}")

        threading.Thread(target=do_launch, daemon=True).start()

    def _schedule_hide_check(self):
        """Check if we should hide after focus loss."""
        # Small delay to handle focus transitions
        self.window.after(100, self._check_focus)

    def _check_focus(self):
        """Hide if window doesn't have focus."""
        try:
            if not self.window.focus_get():
                self.hide()
        except:
            pass

    def show(self):
        """Show the command palette."""
        if not self.window:
            return
        self.window.after(0, self._do_show)

    def _do_show(self):
        """Internal show."""
        # Refresh projects in background (non-blocking)
        threading.Thread(target=self._load_projects_sync, daemon=True).start()

        # Reset state
        self.selected_index = 0
        self._last_query = ""
        self.filtered_projects = self.projects

        # Center and show
        self._center_window()
        self.window.deiconify()
        self.window.lift()
        self.window.attributes('-topmost', True)

        # Render current projects immediately
        self._render()

        # Focus
        if self._first_show:
            self._first_show = False
            self.window.after(50, self._focus_search)
            self.window.after(100, self._focus_search)
        else:
            self.window.after(10, self._focus_search)

    def _focus_search(self):
        """Focus the search entry."""
        try:
            hwnd = user32.GetParent(self.window.winfo_id())
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
            our_thread = kernel32.GetCurrentThreadId()

            if fg_thread != our_thread:
                user32.AttachThreadInput(fg_thread, our_thread, True)

            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)

            if fg_thread != our_thread:
                user32.AttachThreadInput(fg_thread, our_thread, False)
        except:
            pass

        self.search_entry.focus_force()
        self.search_entry.delete(0, 'end')
        self.search_entry.icursor(0)

    def hide(self):
        """Hide the command palette."""
        if not self.window:
            return
        self.window.after(0, self._do_hide)

    def _do_hide(self):
        """Internal hide."""
        self.window.geometry("750x550-10000-10000")
        self.search_entry.delete(0, 'end')
        self._last_query = ""

    def _center_window(self):
        """Center window on screen."""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 750) // 2
        y = (self.window.winfo_screenheight() - 550) // 3
        self.window.geometry(f"750x550+{x}+{y}")

    def run(self):
        """Run standalone."""
        self.show()
        self.window.mainloop()


def main():
    """Standalone test."""
    palette = CommandPaletteUI()
    palette.run()


if __name__ == "__main__":
    main()
