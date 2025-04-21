import sys
import time
import random
import platform
import threading
import queue
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime
import psutil

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QFrame, QSplitter, QGridLayout, QGroupBox, QLineEdit, QScrollArea,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QBrush, QPen

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

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
    },
    'page_access': {
        'hit': '#2ecc71',      # Green
        'miss': '#e74c3c',     # Red
        'fault': '#f39c12',    # Yellow
    }
}

# Define types similar to TypeScript types
class PageTableEntry:
    def __init__(self, virtual_page: int, physical_frame: int, valid_bit: int, referenced: int, modified: int):
        self.virtual_page = virtual_page
        self.physical_frame = physical_frame
        self.valid_bit = valid_bit
        self.referenced = referenced
        self.modified = modified

class PageAccessResult:
    def __init__(self, process: str, virtual_address: int, page_number: int, offset: int, 
                 physical_address: Optional[int], frame_number: Optional[int], result: str, 
                 message: str, timestamp: str, table_updated: bool = False, 
                 updated_page_table: Optional[Dict[str, List[PageTableEntry]]] = None):
        self.process = process
        self.virtual_address = virtual_address
        self.page_number = page_number
        self.offset = offset
        self.physical_address = physical_address
        self.frame_number = frame_number
        self.result = result
        self.message = message
        self.timestamp = timestamp
        self.table_updated = table_updated
        self.updated_page_table = updated_page_table

class TLBEntry:
    def __init__(self, virtual_page: int, physical_frame: int, valid: bool):
        self.virtual_page = virtual_page
        self.physical_frame = physical_frame
        self.valid = valid

# Page Table Simulation
class PageTableSimulator:
    """Simulates page table operations with hit/miss/fault tracking."""
    
    def __init__(self, num_processes=3, pages_per_process=5):
        """Initialize the page table simulator.
        
        Args:
            num_processes: Number of processes to simulate
            pages_per_process: Number of pages per process
        """
        self.num_processes = num_processes
        self.pages_per_process = pages_per_process
        self.processes = {}
        self.physical_frames = {}
        self.access_history = {
            'hits': 0,
            'misses': 0,
            'faults': 0,
            'history': []  # List of recent access results (hit/miss/fault)
        }
        
        # Initialize processes and their page tables
        self._initialize_processes()
    
    def _initialize_processes(self):
        """Initialize processes with random page tables."""
        process_names = [f"Process {chr(65 + i)}" for i in range(self.num_processes)]
        
        # Create processes with page tables
        for name in process_names:
            page_table = {}
            for page in range(self.pages_per_process):
                # Randomly assign physical frames or mark as not in memory
                if random.random() < 0.7:  # 70% chance page is in memory
                    frame = random.randint(1, 20)
                    valid_bit = 1
                    self.physical_frames[frame] = {
                        'process': name,
                        'page': page
                    }
                else:
                    frame = None
                    valid_bit = 0
                
                page_table[page] = {
                    'Physical Frame': frame,
                    'Valid Bit': valid_bit,
                    'Referenced': random.choice([0, 1]),
                    'Modified': random.choice([0, 1])
                }
            
            self.processes[name] = page_table
    
    def access_page(self, process_name, page_num):
        """Simulate accessing a page and track hit/miss/fault.
        
        Args:
            process_name: Name of the process
            page_num: Page number to access
            
        Returns:
            str: 'hit', 'miss', or 'fault'
        """
        if process_name not in self.processes:
            result = 'fault'
        elif page_num not in self.processes[process_name]:
            result = 'fault'
        elif self.processes[process_name][page_num]['Valid Bit'] == 0:
            # Page is not in memory - page fault
            result = 'fault'
            
            # Simulate page fault handling - load page into memory
            frame = random.randint(1, 20)
            self.processes[process_name][page_num]['Physical Frame'] = frame
            self.processes[process_name][page_num]['Valid Bit'] = 1
            self.physical_frames[frame] = {
                'process': process_name,
                'page': page_num
            }
        else:
            # Page is in memory - check TLB
            if random.random() < 0.8:  # 80% chance of TLB hit
                result = 'hit'
            else:
                result = 'miss'
            
            # Mark as referenced
            self.processes[process_name][page_num]['Referenced'] = 1
            
            # 30% chance of modifying the page
            if random.random() < 0.3:
                self.processes[process_name][page_num]['Modified'] = 1
        
        # Update access history
        self.access_history[result + 's'] += 1
        self.access_history['history'].append(result)
        
        # Keep history to last 20 accesses
        if len(self.access_history['history']) > 20:
            self.access_history['history'] = self.access_history['history'][-20:]
        
        return result
    
    def simulate_random_access(self, num_accesses=1):
        """Simulate random page accesses.
        
        Args:
            num_accesses: Number of random accesses to simulate
            
        Returns:
            List of access results
        """
        results = []
        for _ in range(num_accesses):
            process_name = random.choice(list(self.processes.keys()))
            page_num = random.choice(list(self.processes[process_name].keys()))
            result = self.access_page(process_name, page_num)
            results.append({
                'process': process_name,
                'page': page_num,
                'result': result
            })
        
        return results
    
    def get_page_tables(self):
        """Get all page tables for visualization.
        
        Returns:
            Dict of processes and their page tables
        """
        return self.processes
    
    def get_access_stats(self):
        """Get access statistics.
        
        Returns:
            Dict with hit/miss/fault counts and history
        """
        return self.access_history
    
    def get_detailed_page_tables(self):
        """Get detailed page tables for pandas DataFrame visualization.
        
        Returns:
            Dict of DataFrames for each process
        """
        detailed_tables = {}
        
        for process_name, page_table in self.processes.items():
            rows = []
            for vpage, details in page_table.items():
                row = {'Virtual Page': vpage}
                row.update(details)
                rows.append(row)
            
            df = pd.DataFrame(rows)
            
            # Reorder columns for better presentation
            df = df[['Virtual Page', 'Physical Frame', 'Valid Bit', 'Referenced', 'Modified']]
            
            detailed_tables[process_name] = df
        
        return detailed_tables

