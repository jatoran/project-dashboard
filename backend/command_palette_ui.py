"""
Ultra-Fast Command Palette using CustomTkinter.
Lightweight (~20MB), instant show/hide (<50ms).
"""
import customtkinter as ctk
import threading
import requests
from typing import List, Dict, Optional
import time
import ctypes
from ctypes import wintypes

# Direct launcher import for speed (bypasses HTTP)
from .services.launcher import Launcher
from .services.store import ProjectStore

# Windows API for forcing focus
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Singleton instances for direct calls
_launcher = Launcher()
_store = ProjectStore()


class CommandPaletteUI:
    """Fast, lightweight command palette window."""

    def __init__(self):
        # Data
        self.projects: List[Dict] = []
        self.filtered_projects: List[Dict] = []
        self.selected_index = 0

        # Window reference
        self.window = None
        self.search_entry = None
        self.results_frame = None

        # Item references for efficient updates
        self._item_frames: List[ctk.CTkFrame] = []
        self._item_buttons: List[ctk.CTkFrame] = []  # Button frames for each item
        self._item_dots: List[ctk.CTkLabel] = []  # Status dots for each item
        self._last_query = ""

        # Thread-safe flag
        self._initialized = False
        self._first_show = True  # Track first show for extra focus handling

        # Start Tkinter in its own thread with event loop
        self._ui_thread = threading.Thread(target=self._run_ui_thread, daemon=True)
        self._ui_thread.start()

        # Wait for UI to initialize
        timeout = 5
        start = time.time()
        while not self._initialized and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not self._initialized:
            raise RuntimeError("Failed to initialize command palette UI")

    def _run_ui_thread(self):
        """Run Tkinter in its own thread."""
        # Create main window
        self.window = ctk.CTk()
        self.window.title("Command Palette")

        # Window settings
        self.window.geometry("700x500")
        self.window.resizable(False, False)

        # Make it frameless and always on top
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)

        # Dark theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Setup UI
        self.setup_ui()

        # Instead of hiding, move it way off-screen
        # This keeps the window "visible" to Windows, ensuring focus works
        self.window.geometry("700x500-10000-10000")
        self.window.update()

        # Bind focus loss to hide
        self.window.bind('<FocusOut>', lambda e: self.hide())

        # Mark as initialized
        self._initialized = True

        # Load projects
        threading.Thread(target=self.load_projects, daemon=True).start()

        # Run the event loop (blocks this thread)
        self.window.mainloop()

    def setup_ui(self):
        """Create the UI elements."""
        # Main container with padding
        container = ctk.CTkFrame(self.window, fg_color="#0f172a", corner_radius=12)
        container.pack(fill="both", expand=True, padx=2, pady=2)

        # Search box
        search_frame = ctk.CTkFrame(container, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search projects...",
            height=50,
            font=("Segoe UI", 16),
            fg_color="#1e293b",
            border_color="#334155",
            border_width=2,
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind('<KeyRelease>', self.on_search)
        self.search_entry.bind('<Return>', self.on_enter)
        self.search_entry.bind('<Control-Return>', lambda e: self.on_enter(e, 'terminal') or "break")
        self.search_entry.bind('<Shift-Return>', lambda e: self.on_enter(e, 'explorer') or "break")
        self.search_entry.bind('<Escape>', lambda e: self.hide() or "break")
        self.search_entry.bind('<Up>', self.on_arrow_up)
        self.search_entry.bind('<Down>', self.on_arrow_down)

        # Results scrollable frame
        self.results_frame = ctk.CTkScrollableFrame(
            container,
            fg_color="#1e293b",
            height=320,
            corner_radius=8,
        )
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Hints
        hints = ctk.CTkLabel(
            container,
            text="↑↓ Navigate • Enter: Code • Ctrl+Enter: Terminal • Shift+Enter: Explorer • Esc: Close",
            font=("Segoe UI", 11),
            text_color="#64748b",
        )
        hints.pack(pady=(0, 15))

        # Initially show empty state
        self.show_empty_state("Loading projects...")

    def show_empty_state(self, message: str):
        """Show empty state message."""
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        label = ctk.CTkLabel(
            self.results_frame,
            text=message,
            font=("Segoe UI", 14),
            text_color="#64748b",
        )
        label.pack(pady=40)

    def load_projects(self):
        """Load projects from API, sorted by palette recency."""
        try:
            # Fetch with palette recency sorting
            response = requests.get(
                'http://localhost:37453/api/projects',
                params={'sort_by_palette': 'true'},
                timeout=2
            )
            response.raise_for_status()
            self.projects = response.json()
            self.filtered_projects = self.projects

            # Update UI in main thread
            self.window.after(0, self.render_results)
        except Exception as e:
            error_msg = "Failed to load projects. Is the server running?"
            self.window.after(0, lambda: self.show_empty_state(error_msg))

    def fuzzy_match(self, text: str, query: str) -> int:
        """Simple fuzzy matching with scoring."""
        text = text.lower()
        query = query.lower()

        if not query:
            return 1

        score = 0
        text_idx = 0
        consecutive = 0

        for char in query:
            # Find next occurrence
            found = False
            while text_idx < len(text):
                if text[text_idx] == char:
                    score += 1 + consecutive
                    consecutive += 1
                    found = True
                    text_idx += 1
                    break
                else:
                    consecutive = 0
                    text_idx += 1

            if not found:
                return 0

        return score

    def filter_projects(self, query: str):
        """Filter projects by fuzzy search."""
        if not query.strip():
            self.filtered_projects = self.projects
            return

        # Score each project
        scored = []
        for project in self.projects:
            name_score = self.fuzzy_match(project['name'], query)
            path_score = self.fuzzy_match(project['path'], query) * 0.8

            # Tech stack scoring
            tag_score = 0
            if project.get('tech_stack'):
                tag_score = max(
                    (self.fuzzy_match(tag, query) * 0.6 for tag in project['tech_stack']),
                    default=0
                )

            total_score = max(name_score, path_score, tag_score)

            if total_score > 0:
                scored.append((project, total_score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        self.filtered_projects = [item[0] for item in scored]

    def on_search(self, event=None):
        """Handle search input."""
        # Ignore arrow keys, modifiers, and navigation keys
        if event and event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return',
                                       'Escape', 'Shift_L', 'Shift_R',
                                       'Control_L', 'Control_R', 'Alt_L', 'Alt_R',
                                       'Home', 'End', 'Tab', 'Caps_Lock'):
            return

        # Check if query actually changed
        query = self.search_entry.get()
        if hasattr(self, '_last_query') and self._last_query == query:
            return  # No change, don't re-render

        self._last_query = query
        self.filter_projects(query)
        self.selected_index = 0
        self.render_results()

    def render_results(self):
        """Render filtered results."""
        # Clear existing
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        self._item_frames = []
        self._item_buttons = []
        self._item_dots = []

        if not self.filtered_projects:
            self.show_empty_state("No projects found")
            return

        # Render each project and track widgets
        for idx, project in enumerate(self.filtered_projects[:20]):  # Limit to 20
            widget = self.create_project_item(project, idx)
            self._item_frames.append(widget)

        # Scroll selected item into view
        if self.selected_index < len(self._item_frames):
            selected_widget = self._item_frames[self.selected_index]
            self.window.after(10, lambda: self._scroll_to_widget(selected_widget))

    def _scroll_to_widget(self, widget):
        """Scroll to make a widget visible in the scrollable frame."""
        try:
            # Get the canvas that backs the scrollable frame
            canvas = self.results_frame._parent_canvas

            # Get widget position
            widget.update_idletasks()
            bbox = canvas.bbox("all")

            # Calculate the widget's position
            widget_y = widget.winfo_y()
            canvas_height = canvas.winfo_height()

            # Scroll to show the widget
            if widget_y < 0:
                # Widget is above visible area
                canvas.yview_moveto(widget_y / bbox[3])
            elif widget_y + widget.winfo_height() > canvas_height:
                # Widget is below visible area
                canvas.yview_moveto((widget_y + widget.winfo_height() - canvas_height) / bbox[3])
        except:
            pass  # Ignore scrolling errors

    def create_project_item(self, project: Dict, idx: int) -> ctk.CTkFrame:
        """Create a project result item. Returns the frame widget."""
        is_selected = idx == self.selected_index

        # Container frame - only set border_color if selected
        frame_kwargs = {
            "master": self.results_frame,
            "fg_color": "#334155" if is_selected else "#1e293b",
            "corner_radius": 6,
            "height": 60,
        }
        if is_selected:
            frame_kwargs["border_width"] = 2
            frame_kwargs["border_color"] = "#6366f1"
        else:
            frame_kwargs["border_width"] = 0

        item_frame = ctk.CTkFrame(**frame_kwargs)
        item_frame.pack(fill="x", padx=5, pady=3)
        item_frame.pack_propagate(False)

        # Make clickable
        item_frame.bind('<Button-1>', lambda e, p=project: self.launch_project(p, 'vscode'))

        # Left side - icon and info
        left_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        # Project name
        name_label = ctk.CTkLabel(
            left_frame,
            text=project['name'],
            font=("Segoe UI Semibold", 14),
            text_color="#f1f5f9",
            anchor="w",
        )
        name_label.pack(anchor="w")
        name_label.bind('<Button-1>', lambda e, p=project: self.launch_project(p, 'vscode'))

        # Project path (truncated)
        path = project['path']
        if len(path) > 60:
            path = "..." + path[-57:]
        path_label = ctk.CTkLabel(
            left_frame,
            text=path,
            font=("Segoe UI", 11),
            text_color="#94a3b8",
            anchor="w",
        )
        path_label.pack(anchor="w")
        path_label.bind('<Button-1>', lambda e, p=project: self.launch_project(p, 'vscode'))

        # Right side - status and actions
        right_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=10, pady=8)

        # Status dot (always created, shown when not selected)
        status = project.get('frontend_status', 'offline')
        dot_color = "#22c55e" if status == 'online' else "#64748b"
        status_dot = ctk.CTkLabel(
            right_frame,
            text="●",
            font=("Segoe UI", 16),
            text_color=dot_color,
        )
        self._item_dots.append(status_dot)

        # Action buttons (always created, shown when selected)
        btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self._item_buttons.append(btn_frame)

        # Code button
        code_btn = ctk.CTkButton(
            btn_frame,
            text="Code",
            width=60,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#475569",
            hover_color="#6366f1",
            command=lambda p=project: self.launch_project(p, 'vscode')
        )
        code_btn.pack(side="left", padx=2)

        # Terminal button
        term_btn = ctk.CTkButton(
            btn_frame,
            text="Term",
            width=60,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#475569",
            hover_color="#6366f1",
            command=lambda p=project: self.launch_project(p, 'terminal')
        )
        term_btn.pack(side="left", padx=2)

        # Explorer button
        exp_btn = ctk.CTkButton(
            btn_frame,
            text="Files",
            width=60,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#475569",
            hover_color="#6366f1",
            command=lambda p=project: self.launch_project(p, 'explorer')
        )
        exp_btn.pack(side="left", padx=2)

        # Show buttons or dot based on selection
        if is_selected:
            btn_frame.pack(side="right")
        else:
            status_dot.pack()

        return item_frame

    def on_arrow_up(self, event):
        """Handle up arrow."""
        if self.selected_index > 0:
            old_index = self.selected_index
            self.selected_index -= 1
            self._update_selection(old_index, self.selected_index)
        return "break"  # Prevent event propagation

    def on_arrow_down(self, event):
        """Handle down arrow."""
        if self.selected_index < len(self.filtered_projects) - 1:
            old_index = self.selected_index
            self.selected_index += 1
            self._update_selection(old_index, self.selected_index)
        return "break"  # Prevent event propagation

    def _update_selection(self, old_index: int, new_index: int):
        """Update only the selection styling without re-rendering everything."""
        if not self._item_frames:
            return

        # Update old selected item to unselected style
        if 0 <= old_index < len(self._item_frames):
            old_frame = self._item_frames[old_index]
            old_frame.configure(fg_color="#1e293b", border_width=0)

            # Hide buttons, show dot
            if old_index < len(self._item_buttons):
                self._item_buttons[old_index].pack_forget()
            if old_index < len(self._item_dots):
                self._item_dots[old_index].pack()

        # Update new selected item to selected style
        if 0 <= new_index < len(self._item_frames):
            new_frame = self._item_frames[new_index]
            new_frame.configure(fg_color="#334155", border_width=2, border_color="#6366f1")

            # Show buttons, hide dot
            if new_index < len(self._item_dots):
                self._item_dots[new_index].pack_forget()
            if new_index < len(self._item_buttons):
                self._item_buttons[new_index].pack(side="right")

            # Scroll into view
            self.window.after(10, lambda: self._scroll_to_widget(new_frame))

    def on_enter(self, event, launch_type='vscode'):
        """Handle Enter key."""
        if self.filtered_projects and self.selected_index < len(self.filtered_projects):
            project = self.filtered_projects[self.selected_index]
            self.launch_project(project, launch_type)
        return "break"  # Prevent event propagation

    def launch_project(self, project: Dict, launch_type: str):
        """Launch a project."""
        # Hide immediately for instant feedback
        self.hide()

        # Launch in background thread (don't block UI)
        def do_launch():
            try:
                # Launch directly (no HTTP overhead)
                _launcher.launch(project['path'], launch_type)
                # Mark as recently opened for recency sorting
                _store.mark_palette_open(project['path'])
            except Exception as e:
                print(f"Launch failed: {e}")

        threading.Thread(target=do_launch, daemon=True).start()

    def show(self):
        """Show the command palette (instant!). Thread-safe."""
        if not self.window:
            return

        # Schedule on Tkinter thread
        self.window.after(0, self._do_show)

    def _do_show(self):
        """Internal show method (runs on Tkinter thread)."""
        # Center on screen
        self.center_window()

        # Show window
        self.window.deiconify()

        # Force window to front and focus
        self.window.lift()
        self.window.focus_force()
        self.window.attributes('-topmost', True)
        self.window.attributes('-topmost', False)  # Reset to allow other windows on top
        self.window.attributes('-topmost', True)   # But keep on top

        # First show needs extra time for Windows to fully initialize
        if self._first_show:
            self._first_show = False
            # Multiple focus attempts with delays for first show
            self.window.after(50, self._focus_search)
            self.window.after(100, self._focus_search)
            self.window.after(150, self._focus_search)
        else:
            # Subsequent shows can be faster
            self.window.after(10, self._focus_search)

        # Reload projects
        threading.Thread(target=self.load_projects, daemon=True).start()

    def _force_window_focus(self):
        """Force window focus using Windows API."""
        try:
            # Get the Tkinter window handle
            hwnd = user32.GetParent(self.window.winfo_id())

            # Get current foreground window's thread
            foreground_hwnd = user32.GetForegroundWindow()
            foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)

            # Get our thread
            our_thread = kernel32.GetCurrentThreadId()

            # Attach our thread to the foreground thread's input
            # This tricks Windows into thinking we're the foreground app
            if foreground_thread != our_thread:
                user32.AttachThreadInput(foreground_thread, our_thread, True)

            # Now we can set foreground
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.SetFocus(hwnd)

            # Detach threads
            if foreground_thread != our_thread:
                user32.AttachThreadInput(foreground_thread, our_thread, False)

        except Exception as e:
            print(f"Force focus failed: {e}")

    def _focus_search(self):
        """Focus the search entry (delayed for reliability)."""
        # Use Windows API to force window focus
        self._force_window_focus()

        # Then focus the search entry with Tkinter
        self.search_entry.focus_force()
        self.search_entry.select_range(0, 'end')
        self.search_entry.icursor('end')

    def hide(self):
        """Hide the command palette (instant!). Thread-safe."""
        if not self.window:
            return

        # Schedule on Tkinter thread
        self.window.after(0, self._do_hide)

    def _do_hide(self):
        """Internal hide method (runs on Tkinter thread)."""
        # Move off-screen instead of withdrawing
        # This keeps the window "active" in Windows, ensuring focus works next time
        self.window.geometry("700x500-10000-10000")

        # Clear search
        self.search_entry.delete(0, 'end')
        self.selected_index = 0

    def center_window(self):
        """Center window on screen."""
        self.window.update_idletasks()

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        x = (screen_width - 700) // 2
        y = (screen_height - 500) // 3  # Upper third looks better

        self.window.geometry(f"700x500+{x}+{y}")

    def run(self):
        """Run the main loop (for standalone testing)."""
        self.show()
        self.window.mainloop()


def main():
    """Standalone test."""
    palette = CommandPaletteUI()
    palette.run()


if __name__ == "__main__":
    main()
