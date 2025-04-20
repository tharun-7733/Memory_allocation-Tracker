import tkinter as tk
from tkinter import ttk, messagebox, font
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
import psutil
import threading
import time
import platform
import queue
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Union
import random
from datetime import datetime

# Constants
REFRESH_RATES = [5000, 10000, 15000, 20000]  # in milliseconds
DEFAULT_REFRESH_RATE = 5000
MAX_DATA_POINTS = 60  # Maximum number of data points to display in time-series graphs
COLORS = {
    'background': '#f5f5f5',
    'sidebar': '#2c3e50',
    'sidebar_hover': '#34495e',
    'sidebar_active': '#1abc9c',
    'text_light': '#ecf0f1',
    'text_dark': '#2c3e50',
    'accent': '#3498db',
    'warning': '#e74c3c',
    'success': '#2ecc71',
    'chart_colors': ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#34495e', '#95a5a6'],
    'memory_segments': {
        'code': '#3498db',    # Blue
        'data': '#e74c3c',    # Red
        'heap': '#f39c12',    # Yellow
        'stack': '#2ecc71',   # Green
        'shared': '#9b59b6',  # Purple
    },
    'page_states': {
        'used': '#3498db',     # Blue
        'free': '#2ecc71',     # Green
        'shared': '#9b59b6',   # Purple
        'swapped': '#e74c3c',  # Red
    }
}