# Generate a simulated page table for a process
def generate_page_table(process_name: str, num_pages: int) -> List[PageTableEntry]:
    page_table = []
    
    # For realism, we'll generate different patterns based on the process name
    for i in range(num_pages):
        is_valid = random.random() < 0.8  # 80% chance page is in memory
        
        if process_name == 'Process A':
            entry = PageTableEntry(
                virtual_page=i,
                physical_frame=int(random.random() * 20) + 1 if is_valid else 0,
                valid_bit=1 if is_valid else 0,
                referenced=1 if random.random() < 0.5 else 0,
                modified=1 if random.random() < 0.3 else 0
            )
        elif process_name == 'Process B':
            entry = PageTableEntry(
                virtual_page=i,
                physical_frame=(i % 10) + 1 if is_valid else 0,  # More predictable pattern
                valid_bit=1 if is_valid else 0,
                referenced=i % 2,  # Alternating pattern
                modified=1 if i % 3 == 0 else 0  # Every third page modified
            )
        else:
            # Process C or any other process
            entry = PageTableEntry(
                virtual_page=i,
                physical_frame=7 + i if is_valid else 0,  # Sequential frames
                valid_bit=1 if i < 2 else 0,  # Only first two pages in memory
                referenced=1 if i == 1 else 0,  # Only second page referenced
                modified=1 if i == 0 else 0  # Only first page modified
            )
        
        page_table.append(entry)
    
    return page_table

