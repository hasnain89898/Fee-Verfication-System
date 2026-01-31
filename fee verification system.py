"""
Fee Verification System - Modern UI Edition
============================================
A beautifully designed desktop application for managing student fee submissions.
"""

import os
import sqlite3
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import shutil
import logging

# Optional libraries
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# --- Configuration ---
class Config:
    """Centralized configuration with modern color palette"""
    RECEIPTS_DIR = Path("receipts")
    CONFIRMATIONS_DIR = Path("confirmations")
    EXPORTS_DIR = Path("exports")
    DB_NAME = "fees.db"
    LOG_FILE = "fee_system.log"
    
    # Modern Color Palette - Vibrant and Professional
    COLORS = {
        # Primary gradient colors
        'primary': '#6366f1',        # Indigo
        'primary_dark': '#4f46e5',   # Darker Indigo
        'primary_light': '#818cf8',  # Light Indigo
        
        # Accent colors
        'accent': '#ec4899',         # Pink
        'accent_light': '#f9a8d4',   # Light Pink
        
        # Status colors
        'success': '#10b981',        # Emerald
        'warning': '#f59e0b',        # Amber
        'danger': '#ef4444',         # Red
        'info': '#3b82f6',           # Blue
        
        # Neutrals with warmth
        'bg_primary': '#f8fafc',     # Very light blue-gray
        'bg_secondary': '#ffffff',   # White
        'bg_dark': '#1e293b',        # Dark slate
        'bg_card': '#ffffff',        # Card background
        
        # Text colors
        'text_primary': '#0f172a',   # Almost black
        'text_secondary': '#64748b', # Slate gray
        'text_light': '#94a3b8',     # Light slate
        'text_white': '#ffffff',     # White
        
        # Borders and dividers
        'border': '#e2e8f0',         # Light border
        'border_hover': '#cbd5e1',   # Hover border
        
        # Special effects
        'shadow': 'rgba(100, 116, 139, 0.1)',
        'overlay': 'rgba(15, 23, 42, 0.6)',
    }
    
    DEPARTMENTS = [
        "Computer Science",
        "Information Technology",
        "Business Administration",
        "Electrical Engineering",
        "Mechanical Engineering",
        "Civil Engineering",
        "Other"
    ]
    
    STATUSES = ["Pending", "Verified", "Rejected"]
    
    @classmethod
    def setup_directories(cls):
        """Create necessary directories"""
        for directory in [cls.RECEIPTS_DIR, cls.CONFIRMATIONS_DIR, cls.EXPORTS_DIR]:
            directory.mkdir(exist_ok=True)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Database Layer ---