class MemoryVisualizerApp:
    """Main application class for Memory Visualizer."""
    
    def __init__(self, root: tk.Tk):
        """Initialize the application.
        
        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("Memory Visualizer")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        self.configure_styles()
        
        # Data structures
        self.data_queue = queue.Queue()
        self.current_view = tk.StringVar(value="Memory Dashboard")
        self.refresh_rate = tk.IntVar(value=DEFAULT_REFRESH_RATE)
        self.running = True
        self.page_size = tk.IntVar(value=4)  # Default page size in KB
        
        # Time series data
        self.time_labels = []
        self.cpu_data = []
        self.ram_used_data = []
        self.ram_available_data = []
        self.ram_cached_data = []
        
        # Create main layout
        self.create_layout()
        
        # Start data collection thread
        self.data_thread = threading.Thread(target=self.collect_data, daemon=True)
        self.data_thread.start()
        
        # Schedule first update
        self.root.after(100, self.process_data_queue)
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def configure_styles(self):
        """Configure ttk styles for the application."""
        self.style = ttk.Style()
        
        # Configure fonts
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        self.root.option_add("*Font", default_font)
        
        # Configure ttk styles
        self.style.configure("TFrame", background=COLORS['background'])
        self.style.configure("TLabel", background=COLORS['background'], foreground=COLORS['text_dark'])
        self.style.configure("TButton", background=COLORS['accent'], foreground=COLORS['text_light'])
        
        # Sidebar button style
        self.style.configure(
            "Sidebar.TButton", 
            background=COLORS['sidebar'],
            foreground=COLORS['text_light'],
            borderwidth=0,
            font=("Segoe UI", 11),
            padding=10
        )
        
        self.style.map(
            "Sidebar.TButton",
            background=[('active', COLORS['sidebar_hover']), ('selected', COLORS['sidebar_active'])],
            foreground=[('active', COLORS['text_light']), ('selected', COLORS['text_light'])]
        )
        
        # System info panel style
        self.style.configure(
            "SysInfo.TFrame", 
            background="#ffffff",
            relief="raised",
            borderwidth=1
        )
        
        self.style.configure(
            "SysInfo.TLabel",
            background="#ffffff",
            foreground=COLORS['text_light'],
            padding=2
        )
        
        # Treeview style (for process table)
        self.style.configure(
            "Treeview", 
            background="#ffffff",
            foreground=COLORS['text_dark'],
            rowheight=25,
            fieldbackground="#ffffff"
        )
        self.style.map(
            "Treeview",
            background=[('selected', COLORS['accent'])],
            foreground=[('selected', COLORS['text_light'])]
        )
        
        # Treeview heading style
        self.style.configure(
            "Treeview.Heading",
            background=COLORS['sidebar'],   
            foreground=COLORS['text_light'],
            padding=5,
            font=("Segoe UI", 10, "bold")
        )
    
    def create_layout(self):
        """Create the main application layout."""
        # Main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create content area
        self.content_frame = ttk.Frame(self.main_container, style="TFrame")
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create system info panel
        self.create_system_info_panel()
        
        # Create content views
        self.create_dashboard_view()
        self.create_process_memory_view()
        self.create_segmentation_view()
        self.create_paging_view()
        
        # Show default view
        self.show_view(self.current_view.get())
    
    def create_sidebar(self):
        """Create the sidebar navigation panel."""
        # Sidebar container
        self.sidebar = ttk.Frame(self.main_container, width=200, style="TFrame")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        self.sidebar.pack_propagate(False)  # Prevent the sidebar from shrinking
        
        # Sidebar background
        sidebar_bg = tk.Canvas(self.sidebar, background=COLORS['sidebar'], highlightthickness=0)
        sidebar_bg.place(x=0, y=0, relwidth=1, relheight=1)
        
        # App title
        title_frame = ttk.Frame(self.sidebar, style="TFrame")
        title_frame.pack(fill=tk.X, padx=10, pady=(20, 30))
        
        title_label = ttk.Label(
            title_frame, 
            text="Memory Visualizer", 
            foreground=COLORS['text_light'],
            background=COLORS['sidebar'],
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(anchor=tk.W)
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_options = [
            "Memory Dashboard",
            "Process Memory",
            "Segmentation",
            "Paging System"
        ]
        
        for option in nav_options:
            btn = ttk.Button(
                self.sidebar,
                text=option,
                style="Sidebar.TButton",
                command=lambda opt=option: self.show_view(opt)
            )
            btn.pack(fill=tk.X, padx=0, pady=1)
            self.nav_buttons[option] = btn
        
        # Refresh rate control
        refresh_frame = ttk.Frame(self.sidebar, style="TFrame")
        refresh_frame.pack(fill=tk.X, padx=10, pady=(50, 10), side=tk.BOTTOM)
        
        refresh_label = ttk.Label(
            refresh_frame, 
            text="Refresh Rate:", 
            foreground=COLORS['text_light'],
            background=COLORS['sidebar']
        )
        refresh_label.pack(anchor=tk.W, pady=(0, 5))
        
        refresh_combo = ttk.Combobox(
            refresh_frame,
            textvariable=self.refresh_rate,
            values=[f"{rate/1000}s" for rate in REFRESH_RATES],
            state="readonly",
            width=10
        )
        refresh_combo.pack(fill=tk.X)
        refresh_combo.current(REFRESH_RATES.index(DEFAULT_REFRESH_RATE))
        refresh_combo.bind("<<ComboboxSelected>>", self.on_refresh_rate_change)
    
    def create_system_info_panel(self):
        """Create the system information panel."""
        self.sysinfo_frame = ttk.Frame(self.content_frame, style="SysInfo.TFrame")
        self.sysinfo_frame.pack(fill=tk.X, pady=(0, 10))
        
        # System info grid
        info_grid = ttk.Frame(self.sysinfo_frame, style="SysInfo.TFrame")
        info_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # System name and OS info
        system_name = platform.node()
        os_info = f"{platform.system()} {platform.release()}"
        
        # Create info labels
        labels = [
            ("System:", system_name),
            ("OS:", os_info),
            ("CPU:", ""),
            ("Memory:", ""),
            ("Disk:", "")
        ]
        
        # Create and place labels in grid
        self.info_labels = {}
        for i, (label_text, value_text) in enumerate(labels):
            label = ttk.Label(
                info_grid, 
                text=label_text, 
                style="SysInfo.TLabel",
                font=("Segoe UI", 9, "bold")
            )
            label.grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            
            value = ttk.Label(
                info_grid, 
                text=value_text, 
                style="SysInfo.TLabel"
            )
            value.grid(row=i, column=1, sticky=tk.W, padx=0, pady=2)
            
            self.info_labels[label_text] = value
    
    def create_dashboard_view(self):
        """Create the Memory Dashboard view."""
        self.dashboard_frame = ttk.Frame(self.content_frame)
        
        # Create 2x2 grid for charts
        self.dashboard_grid = ttk.Frame(self.dashboard_frame)
        self.dashboard_grid.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid layout
        self.dashboard_grid.columnconfigure(0, weight=1)
        self.dashboard_grid.columnconfigure(1, weight=1)
        self.dashboard_grid.rowconfigure(0, weight=1)
        self.dashboard_grid.rowconfigure(1, weight=1)
        
        # Create figures for each chart
        self.cpu_fig = Figure(figsize=(5, 4), dpi=100)
        self.ram_fig = Figure(figsize=(5, 4), dpi=100)
        self.cache_fig = Figure(figsize=(5, 4), dpi=100)
        self.disk_fig = Figure(figsize=(5, 4), dpi=100)
        
        # Style the figures
        for fig in [self.cpu_fig, self.ram_fig, self.cache_fig, self.disk_fig]:
            fig.patch.set_facecolor(COLORS['background'])
        
        # Create subplots
        self.cpu_ax = self.cpu_fig.add_subplot(111)
        self.ram_ax = self.ram_fig.add_subplot(111)
        self.cache_ax = self.cache_fig.add_subplot(111)
        self.disk_ax = self.disk_fig.add_subplot(111)
        
        # Create canvas for each chart
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_fig, master=self.dashboard_grid)
        self.ram_canvas = FigureCanvasTkAgg(self.ram_fig, master=self.dashboard_grid)
        self.cache_canvas = FigureCanvasTkAgg(self.cache_fig, master=self.dashboard_grid)
        self.disk_canvas = FigureCanvasTkAgg(self.disk_fig, master=self.dashboard_grid)
        
        # Place canvases in grid
        self.cpu_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.ram_canvas.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.cache_canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.disk_canvas.get_tk_widget().grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        # Initialize charts
        self.init_dashboard_charts()
    
    def init_dashboard_charts(self):
        """Initialize the dashboard charts with empty data."""
        # CPU Usage chart
        self.cpu_ax.clear()
        self.cpu_ax.set_title("CPU Usage", fontsize=12, fontweight='bold')
        self.cpu_ax.set_xlabel("Time", fontsize=10)
        self.cpu_ax.set_ylabel("Usage (%)", fontsize=10)
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.grid(True, linestyle='--', alpha=0.7)
        self.cpu_line, = self.cpu_ax.plot([], [], lw=2, color=COLORS['chart_colors'][0])
        self.cpu_fig.tight_layout()
        
        # RAM Allocation chart
        self.ram_ax.clear()
        self.ram_ax.set_title("RAM Allocation", fontsize=12, fontweight='bold')
        self.ram_ax.set_xlabel("Time", fontsize=10)
        self.ram_ax.set_ylabel("Memory (GB)", fontsize=10)
        self.ram_ax.grid(True, linestyle='--', alpha=0.7)
        self.ram_fig.tight_layout()
        
        # Cache Memory chart
        self.cache_ax.clear()
        self.cache_ax.set_title("Cache Memory Distribution", fontsize=12, fontweight='bold')
        self.cache_ax.axis('equal')
        self.cache_fig.tight_layout()
        
        # Disk Usage chart
        self.disk_ax.clear()
        self.disk_ax.set_title("Disk Usage", fontsize=12, fontweight='bold')
        self.disk_ax.axis('equal')
        self.disk_fig.tight_layout()
    
    def create_process_memory_view(self):
        """Create the Process Memory view."""
        self.process_frame = ttk.Frame(self.content_frame)
        
        # Create process table
        table_frame = ttk.Frame(self.process_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create treeview for process list
        self.process_tree = ttk.Treeview(
            table_frame,
            columns=("pid", "name", "memory", "threads"),
            show="headings",
            selectmode="browse"
        )
        
        # Define columns
        self.process_tree.heading("pid", text="Process ID")
        self.process_tree.heading("name", text="Process Name")
        self.process_tree.heading("memory", text="Memory Usage (MB)")
        self.process_tree.heading("threads", text="Thread Count")
        
        self.process_tree.column("pid", width=100, anchor=tk.CENTER)
        self.process_tree.column("name", width=250, anchor=tk.W)
        self.process_tree.column("memory", width=150, anchor=tk.CENTER)
        self.process_tree.column("threads", width=150, anchor=tk.CENTER)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.process_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.process_tree.bind("<<TreeviewSelect>>", self.on_process_select)
        
        # Create memory map visualization
        self.memory_map_frame = ttk.Frame(self.process_frame)
        self.memory_map_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Memory map figure
        self.memory_map_fig = Figure(figsize=(8, 4), dpi=100)
        self.memory_map_fig.patch.set_facecolor(COLORS['background'])
        self.memory_map_ax = self.memory_map_fig.add_subplot(111)
        
        # Memory map canvas
        self.memory_map_canvas = FigureCanvasTkAgg(self.memory_map_fig, master=self.memory_map_frame)
        self.memory_map_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Memory map toolbar
        self.memory_map_toolbar_frame = ttk.Frame(self.memory_map_frame)
        self.memory_map_toolbar_frame.pack(fill=tk.X)
        self.memory_map_toolbar = NavigationToolbar2Tk(self.memory_map_canvas, self.memory_map_toolbar_frame)
        self.memory_map_toolbar.update()
        
        # Initialize memory map
        self.init_memory_map()
    
    def init_memory_map(self):
        """Initialize the memory map visualization."""
        self.memory_map_ax.clear()
        self.memory_map_ax.set_title("Memory Map", fontsize=12, fontweight='bold')
        self.memory_map_ax.set_xlabel("Memory Address Space", fontsize=10)
        self.memory_map_ax.set_ylabel("", fontsize=10)
        self.memory_map_ax.set_yticks([])
        
        # Create legend
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['code'], label='Code'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['data'], label='Data'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['heap'], label='Heap'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['stack'], label='Stack'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['shared'], label='Shared')
        ]
        self.memory_map_ax.legend(handles=legend_elements, loc='upper center', 
                                 bbox_to_anchor=(0.5, -0.05), ncol=5)
        
        self.memory_map_ax.set_xlim(0, 100)
        self.memory_map_ax.set_ylim(0, 1)
        self.memory_map_ax.text(50, 0.5, "Select a process to view memory map", 
                               ha='center', va='center', fontsize=12)
        
        self.memory_map_fig.tight_layout()
        self.memory_map_canvas.draw()
    
    def create_segmentation_view(self):
        """Create the Segmentation view."""
        self.segmentation_frame = ttk.Frame(self.content_frame)
        
        # Create segmentation visualization
        self.seg_fig = Figure(figsize=(10, 6), dpi=100)
        self.seg_fig.patch.set_facecolor(COLORS['background'])
        self.seg_ax = self.seg_fig.add_subplot(111)
        
        # Segmentation canvas
        self.seg_canvas = FigureCanvasTkAgg(self.seg_fig, master=self.segmentation_frame)
        self.seg_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Segmentation toolbar
        self.seg_toolbar_frame = ttk.Frame(self.segmentation_frame)
        self.seg_toolbar_frame.pack(fill=tk.X)
        self.seg_toolbar = NavigationToolbar2Tk(self.seg_canvas, self.seg_toolbar_frame)
        self.seg_toolbar.update()
        
        # Initialize segmentation visualization
        self.init_segmentation_view()
    
    def init_segmentation_view(self):
        """Initialize the segmentation visualization."""
        self.seg_ax.clear()
        self.seg_ax.set_title("Memory Segmentation", fontsize=14, fontweight='bold')
        self.seg_ax.set_xlabel("Memory Address Space", fontsize=12)
        self.seg_ax.set_yticks([])
        
        # Create legend
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['code'], label='Code'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['data'], label='Data'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['heap'], label='Heap'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['stack'], label='Stack'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['shared'], label='Shared')
        ]
        self.seg_ax.legend(handles=legend_elements, loc='upper center', 
                          bbox_to_anchor=(0.5, -0.05), ncol=5)
        
        self.seg_fig.tight_layout()
        self.seg_canvas.draw()
    
    def create_paging_view(self):
        """Create the Paging System view."""
        self.paging_frame = ttk.Frame(self.content_frame)
        
        # Controls frame
        controls_frame = ttk.Frame(self.paging_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Page size control
        page_size_label = ttk.Label(controls_frame, text="Page Size (KB):")
        page_size_label.pack(side=tk.LEFT, padx=(0, 5))
        
        page_size_values = [2, 4, 8, 16, 32, 64]
        page_size_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.page_size,
            values=page_size_values,
            state="readonly",
            width=5
        )
        page_size_combo.pack(side=tk.LEFT)
        page_size_combo.current(page_size_values.index(4))  # Default to 4KB
        page_size_combo.bind("<<ComboboxSelected>>", self.on_page_size_change)
        
        # Create paging visualization
        self.paging_fig = Figure(figsize=(10, 6), dpi=100)
        self.paging_fig.patch.set_facecolor(COLORS['background'])
        self.paging_ax = self.paging_fig.add_subplot(111)
        
        # Paging canvas
        self.paging_canvas = FigureCanvasTkAgg(self.paging_fig, master=self.paging_frame)
        self.paging_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Paging toolbar
        self.paging_toolbar_frame = ttk.Frame(self.paging_frame)
        self.paging_toolbar_frame.pack(fill=tk.X)
        self.paging_toolbar = NavigationToolbar2Tk(self.paging_canvas, self.paging_toolbar_frame)
        self.paging_toolbar.update()
        
        # Initialize paging visualization
        self.init_paging_view()
    
    def init_paging_view(self):
        """Initialize the paging system visualization."""
        self.paging_ax.clear()
        self.paging_ax.set_title(f"Page Table ({self.page_size.get()}KB pages)", 
                                fontsize=14, fontweight='bold')
        
        # Create legend
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=COLORS['page_states']['used'], label='Used'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['page_states']['free'], label='Free'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['page_states']['shared'], label='Shared'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['page_states']['swapped'], label='Swapped')
        ]
        self.paging_ax.legend(handles=legend_elements, loc='upper center', 
                             bbox_to_anchor=(0.5, -0.05), ncol=4)
        
        self.paging_fig.tight_layout()
        self.paging_canvas.draw()
    
    def show_view(self, view_name: str):
        """Show the selected view and hide others.
        
        Args:
            view_name: Name of the view to show
        """
        self.current_view.set(view_name)
        
        for frame in [self.dashboard_frame, self.process_frame, 
                     self.segmentation_frame, self.paging_frame]:
            frame.pack_forget()
        
        if view_name == "Memory Dashboard":
            self.dashboard_frame.pack(fill=tk.BOTH, expand=True)
        elif view_name == "Process Memory":
            self.process_frame.pack(fill=tk.BOTH, expand=True)
        elif view_name == "Segmentation":
            self.segmentation_frame.pack(fill=tk.BOTH, expand=True)
        elif view_name == "Paging System":
            self.paging_frame.pack(fill=tk.BOTH, expand=True)
        
        for option, button in self.nav_buttons.items():
            if option == view_name:
                button.state(['selected'])
            else:
                button.state(['!selected'])
    
    def collect_data(self):
        """Collect system data in a separate thread."""
        while self.running:
            try:
                data = self.get_system_data()
                self.data_queue.put(data)
                time.sleep(self.refresh_rate.get() / 1000)
                if self.current_view.get() == "Paging System":
                    time.sleep(1.0)
            except Exception as e:
                print(f"Error collecting data: {e}")
                time.sleep(1)
    
    def get_system_data(self) -> Dict[str, Any]:
        current_time = datetime.now().strftime("%H:%M:%S")
        
        cpu_percent = psutil.cpu_percent()
        cpu_count = psutil.cpu_count(logical=True)
        cpu_info = f"{cpu_count} cores @ {cpu_percent:.1f}%"
        
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024 ** 3)
        memory_used = memory.used / (1024 ** 3)
        memory_available = memory.available / (1024 ** 3)
        memory_cached = memory.cached / (1024 ** 3) if hasattr(memory, 'cached') else 0
        memory_info = f"{memory_used:.1f}GB / {memory_total:.1f}GB ({memory.percent}%)"
        
        try:
            disk = psutil.disk_usage('/')
            disk_total = disk.total / (1024 ** 3)
            disk_used = disk.used / (1024 ** 3)
            disk_free = disk.free / (1024 ** 3)
            disk_percent = disk.percent
            disk_info = f"{disk_used:.1f}GB / {disk_total:.1f}GB ({disk_percent}%)"
        except Exception as e:
            print(f"Error getting disk info: {e}")
            disk_total = disk_used = disk_free = disk_percent = 0
            disk_info = "N/A"
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'num_threads', 'status']):
            try:
                pinfo = proc.info
                memory_mb = pinfo['memory_info'].rss / (1024 * 1024) if pinfo['memory_info'] else 0
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'memory_mb': memory_mb,
                    'threads': pinfo['num_threads'] if pinfo['num_threads'] else 0,
                    'status': pinfo['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        processes.sort(key=lambda x: x['memory_mb'], reverse=True)
        
        memory_segments = self.generate_memory_segments()
        page_table = self.generate_page_table()
        
        return {
            'timestamp': current_time,
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count,
                'info': cpu_info
            },
            'memory': {
                'total': memory_total,
                'used': memory_used,
                'available': memory_available,
                'cached': memory_cached,
                'percent': memory.percent,
                'info': memory_info
            },
            'disk': {
                'total': disk_total,
                'used': disk_used,
                'free': disk_free,
                'percent': disk_percent,
                'info': disk_info
            },
            'processes': processes,
            'memory_segments': memory_segments,
            'page_table': page_table
        }
    
    def generate_memory_segments(self) -> List[Dict[str, Any]]:
        """Generate simulated memory segments for visualization."""
        segments = []
        current_pos = 0
        
        code_size = random.uniform(5, 15)
        segments.append({
            'type': 'code',
            'start': current_pos,
            'size': code_size,
            'color': COLORS['memory_segments']['code']
        })
        current_pos += code_size
        
        current_pos += random.uniform(0.5, 2)
        
        data_size = random.uniform(10, 20)
        segments.append({
            'type': 'data',
            'start': current_pos,
            'size': data_size,
            'color': COLORS['memory_segments']['data']
        })
        current_pos += data_size
        
        current_pos += random.uniform(0.5, 2)
        
        heap_size = random.uniform(15, 30)
        segments.append({
            'type': 'heap',
            'start': current_pos,
            'size': heap_size,
            'color': COLORS['memory_segments']['heap']
        })
        current_pos += heap_size
        
        current_pos += random.uniform(20, 40)
        
        shared_size = random.uniform(5, 15)
        segments.append({
            'type': 'shared',
            'start': current_pos,
            'size': shared_size,
            'color': COLORS['memory_segments']['shared']
        })
        current_pos += shared_size
        
        current_pos += random.uniform(0.5, 2)
        
        stack_size = random.uniform(10, 20)
        segments.append({
            'type': 'stack',
            'start': 100 - stack_size,
            'size': stack_size,
            'color': COLORS['memory_segments']['stack']
        })
        
        return segments
    
    def generate_page_table(self) -> List[Dict[str, Any]]:
        """Generate simulated page table data for visualization."""
        pages = []
        page_states = ['used', 'free', 'shared', 'swapped']
        weights = [0.6, 0.2, 0.1, 0.1]
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        rows, cols = 8, 16
        for row in range(rows):
            for col in range(cols):
                state = random.choices(page_states, weights=weights)[0]
                process = random.choice(processes) if processes and state != 'free' else None
                
                pages.append({
                    'row': row,
                    'col': col,
                    'state': state,
                    'color': COLORS['page_states'][state],
                    'page_num': row * cols + col,
                    'process': process
                })
        
        return pages
    
    def get_process_activity(self, pid: int) -> str:
        """Get current activity of a process."""
        try:
            proc = psutil.Process(pid)
            cpu_percent = proc.cpu_percent(interval=0.1)
            memory_info = proc.memory_info()
            io_counters = proc.io_counters()
            
            activity = []
            if cpu_percent > 0:
                activity.append(f"CPU: {cpu_percent:.1f}%")
            if memory_info.rss > 0:
                activity.append(f"Memory: {memory_info.rss / (1024*1024):.1f}MB")
            if io_counters.read_bytes > 0 or io_counters.write_bytes > 0:
                activity.append("I/O Active")
            
            return " | ".join(activity) if activity else "Idle"
        except:
            return "Unknown"
    
    def process_data_queue(self):
        """Process data from the queue and update UI."""
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get()
                self.update_ui(data)
                self.data_queue.task_done()
        except Exception as e:
            print(f"Error processing data: {e}")
        finally:
            if self.running:
                self.root.after(100, self.process_data_queue)
    
    def update_ui(self, data: Dict[str, Any]):
        """Update UI with new data."""
        self.info_labels["CPU:"].configure(text=data['cpu']['info'])
        self.info_labels["Memory:"].configure(text=data['memory']['info'])
        self.info_labels["Disk:"].configure(text=data['disk']['info'])
        
        current_view = self.current_view.get()
        
        if current_view == "Memory Dashboard":
            self.update_dashboard(data)
        elif current_view == "Process Memory":
            self.update_process_memory(data)
        elif current_view == "Segmentation":
            self.update_segmentation(data)
        elif current_view == "Paging System":
            self.update_paging(data)
    
    def update_dashboard(self, data: Dict[str, Any]):
        """Update the Memory Dashboard view."""
        self.time_labels.append(data['timestamp'])
        self.cpu_data.append(data['cpu']['percent'])
        self.ram_used_data.append(data['memory']['used'])
        self.ram_available_data.append(data['memory']['available'])
        self.ram_cached_data.append(data['memory']['cached'])
        
        if len(self.time_labels) > MAX_DATA_POINTS:
            self.time_labels = self.time_labels[-MAX_DATA_POINTS:]
            self.cpu_data = self.cpu_data[-MAX_DATA_POINTS:]
            self.ram_used_data = self.ram_used_data[-MAX_DATA_POINTS:]
            self.ram_available_data = self.ram_available_data[-MAX_DATA_POINTS:]
            self.ram_cached_data = self.ram_cached_data[-MAX_DATA_POINTS:]
        
        self.cpu_ax.clear()
        self.cpu_ax.set_title("CPU Usage", fontsize=12, fontweight='bold')
        self.cpu_ax.set_xlabel("Time", fontsize=10)
        self.cpu_ax.set_ylabel("Usage (%)", fontsize=10)
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.grid(True, linestyle='--', alpha=0.7)
        
        x_ticks = range(len(self.time_labels))
        self.cpu_ax.plot(x_ticks, self.cpu_data, lw=2, color=COLORS['chart_colors'][0])
        
        n = max(1, len(self.time_labels) // 10)
        self.cpu_ax.set_xticks(x_ticks[::n])
        self.cpu_ax.set_xticklabels(self.time_labels[::n], rotation=45, ha='right')
        
        self.cpu_fig.tight_layout()
        self.cpu_canvas.draw()
        
        self.ram_ax.clear()
        self.ram_ax.set_title("RAM Allocation", fontsize=12, fontweight='bold')
        self.ram_ax.set_xlabel("Time", fontsize=10)
        self.ram_ax.set_ylabel("Memory (GB)", fontsize=10)
        self.ram_ax.grid(True, linestyle='--', alpha=0.7)
        
        self.ram_ax.fill_between(x_ticks, 0, self.ram_used_data, 
                                color=COLORS['chart_colors'][0], alpha=0.7, label='Used')
        self.ram_ax.fill_between(x_ticks, self.ram_used_data, 
                                [u + a for u, a in zip(self.ram_used_data, self.ram_available_data)], 
                                color=COLORS['chart_colors'][1], alpha=0.7, label='Available')
        self.ram_ax.fill_between(x_ticks, 
                                [u + a for u, a in zip(self.ram_used_data, self.ram_available_data)],
                                [u + a + c for u, a, c in zip(self.ram_used_data, self.ram_available_data, self.ram_cached_data)], 
                                color=COLORS['chart_colors'][2], alpha=0.7, label='Cached')
        
        self.ram_ax.set_xticks(x_ticks[::n])
        self.ram_ax.set_xticklabels(self.time_labels[::n], rotation=45, ha='right')
        self.ram_ax.legend(loc='upper left')
        
        self.ram_fig.tight_layout()
        self.ram_canvas.draw()
        
        self.cache_ax.clear()
        self.cache_ax.set_title("Cache Memory Distribution", fontsize=12, fontweight='bold')
        
        cache_labels = ['L1 Cache', 'L2 Cache', 'L3 Cache', 'Other']
        cache_sizes = [random.uniform(5, 15), random.uniform(15, 30), 
                      random.uniform(40, 60), random.uniform(10, 20)]
        
        self.cache_ax.pie(cache_sizes, labels=cache_labels, autopct='%1.1f%%', 
                         startangle=90, colors=COLORS['chart_colors'][:4],
                         wedgeprops={'edgecolor': 'w', 'linewidth': 1})
        self.cache_ax.axis('equal')
        
        self.cache_fig.tight_layout()
        self.cache_canvas.draw()
        
        self.disk_ax.clear()
        self.disk_ax.set_title("Disk Usage", fontsize=12, fontweight='bold')
        
        disk_labels = ['Used', 'Free']
        disk_sizes = [data['disk']['used'], data['disk']['free']]
        
        self.disk_ax.pie(disk_sizes, labels=disk_labels, autopct='%1.1f%%', 
                        startangle=90, colors=[COLORS['chart_colors'][0], COLORS['chart_colors'][1]],
                        wedgeprops={'edgecolor': 'w', 'linewidth': 1})
        self.disk_ax.axis('equal')
        
        self.disk_fig.tight_layout()
        self.disk_canvas.draw()
    
    def update_process_memory(self, data: Dict[str, Any]):
        """Update the Process Memory view."""
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        
        for i, proc in enumerate(data['processes'][:100]):
            self.process_tree.insert(
                "", 
                tk.END, 
                values=(
                    proc['pid'],
                    proc['name'],
                    f"{proc['memory_mb']:.1f}",
                    proc['threads']
                )
            )
    
    def update_memory_map(self, segments: List[Dict[str, Any]]):
        """Update the memory map visualization."""
        self.memory_map_ax.clear()
        self.memory_map_ax.set_title("Memory Map", fontsize=12, fontweight='bold')
        self.memory_map_ax.set_xlabel("Memory Address Space", fontsize=10)
        self.memory_map_ax.set_ylabel("", fontsize=10)
        self.memory_map_ax.set_yticks([])
        self.memory_map_ax.set_xlim(0, 100)
        self.memory_map_ax.set_ylim(0, 1)
        
        for segment in segments:
            self.memory_map_ax.add_patch(
                plt.Rectangle(
                    (segment['start'], 0),
                    segment['size'],
                    0.5,
                    color=segment['color'],
                    alpha=0.7
                )
            )
            
            self.memory_map_ax.text(
                segment['start'] + segment['size']/2,
                0.25,
                segment['type'].capitalize(),
                ha='center',
                va='center',
                color='white',
                fontweight='bold'
            )
        
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['code'], label='Code'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['data'], label='Data'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['heap'], label='Heap'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['stack'], label='Stack'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['shared'], label='Shared')
        ]
        self.memory_map_ax.legend(handles=legend_elements, loc='upper center', 
                                 bbox_to_anchor=(0.5, -0.05), ncol=5)
        
        self.memory_map_fig.tight_layout()
        self.memory_map_canvas.draw()
    
    def update_segmentation(self, data: Dict[str, Any]):
        """Update the Segmentation view."""
        self.seg_ax.clear()
        self.seg_ax.set_title("Memory Segmentation", fontsize=14, fontweight='bold')
        self.seg_ax.set_xlabel("Memory Address Space", fontsize=12)
        self.seg_ax.set_yticks([])
        self.seg_ax.set_xlim(0, 100)
        
        num_processes = min(5, len(data['processes']))
        
        for i in range(num_processes):
            proc_segments = self.generate_memory_segments()
            proc_name = data['processes'][i]['name'] if i < len(data['processes']) else f"Process {i+1}"
            
            self.seg_ax.text(-5, i, proc_name, ha='right', va='center', fontsize=10)
            
            for segment in proc_segments:
                self.seg_ax.add_patch(
                    plt.Rectangle(
                        (segment['start'], i - 0.3),
                        segment['size'],
                        0.6,
                        color=segment['color'],
                        alpha=0.7
                    )
                )
                
                if segment['size'] > 10:
                    self.seg_ax.text(
                        segment['start'] + segment['size']/2,
                        i,
                        segment['type'].capitalize(),
                        ha='center',
                        va='center',
                        color='white',
                        fontweight='bold',
                        fontsize=9
                    )
        
        self.seg_ax.set_ylim(-0.5, num_processes - 0.5)
        
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['code'], label='Code'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['data'], label='Data'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['heap'], label='Heap'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['stack'], label='Stack'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['memory_segments']['shared'], label='Shared')
        ]
        self.seg_ax.legend(handles=legend_elements, loc='upper center', 
                          bbox_to_anchor=(0.5, -0.05), ncol=5)
        
        self.seg_fig.tight_layout()
        self.seg_canvas.draw()
    
    def update_paging(self, data: Dict[str, Any]):
        """Update the Paging System view."""
        self.paging_ax.clear()
        self.paging_ax.set_title(f"Page Table ({self.page_size.get()}KB pages)", 
                                fontsize=14, fontweight='bold')
        
        pages = data['page_table']
        rows = max(page['row'] for page in pages) + 1
        cols = max(page['col'] for page in pages) + 1
        
        self.page_rectangles = {}
        
        for page in pages:
            row, col = page['row'], page['col']
            color = page['color']
            page_num = page['page_num']
            
            rect = plt.Rectangle(
                (col, rows - row - 1),
                1, 1,
                color=color,
                alpha=0.7,
                edgecolor='white',
                linewidth=1
            )
            self.paging_ax.add_patch(rect)
            
            self.page_rectangles[page_num] = {
                'rect': rect,
                'state': page['state'],
                'row': row,
                'col': col,
                'process': page['process']
            }
            
            self.paging_ax.text(
                col + 0.5,
                rows - row - 0.5,
                str(page_num),
                ha='center',
                va='center',
                color='white',
                fontweight='bold',
                fontsize=8
            )
        
        self.paging_ax.set_xlim(0, cols)
        self.paging_ax.set_ylim(0, rows)
        self.paging_ax.set_xticks([])
        self.paging_ax.set_yticks([])
        self.paging_ax.grid(True, color='white', linestyle='-', linewidth=0.5)
        
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=COLORS['page_states']['used'], label='Used'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['page_states']['free'], label='Free'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['page_states']['shared'], label='Shared'),
            plt.Rectangle((0, 0), 1, 1, color=COLORS['page_states']['swapped'], label='Swapped')
        ]
        self.paging_ax.legend(handles=legend_elements, loc='upper center', 
                             bbox_to_anchor=(0.5, -0.05), ncol=4)
        
        self.paging_canvas.mpl_connect('motion_notify_event', self.on_page_hover)
        
        self.paging_fig.tight_layout()
        self.paging_canvas.draw()
    
    def on_page_hover(self, event):
        """Handle mouse hover over page cells."""
        if event.inaxes != self.paging_ax:
            self._hide_tooltip()
            return
            
        for page_num, page_data in self.page_rectangles.items():
            if page_data['rect'].contains(event)[0]:
                tooltip_text = (
                    f"Page Number: {page_num}\n"
                    f"Page State: {page_data['state'].capitalize()}"
                )
                
                if page_data['process']:
                    process = page_data['process']
                    try:
                        proc = psutil.Process(process['pid'])
                        status = proc.status()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        status = "Terminated"
                    
                    tooltip_text += (
                        f"\nProcess Name: {process['name']}\n"
                        f"Process ID: {process['pid']}\n"
                        f"Process State: {status.capitalize()}"
                    )
                
                self._show_tooltip(event, tooltip_text)
                return
        
        self._hide_tooltip()
    
    def _show_tooltip(self, event, text: str):
        """Display tooltip with page information."""
        self._hide_tooltip()
        
        self.tooltip = self.paging_ax.annotate(
            text,
            xy=(event.xdata, event.ydata),
            xytext=(10, 10),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
            arrowprops=dict(arrowstyle='->'),
            fontsize=9
        )
        self.paging_canvas.draw()
    
    def _hide_tooltip(self):
        """Hide the current tooltip if it exists."""
        if hasattr(self, 'tooltip'):
            try:
                self.tooltip.set_visible(False)
                self.paging_canvas.draw()
            except:
                pass
    
    def on_process_select(self, event):
        """Handle process selection in the process tree."""
        selected_items = self.process_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.process_tree.item(item, 'values')
        
        segments = self.generate_memory_segments()
        self.update_memory_map(segments)
    
    def on_refresh_rate_change(self, event):
        """Handle refresh rate change."""
        selected = event.widget.get()
        rate_seconds = float(selected.rstrip('s'))
        self.refresh_rate.set(int(rate_seconds * 1000))
    
    def on_page_size_change(self, event):
        """Handle page size change."""
        self.paging_ax.set_title(f"Page Table ({self.page_size.get()}KB pages)", 
                                fontsize=14, fontweight='bold')
        self.paging_canvas.draw()
    
    def on_closing(self):
        """Handle window closing event."""
        self.running = False
        if self.data_thread.is_alive():
            self.data_thread.join(timeout=1.0)
        self.root.destroy()

def main():
    """Main function to start the application."""
    import os
    if "DISPLAY" not in os.environ and os.name != 'nt':
        print("Error: No DISPLAY environment variable set. Run with Xvfb or in a GUI environment.")
        exit(1)
    
    root = tk.Tk()
    app = MemoryVisualizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