# Simulate a random memory access
def generate_memory_access(
    process_name: str,
    page_size: int,
    current_page_table: Dict[str, List[PageTableEntry]]
) -> PageAccessResult:
    page_table = current_page_table.get(process_name, [])
    
    # Generate a random page number within the valid range
    max_page = max([entry.virtual_page for entry in page_table]) if page_table else 5
    
    # 70% chance we access an existing page, 30% chance we access a non-existent page
    access_existing_page = random.random() < 0.7
    
    if access_existing_page and page_table:
        # Select a random existing page
        random_index = int(random.random() * len(page_table))
        page_number = page_table[random_index].virtual_page
    else:
        # Generate a random page number, potentially outside the table
        page_number = int(random.random() * (max_page + 3))
    
    # Generate a random offset within the page
    offset = int(random.random() * (page_size * 1024))
    
    # Calculate the virtual address
    virtual_address = (page_number * page_size * 1024) + offset
    
    # Find the page table entry
    entry = next((e for e in page_table if e.virtual_page == page_number), None)
    
    # If page doesn't exist or is not valid, it's a page fault
    if not entry or entry.valid_bit == 0:
        updated_page_table = None
        table_updated = False
        
        # If the page exists but is not in memory, we can load it (page fault - not in memory)
        if entry and entry.valid_bit == 0:
            # Simulate loading the page into memory
            updated_page_table = current_page_table.copy()
            entry_index = next((i for i, e in enumerate(page_table) if e.virtual_page == page_number), -1)
            
            if entry_index != -1:
                # Assign a random frame number
                frame_number = int(random.random() * 20) + 1
                
                updated_page_table[process_name] = page_table.copy()
                updated_entry = PageTableEntry(
                    virtual_page=page_table[entry_index].virtual_page,
                    physical_frame=frame_number,
                    valid_bit=1,
                    referenced=page_table[entry_index].referenced,
                    modified=page_table[entry_index].modified
                )
                updated_page_table[process_name][entry_index] = updated_entry
                
                table_updated = True
        
        return PageAccessResult(
            process=process_name,
            virtual_address=virtual_address,
            page_number=page_number,
            offset=offset,
            physical_address=None,
            frame_number=None,
            result='fault',
            message='Page fault: Page not in memory' if entry else 'Page fault: Virtual page does not exist',
            timestamp=datetime.now().isoformat(),
            table_updated=table_updated,
            updated_page_table=updated_page_table
        )
    
    # If we reach here, the page is valid and in memory
    # Simulate TLB hit/miss (random for demo)
    is_tlb_hit = random.random() < 0.6  # 60% chance of TLB hit
    
    # Calculate physical address
    physical_address = (entry.physical_frame * page_size * 1024) + offset
    
    # Update referenced bit
    updated_page_table = current_page_table.copy()
    entry_index = next((i for i, e in enumerate(page_table) if e.virtual_page == page_number), -1)
    
    if entry_index != -1:
        updated_page_table[process_name] = page_table.copy()
        updated_entry = PageTableEntry(
            virtual_page=page_table[entry_index].virtual_page,
            physical_frame=page_table[entry_index].physical_frame,
            valid_bit=page_table[entry_index].valid_bit,
            referenced=1,
            # 20% chance to modify the page
            modified=1 if random.random() < 0.2 else page_table[entry_index].modified
        )
        updated_page_table[process_name][entry_index] = updated_entry
    
    return PageAccessResult(
        process=process_name,
        virtual_address=virtual_address,
        page_number=page_number,
        offset=offset,
        physical_address=physical_address,
        frame_number=entry.physical_frame,
        result='hit' if is_tlb_hit else 'miss',
        message='TLB Hit: Address translated successfully' if is_tlb_hit else 'TLB Miss: Found in page table',
        timestamp=datetime.now().isoformat(),
        table_updated=True,
        updated_page_table=updated_page_table
    )