class Database:
    """Database operations handler"""
    
    def __init__(self, db_path=Config.DB_NAME):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    roll TEXT NOT NULL UNIQUE,
                    department TEXT NOT NULL,
                    fee_amount REAL NOT NULL,
                    receipt_path TEXT,
                    receipt_status TEXT DEFAULT 'Pending',
                    submitted_at TEXT NOT NULL,
                    updated_at TEXT,
                    notes TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    action TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT,
                    performed_by TEXT DEFAULT 'Admin',
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(id)
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
            self._insert_sample_data(cursor)
            conn.commit()
    
    def _insert_sample_data(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM students")
        if cursor.fetchone()[0] == 0:
            sample_data = [
                ("Ali Khan", "BSCS001", "Computer Science", 18300, "", "Pending"),
                ("Sara Ahmed", "BSIT002", "Information Technology", 15000, "", "Verified"),
                ("Omar Farooq", "BBA003", "Business Administration", 20000, "", "Pending"),
                ("Ayesha Noor", "BSE004", "Electrical Engineering", 19500, "", "Pending"),
                ("Hassan Raza", "BSCS005", "Computer Science", 18300, "", "Verified"),
            ]
            
            timestamp = self._get_timestamp()
            cursor.executemany(
                """INSERT INTO students 
                   (name, roll, department, fee_amount, receipt_path, receipt_status, submitted_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [(name, roll, dept, fee, receipt, status, timestamp) 
                 for name, roll, dept, fee, receipt, status in sample_data]
            )
            logger.info("Sample data inserted")
    
    @staticmethod
    def _get_timestamp():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def insert_student(self, name, roll, department, fee_amount, receipt_path=""):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                timestamp = self._get_timestamp()
                
                cursor.execute(
                    """INSERT INTO students 
                       (name, roll, department, fee_amount, receipt_path, receipt_status, submitted_at)
                       VALUES (?, ?, ?, ?, ?, 'Pending', ?)""",
                    (name, roll, department, fee_amount, receipt_path, timestamp)
                )
                
                student_id = cursor.lastrowid
                self._log_action(cursor, student_id, "Student Created", None, "Pending")
                conn.commit()
                logger.info(f"Student inserted: {roll} - {name}")
                return student_id
                
        except sqlite3.IntegrityError:
            logger.error(f"Duplicate roll number: {roll}")
            raise ValueError(f"Roll number {roll} already exists in the system")
        except Exception as e:
            logger.error(f"Error inserting student: {e}")
            raise
    
    def fetch_all_students(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, name, roll, department, fee_amount, receipt_path, 
                          receipt_status, submitted_at, updated_at, notes
                   FROM students ORDER BY id DESC"""
            )
            return cursor.fetchall()
    
    def fetch_student_by_id(self, student_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, name, roll, department, fee_amount, receipt_path,
                          receipt_status, submitted_at, updated_at, notes
                   FROM students WHERE id = ?""",
                (student_id,)
            )
            return cursor.fetchone()
    
    def update_receipt_status(self, student_id, new_status, notes=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT receipt_status FROM students WHERE id = ?", (student_id,))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Student ID {student_id} not found")
            
            old_status = result[0]
            timestamp = self._get_timestamp()
            
            if notes:
                cursor.execute(
                    "UPDATE students SET receipt_status = ?, updated_at = ?, notes = ? WHERE id = ?",
                    (new_status, timestamp, notes, student_id)
                )
            else:
                cursor.execute(
                    "UPDATE students SET receipt_status = ?, updated_at = ? WHERE id = ?",
                    (new_status, timestamp, student_id)
                )
            
            self._log_action(cursor, student_id, "Status Updated", old_status, new_status)
            conn.commit()
            logger.info(f"Updated student {student_id}: {old_status} -> {new_status}")
    
    def _log_action(self, cursor, student_id, action, old_status, new_status):
        timestamp = self._get_timestamp()
        cursor.execute(
            """INSERT INTO audit_log 
               (student_id, action, old_status, new_status, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (student_id, action, old_status, new_status, timestamp)
        )
    
    def search_students(self, search_term):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{search_term}%"
            cursor.execute(
                """SELECT id, name, roll, department, fee_amount, receipt_path,
                          receipt_status, submitted_at, updated_at, notes
                   FROM students 
                   WHERE name LIKE ? OR roll LIKE ?
                   ORDER BY id DESC""",
                (search_pattern, search_pattern)
            )
            return cursor.fetchall()
    
    def get_statistics(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM students")
            stats['total'] = cursor.fetchone()[0]
            
            for status in Config.STATUSES:
                cursor.execute("SELECT COUNT(*) FROM students WHERE receipt_status = ?", (status,))
                stats[status.lower()] = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(fee_amount) FROM students WHERE receipt_status = 'Verified'")
            result = cursor.fetchone()[0]
            stats['total_verified_fees'] = result if result else 0
            
            return stats

# --- File Handler ---
class FileHandler:
    """Handle file operations"""
    
    @staticmethod
    def copy_receipt(source_path):
        if not source_path or not os.path.exists(source_path):
            return ""
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(source_path).name
        dest_filename = f"{timestamp}_{filename}"
        dest_path = Config.RECEIPTS_DIR / dest_filename
        
        try:
            shutil.copy2(source_path, dest_path)
            logger.info(f"Receipt copied: {dest_path}")
            return str(dest_path)
        except Exception as e:
            logger.error(f"Error copying receipt: {e}")
            raise
    
    @staticmethod
    def generate_confirmation(student_data):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{student_data['roll']}_{timestamp}.txt"
        filepath = Config.CONFIRMATIONS_DIR / filename
        
        content = f"""
╔════════════════════════════════════════════════════════════╗
║          FEE VERIFICATION REQUEST CONFIRMATION             ║
╚════════════════════════════════════════════════════════════╝

Student Information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name:            {student_data['name']}
Roll Number:     {student_data['roll']}
Department:      {student_data['department']}
Fee Amount:      Rs. {student_data['fee_amount']:,.2f}
Submission Date: {datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your fee verification request has been submitted successfully.
Please keep this confirmation for your records.

Status: Pending Verification

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        try:
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"Confirmation generated: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error generating confirmation: {e}")
            raise
    
    @staticmethod
    def export_to_excel(students_data):
        if not PANDAS_AVAILABLE:
            raise RuntimeError(
                "pandas is not installed. "
                "Install it using: pip install pandas openpyxl"
            )
        
        df = pd.DataFrame(
            students_data,
            columns=[
                "ID", "Name", "Roll Number", "Department", "Fee Amount",
                "Receipt Path", "Status", "Submitted At", "Updated At", "Notes"
            ]
        )
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"students_export_{timestamp}.xlsx"
        filepath = Config.EXPORTS_DIR / filename
        
        try:
            df.to_excel(filepath, index=False, engine='openpyxl')
            logger.info(f"Data exported to Excel: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            raise

# --- Validators ---
class Validator:
    """Input validation"""
    
    @staticmethod
    def validate_name(name):
        if not name or len(name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if not all(c.isalpha() or c.isspace() for c in name):
            raise ValueError("Name can only contain letters and spaces")
        return name.strip()
    
    @staticmethod
    def validate_roll(roll):
        if not roll or len(roll.strip()) < 3:
            raise ValueError("Roll number must be at least 3 characters long")
        return roll.strip().upper()
    
    @staticmethod
    def validate_fee(fee_str):
        try:
            fee = float(fee_str.replace(",", "").strip())
            if fee <= 0:
                raise ValueError("Fee amount must be positive")
            if fee > 1000000:
                raise ValueError("Fee amount seems unreasonably high")
            return fee
        except ValueError as e:
            if "could not convert" in str(e):
                raise ValueError("Fee must be a valid number")
            raise

# --- Custom Widgets ---
class ModernButton(tk.Canvas):
    """Custom gradient button with hover effects"""
    
    def __init__(self, parent, text, command, color='primary', width=200, height=45):
        super().__init__(parent, width=width, height=height, highlightthickness=0, bg=Config.COLORS['bg_primary'])
        
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        
        if color == 'primary':
            self.color1 = Config.COLORS['primary']
            self.color2 = Config.COLORS['primary_dark']
        elif color == 'success':
            self.color1 = Config.COLORS['success']
            self.color2 = '#059669'
        elif color == 'accent':
            self.color1 = Config.COLORS['accent']
            self.color2 = '#db2777'
        else:
            self.color1 = color
            self.color2 = color
        
        self.draw_button(False)
        self.bind('<Button-1>', self.on_click)
        self.bind('<Enter>', lambda e: self.draw_button(True))
        self.bind('<Leave>', lambda e: self.draw_button(False))
    
    def draw_button(self, hover):
        self.delete('all')
        
        # Draw rounded rectangle with gradient effect
        if hover:
            fill_color = self.color2
        else:
            fill_color = self.color1
        
        # Create rounded rectangle
        self.create_rounded_rect(2, 2, self.width-2, self.height-2, 
                                radius=8, fill=fill_color, outline='')
        
        # Add text
        self.create_text(self.width/2, self.height/2, 
                        text=self.text, 
                        fill=Config.COLORS['text_white'],
                        font=('Segoe UI', 11, 'bold'))
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_click(self, event):
        if self.command:
            self.command()

class ModernEntry(ttk.Frame):
    """Custom styled entry with icon and label"""
    
    def __init__(self, parent, label, textvariable=None, **kwargs):
        super().__init__(parent)
        
        # Label
        label_widget = tk.Label(
            self, 
            text=label,
            font=('Segoe UI', 10, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_primary']
        )
        label_widget.pack(anchor='w', pady=(0, 5))
        
        # Entry
        self.entry = tk.Entry(
            self,
            textvariable=textvariable,
            font=('Segoe UI', 11),
            relief='flat',
            bd=0,
            bg=Config.COLORS['bg_secondary'],
            fg=Config.COLORS['text_primary'],
            insertbackground=Config.COLORS['primary'],
            **kwargs
        )
        self.entry.pack(fill='x', ipady=10, ipadx=15)
        
        # Add border frame
        self.entry.config(highlightthickness=2, 
                         highlightcolor=Config.COLORS['primary'],
                         highlightbackground=Config.COLORS['border'])

# --- GUI Application ---
class FeeVerificationApp:
    """Main application with modern UI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Fee Verification System")
        self.root.geometry("1300x850")
        
        # Set window background color
        self.root.configure(bg=Config.COLORS['bg_primary'])
        
        # Initialize database
        self.db = Database()
        
        # Initialize variables
        self.selected_receipt_path = ""
        
        # Setup styles
        self.setup_modern_styles()
        
        # Create widgets
        self.create_modern_layout()
        
        # Load initial data
        self.refresh_admin_table()
        self.update_statistics()
    
    def setup_modern_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure notebook
        style.configure('Modern.TNotebook', 
                       background=Config.COLORS['bg_primary'],
                       borderwidth=0)
        style.configure('Modern.TNotebook.Tab',
                       background=Config.COLORS['bg_secondary'],
                       foreground=Config.COLORS['text_secondary'],
                       padding=[20, 12],
                       font=('Segoe UI', 10, 'bold'),
                       borderwidth=0)
        style.map('Modern.TNotebook.Tab',
                 background=[('selected', Config.COLORS['primary'])],
                 foreground=[('selected', Config.COLORS['text_white'])])
        
        # Configure treeview
        style.configure('Modern.Treeview',
                       background=Config.COLORS['bg_secondary'],
                       foreground=Config.COLORS['text_primary'],
                       fieldbackground=Config.COLORS['bg_secondary'],
                       borderwidth=0,
                       font=('Segoe UI', 10),
                       rowheight=35)
        style.configure('Modern.Treeview.Heading',
                       background=Config.COLORS['primary'],
                       foreground=Config.COLORS['text_white'],
                       borderwidth=0,
                       font=('Segoe UI', 10, 'bold'))
        style.map('Modern.Treeview',
                 background=[('selected', Config.COLORS['primary_light'])])
        
        # Configure combobox
        style.configure('Modern.TCombobox',
                       background=Config.COLORS['bg_secondary'],
                       foreground=Config.COLORS['text_primary'],
                       fieldbackground=Config.COLORS['bg_secondary'],
                       borderwidth=2,
                       relief='flat',
                       padding=10,
                       font=('Segoe UI', 10))
    
    def create_modern_layout(self):
        """Create main layout with modern design"""
        # Main container
        main_container = tk.Frame(self.root, bg=Config.COLORS['bg_primary'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header
        header = tk.Frame(main_container, bg=Config.COLORS['primary'], height=80)
        header.pack(fill='x', pady=(0, 20))
        header.pack_propagate(False)
        
        # Header content
        title_label = tk.Label(
            header,
            text="💳 Fee Verification System",
            font=('Segoe UI', 24, 'bold'),
            fg=Config.COLORS['text_white'],
            bg=Config.COLORS['primary']
        )
        title_label.pack(side='left', padx=30, pady=20)
        
        subtitle = tk.Label(
            header,
            text="Manage student fee submissions efficiently",
            font=('Segoe UI', 11),
            fg=Config.COLORS['primary_light'],
            bg=Config.COLORS['primary']
        )
        subtitle.pack(side='left', padx=(0, 30))
        
        # Notebook
        self.notebook = ttk.Notebook(main_container, style='Modern.TNotebook')
        self.notebook.pack(fill='both', expand=True)
        
        # Create tabs
        self.create_student_tab_modern()
        self.create_admin_tab_modern()
        self.create_statistics_tab_modern()
    
    def create_student_tab_modern(self):
        """Create modern student submission tab"""
        # Main frame
        student_frame = tk.Frame(self.notebook, bg=Config.COLORS['bg_primary'])
        self.notebook.add(student_frame, text="📝 Student Submission")
        
        # Content container
        content = tk.Frame(student_frame, bg=Config.COLORS['bg_primary'])
        content.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Left panel - Form
        left_panel = tk.Frame(content, bg=Config.COLORS['bg_secondary'], relief='flat', bd=0)
        left_panel.pack(side='left', fill='both', padx=(0, 20), ipadx=30, ipady=30)
        
        # Form title
        form_title = tk.Label(
            left_panel,
            text="Submit Fee Verification",
            font=('Segoe UI', 18, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_secondary']
        )
        form_title.pack(anchor='w', pady=(0, 25))
        
        # Name
        self.name_var = tk.StringVar()
        name_entry = ModernEntry(left_panel, "Student Name *", textvariable=self.name_var, width=40)
        name_entry.pack(fill='x', pady=(0, 15))
        
        # Roll
        self.roll_var = tk.StringVar()
        roll_entry = ModernEntry(left_panel, "Roll Number *", textvariable=self.roll_var, width=40)
        roll_entry.pack(fill='x', pady=(0, 15))
        
        # Department
        dept_label = tk.Label(
            left_panel,
            text="Department *",
            font=('Segoe UI', 10, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_secondary']
        )
        dept_label.pack(anchor='w', pady=(0, 5))
        
        self.dept_var = tk.StringVar()
        dept_combo = ttk.Combobox(
            left_panel,
            textvariable=self.dept_var,
            values=Config.DEPARTMENTS,
            state='readonly',
            style='Modern.TCombobox',
            font=('Segoe UI', 10)
        )
        dept_combo.current(0)
        dept_combo.pack(fill='x', pady=(0, 15))
        
        # Fee
        self.fee_var = tk.StringVar()
        fee_entry = ModernEntry(left_panel, "Fee Amount (Rs.) *", textvariable=self.fee_var, width=40)
        fee_entry.pack(fill='x', pady=(0, 15))
        
        # Receipt upload
        receipt_label = tk.Label(
            left_panel,
            text="Upload Receipt",
            font=('Segoe UI', 10, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_secondary']
        )
        receipt_label.pack(anchor='w', pady=(0, 5))
        
        self.receipt_label = tk.Label(
            left_panel,
            text="No file selected",
            font=('Segoe UI', 9),
            fg=Config.COLORS['text_light'],
            bg=Config.COLORS['bg_secondary']
        )
        self.receipt_label.pack(anchor='w', pady=(0, 10))
        
        choose_btn = ModernButton(left_panel, "📎 Choose File", self.choose_receipt, 
                                 color=Config.COLORS['info'], width=180, height=40)
        choose_btn.pack(anchor='w', pady=(0, 25))
        
        # Submit button
        submit_btn = ModernButton(left_panel, "✓ Submit Fee Verification", 
                                 self.submit_fee, color='success', width=280, height=50)
        submit_btn.pack(anchor='w', pady=(0, 10))
        
        # Clear button
        clear_btn = ModernButton(left_panel, "Clear Form", self.clear_student_form,
                                color=Config.COLORS['text_secondary'], width=280, height=40)
        clear_btn.pack(anchor='w')
        
        # Right panel - Preview
        right_panel = tk.Frame(content, bg=Config.COLORS['bg_secondary'])
        right_panel.pack(side='left', fill='both', expand=True, ipadx=20, ipady=20)
        
        preview_title = tk.Label(
            right_panel,
            text="Submission Preview",
            font=('Segoe UI', 16, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_secondary']
        )
        preview_title.pack(anchor='w', padx=20, pady=(20, 15))
        
        # Preview text with custom styling
        preview_frame = tk.Frame(right_panel, bg=Config.COLORS['bg_primary'])
        preview_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.preview_text = tk.Text(
            preview_frame,
            wrap='word',
            font=('Consolas', 10),
            bg=Config.COLORS['bg_dark'],
            fg=Config.COLORS['text_white'],
            relief='flat',
            bd=0,
            padx=20,
            pady=20,
            state='disabled'
        )
        self.preview_text.pack(fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(self.preview_text, command=self.preview_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.preview_text.config(yscrollcommand=scrollbar.set)
    
    def create_admin_tab_modern(self):
        """Create modern admin panel tab"""
        admin_frame = tk.Frame(self.notebook, bg=Config.COLORS['bg_primary'])
        self.notebook.add(admin_frame, text="⚙️ Admin Panel")
        
        # Content
        content = tk.Frame(admin_frame, bg=Config.COLORS['bg_primary'])
        content.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Top controls
        top_frame = tk.Frame(content, bg=Config.COLORS['bg_secondary'], relief='flat')
        top_frame.pack(fill='x', pady=(0, 20), ipady=15, ipadx=20)
        
        # Buttons
        refresh_btn = ModernButton(top_frame, "🔄 Refresh", self.refresh_admin_table,
                                   width=120, height=40)
        refresh_btn.pack(side='left', padx=(0, 10))
        
        export_btn = ModernButton(top_frame, "📊 Export to Excel", self.export_data,
                                 color='success', width=160, height=40)
        export_btn.pack(side='left', padx=(0, 30))
        
        # Search
        search_label = tk.Label(
            top_frame,
            text="🔍 Search:",
            font=('Segoe UI', 10, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_secondary']
        )
        search_label.pack(side='left', padx=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            top_frame,
            textvariable=self.search_var,
            font=('Segoe UI', 10),
            relief='flat',
            bd=0,
            bg=Config.COLORS['bg_primary'],
            width=30,
            highlightthickness=2,
            highlightcolor=Config.COLORS['primary'],
            highlightbackground=Config.COLORS['border']
        )
        search_entry.pack(side='left', padx=(0, 10), ipady=8, ipadx=10)
        
        search_btn = ModernButton(top_frame, "Search", self.search_students,
                                 width=100, height=40)
        search_btn.pack(side='left')
        
        # Table frame
        table_frame = tk.Frame(content, bg=Config.COLORS['bg_secondary'])
        table_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient='vertical')
        h_scroll = ttk.Scrollbar(table_frame, orient='horizontal')
        
        # Treeview
        columns = ('ID', 'Name', 'Roll', 'Department', 'Fee', 'Status', 'Submitted')
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            style='Modern.Treeview'
        )
        
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)
        
        # Column configuration
        column_widths = {
            'ID': 60, 'Name': 180, 'Roll': 120, 
            'Department': 220, 'Fee': 120, 'Status': 100, 'Submitted': 180
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100), anchor='w')
        
        # Pack
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click
        self.tree.bind('<Double-1>', self.show_student_details)
        
        # Bottom controls
        bottom_frame = tk.Frame(content, bg=Config.COLORS['bg_secondary'], relief='flat')
        bottom_frame.pack(fill='x', ipady=15, ipadx=20)
        
        status_label = tk.Label(
            bottom_frame,
            text="Update Status:",
            font=('Segoe UI', 10, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_secondary']
        )
        status_label.pack(side='left', padx=(0, 10))
        
        self.status_var = tk.StringVar(value='Verified')
        status_combo = ttk.Combobox(
            bottom_frame,
            textvariable=self.status_var,
            values=Config.STATUSES,
            state='readonly',
            style='Modern.TCombobox',
            width=15,
            font=('Segoe UI', 10)
        )
        status_combo.pack(side='left', padx=(0, 15))
        
        notes_label = tk.Label(
            bottom_frame,
            text="Notes:",
            font=('Segoe UI', 10, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_secondary']
        )
        notes_label.pack(side='left', padx=(0, 10))
        
        self.notes_var = tk.StringVar()
        notes_entry = tk.Entry(
            bottom_frame,
            textvariable=self.notes_var,
            font=('Segoe UI', 10),
            relief='flat',
            bd=0,
            bg=Config.COLORS['bg_primary'],
            width=35,
            highlightthickness=2,
            highlightcolor=Config.COLORS['primary'],
            highlightbackground=Config.COLORS['border']
        )
        notes_entry.pack(side='left', padx=(0, 15), ipady=8, ipadx=10)
        
        update_btn = ModernButton(bottom_frame, "Update Selected", self.update_status,
                                 color='accent', width=150, height=40)
        update_btn.pack(side='left')
    
    def create_statistics_tab_modern(self):
        """Create modern statistics tab with gradient cards"""
        stats_frame = tk.Frame(self.notebook, bg=Config.COLORS['bg_primary'])
        self.notebook.add(stats_frame, text="📊 Statistics")
        
        # Content
        content = tk.Frame(stats_frame, bg=Config.COLORS['bg_primary'])
        content.pack(fill='both', expand=True, padx=40, pady=40)
        
        # Title
        title = tk.Label(
            content,
            text="System Statistics",
            font=('Segoe UI', 28, 'bold'),
            fg=Config.COLORS['text_primary'],
            bg=Config.COLORS['bg_primary']
        )
        title.pack(anchor='w', pady=(0, 30))
        
        # Stats container
        self.stats_container = tk.Frame(content, bg=Config.COLORS['bg_primary'])
        self.stats_container.pack(fill='both', expand=True)
    
    def update_statistics(self):
        """Update statistics with beautiful gradient cards"""
        # Clear previous
        for widget in self.stats_container.winfo_children():
            widget.destroy()
        
        stats = self.db.get_statistics()
        
        # Define stat cards with modern colors
        stat_cards = [
            {
                'title': 'Total Students',
                'value': stats['total'],
                'icon': '👥',
                'color1': '#6366f1',
                'color2': '#4f46e5',
                'text_color': '#ffffff'
            },
            {
                'title': 'Pending',
                'value': stats['pending'],
                'icon': '⏳',
                'color1': '#f59e0b',
                'color2': '#d97706',
                'text_color': '#ffffff'
            },
            {
                'title': 'Verified',
                'value': stats['verified'],
                'icon': '✓',
                'color1': '#10b981',
                'color2': '#059669',
                'text_color': '#ffffff'
            },
            {
                'title': 'Rejected',
                'value': stats['rejected'],
                'icon': '✗',
                'color1': '#ef4444',
                'color2': '#dc2626',
                'text_color': '#ffffff'
            },
            {
                'title': 'Total Verified Fees',
                'value': f"Rs. {stats['total_verified_fees']:,.0f}",
                'icon': '💰',
                'color1': '#ec4899',
                'color2': '#db2777',
                'text_color': '#ffffff'
            }
        ]
        
        # Create cards in grid
        for i, card_data in enumerate(stat_cards):
            self.create_stat_card(
                self.stats_container,
                card_data,
                row=i // 2,
                col=i % 2
            )
        
        # Configure grid
        self.stats_container.grid_columnconfigure(0, weight=1)
        self.stats_container.grid_columnconfigure(1, weight=1)
    
    def create_stat_card(self, parent, data, row, col):
        """Create a beautiful gradient stat card"""
        # Card frame
        card = tk.Canvas(
            parent,
            width=500,
            height=180,
            bg=Config.COLORS['bg_primary'],
            highlightthickness=0
        )
        card.grid(row=row, column=col, padx=15, pady=15, sticky='nsew')
        
        # Draw gradient background (simulated with single color)
        card.create_rectangle(
            0, 0, 500, 180,
            fill=data['color1'],
            outline='',
            width=0
        )
        
        # Icon
        card.create_text(
            40, 90,
            text=data['icon'],
            font=('Segoe UI', 48),
            fill=data['text_color'],
            anchor='w'
        )
        
        # Value
        card.create_text(
            140, 70,
            text=str(data['value']),
            font=('Segoe UI', 36, 'bold'),
            fill=data['text_color'],
            anchor='w'
        )
        
        # Title
        card.create_text(
            140, 115,
            text=data['title'],
            font=('Segoe UI', 14),
            fill=data['text_color'],
            anchor='w'
        )
    
    # --- Event Handlers ---
    
    def choose_receipt(self):
        filepath = filedialog.askopenfilename(
            title="Select Receipt File",
            filetypes=[
                ("All Files", "*.*"),
                ("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                ("PDF Files", "*.pdf")
            ]
        )
        
        if filepath:
            self.selected_receipt_path = filepath
            filename = os.path.basename(filepath)
            self.receipt_label.config(
                text=f"✓ {filename}",
                fg=Config.COLORS['success']
            )
    
    def submit_fee(self):
        try:
            name = Validator.validate_name(self.name_var.get())
            roll = Validator.validate_roll(self.roll_var.get())
            department = self.dept_var.get()
            fee_amount = Validator.validate_fee(self.fee_var.get())
            
            receipt_path = ""
            if self.selected_receipt_path:
                receipt_path = FileHandler.copy_receipt(self.selected_receipt_path)
            
            student_id = self.db.insert_student(name, roll, department, fee_amount, receipt_path)
            
            student_data = {
                'name': name,
                'roll': roll,
                'department': department,
                'fee_amount': fee_amount
            }
            confirmation_path = FileHandler.generate_confirmation(student_data)
            
            self.update_preview(student_data, confirmation_path)
            
            messagebox.showinfo(
                "Success ✓",
                f"Fee verification request submitted successfully!\n\n"
                f"Student ID: {student_id}\n"
                f"Roll Number: {roll}\n\n"
                f"Confirmation saved!"
            )
            
            self.clear_student_form()
            self.refresh_admin_table()
            self.update_statistics()
            
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            logger.error(f"Error submitting fee: {e}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def clear_student_form(self):
        self.name_var.set("")
        self.roll_var.set("")
        self.dept_var.set(Config.DEPARTMENTS[0])
        self.fee_var.set("")
        self.selected_receipt_path = ""
        self.receipt_label.config(text="No file selected", fg=Config.COLORS['text_light'])
        
        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.config(state='disabled')
    
    def update_preview(self, student_data, confirmation_path):
        preview = f"""
╔════════════════════════════════════════════════════════╗
║        FEE VERIFICATION SUBMITTED                      ║
╚════════════════════════════════════════════════════════╝

Student Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Name:        {student_data['name']}
  Roll:        {student_data['roll']}
  Department:  {student_data['department']}
  Fee Amount:  Rs. {student_data['fee_amount']:,.2f}

Status: ⏳ Pending Verification

Confirmation saved to:
{confirmation_path}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your request has been submitted successfully!
        """
        
        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', preview)
        self.preview_text.config(state='disabled')
    
    def refresh_admin_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        students = self.db.fetch_all_students()
        for student in students:
            # Color code status
            status = student[6]
            status_display = status
            if status == 'Verified':
                status_display = '✓ Verified'
            elif status == 'Pending':
                status_display = '⏳ Pending'
            elif status == 'Rejected':
                status_display = '✗ Rejected'
            
            self.tree.insert('', 'end', values=(
                student[0],
                student[1],
                student[2],
                student[3],
                f"Rs. {student[4]:,.2f}",
                status_display,
                student[7]
            ))
    
    def search_students(self):
        search_term = self.search_var.get().strip()
        
        if not search_term:
            self.refresh_admin_table()
            return
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        results = self.db.search_students(search_term)
        for student in results:
            status = student[6]
            status_display = status
            if status == 'Verified':
                status_display = '✓ Verified'
            elif status == 'Pending':
                status_display = '⏳ Pending'
            elif status == 'Rejected':
                status_display = '✗ Rejected'
            
            self.tree.insert('', 'end', values=(
                student[0],
                student[1],
                student[2],
                student[3],
                f"Rs. {student[4]:,.2f}",
                status_display,
                student[7]
            ))
        
        if not results:
            messagebox.showinfo("No Results", f"No students found matching '{search_term}'")
    
    def show_student_details(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        student_id = item['values'][0]
        
        student = self.db.fetch_student_by_id(student_id)
        if not student:
            return
        
        details = f"""
╔════════════════════════════════════════════════════════╗
║              STUDENT DETAILS                           ║
╚════════════════════════════════════════════════════════╝

ID:              {student[0]}
Name:            {student[1]}
Roll Number:     {student[2]}
Department:      {student[3]}
Fee Amount:      Rs. {student[4]:,.2f}
Status:          {student[6]}
Submitted At:    {student[7]}
Updated At:      {student[8] or 'N/A'}

Receipt Path:    {student[5] or 'No receipt uploaded'}
Notes:           {student[9] or 'None'}
        """
        
        if student[5] and os.path.exists(student[5]):
            if messagebox.askyesno("Student Details", details + "\n\nOpen receipt file?"):
                self.open_file(student[5])
        else:
            messagebox.showinfo("Student Details", details)
    
    def open_file(self, filepath):
        try:
            if os.name == 'nt':
                os.startfile(filepath)
            elif os.name == 'posix':
                import subprocess
                if os.uname().sysname == 'Darwin':
                    subprocess.call(['open', filepath])
                else:
                    subprocess.call(['xdg-open', filepath])
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            messagebox.showerror("Error", f"Could not open file:\n{filepath}")
    
    def update_status(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a student from the table")
            return
        
        item = self.tree.item(selection[0])
        student_id = item['values'][0]
        new_status = self.status_var.get()
        notes = self.notes_var.get().strip() or None
        
        try:
            self.db.update_receipt_status(student_id, new_status, notes)
            messagebox.showinfo("Success ✓", f"Status updated to '{new_status}'")
            
            self.notes_var.set("")
            self.refresh_admin_table()
            self.update_statistics()
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            messagebox.showerror("Error", str(e))
    
    def export_data(self):
        try:
            students = self.db.fetch_all_students()
            filepath = FileHandler.export_to_excel(students)
            
            messagebox.showinfo(
                "Export Successful ✓",
                f"Data exported successfully to:\n{filepath}"
            )
            
            if messagebox.askyesno("Open File", "Would you like to open the exported file?"):
                self.open_file(filepath)
                
        except RuntimeError as e:
            messagebox.showerror("Export Error", str(e))
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            messagebox.showerror("Error", f"An error occurred during export:\n{str(e)}")

# --- Main Entry Point ---
def main():
    Config.setup_directories()
    
    root = tk.Tk()
    app = FeeVerificationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()