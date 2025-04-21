import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QPushButton, QLineEdit, QGroupBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QTabWidget
)
from typing import Dict, List, Optional
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QLinearGradient, QPainterPath

import random
from datetime import datetime

# Constants
COLORS = {
    'virtual': '#3498db',    # Blue
    'physical': '#2ecc71',   # Green
    'fault': '#f39c12',      # Yellow
    'arrow': '#34495e',      # Dark blue
    'text': '#2c3e50',       # Dark text
    'background': '#f5f5f5', # Light background
    'highlight': '#1abc9c',  # Teal highlight
}

class PageTableEntry:
    def __init__(self, virtual_page, physical_frame, valid_bit=1, referenced=0, modified=0):
        self.virtual_page = virtual_page
        self.physical_frame = physical_frame
        self.valid_bit = valid_bit
        self.referenced = referenced
        self.modified = modified

class AnimatedLabel(QLabel):
    """A label that can animate its text with a typewriter effect"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_text = ""
        self.current_text = ""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_text)
        self.typing_speed = 50  # ms per character
    
    def set_text_animated(self, text):
        """Set text with animation"""
        self.full_text = text
        self.current_text = ""
        self.timer.start(self.typing_speed)
    
    def update_text(self):
        """Update text for animation"""
        if len(self.current_text) < len(self.full_text):
            self.current_text = self.full_text[:len(self.current_text) + 1]
            self.setText(self.current_text)
        else:
            self.timer.stop()

class AddressTranslationWidget(QWidget):
    """Widget for visualizing memory address translation with animations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        
        # Memory mapping data
        self.virtual_address = 0
        self.physical_address = 0
        self.page_number = 0
        self.frame_number = 0
        self.offset = 0
        self.page_size = 4096  # 4KB default
        self.result = "success"  # success, fault
        
        # Animation state
        self.animation_step = 0
        self.animation_in_progress = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_animation_step)
        
        # Animation objects
        self.address_ball_pos = QPoint(0, 0)
        self.address_ball_animation = QPropertyAnimation(self, b"addressBallPos")
        self.address_ball_animation.setDuration(800)
        self.address_ball_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Page table
        self.page_table = {}
        self.init_page_table()
    
    def get_addressBallPos(self):
        return self.address_ball_pos
    
    def set_addressBallPos(self, pos):
        self.address_ball_pos = pos
        self.update()
    
    addressBallPos = pyqtSignal(QPoint)
    
    def init_page_table(self):
        """Initialize a sample page table"""
        for i in range(10):
            is_valid = random.random() < 0.8
            self.page_table[i] = PageTableEntry(
                virtual_page=i,
                physical_frame=random.randint(1, 20) if is_valid else 0,
                valid_bit=1 if is_valid else 0,
                referenced=random.choice([0, 1]),
                modified=random.choice([0, 1])
            )
    
    def set_address_mapping(self, virtual_address, physical_address=None, 
                           page_number=None, frame_number=None, offset=None, 
                           result="success"):
        """Set the address mapping to visualize"""
        self.virtual_address = virtual_address
        self.physical_address = physical_address
        self.page_number = page_number if page_number is not None else virtual_address // self.page_size
        self.offset = offset if offset is not None else virtual_address % self.page_size
        self.result = result
        
        if result == "success":
            self.frame_number = frame_number if frame_number is not None else self.page_table.get(self.page_number, PageTableEntry(0, 0)).physical_frame
            if physical_address is None:
                self.physical_address = self.frame_number * self.page_size + self.offset
        else:
            self.frame_number = None
            self.physical_address = None
        
        # Start animation
        self.animation_step = 0
        self.animation_in_progress = True
        self.timer.start(1000)  # Animation step every 1000ms
        self.update()
    
    def next_animation_step(self):
        """Advance to the next animation step"""
        self.animation_step += 1
        if self.animation_step > 3:  # End of animation
            self.timer.stop()
            self.animation_in_progress = False
        self.update()
        
        # Start ball animation for address translation
        if self.animation_step == 1:
            # Animate from virtual address to page table
            width = self.width()
            height = self.height()
            
            va_x = width * 0.05
            va_y = height * 0.1
            va_width = width * 0.4
            va_height = height * 0.8
            
            pt_x = width * 0.5
            pt_y = height * 0.2
            pt_width = width * 0.15
            pt_height = height * 0.6
            
            # Start position (in virtual address space)
            start_x = va_x + va_width / 2
            start_y = va_y + (self.page_number * va_height / 10) + va_height / 20
            
            # End position (in page table)
            end_x = pt_x + pt_width / 2
            end_y = pt_y + pt_height / 2
            
            self.address_ball_pos = QPoint(int(start_x), int(start_y))
            self.address_ball_animation.setStartValue(self.address_ball_pos)
            self.address_ball_animation.setEndValue(QPoint(int(end_x), int(end_y)))
            self.address_ball_animation.start()
        
        elif self.animation_step == 2 and self.result == "success":
            # Animate from page table to physical address
            width = self.width()
            height = self.height()
            
            pt_x = width * 0.5
            pt_y = height * 0.2
            pt_width = width * 0.15
            pt_height = height * 0.6
            
            pa_x = width * 0.7
            pa_y = height * 0.1
            pa_width = width * 0.4
            pa_height = height * 0.8
            
            # Start position (in page table)
            start_x = pt_x + pt_width / 2
            start_y = pt_y + pt_height / 2
            
            # End position (in physical address space)
            end_x = pa_x + pa_width / 2
            end_y = pa_y + (self.frame_number * pa_height / 20) + pa_height / 40
            
            self.address_ball_pos = QPoint(int(start_x), int(start_y))
            self.address_ball_animation.setStartValue(self.address_ball_pos)
            self.address_ball_animation.setEndValue(QPoint(int(end_x), int(end_y)))
            self.address_ball_animation.start()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw background
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(COLORS['background']))
        gradient.setColorAt(1, QColor("#e0e0e0"))
        painter.fillRect(0, 0, width, height, gradient)
        
        # Set up fonts
        title_font = QFont("Arial", 12, QFont.Bold)
        label_font = QFont("Arial", 10)
        address_font = QFont("Courier New", 11, QFont.Bold)
        
        # Draw virtual address space (left side)
        va_width = width * 0.4
        va_height = height * 0.8
        va_x = width * 0.05
        va_y = height * 0.1
        
        # Draw a rounded rectangle for virtual address space
        path = QPainterPath()
        path.addRoundedRect(va_x, va_y, va_width, va_height, 10, 10)
        
        gradient = QLinearGradient(va_x, va_y, va_x + va_width, va_y)
        gradient.setColorAt(0, QColor(COLORS['virtual']))
        gradient.setColorAt(1, QColor(COLORS['virtual']).lighter(120))
        
        painter.fillPath(path, gradient)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawPath(path)
        
        # Draw virtual address title
        painter.setFont(title_font)
        painter.setPen(QPen(QColor(COLORS['text'])))
        painter.drawText(int(va_x), int(va_y - 20), int(va_width), 20, 
                        Qt.AlignCenter, "Virtual Address Space")
        
        # Draw page divisions in virtual address space
        painter.setPen(QPen(Qt.white, 1, Qt.DashLine))
        for i in range(1, 10):
            y = va_y + (i * va_height / 10)
            painter.drawLine(int(va_x), int(y), int(va_x + va_width), int(y))
            
            # Add page numbers
            painter.setPen(QPen(Qt.white))
            painter.setFont(label_font)
            painter.drawText(int(va_x + 5), int(y - va_height/10), 50, int(va_height/10), 
                            Qt.AlignVCenter | Qt.AlignLeft, f"Page {i-1}")
        
        # Draw page table (middle)
        pt_width = width * 0.15
        pt_height = height * 0.6
        pt_x = width * 0.5
        pt_y = height * 0.2
        
        # Draw a rounded rectangle for page table
        path = QPainterPath()
        path.addRoundedRect(pt_x, pt_y, pt_width, pt_height, 10, 10)
        
        gradient = QLinearGradient(pt_x, pt_y, pt_x + pt_width, pt_y)
        gradient.setColorAt(0, QColor(COLORS['arrow']))
        gradient.setColorAt(1, QColor(COLORS['arrow']).lighter(120))
        
        painter.fillPath(path, gradient)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawPath(path)
        
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.white))
        painter.drawText(int(pt_x), int(pt_y + 10), int(pt_width), 30, 
                        Qt.AlignCenter, "Page Table")
        
        # Draw physical address space (right side)
        pa_width = width * 0.4
        pa_height = height * 0.8
        pa_x = width * 0.7
        pa_y = height * 0.1
        
        # Draw a rounded rectangle for physical address space
        path = QPainterPath()
        path.addRoundedRect(pa_x, pa_y, pa_width, pa_height, 10, 10)
        
        gradient = QLinearGradient(pa_x, pa_y, pa_x + pa_width, pa_y)
        gradient.setColorAt(0, QColor(COLORS['physical']))
        gradient.setColorAt(1, QColor(COLORS['physical']).lighter(120))
        
        painter.fillPath(path, gradient)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawPath(path)
        
        # Draw physical address title
        painter.setFont(title_font)
        painter.setPen(QPen(QColor(COLORS['text'])))
        painter.drawText(int(pa_x), int(pa_y - 20), int(pa_width), 20, 
                        Qt.AlignCenter, "Physical Address Space")
        
        # Draw frame divisions in physical address space
        painter.setPen(QPen(Qt.white, 1, Qt.DashLine))
        for i in range(1, 20):
            y = pa_y + (i * pa_height / 20)
            painter.drawLine(int(pa_x), int(y), int(pa_x + pa_width), int(y))
            
            # Add frame numbers (every other frame to avoid clutter)
            if i % 2 == 0:
                painter.setPen(QPen(Qt.white))
                painter.setFont(label_font)
                painter.drawText(int(pa_x + 5), int(y - pa_height/20), 60, int(pa_height/20), 
                                Qt.AlignVCenter | Qt.AlignLeft, f"Frame {i-1}")
        
        # Draw virtual address details
        if self.animation_step >= 1:
            # Highlight virtual page in virtual address space
            page_height = va_height / 10  # Assuming 10 pages for visualization
            page_y = va_y + self.page_number * page_height
            
            # Draw a glowing highlight for the selected page
            highlight_path = QPainterPath()
            highlight_path.addRoundedRect(va_x + 5, page_y + 5, va_width - 10, page_height - 10, 5, 5)
            
            painter.setBrush(QBrush(QColor(COLORS['highlight'])))
            painter.setPen(QPen(Qt.white, 2))
            painter.drawPath(highlight_path)
            
            painter.setFont(label_font)
            painter.setPen(QPen(Qt.white))
            painter.drawText(int(va_x + 10), int(page_y), int(va_width - 20), int(page_height), 
                            Qt.AlignVCenter | Qt.AlignLeft, 
                            f"Page {self.page_number}")
            
            # Draw virtual address info
            painter.setFont(address_font)
            painter.setPen(QPen(QColor(COLORS['text'])))
            painter.drawText(int(va_x), int(va_y + va_height + 10), int(va_width), 30, 
                            Qt.AlignCenter, 
                            f"VA: 0x{self.virtual_address:08x}")
            
            painter.setFont(label_font)
            painter.drawText(int(va_x), int(va_y + va_height + 40), int(va_width), 20, 
                            Qt.AlignCenter, 
                            f"Page: {self.page_number} | Offset: {self.offset}")
        
        # Draw page table lookup
        if self.animation_step >= 2:
            # Draw page table entry
            entry_height = 30
            entry_y = pt_y + pt_height/2 - entry_height/2
            
            # Draw a glowing highlight for the page table entry
            highlight_path = QPainterPath()
            highlight_path.addRoundedRect(pt_x + 10, entry_y, pt_width - 20, entry_height, 5, 5)
            
            painter.setBrush(QBrush(QColor(COLORS['background'])))
            painter.setPen(QPen(Qt.white, 2))
            painter.drawPath(highlight_path)
            
            painter.setFont(label_font)
            painter.setPen(QPen(QColor(COLORS['text'])))
            
            if self.result == "success":
                painter.drawText(int(pt_x + 15), int(entry_y), int(pt_width - 30), int(entry_height), 
                                Qt.AlignVCenter | Qt.AlignLeft, 
                                f"VP: {self.page_number}\nPF: {self.frame_number}")
            else:
                # Page fault
                painter.setPen(QPen(QColor(COLORS['fault'])))
                painter.drawText(int(pt_x + 15), int(entry_y), int(pt_width - 30), int(entry_height), 
                                Qt.AlignVCenter | Qt.AlignLeft, 
                                f"Page Fault!")
        
        # Draw physical address details
        if self.animation_step >= 3 and self.result == "success":
            # Highlight physical frame in physical address space
            frame_height = pa_height / 20  # Assuming 20 frames for visualization
            frame_y = pa_y + self.frame_number * frame_height
            
            # Draw a glowing highlight for the selected frame
            highlight_path = QPainterPath()
            highlight_path.addRoundedRect(pa_x + 5, frame_y + 5, pa_width - 10, frame_height - 10, 5, 5)
            
            painter.setBrush(QBrush(QColor(COLORS['highlight'])))
            painter.setPen(QPen(Qt.white, 2))
            painter.drawPath(highlight_path)
            
            painter.setFont(label_font)
            painter.setPen(QPen(Qt.white))
            painter.drawText(int(pa_x + 10), int(frame_y), int(pa_width - 20), int(frame_height), 
                            Qt.AlignVCenter | Qt.AlignLeft, 
                            f"Frame {self.frame_number}")
            
            # Draw physical address info
            painter.setFont(address_font)
            painter.setPen(QPen(QColor(COLORS['text'])))
            painter.drawText(int(pa_x), int(pa_y + pa_height + 10), int(pa_width), 30, 
                            Qt.AlignCenter, 
                            f"PA: 0x{self.physical_address:08x}")
            
            painter.setFont(label_font)
            painter.drawText(int(pa_x), int(pa_y + pa_height + 40), int(pa_width), 20, 
                            Qt.AlignCenter, 
                            f"Frame: {self.frame_number} | Offset: {self.offset}")
        
        # Draw result status
        if self.animation_step >= 3:
            result_y = height * 0.95
            result_height = 30
            
            painter.setFont(title_font)
            
            if self.result == "success":
                painter.setPen(QPen(QColor(COLORS['highlight'])))
                painter.drawText(0, int(result_y), width, result_height, 
                                Qt.AlignCenter, "✓ Address translated successfully")
            else:
                painter.setPen(QPen(QColor(COLORS['fault'])))
                painter.drawText(0, int(result_y), width, result_height, 
                                Qt.AlignCenter, "⚠ Page Fault: Page not in memory")
        
        # Draw the animated address ball
        if self.animation_in_progress and self.animation_step < 3:
            painter.setBrush(QBrush(QColor(COLORS['highlight'])))
            painter.setPen(QPen(Qt.white, 2))
            painter.drawEllipse(self.address_ball_pos, 10, 10)