# Custom matplotlib canvas for PyQt
class MplCanvas(FigureCanvas):
    def __init__(self, fig=None, parent=None, width=5, height=4, dpi=100):
        if fig is None:
            self.fig = Figure(figsize=(width, height), dpi=dpi)
            self.fig.patch.set_facecolor(COLORS['background'])
        else:
            self.fig = fig
        
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        FigureCanvas.setSizePolicy(self,
                                  QSizePolicy.Expanding,
                                  QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

# Data collection thread
class DataCollector(QThread):
    data_ready = pyqtSignal(dict)
    
    def __init__(self, refresh_rate=DEFAULT_REFRESH_RATE):
        super().__init__()
        self.refresh_rate = refresh_rate
        self.running = True
        self.page_simulator = PageTableSimulator(num_processes=3, pages_per_process=5)
    
    def run(self):
        while self.running:
            try:
                data = self.get_system_data()
                self.data_ready.emit(data)
                time.sleep(self.refresh_rate / 1000)
            except Exception as e:
                print(f"Error collecting data: {e}")
                time.sleep(1)
    
    def set_refresh_rate(self, rate):
        self.refresh_rate = rate
    
    def stop(self):
        self.running = False
        self.wait()
    
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
            disk = psutil.disk_usage('../')
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
        tlb_entries = self.generate_tlb_entries()
        
        # Simulate page accesses
        page_access_results = self.page_simulator.simulate_random_access(1)
        
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
            'page_table': page_table,
            'tlb_entries': tlb_entries,
            'page_access': page_access_results,
            'page_stats': self.page_simulator.get_access_stats()
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
    
    def generate_tlb_entries(self) -> List[Dict[str, Any]]:
        """Generate simulated TLB entries for visualization."""
        tlb_entries = []
        page_size = 4 * 1024  # Default 4KB page size
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        for i in range(8):  # Simulate 8 TLB entries
            virtual_page = random.randint(0, 1023)  # 10-bit virtual page number
            physical_frame = random.randint(0, 511)  # 9-bit physical frame number
            process = random.choice(processes) if processes else None
            
            tlb_entries.append({
                'virtual_page': virtual_page,
                'physical_frame': physical_frame,
                'valid': random.choice([True, False]),
                'process': process,
                'virtual_address': virtual_page * page_size,
                'physical_address': physical_frame * page_size
            })
        
        return tlb_entries

# Custom widgets
class MemorySegmentWidget(QWidget):
    """Widget for visualizing memory segments"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments = []
        self.setMinimumHeight(100)
    
    def set_segments(self, segments):
        self.segments = segments
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw background
        painter.fillRect(0, 0, width, height, QBrush(QColor(COLORS['background'])))
        
        # Draw segments
        for segment in self.segments:
            start_x = int(segment['start'] * width / 100)
            segment_width = int(segment['size'] * width / 100)
            
            painter.setBrush(QBrush(QColor(segment['color'])))
            painter.setPen(QPen(Qt.white, 1))
            painter.drawRect(start_x, 10, segment_width, height - 20)
            
            # Draw text if segment is wide enough
            if segment_width > 40:
                painter.setPen(QPen(Qt.white))
                painter.drawText(
                    start_x + 5, 
                    10, 
                    segment_width - 10, 
                    height - 20, 
                    Qt.AlignCenter, 
                    segment['type'].capitalize()
                )

class PageTableWidget(QWidget):
    """Widget for visualizing page tables"""
    
    page_clicked = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pages = []
        self.hover_page = None
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
    
    def set_pages(self, pages):
        self.pages = pages
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw background
        painter.fillRect(0, 0, width, height, QBrush(QColor(COLORS['background'])))
        
        if not self.pages:
            return
        
        # Calculate grid dimensions
        rows = max(page['row'] for page in self.pages) + 1
        cols = max(page['col'] for page in self.pages) + 1
        
        cell_width = width / cols
        cell_height = height / rows
        
        # Draw grid
        for page in self.pages:
            row, col = page['row'], page['col']
            x = col * cell_width
            y = row * cell_height
            
            # Draw cell
            painter.setBrush(QBrush(QColor(page['color'])))
            painter.setPen(QPen(Qt.white, 1))
            
            # Highlight hovered page
            if self.hover_page and self.hover_page['page_num'] == page['page_num']:
                painter.setPen(QPen(Qt.black, 2))
            
            painter.drawRect(int(x), int(y), int(cell_width), int(cell_height))
            
            # Draw page number
            painter.setPen(QPen(Qt.white))
            painter.drawText(
                x, y, cell_width, cell_height, 
                Qt.AlignCenter, 
                str(page['page_num'])
            )
    
    def mouseMoveEvent(self, event):
        if not self.pages:
            return
        
        # Calculate grid dimensions
        rows = max(page['row'] for page in self.pages) + 1
        cols = max(page['col'] for page in self.pages) + 1
        
        cell_width = self.width() / cols
        cell_height = self.height() / rows + 1
        
        cell_width = self.width() / cols
        cell_height = self.height() / rows
        
        # Find which cell the mouse is over
        x, y = event.x(), event.y()
        col = int(x / cell_width)
        row = int(y / cell_height)
        
        # Find the page at this position
        for page in self.pages:
            if page['row'] == row and page['col'] == col:
                if self.hover_page != page:
                    self.hover_page = page
                    self.update()
                return
        
        self.hover_page = None
        self.update()
    
    def mousePressEvent(self, event):
        if self.hover_page:
            self.page_clicked.emit(self.hover_page)

class MemoryVisualizerApp(QMainWindow):
    """Main application class for Memory Visualizer."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Memory Visualizer")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        
        # Data structures
        self.refresh_rate = DEFAULT_REFRESH_RATE
        self.page_size = 4  # Default page size in KB
        
        # Time series data
        self.time_labels = []
        self.cpu_data = []
        self.ram_used_data = []
        self.ram_available_data = []
        self.ram_cached_data = []
        
        # Create main layout
        self.create_layout()
        
        # Start data collection thread
        self.data_collector = DataCollector(self.refresh_rate)
        self.data_collector.data_ready.connect(self.update_ui)
        self.data_collector.start()
    
    def create_layout(self):
        """Create the main application layout."""
        # Main widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.main_layout.addWidget(self.content_widget, 1)
        
        # Create system info panel
        self.create_system_info_panel()
        
        # Create stacked widget for different views
        self.stacked_widget = QStackedWidget()
        self.content_layout.addWidget(self.stacked_widget)
        
        # Create content views
        self.create_dashboard_view()
        self.create_process_memory_view()
        self.create_segmentation_view()
        
        # Show default view
        self.show_view("Memory Dashboard")
    
    def create_sidebar(self):
        """Create the sidebar navigation panel."""
        # Sidebar container
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet(f"background-color: {COLORS['sidebar']};")
        
        # Sidebar layout
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(1)
        
        # App title
        title_label = QLabel("Memory Visualizer")
        title_label.setStyleSheet(f"""
            color: {COLORS['text_light']};
            font-size: 14pt;
            font-weight: bold;
            padding: 20px 10px;
        """)
        sidebar_layout.addWidget(title_label)
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_options = [
            "Memory Dashboard",
            "Process Memory",
            "Segmentation"
        ]
        
        for option in nav_options:
            btn = QPushButton(option)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['sidebar']};
                    color: {COLORS['text_light']};
                    border: none;
                    text-align: left;
                    padding: 10px;
                    font-size: 11pt;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['sidebar_hover']};
                }}
                QPushButton:checked {{
                    background-color: {COLORS['sidebar_active']};
                }}
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, opt=option: self.show_view(opt))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[option] = btn
        
        # Add stretch to push refresh rate control to bottom
        sidebar_layout.addStretch()
        
        # Refresh rate control
        refresh_frame = QWidget()
        refresh_layout = QVBoxLayout(refresh_frame)
        
        refresh_label = QLabel("Refresh Rate:")
        refresh_label.setStyleSheet(f"color: {COLORS['text_light']};")
        refresh_layout.addWidget(refresh_label)
        
        self.refresh_combo = QComboBox()
        self.refresh_combo.addItems([f"{rate/1000}s" for rate in REFRESH_RATES])
        self.refresh_combo.setCurrentIndex(REFRESH_RATES.index(DEFAULT_REFRESH_RATE))
        self.refresh_combo.currentIndexChanged.connect(self.on_refresh_rate_change)
        refresh_layout.addWidget(self.refresh_combo)
        
        sidebar_layout.addWidget(refresh_frame)
        sidebar_layout.addSpacing(10)
        
        # Add sidebar to main layout
        self.main_layout.addWidget(self.sidebar)
    
    def create_system_info_panel(self):
        """Create the system information panel."""
        self.sysinfo_frame = QFrame()
        self.sysinfo_frame.setFrameShape(QFrame.StyledPanel)
        self.sysinfo_frame.setStyleSheet("background-color: white;")
        
        # System info layout
        sysinfo_layout = QHBoxLayout(self.sysinfo_frame)
        
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
        
        # Create and place labels in layout
        self.info_labels = {}
        
        for label_text, value_text in labels:
            group = QWidget()
            group_layout = QHBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            group_layout.addWidget(label)
            
            value = QLabel(value_text)
            group_layout.addWidget(value)
            
            self.info_labels[label_text] = value
            sysinfo_layout.addWidget(group)
        
        # Add to content layout
        self.content_layout.addWidget(self.sysinfo_frame)
    
    def create_dashboard_view(self):
        """Create the Memory Dashboard view."""
        dashboard_widget = QWidget()
        dashboard_layout = QGridLayout(dashboard_widget)
        
        # CPU Usage chart
        cpu_group = QGroupBox("CPU Usage")
        cpu_layout = QVBoxLayout(cpu_group)
        
        self.cpu_fig = Figure(figsize=(5, 4), dpi=100)
        self.cpu_fig.patch.set_facecolor(COLORS['background'])
        self.cpu_ax = self.cpu_fig.add_subplot(111)
        
        self.cpu_canvas = MplCanvas(self.cpu_fig)
        cpu_layout.addWidget(self.cpu_canvas)
        
        # RAM Allocation chart
        ram_group = QGroupBox("RAM Allocation")
        ram_layout = QVBoxLayout(ram_group)
        
        self.ram_fig = Figure(figsize=(5, 4), dpi=100)
        self.ram_fig.patch.set_facecolor(COLORS['background'])
        self.ram_ax = self.ram_fig.add_subplot(111)
        
        self.ram_canvas = MplCanvas(self.ram_fig)
        ram_layout.addWidget(self.ram_canvas)
        
        # Cache Memory chart
        cache_group = QGroupBox("Cache Memory Distribution")
        cache_layout = QVBoxLayout(cache_group)
        
        self.cache_fig = Figure(figsize=(5, 4), dpi=100)
        self.cache_fig.patch.set_facecolor(COLORS['background'])
        self.cache_ax = self.cache_fig.add_subplot(111)
        
        self.cache_canvas = MplCanvas(self.cache_fig)
        cache_layout.addWidget(self.cache_canvas)
        
        # Disk Usage chart
        disk_group = QGroupBox("Disk Usage")
        disk_layout = QVBoxLayout(disk_group)
        
        self.disk_fig = Figure(figsize=(5, 4), dpi=100)
        self.disk_fig.patch.set_facecolor(COLORS['background'])
        self.disk_ax = self.disk_fig.add_subplot(111)
        
        self.disk_canvas = MplCanvas(self.disk_fig)
        disk_layout.addWidget(self.disk_canvas)
        
        # Add charts to grid
        dashboard_layout.addWidget(cpu_group, 0, 0)
        dashboard_layout.addWidget(ram_group, 0, 1)
        dashboard_layout.addWidget(cache_group, 1, 0)
        dashboard_layout.addWidget(disk_group, 1, 1)
        
        # Initialize charts
        self.init_dashboard_charts()
        
        # Add to stacked widget
        self.stacked_widget.addWidget(dashboard_widget)
    
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
        process_widget = QWidget()
        process_layout = QVBoxLayout(process_widget)
        
        # Create process table
        table_group = QGroupBox("Process List")
        table_layout = QVBoxLayout(table_group)
        
        self.process_tree = QTreeWidget()
        self.process_tree.setHeaderLabels(["Process ID", "Process Name", "Memory Usage (MB)", "Thread Count"])
        self.process_tree.setAlternatingRowColors(True)
        self.process_tree.setColumnWidth(0, 100)
        self.process_tree.setColumnWidth(1, 250)
        self.process_tree.setColumnWidth(2, 150)
        self.process_tree.setColumnWidth(3, 150)
        self.process_tree.itemSelectionChanged.connect(self.on_process_select)
        
        table_layout.addWidget(self.process_tree)
        process_layout.addWidget(table_group)
        
        # Create memory map visualization
        map_group = QGroupBox("Memory Map")
        map_layout = QVBoxLayout(map_group)
        
        self.memory_map_widget = MemorySegmentWidget()
        map_layout.addWidget(self.memory_map_widget)
        
        process_layout.addWidget(map_group)
        
        # Add to stacked widget
        self.stacked_widget.addWidget(process_widget)
    
    def create_segmentation_view(self):
        """Create the Segmentation view."""
        segmentation_widget = QWidget()
        segmentation_layout = QVBoxLayout(segmentation_widget)
        
        # Create segmentation visualization
        self.seg_fig = Figure(figsize=(10, 6), dpi=100)
        self.seg_fig.patch.set_facecolor(COLORS['background'])
        self.seg_ax = self.seg_fig.add_subplot(111)
        
        self.seg_canvas = MplCanvas(self.seg_fig)
        segmentation_layout.addWidget(self.seg_canvas)
        
        # Initialize segmentation visualization
        self.init_segmentation_view()
        
        # Add to stacked widget
        self.stacked_widget.addWidget(segmentation_widget)
    
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
    
    def show_view(self, view_name: str):
        """Show the selected view and hide others."""
        view_index = {
            "Memory Dashboard": 0,
            "Process Memory": 1,
            "Segmentation": 2
        }
        
        self.stacked_widget.setCurrentIndex(view_index[view_name])
        
        # Update button states
        for option, button in self.nav_buttons.items():
            button.setChecked(option == view_name)
    
    def on_process_select(self):
        """Handle process selection in the process tree."""
        selected_items = self.process_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        pid = item.text(0)
        name = item.text(1)
        
        # Generate memory segments for the selected process
        segments = self.data_collector.generate_memory_segments()
        self.memory_map_widget.set_segments(segments)
    
    def on_refresh_rate_change(self, index):
        """Handle refresh rate change."""
        rate = REFRESH_RATES[index]
        self.refresh_rate = rate
        self.data_collector.set_refresh_rate(rate)
    
    def update_ui(self, data):
        """Update UI with new data."""
        self.info_labels["CPU:"].setText(data['cpu']['info'])
        self.info_labels["Memory:"].setText(data['memory']['info'])
        self.info_labels["Disk:"].setText(data['disk']['info'])
        
        current_index = self.stacked_widget.currentIndex()
        
        if current_index == 0:  # Memory Dashboard
            self.update_dashboard(data)
        elif current_index == 1:  # Process Memory
            self.update_process_memory(data)
        elif current_index == 2:  # Segmentation
            self.update_segmentation(data)
    
    def update_dashboard(self, data):
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
    
    def update_process_memory(self, data):
        """Update the Process Memory view."""
        self.process_tree.clear()
        
        for proc in data['processes'][:100]:
            item = QTreeWidgetItem([
                str(proc['pid']),
                proc['name'],
                f"{proc['memory_mb']:.1f}",
                str(proc['threads'])
            ])
            
            self.process_tree.addTopLevelItem(item)
    
    def update_segmentation(self, data):
        """Update the Segmentation view."""
        self.seg_ax.clear()
        self.seg_ax.set_title("Memory Segmentation", fontsize=14, fontweight='bold')
        self.seg_ax.set_xlabel("Memory Address Space", fontsize=12)
        self.seg_ax.set_yticks([])
        self.seg_ax.set_xlim(0, 100)
        
        num_processes = min(5, len(data['processes']))
        
        for i in range(num_processes):
            proc_segments = self.data_collector.generate_memory_segments()
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
    
    def closeEvent(self, event):
        """Handle window closing event."""
        self.data_collector.stop()
        event.accept()

def main():
    """Main function to start the application."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a consistent look across platforms
    
    # Set application-wide stylesheet
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
        }
    """)
    
    window = MemoryVisualizerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