class PageReplacementWidget(QWidget):
    """Widget for visualizing page replacement algorithms"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 200)
        
        # Page replacement data
        self.algorithm = "LRU"  # LRU, FIFO, Clock
        self.frames = [None] * 5  # 5 physical frames
        self.reference_string = []
        self.current_step = 0
        self.page_faults = 0
        
        # Animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_step)
        self.animation_active = False
        
        # Generate initial reference string
        self.generate_reference_string()
    
    def generate_reference_string(self, length=20):
        """Generate a random page reference string"""
        self.reference_string = [random.randint(0, 9) for _ in range(length)]
        self.current_step = 0
        self.page_faults = 0
        self.frames = [None] * len(self.frames)
        self.update()
    
    def set_algorithm(self, algorithm):
        """Set the page replacement algorithm"""
        self.algorithm = algorithm
        self.current_step = 0
        self.page_faults = 0
        self.frames = [None] * len(self.frames)
        self.update()
    
    def start_animation(self):
        """Start the page replacement animation"""
        if not self.animation_active:
            self.animation_active = True
            self.timer.start(1000)  # Step every 1 second
    
    def stop_animation(self):
        """Stop the page replacement animation"""
        self.animation_active = False
        self.timer.stop()
    
    def next_step(self):
        """Process the next step in the page replacement algorithm"""
        if self.current_step >= len(self.reference_string):
            self.stop_animation()
            return
        
        page = self.reference_string[self.current_step]
        
        # Check if page is already in frames
        if page in self.frames:
            # Page hit
            if self.algorithm == "LRU":
                # Move the page to the end (most recently used)
                self.frames.remove(page)
                self.frames.append(page)
        else:
            # Page fault
            self.page_faults += 1
            
            if None in self.frames:
                # There's an empty frame
                index = self.frames.index(None)
                self.frames[index] = page
            else:
                # Need to replace a page
                if self.algorithm == "FIFO":
                    # Remove the first page (oldest)
                    self.frames.pop(0)
                    self.frames.append(page)
                elif self.algorithm == "LRU":
                    # Remove the first page (least recently used)
                    self.frames.pop(0)
                    self.frames.append(page)
                elif self.algorithm == "Clock":
                    # '

                    # Implement clock algorithm (simplified)
                    # In a real implementation, we would need to track reference bits
                    self.frames.pop(0)
                    self.frames.append(page)
        
        self.current_step += 1
        self.update()
        
        # Stop animation if we've reached the end
        if self.current_step >= len(self.reference_string):
            self.stop_animation()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw background
        painter.fillRect(0, 0, width, height, QBrush(QColor(COLORS['background'])))
        
        # Set up fonts
        title_font = QFont("Arial", 12, QFont.Bold)
        label_font = QFont("Arial", 10)
        
        # Draw title
        painter.setFont(title_font)
        painter.setPen(QPen(QColor(COLORS['text'])))
        painter.drawText(10, 10, width - 20, 30, 
                        Qt.AlignLeft | Qt.AlignVCenter, 
                        f"{self.algorithm} Page Replacement")
        
        # Draw statistics
        painter.setFont(label_font)
        painter.drawText(width - 200, 10, 190, 30, 
                        Qt.AlignRight | Qt.AlignVCenter, 
                        f"Page Faults: {self.page_faults}/{self.current_step}")
        
        # Draw reference string
        ref_width = width - 40
        ref_x = 20
        ref_y = 50
        ref_height = 40
        
        painter.setPen(QPen(QColor(COLORS['text'])))
        painter.drawText(ref_x, ref_y, ref_width, 20, 
                        Qt.AlignLeft, "Reference String:")
        
        # Draw reference string boxes
        box_width = min(30, ref_width / len(self.reference_string))
        
        for i, page in enumerate(self.reference_string):
            x = ref_x + i * box_width
            y = ref_y + 20
            
            # Highlight current step
            if i == self.current_step:
                painter.setBrush(QBrush(QColor(COLORS['highlight'])))
                painter.setPen(QPen(Qt.white, 2))
            elif i < self.current_step:
                painter.setBrush(QBrush(QColor(COLORS['virtual']).lighter(130)))
                painter.setPen(QPen(Qt.white, 1))
            else:
                painter.setBrush(QBrush(QColor("#dddddd")))
                painter.setPen(QPen(Qt.gray, 1))
            
            painter.drawRect(int(x), int(y), int(box_width - 2), int(ref_height - 2))
            
            painter.setPen(QPen(Qt.black if i >= self.current_step else Qt.white))
            painter.drawText(int(x), int(y), int(box_width - 2), int(ref_height - 2), 
                            Qt.AlignCenter, str(page))
        
        # Draw frames
        frame_x = 20
        frame_y = ref_y + ref_height + 20
        frame_width = width - 40
        frame_height = 40
        
        painter.setPen(QPen(QColor(COLORS['text'])))
        painter.drawText(frame_x, frame_y, frame_width, 20, 
                        Qt.AlignLeft, "Physical Frames:")
        
        # Draw frame boxes
        box_width = min(60, frame_width / len(self.frames))
        
        for i, page in enumerate(self.frames):
            x = frame_x + i * box_width
            y = frame_y + 20
            
            if page is not None:
                painter.setBrush(QBrush(QColor(COLORS['physical'])))
                painter.setPen(QPen(Qt.white, 2))
                painter.drawRect(int(x), int(y), int(box_width - 2), int(frame_height - 2))
                
                painter.setPen(QPen(Qt.white))
                painter.drawText(int(x), int(y), int(box_width - 2), int(frame_height - 2), 
                                Qt.AlignCenter, str(page))
            else:
                painter.setBrush(QBrush(QColor("#dddddd")))
                painter.setPen(QPen(Qt.gray, 1))
                painter.drawRect(int(x), int(y), int(box_width - 2), int(frame_height - 2))
                
                painter.setPen(QPen(Qt.gray))
                painter.drawText(int(x), int(y), int(box_width - 2), int(frame_height - 2), 
                                Qt.AlignCenter, "Empty")

class EnhancedPagingSystem(QMainWindow):
    """Enhanced paging system visualization"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Enhanced Paging System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Memory Address Translation & Page Replacement")
        title_label.setStyleSheet("""
            font-size: 18pt; 
            font-weight: bold; 
            color: #2c3e50;
            margin-bottom: 10px;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 5px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Create tab widget for different visualizations
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create address translation tab
        self.create_address_translation_tab()
        
        # Create page replacement tab
        self.create_page_replacement_tab()
        
        # Status bar for messages
        self.status_label = AnimatedLabel("Ready")
        self.status_label.setStyleSheet("""
            font-size: 11pt;
            padding: 5px;
            background-color: #f8f9fa;
            border-top: 1px solid #dee2e6;
        """)
        main_layout.addWidget(self.status_label)
    
    def create_address_translation_tab(self):
        """Create the address translation visualization tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create splitter for controls and visualization
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Process selection
        process_group = QGroupBox("Process Selection")
        process_layout = QVBoxLayout(process_group)
        
        process_label = QLabel("Select Process:")
        process_layout.addWidget(process_label)
        
        self.process_combo = QComboBox()
        self.process_combo.addItems(["Process A", "Process B", "Process C"])
        self.process_combo.currentIndexChanged.connect(self.on_process_change)
        process_layout.addWidget(self.process_combo)
        
        # Page size selection
        page_size_label = QLabel("Page Size:")
        process_layout.addWidget(page_size_label)
        
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["4 KB", "8 KB", "16 KB", "64 KB"])
        self.page_size_combo.currentIndexChanged.connect(self.on_page_size_change)
        process_layout.addWidget(self.page_size_combo)
        
        # Address input
        addr_label = QLabel("Virtual Address:")
        process_layout.addWidget(addr_label)
        
        addr_input_layout = QHBoxLayout()
        self.addr_input = QLineEdit()
        self.addr_input.setPlaceholderText("Enter decimal address")
        addr_input_layout.addWidget(self.addr_input)
        
        random_btn = QPushButton("Random")
        random_btn.clicked.connect(self.generate_random_address)
        random_btn.setStyleSheet("""
            background-color: #3498db;
            color: white;
            padding: 5px;
            border: none;
            border-radius: 3px;
        """)
        addr_input_layout.addWidget(random_btn)
        
        process_layout.addLayout(addr_input_layout)
        
        # Translate button
        translate_btn = QPushButton("Translate Address")
        translate_btn.clicked.connect(self.translate_address)
        translate_btn.setStyleSheet("""
            background-color: #2ecc71;
            color: white;
            padding: 8px;
            font-weight: bold;
            border: none;
            border-radius: 3px;
        """)
        process_layout.addWidget(translate_btn)
        
        left_layout.addWidget(process_group)
        
        # Page table
        table_group = QGroupBox("Page Table")
        table_layout = QVBoxLayout(table_group)
        
        self.page_table_widget = QTableWidget()
        self.page_table_widget.setColumnCount(5)
        self.page_table_widget.setHorizontalHeaderLabels([
            "Virtual Page", "Physical Frame", "Valid", "Referenced", "Modified"
        ])
        self.page_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        table_layout.addWidget(self.page_table_widget)
        
        left_layout.addWidget(table_group)
        
        # Right panel - Visualization
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.address_translation = AddressTranslationWidget()
        right_layout.addWidget(self.address_translation)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])  # Initial sizes
        
        # Add tab to tab widget
        self.tab_widget.addTab(tab, "Address Translation")
        
        # Initialize page table
        self.init_page_table()
    
    def create_page_replacement_tab(self):
        """Create the page replacement visualization tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Controls
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        # Algorithm selection
        algo_label = QLabel("Algorithm:")
        controls_layout.addWidget(algo_label)
        
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["FIFO", "LRU", "Clock"])
        self.algo_combo.currentTextChanged.connect(self.on_algorithm_change)
        controls_layout.addWidget(self.algo_combo)
        
        # Generate new reference string
        generate_btn = QPushButton("Generate New Reference String")
        generate_btn.clicked.connect(self.generate_new_reference)
        generate_btn.setStyleSheet("""
            background-color: #3498db;
            color: white;
            padding: 5px;
            border: none;
            border-radius: 3px;
        """)
        controls_layout.addWidget(generate_btn)
        
        # Start/Stop animation
        self.start_btn = QPushButton("Start Animation")
        self.start_btn.clicked.connect(self.toggle_animation)
        self.start_btn.setStyleSheet("""
            background-color: #2ecc71;
            color: white;
            padding: 5px;
            border: none;
            border-radius: 3px;
        """)
        controls_layout.addWidget(self.start_btn)
        
        # Step button
        step_btn = QPushButton("Step")
        step_btn.clicked.connect(self.step_animation)
        step_btn.setStyleSheet("""
            background-color: #f39c12;
            color: white;
            padding: 5px;
            border: none;
            border-radius: 3px;
        """)
        controls_layout.addWidget(step_btn)
        
        controls_layout.addStretch()
        
        layout.addWidget(controls_frame)
        
        # Page replacement visualization
        self.page_replacement = PageReplacementWidget()
        layout.addWidget(self.page_replacement)
        
        # Add explanation text
        explanation = QLabel("""
            <b>Page Replacement Algorithms:</b><br>
            <b>FIFO (First-In-First-Out):</b> Replaces the oldest page in memory.<br>
            <b>LRU (Least Recently Used):</b> Replaces the page that hasn't been used for the longest time.<br>
            <b>Clock:</b> A more efficient approximation of LRU using a circular buffer and reference bits.
        """)
        explanation.setStyleSheet("""
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        """)
        layout.addWidget(explanation)
        
        # Add tab to tab widget
        self.tab_widget.addTab(tab, "Page Replacement")
    
    def init_page_table(self):
        """Initialize the page table with sample entries"""
        # Clear existing entries
        self.page_table_widget.setRowCount(0)
        
        # Generate new entries based on selected process
        process_name = self.process_combo.currentText()
        num_pages = 10
        
        page_table = {}
        
        for i in range(num_pages):
            is_valid = random.random() < 0.8
            
            if process_name == "Process A":
                entry = PageTableEntry(
                    virtual_page=i,
                    physical_frame=random.randint(1, 20) if is_valid else 0,
                    valid_bit=1 if is_valid else 0,
                    referenced=1 if random.random() < 0.5 else 0,
                    modified=1 if random.random() < 0.3 else 0
                )
            elif process_name == "Process B":
                entry = PageTableEntry(
                    virtual_page=i,
                    physical_frame=(i % 10) + 1 if is_valid else 0,  # More predictable pattern
                    valid_bit=1 if is_valid else 0,
                    referenced=i % 2,  # Alternating pattern
                    modified=1 if i % 3 == 0 else 0  # Every third page modified
                )
            else:  # Process C
                entry = PageTableEntry(
                    virtual_page=i,
                    physical_frame=7 + i if is_valid else 0,  # Sequential frames
                    valid_bit=1 if i < 5 else 0,  # Only first five pages in memory
                    referenced=1 if i == 1 else 0,  # Only second page referenced
                    modified=1 if i == 0 else 0  # Only first page modified
                )
            
            page_table[i] = entry
        
        # Update address translation widget's page table
        self.address_translation.page_table = page_table
        
        # Populate table widget
        self.page_table_widget.setRowCount(num_pages)
        
        for i, entry in page_table.items():
            self.page_table_widget.setItem(i, 0, QTableWidgetItem(str(entry.virtual_page)))
            self.page_table_widget.setItem(i, 1, QTableWidgetItem(str(entry.physical_frame)))
            self.page_table_widget.setItem(i, 2, QTableWidgetItem(str(entry.valid_bit)))
            self.page_table_widget.setItem(i, 3, QTableWidgetItem(str(entry.referenced)))
            self.page_table_widget.setItem(i, 4, QTableWidgetItem(str(entry.modified)))
            
            # Highlight invalid pages
            if entry.valid_bit == 0:
                for col in range(5):
                    item = self.page_table_widget.item(i, col)
                    item.setBackground(QBrush(QColor(255, 200, 200)))
    
    def on_process_change(self):
        """Handle process selection change"""
        self.init_page_table()
        self.status_label.set_text_animated(f"Loaded page table for {self.process_combo.currentText()}")
    
    def on_page_size_change(self):
        """Handle page size selection change"""
        size_text = self.page_size_combo.currentText()
        size_kb = int(size_text.split()[0])
        self.address_translation.page_size = size_kb * 1024
        self.status_label.set_text_animated(f"Page size set to {size_text}")
    
    def generate_random_address(self):
        """Generate a random virtual address"""
        # Generate address within reasonable range (0-40KB)
        addr = random.randint(0, 40 * 1024)
        self.addr_input.setText(str(addr))
        self.status_label.set_text_animated(f"Generated random address: {addr}")
    
    def translate_address(self):
        """Translate the virtual address to physical address"""
        try:
            addr = int(self.addr_input.text())
            page_size = self.address_translation.page_size
            
            # Calculate page number and offset
            page_num = addr // page_size
            offset = addr % page_size
            
            # Look up in page table
            if page_num in self.address_translation.page_table:
                entry = self.address_translation.page_table[page_num]
                
                if entry.valid_bit == 1:
                    # Page is in memory
                    frame_num = entry.physical_frame
                    physical_addr = frame_num * page_size + offset
                    
                    # Update visualization
                    self.address_translation.set_address_mapping(
                        virtual_address=addr,
                        physical_address=physical_addr,
                        page_number=page_num,
                        frame_number=frame_num,
                        offset=offset,
                        result="success"
                    )
                    
                    # Update page table (mark as referenced)
                    entry.referenced = 1
                    self.page_table_widget.setItem(page_num, 3, QTableWidgetItem("1"))
                    
                    # 20% chance to modify the page
                    if random.random() < 0.2:
                        entry.modified = 1
                        self.page_table_widget.setItem(page_num, 4, QTableWidgetItem("1"))
                    
                    self.status_label.set_text_animated(
                        f"Address translated: VA 0x{addr:x} → PA 0x{physical_addr:x}"
                    )
                else:
                    # Page fault - not in memory
                    self.address_translation.set_address_mapping(
                        virtual_address=addr,
                        page_number=page_num,
                        offset=offset,
                        result="fault"
                    )
                    self.status_label.set_text_animated(
                        f"Page fault: Page {page_num} is not in memory"
                    )
            else:
                # Page fault - no page table entry
                self.address_translation.set_address_mapping(
                    virtual_address=addr,
                    page_number=page_num,
                    offset=offset,
                    result="fault"
                )
                self.status_label.set_text_animated(
                    f"Page fault: No page table entry for page {page_num}"
                )
        
        except ValueError:
            # Invalid input
            self.status_label.set_text_animated("Please enter a valid address")
    
    def on_algorithm_change(self, algorithm):
        """Handle page replacement algorithm change"""
        self.page_replacement.set_algorithm(algorithm)
        self.status_label.set_text_animated(f"Algorithm changed to {algorithm}")
    
    def generate_new_reference(self):
        """Generate a new page reference string"""
        self.page_replacement.generate_reference_string()
        self.status_label.set_text_animated("Generated new page reference string")
    
    def toggle_animation(self):
        """Toggle the page replacement animation"""
        if self.page_replacement.animation_active:
            self.page_replacement.stop_animation()
            self.start_btn.setText("Start Animation")
            self.start_btn.setStyleSheet("""
                background-color: #2ecc71;
                color: white;
                padding: 5px;
                border: none;
                border-radius: 3px;
            """)
            self.status_label.set_text_animated("Animation stopped")
        else:
            self.page_replacement.start_animation()
            self.start_btn.setText("Stop Animation")
            self.start_btn.setStyleSheet("""
                background-color: #e74c3c;
                color: white;
                padding: 5px;
                border: none;
                border-radius: 3px;
            """)
            self.status_label.set_text_animated("Animation started")
    
    def step_animation(self):
        """Step through the page replacement animation"""
        self.page_replacement.next_step()
        self.status_label.set_text_animated("Stepped to next reference")

def main():
    app = QApplication(sys.argv)
    window = EnhancedPagingSystem()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()