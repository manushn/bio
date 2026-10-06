"""
College Biometric Attendance System
Modern Enterprise Administration Edition (eTimeTrackLite Replacement)
Built with Python & Clean Enterprise TTK/Tkinter UI
Architecture: Left Sidebar Navigation • Modern Cards • High-Contrast Typography
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import os
import threading
from datetime import datetime, timedelta

from database import (
    init_db, get_connection, get_device_settings, 
    update_device_settings, update_last_sync,
    verify_admin_login, change_admin_password,
    export_database_backup, restore_database_backup,
    sync_users_from_device, get_all_active_staff_list,
    get_attendance_rules, update_attendance_rules
)
from device_driver import BiometricDriver
from attendance_engine import (
    calculate_daily_attendance, get_attendance_report, get_report_statistics
)
from pdf_generator import PDFReportGenerator

# 12 College Departments
COLLEGE_DEPARTMENTS = [
    "AI & DS",
    "CSE",
    "IT",
    "ECE",
    "EEE",
    "MECH",
    "Physics",
    "Chemistry",
    "English",
    "Administration",
    "Library",
    "Maintenance"
]

# Clean Modern Enterprise Color System
COLOR_BG = "#F8FAFC"            # Slate 50 - Very light gray canvas
COLOR_SURFACE = "#FFFFFF"       # Pure white cards & tables
COLOR_BORDER = "#E2E8F0"        # Slate 200 - Subtle 1px borders
COLOR_BORDER_FOCUS = "#CBD5E1"  # Slate 300 - Input borders

COLOR_PRIMARY = "#2563EB"       # Modern Royal Blue
COLOR_PRIMARY_HOVER = "#1D4ED8" # Blue 700
COLOR_PRIMARY_LIGHT = "#EFF6FF" # Blue 50 - Selected pills/rows

COLOR_TEXT_MAIN = "#0F172A"     # Slate 900 - Dark charcoal
COLOR_TEXT_SECONDARY = "#475569"# Slate 600 - Readable medium gray
COLOR_TEXT_MUTED = "#64748B"    # Slate 500 - Metadata & labels

COLOR_SUCCESS = "#059669"       # Emerald 600
COLOR_SUCCESS_BG = "#ECFDF5"    # Emerald 50
COLOR_SUCCESS_BORDER = "#A7F3D0"# Emerald 200

COLOR_DANGER = "#DC2626"        # Red 600
COLOR_DANGER_BG = "#FEF2F2"     # Red 50
COLOR_DANGER_BORDER = "#FECACA" # Red 200

COLOR_WARNING = "#D97706"       # Amber 600
COLOR_WARNING_BG = "#FFFBEB"    # Amber 50
COLOR_WARNING_BORDER = "#FDE68A"# Amber 200

def format_date_display(d_str):
    """Formats YYYY-MM-DD into a clean '05 Oct 26' format."""
    try:
        dt = datetime.strptime(d_str, "%Y-%m-%d")
        return dt.strftime("%d %b %y")
    except Exception:
        return d_str

class AttendanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NICETECH_biometric — Attendance Administration")
        self.geometry("1260x820")
        self.minsize(1050, 680)
        self.configure(bg=COLOR_BG)

        # Database initialization & initial calculations
        init_db()
        calculate_daily_attendance()

        # Session authentication state
        self.logged_in_user = None
        self._clock_started = False

        # Modern TTK styling
        self._setup_ttk_styles()

        # Build Main Application Shell (hidden until authentication)
        self._build_top_bar()
        self._build_main_layout()

        # Build and present the Login Screen
        self._build_login_screen()
        self._show_login_screen()

    # =========================================================================
    # THEME & TTK STYLES
    # =========================================================================
    def _setup_ttk_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        # Treeview (Tables) - Clean, borderless, high contrast
        style.configure('Treeview',
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT_MAIN,
            fieldbackground=COLOR_SURFACE,
            font=('Helvetica', 9),
            rowheight=34,
            borderwidth=0
        )
        style.configure('Treeview.Heading',
            background=COLOR_BG,
            foreground=COLOR_TEXT_MAIN,
            font=('Helvetica', 9, 'bold'),
            relief='flat',
            borderwidth=0,
            padding=[8, 8]
        )
        style.map('Treeview',
            background=[('selected', COLOR_PRIMARY_LIGHT)],
            foreground=[('selected', COLOR_PRIMARY)]
        )

        # Combobox
        style.configure('TCombobox',
            fieldbackground=COLOR_SURFACE,
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT_MAIN,
            selectbackground=COLOR_PRIMARY_LIGHT,
            selectforeground=COLOR_PRIMARY,
            padding=4
        )

        # Scrollbar
        style.configure('Vertical.TScrollbar',
            gripcount=0,
            background=COLOR_SURFACE,
            troughcolor=COLOR_BG,
            borderwidth=0,
            arrowsize=12
        )

    # =========================================================================
    # TOP BAR (Clean header, Page title, Device Status, Time)
    # =========================================================================
    def _build_top_bar(self):
        self.top_bar = tk.Frame(self, bg=COLOR_SURFACE, height=64, highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.top_bar.pack(fill=tk.X, side=tk.TOP)
        self.top_bar.pack_propagate(False)

        # Left: College Logo & Current Page Identity
        left_box = tk.Frame(self.top_bar, bg=COLOR_SURFACE)
        left_box.pack(side=tk.LEFT, padx=20, pady=10)

        icon_lbl = tk.Label(left_box, text="🏛️", font=('Helvetica', 18), bg=COLOR_SURFACE)
        icon_lbl.pack(side=tk.LEFT, padx=(0, 10))

        title_box = tk.Frame(left_box, bg=COLOR_SURFACE)
        title_box.pack(side=tk.LEFT)

        settings = get_device_settings()
        self.lbl_college_title = tk.Label(
            title_box,
            text=settings.get('college_name', 'COLLEGE OF ENGINEERING & TECHNOLOGY'),
            font=('Helvetica', 11, 'bold'),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE
        )
        self.lbl_college_title.pack(anchor=tk.W)

        self.lbl_page_title = tk.Label(
            title_box,
            text="Dashboard Overview",
            font=('Helvetica', 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_SURFACE
        )
        self.lbl_page_title.pack(anchor=tk.W)

        # Right: Connection Status & Clock
        right_box = tk.Frame(self.top_bar, bg=COLOR_SURFACE)
        right_box.pack(side=tk.RIGHT, padx=20, pady=10)

        # Connection Status Widget (Visually Obvious, No Huge Distracting Banner)
        self.status_container = tk.Frame(
            right_box,
            bg=COLOR_WARNING_BG,
            highlightthickness=1,
            highlightbackground=COLOR_WARNING_BORDER,
            padx=12,
            pady=4
        )
        self.status_container.pack(side=tk.LEFT, padx=10)

        self.lbl_status_badge = tk.Label(
            self.status_container,
            text="● Connecting...",
            font=('Helvetica', 9, 'bold'),
            fg=COLOR_WARNING,
            bg=COLOR_WARNING_BG
        )
        self.lbl_status_badge.pack(anchor=tk.W)

        self.lbl_status_details = tk.Label(
            self.status_container,
            text=f"{settings.get('ip_address', '192.168.1.201')} : {settings.get('port', 4370)}",
            font=('Helvetica', 7),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_WARNING_BG
        )
        self.lbl_status_details.pack(anchor=tk.W)

        # Digital Clock
        self.clock_lbl = tk.Label(
            right_box,
            text="🕒 --:--:--",
            font=('Helvetica', 9, 'bold'),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_BG,
            padx=12,
            pady=8,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER
        )
        self.clock_lbl.pack(side=tk.LEFT)

        # Current User Badge & Logout
        self.lbl_user_badge = tk.Label(
            right_box,
            text="👤 Admin: niadmin",
            font=('Helvetica', 9, 'bold'),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_BG,
            padx=12,
            pady=8,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER
        )
        self.lbl_user_badge.pack(side=tk.LEFT, padx=(10, 6))

        self.btn_logout = tk.Button(
            right_box,
            text="🚪  Logout",
            font=('Helvetica', 9, 'bold'),
            bg='#FFFFFF',
            fg='#000000',
            activebackground='#F1F5F9',
            activeforeground='#000000',
            highlightthickness=1,
            highlightbackground='#CBD5E1',
            bd=0,
            padx=12,
            pady=7,
            cursor='hand2',
            command=self._action_logout
        )
        self.btn_logout.pack(side=tk.LEFT)

    def _tick_clock(self):
        now_str = datetime.now().strftime("🕒 %I:%M:%S %p")
        self.clock_lbl.config(text=now_str)
        self.after(1000, self._tick_clock)

    # =========================================================================
    # MAIN WORKSPACE SHELL (Sidebar + Content Pages)
    # =========================================================================
    def _build_main_layout(self):
        self.workspace = tk.Frame(self, bg=COLOR_BG)
        self.workspace.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar (Clean White, 1px Border)
        self.sidebar = tk.Frame(self.workspace, bg=COLOR_SURFACE, width=220, highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Content Container (Light Canvas)
        self.content_area = tk.Frame(self.workspace, bg=COLOR_BG)
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=22, pady=18)

        # Sidebar Menu
        menu_top = tk.Frame(self.sidebar, bg=COLOR_SURFACE)
        menu_top.pack(fill=tk.X, pady=16)

        tk.Label(menu_top, text="NAVIGATION", font=('Helvetica', 8, 'bold'), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W, padx=20, pady=(0, 6))

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "📊   Dashboard", self._show_dashboard_view),
            ("staff", "👥   Staff Directory", self._show_staff_view),
            ("attendance", "📋   Attendance Report", self._show_attendance_view),
            ("audit", "⚡   Audit Punch Logs", self._show_audit_view),
            ("settings", "⚙️   Device Settings", self._show_settings_view),
        ]

        for key, text, cmd in nav_items:
            btn = tk.Button(
                menu_top,
                text=text,
                font=('Helvetica', 10, 'bold'),
                fg='#000000',
                bg='#FFFFFF',
                activebackground='#F1F5F9',
                activeforeground='#000000',
                anchor=tk.W,
                padx=20,
                pady=10,
                bd=0,
                cursor='hand2',
                command=cmd
            )
            btn.pack(fill=tk.X)
            self.nav_buttons[key] = btn

        # Sidebar Footer: Quick Download Attendance
        sidebar_bottom = tk.Frame(self.sidebar, bg=COLOR_SURFACE)
        sidebar_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=18)

        btn_quick_sync = tk.Button(
            sidebar_bottom,
            text="↓ Download Attendance",
            font=('Helvetica', 9, 'bold'),
            bg='#FFFFFF',
            fg='#000000',
            activebackground='#F1F5F9',
            activeforeground='#000000',
            highlightthickness=1,
            highlightbackground='#CBD5E1',
            bd=0,
            padx=10,
            pady=9,
            cursor='hand2',
            command=self._action_download_logs
        )
        btn_quick_sync.pack(fill=tk.X)

        # Build All 5 Pages
        self.view_dashboard = tk.Frame(self.content_area, bg=COLOR_BG)
        self.view_staff = tk.Frame(self.content_area, bg=COLOR_BG)
        self.view_attendance = tk.Frame(self.content_area, bg=COLOR_BG)
        self.view_audit = tk.Frame(self.content_area, bg=COLOR_BG)
        self.view_settings = tk.Frame(self.content_area, bg=COLOR_BG)

        self._build_dashboard_page()
        self._build_staff_page()
        self._build_attendance_page()
        self._build_audit_page()
        self._build_settings_page()

    def show_view(self, key):
        """Swaps views cleanly and updates top bar subtitle & active navigation."""
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.config(bg='#F1F5F9', fg='#000000')
            else:
                btn.config(bg='#FFFFFF', fg='#000000')

        self.view_dashboard.pack_forget()
        self.view_staff.pack_forget()
        self.view_attendance.pack_forget()
        self.view_audit.pack_forget()
        self.view_settings.pack_forget()

        titles = {
            "dashboard": "Dashboard Overview",
            "staff": "Staff Directory & Roles",
            "attendance": "Official Attendance Report (In / Out)",
            "audit": "Technical Audit Punch Logs (Machine Audit Trail)",
            "settings": "Biometric Terminal Configuration & Diagnostics"
        }
        self.lbl_page_title.config(text=titles.get(key, ""))

        if key == "dashboard":
            self.view_dashboard.pack(fill=tk.BOTH, expand=True)
            self._refresh_dashboard()
        elif key == "staff":
            self.view_staff.pack(fill=tk.BOTH, expand=True)
            self._refresh_staff_tab()
        elif key == "attendance":
            self.view_attendance.pack(fill=tk.BOTH, expand=True)
            self._refresh_attendance_report()
        elif key == "audit":
            self.view_audit.pack(fill=tk.BOTH, expand=True)
            self._refresh_raw_logs()
        elif key == "settings":
            self.view_settings.pack(fill=tk.BOTH, expand=True)

    def _show_dashboard_view(self): self.show_view("dashboard")
    def _show_staff_view(self): self.show_view("staff")
    def _show_attendance_view(self): self.show_view("attendance")
    def _show_audit_view(self): self.show_view("audit")
    def _show_settings_view(self): self.show_view("settings")

    # =========================================================================
    # LOGIN SCREEN (Enterprise Authentication Portal)
    # =========================================================================
    def _build_login_screen(self):
        self.login_frame = tk.Frame(self, bg=COLOR_BG)

        # Center wrapper keeps login card centered in window
        center_wrapper = tk.Frame(self.login_frame, bg=COLOR_BG)
        center_wrapper.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # High-Elevation Modern White Card
        card = tk.Frame(
            center_wrapper,
            bg=COLOR_SURFACE,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            padx=44,
            pady=38
        )
        card.pack()

        # Institution Logo & Title
        tk.Label(card, text="🏛️", font=('Helvetica', 34), bg=COLOR_SURFACE).pack(pady=(0, 6))

        settings = get_device_settings()
        college_name = settings.get('college_name', 'COLLEGE OF ENGINEERING & TECHNOLOGY')
        tk.Label(
            card,
            text=college_name.upper(),
            font=('Helvetica', 10, 'bold'),
            fg=COLOR_PRIMARY,
            bg=COLOR_SURFACE
        ).pack(pady=(0, 4))

        tk.Label(
            card,
            text="Biometric Attendance Portal",
            font=('Helvetica', 16, 'bold'),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE
        ).pack(pady=(0, 2))

        tk.Label(
            card,
            text="Administrator Sign In",
            font=('Helvetica', 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_SURFACE
        ).pack(pady=(0, 20))

        # Form Inputs
        form_box = tk.Frame(card, bg=COLOR_SURFACE)
        form_box.pack(fill=tk.X, pady=(0, 10))

        tk.Label(form_box, text="Username", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 4))
        self.txt_login_user = ttk.Entry(form_box, font=('Helvetica', 10), width=32)
        self.txt_login_user.insert(0, "niadmin")
        self.txt_login_user.pack(fill=tk.X, pady=(0, 14))

        tk.Label(form_box, text="Password", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 4))
        self.txt_login_pass = ttk.Entry(form_box, font=('Helvetica', 10), width=32, show="•")
        self.txt_login_pass.pack(fill=tk.X, pady=(0, 10))

        # Status / Error Feedback Label
        self.lbl_login_msg = tk.Label(card, text="", font=('Helvetica', 9, 'bold'), fg=COLOR_DANGER, bg=COLOR_SURFACE)
        self.lbl_login_msg.pack(pady=(0, 10))

        # Sign In Button (Black text on White background with crisp border)
        self.btn_login = tk.Button(
            card,
            text="Sign In to Portal  →",
            font=('Helvetica', 10, 'bold'),
            bg='#FFFFFF',
            fg='#000000',
            activebackground='#F1F5F9',
            activeforeground='#000000',
            highlightthickness=1,
            highlightbackground='#000000',
            bd=0,
            padx=20,
            pady=10,
            cursor='hand2',
            command=self._action_do_login
        )
        self.btn_login.pack(fill=tk.X, pady=(0, 16))

        # Default Credentials Hint Box
        hint_box = tk.Frame(
            card,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            padx=14,
            pady=9
        )
        hint_box.pack(fill=tk.X)

        tk.Label(
            hint_box,
            text="Default Login Credentials:\nUsername: niadmin  •  Password: ni2027",
            font=('Helvetica', 8),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_BG,
            justify=tk.CENTER
        ).pack()

        # Keyboard shortcuts
        self.txt_login_user.bind('<Return>', lambda e: self.txt_login_pass.focus_set())
        self.txt_login_pass.bind('<Return>', lambda e: self._action_do_login())

    def _show_login_screen(self):
        self.top_bar.pack_forget()
        self.workspace.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.lbl_login_msg.config(text="")
        self.txt_login_pass.delete(0, tk.END)
        self.txt_login_pass.focus_set()

    def _action_do_login(self):
        u = self.txt_login_user.get().strip()
        p = self.txt_login_pass.get().strip()
        if not u or not p:
            self.lbl_login_msg.config(text="Please enter both username and password.", fg=COLOR_DANGER)
            return

        ok, user_data = verify_admin_login(u, p)
        if ok:
            self.logged_in_user = user_data['username']
            self.lbl_login_msg.config(text="")
            self.login_frame.pack_forget()

            # Restore and display top bar & workspace
            self.top_bar.pack(fill=tk.X, side=tk.TOP)
            self.workspace.pack(fill=tk.BOTH, expand=True)
            self.lbl_user_badge.config(text=f"👤 Admin: {self.logged_in_user}")

            # Start clock and async hardware probe if not yet started
            if not getattr(self, '_clock_started', False):
                self._clock_started = True
                self._tick_clock()
                self.after(300, self._check_device_status_async)

            self.show_view("dashboard")
        else:
            self.lbl_login_msg.config(text="✕ Invalid username or password. Please try again.", fg=COLOR_DANGER)
            self.txt_login_pass.delete(0, tk.END)
            self.txt_login_pass.focus_set()

    def _action_logout(self):
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to log out of the administration portal?"):
            self.logged_in_user = None
            self._show_login_screen()

    # =========================================================================
    # PAGE 1: DASHBOARD (Clean Summary Cards & Quick Actions)
    # =========================================================================
    def _build_dashboard_page(self):
        container = self.view_dashboard

        # Header Title
        tk.Label(container, text="Attendance Overview", font=('Helvetica', 14, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_BG).pack(anchor=tk.W, pady=(0, 14))

        # 5 Clean Summary Cards (Consistent spacing, large numbers, supporting info)
        kpi_row = tk.Frame(container, bg=COLOR_BG)
        kpi_row.pack(fill=tk.X, pady=(0, 16))

        self.kpi_total_staff = self._create_summary_card(kpi_row, "TOTAL STAFF", "0", "👥 Active members", 0)
        self.kpi_present_today = self._create_summary_card(kpi_row, "PRESENT TODAY", "0", "✓ Verified punches", 1)
        self.kpi_absent_today = self._create_summary_card(kpi_row, "ABSENT TODAY", "0", "✕ No punches recorded", 2)
        self.kpi_rate_today = self._create_summary_card(kpi_row, "ATTENDANCE RATE", "0%", "Calculated today", 3)
        self.kpi_device_stat = self._create_summary_card(kpi_row, "DEVICE STATUS", "Checking...", "192.168.1.201", 4)

        # Split Lower Cards: Quick Actions & Live Hardware Activity Stream
        lower_row = tk.Frame(container, bg=COLOR_BG)
        lower_row.pack(fill=tk.BOTH, expand=True)

        # Left Card: Quick Device Actions
        actions_card = tk.Frame(lower_row, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=20, pady=18)
        actions_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        tk.Label(actions_card, text="Quick Terminal Operations", font=('Helvetica', 11, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 6))
        tk.Label(actions_card, text="Manage biometric hardware synchronization and daily calculations.", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 14))

        self._create_primary_btn(actions_card, "↓  Download Attendance Logs", self._action_download_logs).pack(fill=tk.X, pady=4)
        self._create_outline_btn(actions_card, "📥  Fetch Enrolled Staff from Terminal", self._action_fetch_staff_from_device).pack(fill=tk.X, pady=4)
        self._create_outline_btn(actions_card, "🔍  Test Terminal Connection", self._action_test_connection).pack(fill=tk.X, pady=4)
        self._create_outline_btn(actions_card, "🕒  Synchronize Terminal Clock", self._action_sync_time).pack(fill=tk.X, pady=4)
        self._create_outline_btn(actions_card, "⚙️  Recalculate Attendance", self._action_process_attendance).pack(fill=tk.X, pady=4)
        self._create_outline_btn(actions_card, "💾  Download Database Backup", self._action_export_backup).pack(fill=tk.X, pady=4)

        # Right Card: Activity & Hardware Log
        log_card = tk.Frame(lower_row, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=20, pady=18)
        log_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(log_card, text="Recent System Activity", font=('Helvetica', 11, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(log_card, text="Live diagnostics and connection event log.", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 10))

        log_box = tk.Frame(log_card, bg=COLOR_SURFACE)
        log_box.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_box,
            wrap=tk.WORD,
            font=('Courier', 9),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MAIN,
            bd=0,
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER
        )
        scroll = ttk.Scrollbar(log_box, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._log("System initialized. Database ready.")

    def _create_summary_card(self, parent, title, value, subtext, col):
        card = tk.Frame(parent, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=16, pady=14)
        card.grid(row=0, column=col, sticky='nsew', padx=4)
        parent.columnconfigure(col, weight=1)

        tk.Label(card, text=title, font=('Helvetica', 8, 'bold'), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W)
        lbl_val = tk.Label(card, text=value, font=('Helvetica', 22, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE)
        lbl_val.pack(anchor=tk.W, pady=(4, 2))
        tk.Label(card, text=subtext, font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W)
        return lbl_val

    def _refresh_dashboard(self):
        conn = get_connection()
        try:
            c = conn.cursor()
            total_staff = c.execute("SELECT COUNT(*) FROM staff WHERE status = 'Active'").fetchone()[0]
            self.kpi_total_staff.config(text=str(total_staff))

            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT status, COUNT(*) FROM daily_attendance WHERE date = ? GROUP BY status", (today,))
            stats = dict(c.fetchall())
        finally:
            conn.close()

        present_count = stats.get('Present', 0)
        half_count = stats.get('Half Day', 0)
        absent_count = stats.get('Absent', 0)

        self.kpi_present_today.config(text=str(present_count + half_count))
        self.kpi_absent_today.config(text=str(absent_count))

        effective = present_count + 0.5 * half_count
        rate = round((effective / total_staff * 100), 1) if total_staff > 0 else 0.0
        self.kpi_rate_today.config(text=f"{rate}%")

    # =========================================================================
    # PAGE 2: STAFF DIRECTORY
    # =========================================================================
    def _build_staff_page(self):
        container = self.view_staff

        # Top Control Card (Search, Filters, Add/Edit/Delete Buttons)
        ctrl_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=16, pady=12)
        ctrl_card.pack(fill=tk.X, pady=(0, 12))

        # Search
        tk.Label(ctrl_card, text="Search:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT, padx=(0, 6))
        self.txt_staff_search = ttk.Entry(ctrl_card, width=20, font=('Helvetica', 10))
        self.txt_staff_search.pack(side=tk.LEFT, padx=(0, 14))
        self.txt_staff_search.bind("<KeyRelease>", lambda e: self._refresh_staff_tab())

        # Department Filter
        tk.Label(ctrl_card, text="Department:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT, padx=(0, 6))
        self.drp_staff_dept = ttk.Combobox(ctrl_card, values=["All"] + COLLEGE_DEPARTMENTS, state="readonly", width=16)
        self.drp_staff_dept.set("All")
        self.drp_staff_dept.pack(side=tk.LEFT, padx=(0, 14))
        self.drp_staff_dept.bind("<<ComboboxSelected>>", lambda e: self._refresh_staff_tab())

        # Status Filter
        tk.Label(ctrl_card, text="Status:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT, padx=(0, 6))
        self.drp_staff_status = ttk.Combobox(ctrl_card, values=["All", "Active", "Inactive"], state="readonly", width=10)
        self.drp_staff_status.set("All")
        self.drp_staff_status.pack(side=tk.LEFT, padx=(0, 14))
        self.drp_staff_status.bind("<<ComboboxSelected>>", lambda e: self._refresh_staff_tab())

        # Buttons on Right (White background, Black text)
        self._create_primary_btn(ctrl_card, "➕  Add Staff", self._dialog_add_staff).pack(side=tk.RIGHT, padx=4)
        self._create_outline_btn(ctrl_card, "✏️  Edit Staff", self._dialog_edit_staff).pack(side=tk.RIGHT, padx=4)
        self._create_outline_btn(ctrl_card, "🗑️  Deactivate", self._action_delete_staff).pack(side=tk.RIGHT, padx=4)
        self._create_outline_btn(ctrl_card, "📥  Fetch from Terminal", self._action_fetch_staff_from_device).pack(side=tk.RIGHT, padx=4)
        self._create_outline_btn(ctrl_card, "⬆️  Sync to Terminal", self._action_sync_staff_to_device).pack(side=tk.RIGHT, padx=4)

        # Table Card
        table_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        table_card.pack(fill=tk.BOTH, expand=True)

        cols = ("user_id", "name", "department", "designation", "card_number", "privilege", "status")
        self.tree_staff = ttk.Treeview(table_card, columns=cols, show='headings', selectmode='browse')

        self.tree_staff.heading("user_id", text="Staff ID")
        self.tree_staff.heading("name", text="Full Name")
        self.tree_staff.heading("department", text="Department")
        self.tree_staff.heading("designation", text="Designation")
        self.tree_staff.heading("card_number", text="RFID Card")
        self.tree_staff.heading("privilege", text="Role")
        self.tree_staff.heading("status", text="Status")

        self.tree_staff.column("user_id", width=90, anchor=tk.CENTER)
        self.tree_staff.column("name", width=240)
        self.tree_staff.column("department", width=150)
        self.tree_staff.column("designation", width=170)
        self.tree_staff.column("card_number", width=120, anchor=tk.CENTER)
        self.tree_staff.column("privilege", width=90, anchor=tk.CENTER)
        self.tree_staff.column("status", width=95, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree_staff.yview)
        self.tree_staff.configure(yscrollcommand=scroll_y.set)

        self.tree_staff.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _refresh_staff_tab(self):
        for r in self.tree_staff.get_children():
            self.tree_staff.delete(r)

        conn = get_connection()
        try:
            query = "SELECT user_id, name, department, designation, card_number, privilege, status FROM staff WHERE 1=1"
            params = []

            search = self.txt_staff_search.get().strip()
            if search:
                query += " AND (name LIKE ? OR user_id LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            dept = self.drp_staff_dept.get()
            if dept != "All":
                query += " AND department = ?"
                params.append(dept)

            st = self.drp_staff_status.get()
            if st != "All":
                query += " AND status = ?"
                params.append(st)

            query += " ORDER BY department ASC, name ASC"
            rows = conn.cursor().execute(query, params).fetchall()
        finally:
            conn.close()

        for idx, r in enumerate(rows):
            role_label = "Admin" if r['privilege'] == 14 else "Staff"
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree_staff.insert('', tk.END, values=(
                r['user_id'], r['name'], r['department'],
                r['designation'], r['card_number'] or "--", role_label, r['status']
            ), tags=(tag,))
        self.tree_staff.tag_configure('even', background=COLOR_SURFACE)
        self.tree_staff.tag_configure('odd', background=COLOR_BG)

    # =========================================================================
    # PAGE 3: ATTENDANCE REPORT (THE MOST IMPORTANT PAGE - EXACTLY 5 COLUMNS)
    # Columns: Date | Staff Name | Staff ID | In Time | Out Time
    # =========================================================================
    def _build_attendance_page(self):
        container = self.view_attendance

        # Filter Card at Top
        filter_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=18, pady=14)
        filter_card.pack(fill=tk.X, pady=(0, 12))

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        # Row 1: Date Range & Quick Filters
        r1 = tk.Frame(filter_card, bg=COLOR_SURFACE)
        r1.pack(fill=tk.X, pady=(0, 10))

        tk.Label(r1, text="From Date:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT, padx=(0, 6))
        self.txt_rep_from = ttk.Entry(r1, width=12, font=('Helvetica', 10))
        self.txt_rep_from.insert(0, week_ago.strftime("%Y-%m-%d"))
        self.txt_rep_from.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(r1, text="To Date:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT, padx=(0, 6))
        self.txt_rep_to = ttk.Entry(r1, width=12, font=('Helvetica', 10))
        self.txt_rep_to.insert(0, today.strftime("%Y-%m-%d"))
        self.txt_rep_to.pack(side=tk.LEFT, padx=(0, 16))

        # Quick preset buttons
        def set_dates(d1, d2):
            self.txt_rep_from.delete(0, tk.END); self.txt_rep_from.insert(0, d1)
            self.txt_rep_to.delete(0, tk.END); self.txt_rep_to.insert(0, d2)
            self._refresh_attendance_report()

        presets = [
            ("Today", today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")),
            ("Yesterday", (today - timedelta(days=1)).strftime("%Y-%m-%d"), (today - timedelta(days=1)).strftime("%Y-%m-%d")),
            ("Last 7 Days", (today - timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")),
            ("This Month", today.replace(day=1).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))
        ]
        for lbl, d1, d2 in presets:
            b = tk.Button(
                r1,
                text=lbl,
                font=('Helvetica', 8, 'bold'),
                bg='#FFFFFF',
                fg='#000000',
                activebackground='#F1F5F9',
                activeforeground='#000000',
                highlightthickness=1,
                highlightbackground='#CBD5E1',
                bd=0,
                padx=9,
                pady=4,
                cursor='hand2',
                command=lambda s=d1, e=d2: set_dates(s, e)
            )
            b.pack(side=tk.LEFT, padx=3)

        # Row 2: Staff Dropdown & Generate Button
        r2 = tk.Frame(filter_card, bg=COLOR_SURFACE)
        r2.pack(fill=tk.X)

        tk.Label(r2, text="Staff:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT, padx=(0, 6))
        self.drp_rep_staff = ttk.Combobox(r2, state="readonly", width=32)
        self.drp_rep_staff.pack(side=tk.LEFT, padx=(0, 16))

        self._populate_staff_dropdown()

        self._create_primary_btn(r2, "Generate Report", self._refresh_attendance_report, COLOR_PRIMARY).pack(side=tk.LEFT)

        # Table Card: Clean Modern Table with Status at the end
        # Date | Staff Name | Staff ID | In Time | Out Time | Attendance Status
        table_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        table_card.pack(fill=tk.BOTH, expand=True)

        cols = ("date", "name", "user_id", "in_time", "out_time", "status")
        self.tree_attendance = ttk.Treeview(table_card, columns=cols, show='headings')

        self.tree_attendance.heading("date", text="Date")
        self.tree_attendance.heading("name", text="Staff Name")
        self.tree_attendance.heading("user_id", text="Staff ID")
        self.tree_attendance.heading("in_time", text="In Time")
        self.tree_attendance.heading("out_time", text="Out Time")
        self.tree_attendance.heading("status", text="Attendance Status")

        self.tree_attendance.column("date", width=120, anchor=tk.CENTER)
        self.tree_attendance.column("name", width=330)
        self.tree_attendance.column("user_id", width=100, anchor=tk.CENTER)
        self.tree_attendance.column("in_time", width=130, anchor=tk.CENTER)
        self.tree_attendance.column("out_time", width=130, anchor=tk.CENTER)
        self.tree_attendance.column("status", width=130, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree_attendance.yview)
        self.tree_attendance.configure(yscrollcommand=scroll_y.set)

        self.tree_attendance.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom Bar: Summary Pill & Export Buttons
        bottom_bar = tk.Frame(container, bg=COLOR_BG)
        bottom_bar.pack(fill=tk.X, pady=(12, 0))

        self.lbl_rep_count = tk.Label(
            bottom_bar,
            text="Records: 0",
            font=('Helvetica', 9, 'bold'),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            padx=14,
            pady=7
        )
        self.lbl_rep_count.pack(side=tk.LEFT)

        # Export Buttons
        self._create_primary_btn(bottom_bar, "📄  Export PDF", self._action_export_pdf, COLOR_SUCCESS).pack(side=tk.RIGHT, padx=(6, 0))
        self._create_primary_btn(bottom_bar, "📊  Export Excel", self._action_export_excel, COLOR_PRIMARY).pack(side=tk.RIGHT, padx=(6, 0))
        self._create_outline_btn(bottom_bar, "📑  Export CSV", self._action_export_csv).pack(side=tk.RIGHT)

    def _populate_staff_dropdown(self):
        conn = get_connection()
        try:
            rows = conn.cursor().execute("SELECT user_id, name FROM staff WHERE status = 'Active' ORDER BY name ASC").fetchall()
        finally:
            conn.close()

        items = ["All Staff"]
        self.staff_lookup = {"All Staff": "All"}
        for r in rows:
            display = f"{r['name']} ({r['user_id']})"
            items.append(display)
            self.staff_lookup[display] = r['user_id']

        self.drp_rep_staff['values'] = items
        self.drp_rep_staff.set("All Staff")

    def _refresh_attendance_report(self):
        d1 = self.txt_rep_from.get().strip()
        d2 = self.txt_rep_to.get().strip()
        selected_staff_display = self.drp_rep_staff.get()
        staff_id = self.staff_lookup.get(selected_staff_display, "All")

        for r in self.tree_attendance.get_children():
            self.tree_attendance.delete(r)

        self.current_report_rows = get_attendance_report(d1, d2, department="All", status="All", staff_id=staff_id)

        for idx, r in enumerate(self.current_report_rows):
            date_disp = format_date_display(str(r.get('date', '')))
            name_disp = str(r.get('name', ''))
            id_disp = str(r.get('user_id', ''))
            in_disp = str(r.get('first_in') or '--')
            out_disp = str(r.get('last_out') or '--')
            status_disp = str(r.get('status') or 'Absent')

            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree_attendance.insert('', tk.END, values=(
                date_disp, name_disp, id_disp, in_disp, out_disp, status_disp
            ), tags=(tag,))

        self.tree_attendance.tag_configure('even', background=COLOR_SURFACE)
        self.tree_attendance.tag_configure('odd', background=COLOR_BG)

        self.lbl_rep_count.config(text=f"Total Records: {len(self.current_report_rows)}")

    def _action_export_pdf(self):
        if not hasattr(self, 'current_report_rows') or not self.current_report_rows:
            messagebox.showwarning("No Records", "No attendance records match the selected filter.")
            return

        d1 = self.txt_rep_from.get().strip()
        d2 = self.txt_rep_to.get().strip()
        default_file = f"Attendance_Report_{d1}_to_{d2}.pdf"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            initialfile=default_file,
            title="Export Attendance Report (PDF)"
        )
        if not file_path:
            return

        try:
            settings = get_device_settings()
            college_name = settings.get('college_name', 'COLLEGE OF ENGINEERING & TECHNOLOGY')
            generator = PDFReportGenerator(filename=file_path, college_name=college_name)
            generator.generate(d1, d2, self.current_report_rows)
            self._log(f"PDF exported: {file_path}")
            messagebox.showinfo("Export Successful", f"Official PDF report exported successfully:\n\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate PDF: {e}")

    def _action_export_excel(self):
        if not hasattr(self, 'current_report_rows') or not self.current_report_rows:
            messagebox.showwarning("No Records", "No attendance records to export.")
            return

        d1 = self.txt_rep_from.get().strip()
        d2 = self.txt_rep_to.get().strip()
        default_file = f"Attendance_Report_{d1}_to_{d2}.xlsx"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Spreadsheet", "*.xlsx")],
            initialfile=default_file,
            title="Export Attendance Report (Excel)"
        )
        if not file_path:
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Attendance Report"

            settings = get_device_settings()
            college_name = settings.get('college_name', 'COLLEGE OF ENGINEERING & TECHNOLOGY')

            # Title Header
            ws.merge_cells("A1:F1")
            ws["A1"] = college_name.upper()
            ws["A1"].font = Font(name="Arial", size=14, bold=True, color="0F172A")
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells("A2:F2")
            ws["A2"] = f"Attendance Report • Date Range: {d1} to {d2}"
            ws["A2"].font = Font(name="Arial", size=10, italic=True, color="475569")
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

            # Table Headers (Date, Staff Name, Staff ID, In Time, Out Time, Status)
            headers = ["Date", "Staff Name", "Staff ID", "In Time", "Out Time", "Status"]
            for col_idx, h in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col_idx, value=h)
                cell.font = Font(name="Arial", size=10, bold=True, color="0F172A")
                cell.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
                cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")

            # Table Data
            thin_border = Border(
                left=Side(style='thin', color='E2E8F0'),
                right=Side(style='thin', color='E2E8F0'),
                top=Side(style='thin', color='E2E8F0'),
                bottom=Side(style='thin', color='E2E8F0')
            )

            for row_idx, r in enumerate(self.current_report_rows, 5):
                date_str = format_date_display(str(r.get('date', '')))
                name_str = str(r.get('name', ''))
                id_str = str(r.get('user_id', ''))
                in_str = str(r.get('first_in') or '--')
                out_str = str(r.get('last_out') or '--')
                status_str = str(r.get('status') or 'Absent')

                row_vals = [date_str, name_str, id_str, in_str, out_str, status_str]
                bg_color = "FFFFFF" if row_idx % 2 == 1 else "F8FAFC"

                for col_idx, val in enumerate(row_vals, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=val)
                    cell.font = Font(name="Arial", size=9, color="0F172A")
                    cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
                    cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
                    cell.border = thin_border

            # Set Column Widths
            ws.column_dimensions["A"].width = 16
            ws.column_dimensions["B"].width = 34
            ws.column_dimensions["C"].width = 14
            ws.column_dimensions["D"].width = 16
            ws.column_dimensions["E"].width = 16
            ws.column_dimensions["F"].width = 16

            wb.save(file_path)
            self._log(f"Excel report exported: {file_path}")
            messagebox.showinfo("Export Successful", f"Excel report exported successfully:\n\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export Excel file: {e}")

    def _action_export_csv(self):
        if not hasattr(self, 'current_report_rows') or not self.current_report_rows:
            messagebox.showwarning("No Records", "No attendance records to export.")
            return

        d1 = self.txt_rep_from.get().strip()
        d2 = self.txt_rep_to.get().strip()
        default_file = f"Attendance_Report_{d1}_to_{d2}.csv"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Spreadsheet", "*.csv")],
            initialfile=default_file,
            title="Export Attendance Report (CSV)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Staff Name", "Staff ID", "In Time", "Out Time", "Status"])
                for r in self.current_report_rows:
                    writer.writerow([
                        format_date_display(str(r.get('date', ''))),
                        str(r.get('name', '')),
                        str(r.get('user_id', '')),
                        str(r.get('first_in') or '--'),
                        str(r.get('last_out') or '--'),
                        str(r.get('status') or 'Absent')
                    ])
            self._log(f"CSV exported: {file_path}")
            messagebox.showinfo("Export Successful", f"CSV file exported successfully:\n\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")
            self._log(f"CSV exported: {file_path}")
            messagebox.showinfo("Export Successful", f"CSV file exported successfully:\n\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")

    # =========================================================================
    # PAGE 4: AUDIT PUNCH LOGS (Technical Machine Audit Trail)
    # =========================================================================
    def _build_audit_page(self):
        container = self.view_audit

        top_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=18, pady=12)
        top_card.pack(fill=tk.X, pady=(0, 12))

        tb_box = tk.Frame(top_card, bg=COLOR_SURFACE)
        tb_box.pack(side=tk.LEFT)

        tk.Label(tb_box, text="Machine Audit Logs (Technical Audit Trail)", font=('Helvetica', 12, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).pack(anchor=tk.W)
        tk.Label(tb_box, text="Raw punch events received directly from biometric device memory.", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W)

        self._create_outline_btn(top_card, "🔄  Refresh Audit Logs", self._refresh_raw_logs).pack(side=tk.RIGHT)

        table_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        table_card.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "user_id", "punch_time", "punch_type", "verify_type", "device_ip")
        self.tree_audit = ttk.Treeview(table_card, columns=cols, show='headings')

        self.tree_audit.heading("id", text="Log ID")
        self.tree_audit.heading("user_id", text="Staff ID")
        self.tree_audit.heading("punch_time", text="Punch Timestamp")
        self.tree_audit.heading("punch_type", text="Punch Mode")
        self.tree_audit.heading("verify_type", text="Verify Mode")
        self.tree_audit.heading("device_ip", text="Device Source")

        self.tree_audit.column("id", width=80, anchor=tk.CENTER)
        self.tree_audit.column("user_id", width=100, anchor=tk.CENTER)
        self.tree_audit.column("punch_time", width=180, anchor=tk.CENTER)
        self.tree_audit.column("punch_type", width=130, anchor=tk.CENTER)
        self.tree_audit.column("verify_type", width=130, anchor=tk.CENTER)
        self.tree_audit.column("device_ip", width=150, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.tree_audit.yview)
        self.tree_audit.configure(yscrollcommand=scroll_y.set)

        self.tree_audit.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _refresh_raw_logs(self):
        for r in self.tree_audit.get_children():
            self.tree_audit.delete(r)

        conn = get_connection()
        try:
            rows = conn.cursor().execute("""
                SELECT id, user_id, punch_time, punch_type, verify_type, device_ip 
                FROM attendance_punches 
                ORDER BY punch_time DESC LIMIT 200
            """).fetchall()
        finally:
            conn.close()

        for idx, r in enumerate(rows):
            p_type = "Check-Out" if r['punch_type'] == 1 else "Check-In"
            v_type = "Fingerprint" if r['verify_type'] == 1 else ("Face" if r['verify_type'] == 15 else "Card")
            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree_audit.insert('', tk.END, values=(
                r['id'], r['user_id'], r['punch_time'], p_type, v_type, r['device_ip']
            ), tags=(tag,))
        self.tree_audit.tag_configure('even', background=COLOR_SURFACE)
        self.tree_audit.tag_configure('odd', background=COLOR_BG)

    # =========================================================================
    # PAGE 5: DEVICE SETTINGS & ACTIONS
    # =========================================================================
    def _build_settings_page(self):
        # Scrollable container for all settings cards
        canvas = tk.Canvas(self.view_settings, bg=COLOR_BG, highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(self.view_settings, orient="vertical", command=canvas.yview)
        container = tk.Frame(canvas, bg=COLOR_BG)

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        container.bind("<Configure>", _on_frame_configure)
        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)

        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=v_scrollbar.set)

        def _on_mousewheel(e):
            if hasattr(e, 'delta') and e.delta:
                step = -1 if e.delta > 0 else 1
                canvas.yview_scroll(step, "units")
            elif e.num == 4:
                canvas.yview_scroll(-1, "units")
            elif e.num == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))

        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Section 1: Biometric Terminal Configuration Card
        cfg_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=22, pady=20)
        cfg_card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(cfg_card, text="Biometric Terminal", font=('Helvetica', 12, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(cfg_card, text="Configure network endpoints and security keys for the hardware terminal.", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 16))

        settings = get_device_settings()

        form_grid = tk.Frame(cfg_card, bg=COLOR_SURFACE)
        form_grid.pack(fill=tk.X, pady=(0, 14))
        form_grid.columnconfigure(1, weight=1)

        tk.Label(form_grid, text="Device IP:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=0, column=0, sticky='w', pady=8)
        self.txt_ip = ttk.Entry(form_grid, font=('Helvetica', 10), width=24)
        self.txt_ip.insert(0, settings.get('ip_address', '192.168.1.201'))
        self.txt_ip.grid(row=0, column=1, sticky='w', padx=(14, 0), pady=8)

        tk.Label(form_grid, text="TCP Port:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=1, column=0, sticky='w', pady=8)
        self.txt_port = ttk.Entry(form_grid, font=('Helvetica', 10), width=12)
        self.txt_port.insert(0, str(settings.get('port', 4370)))
        self.txt_port.grid(row=1, column=1, sticky='w', padx=(14, 0), pady=8)

        tk.Label(form_grid, text="Comm Key:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=2, column=0, sticky='w', pady=8)
        self.txt_key = ttk.Entry(form_grid, font=('Helvetica', 10), width=12)
        self.txt_key.insert(0, str(settings.get('comm_key', 0)))
        self.txt_key.grid(row=2, column=1, sticky='w', padx=(14, 0), pady=8)

        tk.Label(form_grid, text="College Name:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=3, column=0, sticky='w', pady=8)
        self.txt_college = ttk.Entry(form_grid, font=('Helvetica', 10), width=38)
        self.txt_college.insert(0, settings.get('college_name', 'COLLEGE OF ENGINEERING & TECHNOLOGY'))
        self.txt_college.grid(row=3, column=1, sticky='w', padx=(14, 0), pady=8)

        self._create_primary_btn(cfg_card, "Save Configuration", self._save_device_settings, COLOR_PRIMARY).pack(anchor=tk.W)

        # Section 2: Device Actions Card
        act_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=22, pady=20)
        act_card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(act_card, text="Device Actions", font=('Helvetica', 12, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(act_card, text="Execute safe read-only operations directly against the biometric reader.", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 16))

        btn_row = tk.Frame(act_card, bg=COLOR_SURFACE)
        btn_row.pack(fill=tk.X, pady=(0, 14))

        self._create_outline_btn(btn_row, "Test Connection", self._action_test_connection).pack(side=tk.LEFT, padx=(0, 10))
        self._create_outline_btn(btn_row, "Synchronize Clock", self._action_sync_time).pack(side=tk.LEFT, padx=(0, 10))
        self._create_outline_btn(btn_row, "📥 Fetch Staff", self._action_fetch_staff_from_device).pack(side=tk.LEFT, padx=(0, 10))
        self._create_primary_btn(btn_row, "Download Attendance", self._action_download_logs).pack(side=tk.LEFT)

        # Status Indicator Box (Clear: ✓ Device reachable or ✕ Device unavailable)
        self.box_test_status = tk.Frame(act_card, bg=COLOR_BG, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=16, pady=12)
        self.box_test_status.pack(fill=tk.X)

        self.lbl_test_result = tk.Label(
            self.box_test_status,
            text="Status: Click 'Test Connection' to verify reachability.",
            font=('Helvetica', 9),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_BG
        )
        self.lbl_test_result.pack(anchor=tk.W)

        # Section 3: Shift & Attendance Calculation Rules Card
        rules_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=22, pady=20)
        rules_card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(rules_card, text="Shift & Attendance Calculation Rules", font=('Helvetica', 12, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(rules_card, text="Configure how daily punch-in and punch-out timestamps are determined, official shift windows, and working hours thresholds.", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 16))

        rules = get_attendance_rules()

        rules_grid = tk.Frame(rules_card, bg=COLOR_SURFACE)
        rules_grid.pack(fill=tk.X, pady=(0, 14))
        rules_grid.columnconfigure(1, weight=1)

        # Rule 1: Punch Mode
        tk.Label(rules_grid, text="Punch Calculation Mode:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=0, column=0, sticky='w', pady=8)
        mode_box = tk.Frame(rules_grid, bg=COLOR_SURFACE)
        mode_box.grid(row=0, column=1, sticky='w', padx=(14, 0), pady=8)

        self.combo_punch_mode = ttk.Combobox(
            mode_box,
            values=["First-In / Last-Out", "Terminal Key Mode (F1=In, F2=Out)"],
            state="readonly",
            font=('Helvetica', 9),
            width=32
        )
        self.combo_punch_mode.set(rules.get('punch_mode', 'First-In / Last-Out'))
        self.combo_punch_mode.pack(side=tk.LEFT)

        tk.Label(
            mode_box,
            text="  (First-In / Last-Out: Earliest punch = IN, Latest punch = OUT — Recommended for Colleges)",
            font=('Helvetica', 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_SURFACE
        ).pack(side=tk.LEFT)

        # Rule 2: Shift Timings & Grace Period
        tk.Label(rules_grid, text="Official Shift Window:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=1, column=0, sticky='w', pady=8)
        shift_box = tk.Frame(rules_grid, bg=COLOR_SURFACE)
        shift_box.grid(row=1, column=1, sticky='w', padx=(14, 0), pady=8)

        tk.Label(shift_box, text="Start: ", font=('Helvetica', 8), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT)
        self.txt_shift_start = ttk.Entry(shift_box, font=('Helvetica', 9), width=10)
        self.txt_shift_start.insert(0, rules.get('shift_start', '09:00:00'))
        self.txt_shift_start.pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(shift_box, text="End: ", font=('Helvetica', 8), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT)
        self.txt_shift_end = ttk.Entry(shift_box, font=('Helvetica', 9), width=10)
        self.txt_shift_end.insert(0, rules.get('shift_end', '17:00:00'))
        self.txt_shift_end.pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(shift_box, text="Grace Period: ", font=('Helvetica', 8), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT)
        self.txt_grace = ttk.Entry(shift_box, font=('Helvetica', 9), width=6)
        self.txt_grace.insert(0, str(rules.get('grace_minutes', 15)))
        self.txt_grace.pack(side=tk.LEFT)
        tk.Label(shift_box, text=" mins", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(side=tk.LEFT)

        # Rule 3: Minimum Working Hours
        tk.Label(rules_grid, text="Working Hours Thresholds:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=2, column=0, sticky='w', pady=8)
        hours_box = tk.Frame(rules_grid, bg=COLOR_SURFACE)
        hours_box.grid(row=2, column=1, sticky='w', padx=(14, 0), pady=8)

        tk.Label(hours_box, text="Min Full Day: ", font=('Helvetica', 8), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT)
        self.txt_min_full = ttk.Entry(hours_box, font=('Helvetica', 9), width=6)
        self.txt_min_full.insert(0, str(rules.get('min_full_hours', 7.0)))
        self.txt_min_full.pack(side=tk.LEFT)
        tk.Label(hours_box, text=" hrs       ", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(side=tk.LEFT)

        tk.Label(hours_box, text="Min Half Day: ", font=('Helvetica', 8), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(side=tk.LEFT)
        self.txt_min_half = ttk.Entry(hours_box, font=('Helvetica', 9), width=6)
        self.txt_min_half.insert(0, str(rules.get('min_half_hours', 4.0)))
        self.txt_min_half.pack(side=tk.LEFT)
        tk.Label(hours_box, text=" hrs", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(side=tk.LEFT)

        # Save Button & Info Note
        rules_action_row = tk.Frame(rules_card, bg=COLOR_SURFACE)
        rules_action_row.pack(fill=tk.X, pady=(6, 0))

        self._create_primary_btn(rules_action_row, "⚙️  Save Rules & Recalculate Attendance", self._save_attendance_rules).pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(
            rules_action_row,
            text="✓ Recalculates all daily IN/OUT records immediately without modifying raw device punch logs.",
            font=('Helvetica', 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_SURFACE
        ).pack(side=tk.LEFT, pady=8)

        # Section 4: Database Backup & Cloud Transfer Card (For Transferring to New PC)
        backup_card = tk.Frame(container, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=22, pady=20)
        backup_card.pack(fill=tk.X, pady=(0, 20))

        tk.Label(backup_card, text="Database Backup & System Transfer", font=('Helvetica', 12, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(backup_card, text="Download full offline database backups to transfer staff details to a new computer, or restore from Google Drive / USB backup.", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 14))

        # Transfer Guidance Note Banner
        guide_banner = tk.Frame(backup_card, bg=COLOR_BG, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=14, pady=10)
        guide_banner.pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            guide_banner,
            text="💡 Transferring to a New Computer:\n"
                 "1. Click 'Download Backup File' below and save the .bak file to a USB drive or Google Drive.\n"
                 "2. Install this application on the new computer and log in.\n"
                 "3. Click 'Restore from Backup File' and select the saved .bak file — all staff records and punches transfer instantly!",
            font=('Helvetica', 8),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_BG,
            justify=tk.LEFT
        ).pack(anchor=tk.W)

        bak_btn_row = tk.Frame(backup_card, bg=COLOR_SURFACE)
        bak_btn_row.pack(fill=tk.X, pady=(0, 12))

        self._create_primary_btn(bak_btn_row, "💾  Download Backup File", self._action_export_backup, COLOR_PRIMARY).pack(side=tk.LEFT, padx=(0, 10))
        self._create_primary_btn(bak_btn_row, "📥  Restore from Backup File", self._action_restore_backup, COLOR_SUCCESS).pack(side=tk.LEFT, padx=(0, 10))
        self._create_outline_btn(bak_btn_row, "🔑  Change Admin Password", self._dialog_change_password).pack(side=tk.LEFT)

        # Backup Status Indicator Box
        self.box_backup_status = tk.Frame(backup_card, bg=COLOR_BG, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=16, pady=10)
        self.box_backup_status.pack(fill=tk.X)

        self.lbl_backup_status = tk.Label(
            self.box_backup_status,
            text="Status: Database active. Ready for backup or restore operations.",
            font=('Helvetica', 8),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_BG
        )
        self.lbl_backup_status.pack(anchor=tk.W)

    def _save_device_settings(self):
        try:
            update_device_settings(
                self.txt_ip.get().strip(),
                self.txt_port.get().strip(),
                self.txt_key.get().strip(),
                self.txt_college.get().strip()
            )
            self.lbl_college_title.config(text=self.txt_college.get().strip())
            self._log("Terminal settings updated and saved.")
            self._check_device_status_async()
            messagebox.showinfo("Success", "Device configuration saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _save_attendance_rules(self):
        try:
            mode = self.combo_punch_mode.get().strip()
            start = self.txt_shift_start.get().strip()
            end = self.txt_shift_end.get().strip()
            min_full = float(self.txt_min_full.get().strip())
            min_half = float(self.txt_min_half.get().strip())
            grace = int(self.txt_grace.get().strip())

            if min_full <= 0 or min_half <= 0:
                messagebox.showerror("Validation Error", "Hours must be greater than zero.")
                return

            if min_half >= min_full:
                messagebox.showerror("Validation Error", "Half Day hours must be less than Full Day hours.")
                return

            update_attendance_rules(mode, start, end, min_full, min_half, grace)
            self._log(f"Attendance rules updated: Mode={mode}, Shift={start}-{end}, Full={min_full}h, Half={min_half}h")

            # Immediately recompute daily attendance with the new rules
            calculate_daily_attendance()
            self._refresh_dashboard()
            self._refresh_attendance_report()

            messagebox.showinfo(
                "Rules Saved & Recalculated",
                f"✓ Shift and Attendance calculation rules have been updated successfully!\n\n"
                f"• Punch Mode: {mode}\n"
                f"• Shift Timing: {start} to {end} (Grace: {grace} min)\n"
                f"• Minimum Full Day: {min_full} hrs\n"
                f"• Minimum Half Day: {min_half} hrs\n\n"
                f"All daily IN/OUT times and attendance statuses have been recomputed."
            )
        except ValueError:
            messagebox.showerror("Validation Error", "Please enter valid numeric values for hours and grace period.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save calculation rules: {e}")

    # =========================================================================
    # ASYNC DEVICE CONNECTIVITY PROBE (Green if Connected, Red if Offline)
    # =========================================================================
    def _get_driver(self):
        ip = self.txt_ip.get().strip() if hasattr(self, 'txt_ip') else "192.168.1.201"
        port = int(self.txt_port.get().strip()) if hasattr(self, 'txt_port') else 4370
        key = int(self.txt_key.get().strip()) if hasattr(self, 'txt_key') else 0
        return BiometricDriver(ip=ip, port=port, comm_key=key, timeout=2)

    def _check_device_status_async(self):
        """Asynchronously probes device without freezing UI."""
        def worker():
            try:
                driver = self._get_driver()
                success, info = driver.test_connection()
                self.after(0, lambda: self._update_connection_ui(success, driver.ip, driver.port, info))
            except Exception as ex:
                self.after(0, lambda: self._update_connection_ui(False, "192.168.1.201", 4370, str(ex)))
            finally:
                # Re-probe every 30 seconds
                self.after(30000, self._check_device_status_async)

        threading.Thread(target=worker, daemon=True).start()

    def _update_connection_ui(self, is_online, ip, port, info=""):
        if is_online:
            self.status_container.config(bg=COLOR_SUCCESS_BG, highlightbackground=COLOR_SUCCESS_BORDER)
            self.lbl_status_badge.config(text="● Connected", fg=COLOR_SUCCESS, bg=COLOR_SUCCESS_BG)
            self.lbl_status_details.config(text=f"{ip} : {port}", bg=COLOR_SUCCESS_BG)
            if hasattr(self, 'kpi_device_stat'):
                self.kpi_device_stat.config(text="Connected")
            if hasattr(self, 'lbl_test_result'):
                self.lbl_test_result.config(text=f"✓ Device reachable ({info})", fg=COLOR_SUCCESS)
                self.box_test_status.config(bg=COLOR_SUCCESS_BG, highlightbackground=COLOR_SUCCESS_BORDER)
        else:
            self.status_container.config(bg=COLOR_DANGER_BG, highlightbackground=COLOR_DANGER_BORDER)
            self.lbl_status_badge.config(text="● Offline", fg=COLOR_DANGER, bg=COLOR_DANGER_BG)
            self.lbl_status_details.config(text=f"{ip} : {port}", bg=COLOR_DANGER_BG)
            if hasattr(self, 'kpi_device_stat'):
                self.kpi_device_stat.config(text="Offline")
            if hasattr(self, 'lbl_test_result'):
                self.lbl_test_result.config(text=f"✕ Device unavailable: {info}", fg=COLOR_DANGER)
                self.box_test_status.config(bg=COLOR_DANGER_BG, highlightbackground=COLOR_DANGER_BORDER)

    def _action_test_connection(self):
        self._log("Testing connection to biometric terminal...")
        driver = self._get_driver()
        success, info = driver.test_connection()
        self._update_connection_ui(success, driver.ip, driver.port, info)
        if success:
            self._log(f"Test SUCCESS: {info}")
            messagebox.showinfo("Connection Verified", f"✓ Device reachable!\n\n{info}")
        else:
            self._log(f"Test FAILED: {info}")
            messagebox.showwarning("Device Offline", f"✕ Device unavailable:\n\n{info}")

    def _action_sync_time(self):
        self._log("Synchronizing device clock with local computer time...")
        driver = self._get_driver()
        success, msg = driver.sync_time()
        self._update_connection_ui(success, driver.ip, driver.port, msg)
        if success:
            self._log(f"Clock Sync SUCCESS: {msg}")
            messagebox.showinfo("Clock Synchronized", msg)
        else:
            self._log(f"Clock Sync FAILED: {msg}")
            messagebox.showwarning("Sync Warning", f"Could not sync time:\n{msg}")

    def _action_download_logs(self):
        self._log("Initiating attendance log download from device...")
        driver = self._get_driver()
        success, msg, punches = driver.download_attendance_punches()
        self._update_connection_ui(success, driver.ip, driver.port, msg)
        if success:
            self._log(f"Download complete: {msg}")
            update_last_sync()
            calculate_daily_attendance()
            self._refresh_dashboard()
            self._refresh_staff_tab()
            self._refresh_attendance_report()
            self._refresh_raw_logs()
            messagebox.showinfo("Download Complete", msg)
        else:
            self._log(f"Download Notice: {msg}")
            messagebox.showwarning("Download Notice", f"{msg}\n(Displaying current offline database records)")

    def _action_fetch_staff_from_device(self):
        self._log("Fetching enrolled users/staff directly from biometric terminal...")
        driver = self._get_driver()
        success, msg, users = driver.download_users()
        self._update_connection_ui(success, driver.ip, driver.port, msg)

        if success:
            new_c, upd_c = sync_users_from_device(users)
            self._log(f"Staff fetch complete: {len(users)} retrieved from terminal ({new_c} new added, {upd_c} updated).")
            self._refresh_staff_tab()
            self._refresh_dashboard()
            self._populate_staff_dropdown()
            messagebox.showinfo(
                "Staff Import Complete",
                f"✓ Successfully fetched enrolled staff from biometric hardware!\n\n"
                f"• Total Retrieved: {len(users)} staff member(s)\n"
                f"• New Profiles Created: {new_c}\n"
                f"• Existing Profiles Updated: {upd_c}\n\n"
                f"All staff records have been loaded into your database.\n"
                f"You can now select any staff member and click 'Edit Staff' to assign their specific College Department and Designation."
            )
        else:
            self._log(f"Staff fetch failed: {msg}")
            messagebox.showwarning(
                "Hardware Fetch Notice",
                f"Could not fetch staff from device:\n{msg}\n\n"
                f"Ensure your computer is connected to the college network (IP: {driver.ip}, Port: {driver.port})."
            )

    def _action_sync_staff_to_device(self):
        staff_list = get_all_active_staff_list()
        if not staff_list:
            messagebox.showwarning("No Staff", "No active staff found in database to sync.")
            return

        if not messagebox.askyesno(
            "Confirm Device Sync",
            f"Are you sure you want to push all {len(staff_list)} staff members to the biometric terminal memory?\n\n"
            f"This will register/update their IDs and names on the physical machine."
        ):
            return

        self._log(f"Pushing {len(staff_list)} staff profiles to biometric terminal...")
        driver = self._get_driver()
        success, msg = driver.upload_all_staff(staff_list)
        self._update_connection_ui(success, driver.ip, driver.port, msg)
        if success:
            self._log(f"Device sync SUCCESS: {msg}")
            messagebox.showinfo("Device Sync Complete", msg)
        else:
            self._log(f"Device sync FAILED: {msg}")
            messagebox.showwarning("Sync Warning", f"Could not sync staff to terminal:\n{msg}")

    def _action_process_attendance(self):
        self._log("Recalculating daily IN/OUT attendance...")
        calculate_daily_attendance()
        self._refresh_dashboard()
        self._refresh_attendance_report()
        self._log("Attendance calculation complete.")
        messagebox.showinfo("Calculations Updated", "Daily attendance records recalculated successfully.")

    def _action_export_backup(self):
        default_name = f"NICETECH_biometric_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".bak",
            filetypes=[
                ("Attendance Database Backup (*.bak)", "*.bak"),
                ("SQLite Database File (*.db)", "*.db"),
                ("All Files (*.*)", "*.*")
            ],
            initialfile=default_name,
            title="Download / Save Database Backup"
        )
        if not file_path:
            return

        ok, result = export_database_backup(file_path)
        if ok:
            msg = (
                f"✓ Database backup downloaded successfully!\n\n"
                f"• Saved To: {result['file']}\n"
                f"• File Size: {result['size_kb']} KB\n"
                f"• Total Staff Records: {result['staff_count']}\n"
                f"• Total Punch Logs: {result['punch_count']}\n"
                f"• Created At: {result['time']}\n\n"
                f"You can safely store this file on Google Drive, a USB drive, or transfer it to another computer."
            )
            self._log(f"Database backup saved: {os.path.basename(file_path)} ({result['size_kb']} KB)")
            if hasattr(self, 'lbl_backup_status'):
                self.lbl_backup_status.config(
                    text=f"✓ Last Backup: {result['time']} ({result['staff_count']} staff, {result['punch_count']} punches saved)",
                    fg=COLOR_SUCCESS
                )
            messagebox.showinfo("Backup Downloaded", msg)
        else:
            self._log(f"Backup ERROR: {result}")
            messagebox.showerror("Backup Failed", f"Could not create backup:\n{result}")

    def _action_restore_backup(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Attendance Database Backup (*.bak, *.db)", "*.bak;*.db;*.sqlite"),
                ("All Files (*.*)", "*.*")
            ],
            title="Select Backup File to Restore"
        )
        if not file_path:
            return

        confirm = messagebox.askyesno(
            "Confirm Database Restore",
            f"Are you sure you want to restore data from:\n'{os.path.basename(file_path)}'?\n\n"
            f"⚠️ WARNING: This will overwrite current staff profiles, punch logs, and settings with the data in this backup file.\n\n"
            f"Do you want to proceed?"
        )
        if not confirm:
            return

        ok, result = restore_database_backup(file_path)
        if ok:
            calculate_daily_attendance()
            self._refresh_dashboard()
            self._refresh_staff_tab()
            self._refresh_attendance_report()
            self._refresh_raw_logs()
            self._populate_staff_dropdown()

            # Refresh settings form inputs
            settings = get_device_settings()
            if hasattr(self, 'txt_ip'):
                self.txt_ip.delete(0, tk.END)
                self.txt_ip.insert(0, settings.get('ip_address', '192.168.1.201'))
            if hasattr(self, 'txt_port'):
                self.txt_port.delete(0, tk.END)
                self.txt_port.insert(0, str(settings.get('port', 4370)))
            if hasattr(self, 'txt_key'):
                self.txt_key.delete(0, tk.END)
                self.txt_key.insert(0, str(settings.get('comm_key', 0)))
            if hasattr(self, 'txt_college'):
                self.txt_college.delete(0, tk.END)
                self.txt_college.insert(0, settings.get('college_name', 'COLLEGE OF ENGINEERING & TECHNOLOGY'))
            if hasattr(self, 'lbl_college_title'):
                self.lbl_college_title.config(text=settings.get('college_name', 'COLLEGE OF ENGINEERING & TECHNOLOGY'))

            rules = get_attendance_rules()
            if hasattr(self, 'combo_punch_mode'):
                self.combo_punch_mode.set(rules.get('punch_mode', 'First-In / Last-Out'))
            if hasattr(self, 'txt_shift_start'):
                self.txt_shift_start.delete(0, tk.END)
                self.txt_shift_start.insert(0, rules.get('shift_start', '09:00:00'))
            if hasattr(self, 'txt_shift_end'):
                self.txt_shift_end.delete(0, tk.END)
                self.txt_shift_end.insert(0, rules.get('shift_end', '17:00:00'))
            if hasattr(self, 'txt_grace'):
                self.txt_grace.delete(0, tk.END)
                self.txt_grace.insert(0, str(rules.get('grace_minutes', 15)))
            if hasattr(self, 'txt_min_full'):
                self.txt_min_full.delete(0, tk.END)
                self.txt_min_full.insert(0, str(rules.get('min_full_hours', 7.0)))
            if hasattr(self, 'txt_min_half'):
                self.txt_min_half.delete(0, tk.END)
                self.txt_min_half.insert(0, str(rules.get('min_half_hours', 4.0)))

            msg = (
                f"✓ Database successfully restored!\n\n"
                f"• Restored Staff Profiles: {result['staff_count']}\n"
                f"• Restored Punch Records: {result['punch_count']}\n"
                f"• Restored At: {result['restored_at']}\n\n"
                f"All application views, staff directory, and reports have been updated."
            )
            self._log(f"Database restored from {os.path.basename(file_path)}")
            if hasattr(self, 'lbl_backup_status'):
                self.lbl_backup_status.config(
                    text=f"✓ Last Restore: {result['restored_at']} ({result['staff_count']} staff loaded)",
                    fg=COLOR_SUCCESS
                )
            messagebox.showinfo("Restore Successful", msg)
        else:
            self._log(f"Restore ERROR: {result}")
            messagebox.showerror("Restore Failed", f"Could not restore database:\n{result}")

    def _dialog_change_password(self):
        dialog = tk.Toplevel(self)
        dialog.title("Change Administrator Password")
        dialog.geometry("450x370")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg=COLOR_BG)

        # Center on screen
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 185
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

        card = tk.Frame(dialog, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER, padx=24, pady=20)
        card.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        tk.Label(card, text="Change Admin Password", font=('Helvetica', 12, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 4))
        user_name = self.logged_in_user or "niadmin"
        tk.Label(card, text=f"Update security password for account '{user_name}'.", font=('Helvetica', 8), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 14))

        tk.Label(card, text="Current Password:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 3))
        e_old = ttk.Entry(card, font=('Helvetica', 10), width=30, show="•")
        e_old.pack(fill=tk.X, pady=(0, 10))

        tk.Label(card, text="New Password:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 3))
        e_new = ttk.Entry(card, font=('Helvetica', 10), width=30, show="•")
        e_new.pack(fill=tk.X, pady=(0, 10))

        tk.Label(card, text="Confirm New Password:", font=('Helvetica', 9, 'bold'), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).pack(anchor=tk.W, pady=(0, 3))
        e_conf = ttk.Entry(card, font=('Helvetica', 10), width=30, show="•")
        e_conf.pack(fill=tk.X, pady=(0, 16))

        btn_row = tk.Frame(card, bg=COLOR_SURFACE)
        btn_row.pack(fill=tk.X)

        def do_update():
            old = e_old.get().strip()
            new = e_new.get().strip()
            conf = e_conf.get().strip()

            if not old or not new:
                messagebox.showerror("Error", "Please fill in all password fields.", parent=dialog)
                return
            if new != conf:
                messagebox.showerror("Error", "New password and confirmation do not match.", parent=dialog)
                return
            if len(new) < 4:
                messagebox.showerror("Error", "New password must be at least 4 characters.", parent=dialog)
                return

            ok, msg = change_admin_password(user_name, old, new)
            if ok:
                dialog.destroy()
                messagebox.showinfo("Success", "Password updated successfully!")
            else:
                messagebox.showerror("Error", msg, parent=dialog)

        self._create_outline_btn(btn_row, "Cancel", dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        self._create_primary_btn(btn_row, "Update Password", do_update, COLOR_PRIMARY).pack(side=tk.RIGHT)

    def _log(self, message):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{t}] {message}\n")
        self.log_text.see(tk.END)

    # =========================================================================
    # REUSABLE MODERN BUTTON BUILDERS (High Contrast, Proper Padding)
    # =========================================================================
    def _create_primary_btn(self, parent, text, cmd, bg_col=None):
        btn = tk.Button(
            parent,
            text=text,
            font=('Helvetica', 9, 'bold'),
            bg='#FFFFFF',
            fg='#000000',
            activebackground='#F1F5F9',
            activeforeground='#000000',
            highlightthickness=1,
            highlightbackground='#FFFFFF',
            bd=0,
            padx=16,
            pady=8,
            cursor='hand2',
            command=cmd
        )
        return btn

    def _create_outline_btn(self, parent, text, cmd, fg_col='#000000'):
        btn = tk.Button(
            parent,
            text=text,
            font=('Helvetica', 9, 'bold'),
            bg='#FFFFFF',
            fg='#000000',
            activebackground='#F1F5F9',
            activeforeground='#000000',
            highlightthickness=1,
            highlightbackground='#FFFFFF',
            bd=0,
            padx=14,
            pady=7,
            cursor='hand2',
            command=cmd
        )
        return btn

    # =========================================================================
    # MODAL DIALOGS (Spacious, Centered, Clean White)
    # =========================================================================
    def _center_window(self, win, w, h):
        win.update_idletasks()
        self.update_idletasks()
        px = self.winfo_rootx()
        py = self.winfo_rooty()
        pw = self.winfo_width()
        ph = self.winfo_height()
        x = max(50, px + (pw - w) // 2)
        y = max(50, py + (ph - h) // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _dialog_add_staff(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add New Staff Member")
        self._center_window(dialog, 540, 520)
        dialog.resizable(False, False)
        dialog.configure(bg=COLOR_SURFACE)
        dialog.transient(self)
        dialog.grab_set()

        # Header
        header = tk.Frame(dialog, bg=COLOR_BG, height=55, highlightthickness=1, highlightbackground=COLOR_BORDER)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="➕   Register New Staff Member", font=('Helvetica', 12, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_BG).pack(side=tk.LEFT, padx=20, pady=12)

        # Form
        body = tk.Frame(dialog, bg=COLOR_SURFACE, padx=25, pady=18)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=0, minsize=140)
        body.columnconfigure(1, weight=1)

        tk.Label(body, text="Staff ID *:", font=('Helvetica', 10, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).grid(row=0, column=0, sticky='w', pady=8)
        e_id = ttk.Entry(body, font=('Helvetica', 10))
        e_id.grid(row=0, column=1, sticky='ew', pady=8)
        e_id.focus_set()

        tk.Label(body, text="Full Name *:", font=('Helvetica', 10, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).grid(row=1, column=0, sticky='w', pady=8)
        e_name = ttk.Entry(body, font=('Helvetica', 10))
        e_name.grid(row=1, column=1, sticky='ew', pady=8)

        tk.Label(body, text="Department:", font=('Helvetica', 10), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=2, column=0, sticky='w', pady=8)
        e_dept = ttk.Combobox(body, values=COLLEGE_DEPARTMENTS, state="readonly", font=('Helvetica', 10))
        e_dept.set(COLLEGE_DEPARTMENTS[0])
        e_dept.grid(row=2, column=1, sticky='ew', pady=8)

        tk.Label(body, text="Designation:", font=('Helvetica', 10), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=3, column=0, sticky='w', pady=8)
        e_desig = ttk.Entry(body, font=('Helvetica', 10))
        e_desig.grid(row=3, column=1, sticky='ew', pady=8)

        tk.Label(body, text="RFID Card No:", font=('Helvetica', 10), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=4, column=0, sticky='w', pady=8)
        e_card = ttk.Entry(body, font=('Helvetica', 10))
        e_card.grid(row=4, column=1, sticky='ew', pady=8)

        # Options (Clean visible checkboxes with high-contrast text)
        opts_frame = tk.LabelFrame(
            body,
            text=" Access & Hardware Settings ",
            font=('Helvetica', 9, 'bold'),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE,
            padx=16,
            pady=12,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER
        )
        opts_frame.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(14, 6))

        # Option 1: Admin Privilege (Locks hardware menu on terminal)
        var_admin = tk.BooleanVar(value=False)
        row_admin = tk.Frame(opts_frame, bg=COLOR_SURFACE)
        row_admin.pack(fill=tk.X, pady=4, anchor='w')

        cb_admin = ttk.Checkbutton(row_admin, variable=var_admin, onvalue=True, offvalue=False)
        cb_admin.pack(side=tk.LEFT)

        lbl_admin = tk.Label(
            row_admin,
            text="Biometric Device Administrator (Locks Hardware Menu)",
            font=('Helvetica', 9),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE,
            cursor='hand2'
        )
        lbl_admin.pack(side=tk.LEFT, padx=(6, 0))
        lbl_admin.bind('<Button-1>', lambda e: var_admin.set(not var_admin.get()))

        # Option 2: Push to Device (Optional, off by default to prevent freeze)
        var_sync = tk.BooleanVar(value=False)
        row_sync = tk.Frame(opts_frame, bg=COLOR_SURFACE)
        row_sync.pack(fill=tk.X, pady=4, anchor='w')

        cb_sync = ttk.Checkbutton(row_sync, variable=var_sync, onvalue=True, offvalue=False)
        cb_sync.pack(side=tk.LEFT)

        lbl_sync = tk.Label(
            row_sync,
            text="Push directly to Biometric Terminal (if online)",
            font=('Helvetica', 9),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE,
            cursor='hand2'
        )
        lbl_sync.pack(side=tk.LEFT, padx=(6, 0))
        lbl_sync.bind('<Button-1>', lambda e: var_sync.set(not var_sync.get()))

        # Footer
        btn_bar = tk.Frame(dialog, bg=COLOR_SURFACE, padx=20, pady=14)
        btn_bar.pack(fill=tk.X)

        def save():
            uid = e_id.get().strip()
            name = e_name.get().strip()
            if not uid or not name:
                messagebox.showerror("Validation Error", "Staff ID and Full Name are required.", parent=dialog)
                return
            conn = None
            try:
                conn = get_connection()
                priv = 14 if var_admin.get() else 0
                conn.cursor().execute("""
                    INSERT INTO staff (user_id, name, department, designation, card_number, privilege)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (uid, name, e_dept.get(), e_desig.get().strip(), e_card.get().strip(), priv))
                conn.commit()
            except Exception as ex:
                if "UNIQUE constraint failed" in str(ex):
                    messagebox.showerror("Duplicate ID", f"Staff ID '{uid}' already exists!", parent=dialog)
                else:
                    messagebox.showerror("Error", f"Failed to add staff: {ex}", parent=dialog)
                return
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

            self._log(f"Staff added: {name} ({uid})")

            if var_sync.get():
                def push_worker():
                    try:
                        driver = self._get_driver()
                        ok, msg = driver.add_user(uid, name, priv, e_card.get().strip())
                        if ok: self._log(f"Device sync: {msg}")
                        else: self._log(f"Device sync notice: {msg}")
                    except Exception as e:
                        self._log(f"Device sync skipped: {e}")
                threading.Thread(target=push_worker, daemon=True).start()

            self._refresh_staff_tab()
            self._refresh_dashboard()
            self._populate_staff_dropdown()
            dialog.destroy()
            messagebox.showinfo("Success", f"Staff member '{name}' ({uid}) registered successfully.")

        self._create_outline_btn(btn_bar, "Cancel", dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        self._create_primary_btn(btn_bar, "Save Staff", save).pack(side=tk.RIGHT)

    def _dialog_edit_staff(self):
        sel = self.tree_staff.selection()
        if not sel:
            messagebox.showwarning("Select Staff", "Please select a staff member to edit.")
            return
        item = self.tree_staff.item(sel[0])['values']
        uid, name, dept, desig, card, role_str, status = item

        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Staff: {name}")
        self._center_window(dialog, 540, 520)
        dialog.resizable(False, False)
        dialog.configure(bg=COLOR_SURFACE)
        dialog.transient(self)
        dialog.grab_set()

        header = tk.Frame(dialog, bg=COLOR_BG, height=55, highlightthickness=1, highlightbackground=COLOR_BORDER)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text=f"✏️   Edit Staff Member ({uid})", font=('Helvetica', 12, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_BG).pack(side=tk.LEFT, padx=20, pady=12)

        body = tk.Frame(dialog, bg=COLOR_SURFACE, padx=25, pady=18)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=0, minsize=140)
        body.columnconfigure(1, weight=1)

        tk.Label(body, text="Staff ID:", font=('Helvetica', 10), fg=COLOR_TEXT_MUTED, bg=COLOR_SURFACE).grid(row=0, column=0, sticky='w', pady=8)
        tk.Label(body, text=f"{uid}  (Fixed ID)", font=('Helvetica', 10, 'bold'), fg=COLOR_PRIMARY, bg=COLOR_SURFACE).grid(row=0, column=1, sticky='w', pady=8)

        tk.Label(body, text="Full Name *:", font=('Helvetica', 10, 'bold'), fg=COLOR_TEXT_MAIN, bg=COLOR_SURFACE).grid(row=1, column=0, sticky='w', pady=8)
        e_name = ttk.Entry(body, font=('Helvetica', 10))
        e_name.insert(0, str(name))
        e_name.grid(row=1, column=1, sticky='ew', pady=8)
        e_name.focus_set()

        tk.Label(body, text="Department:", font=('Helvetica', 10), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=2, column=0, sticky='w', pady=8)
        e_dept = ttk.Combobox(body, values=COLLEGE_DEPARTMENTS, state="readonly", font=('Helvetica', 10))
        e_dept.set(str(dept))
        e_dept.grid(row=2, column=1, sticky='ew', pady=8)

        tk.Label(body, text="Designation:", font=('Helvetica', 10), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=3, column=0, sticky='w', pady=8)
        e_desig = ttk.Entry(body, font=('Helvetica', 10))
        e_desig.insert(0, str(desig))
        e_desig.grid(row=3, column=1, sticky='ew', pady=8)

        tk.Label(body, text="RFID Card No:", font=('Helvetica', 10), fg=COLOR_TEXT_SECONDARY, bg=COLOR_SURFACE).grid(row=4, column=0, sticky='w', pady=8)
        e_card = ttk.Entry(body, font=('Helvetica', 10))
        e_card.insert(0, "" if card == "--" else str(card))
        e_card.grid(row=4, column=1, sticky='ew', pady=8)

        opts_frame = tk.LabelFrame(
            body,
            text=" Access & Hardware Settings ",
            font=('Helvetica', 9, 'bold'),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE,
            padx=16,
            pady=12,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER
        )
        opts_frame.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(14, 6))

        var_admin = tk.BooleanVar(value=(role_str == "Admin"))
        row_admin = tk.Frame(opts_frame, bg=COLOR_SURFACE)
        row_admin.pack(fill=tk.X, pady=4, anchor='w')

        cb_admin = ttk.Checkbutton(row_admin, variable=var_admin, onvalue=True, offvalue=False)
        cb_admin.pack(side=tk.LEFT)

        lbl_admin = tk.Label(
            row_admin,
            text="Biometric Device Administrator (Locks Hardware Menu)",
            font=('Helvetica', 9),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE,
            cursor='hand2'
        )
        lbl_admin.pack(side=tk.LEFT, padx=(6, 0))
        lbl_admin.bind('<Button-1>', lambda e: var_admin.set(not var_admin.get()))

        var_sync = tk.BooleanVar(value=False)
        row_sync = tk.Frame(opts_frame, bg=COLOR_SURFACE)
        row_sync.pack(fill=tk.X, pady=4, anchor='w')

        cb_sync = ttk.Checkbutton(row_sync, variable=var_sync, onvalue=True, offvalue=False)
        cb_sync.pack(side=tk.LEFT)

        lbl_sync = tk.Label(
            row_sync,
            text="Update Biometric Terminal immediately (if online)",
            font=('Helvetica', 9),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_SURFACE,
            cursor='hand2'
        )
        lbl_sync.pack(side=tk.LEFT, padx=(6, 0))
        lbl_sync.bind('<Button-1>', lambda e: var_sync.set(not var_sync.get()))

        btn_bar = tk.Frame(dialog, bg=COLOR_SURFACE, padx=20, pady=14)
        btn_bar.pack(fill=tk.X)

        def save():
            new_name = e_name.get().strip()
            if not new_name:
                messagebox.showerror("Validation Error", "Full Name cannot be empty.", parent=dialog)
                return
            conn = None
            try:
                conn = get_connection()
                priv = 14 if var_admin.get() else 0
                conn.cursor().execute("""
                    UPDATE staff 
                    SET name = ?, department = ?, designation = ?, card_number = ?, privilege = ?
                    WHERE user_id = ?
                """, (new_name, e_dept.get(), e_desig.get().strip(), e_card.get().strip(), priv, uid))
                conn.commit()
            except Exception as ex:
                messagebox.showerror("Error", f"Failed to update staff: {ex}", parent=dialog)
                return
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

            self._log(f"Staff updated: {new_name} ({uid})")

            if var_sync.get():
                def push_edit_worker():
                    try:
                        driver = self._get_driver()
                        ok, msg = driver.add_user(str(uid), new_name, priv, e_card.get().strip())
                        if ok: self._log(f"Device sync: {msg}")
                        else: self._log(f"Device sync notice: {msg}")
                    except Exception as e:
                        self._log(f"Device sync notice: {e}")
                threading.Thread(target=push_edit_worker, daemon=True).start()

            self._refresh_staff_tab()
            self._refresh_dashboard()
            self._populate_staff_dropdown()
            dialog.destroy()
            messagebox.showinfo("Success", f"Staff member '{new_name}' updated successfully.")

        self._create_outline_btn(btn_bar, "Cancel", dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        self._create_primary_btn(btn_bar, "Update Staff", save).pack(side=tk.RIGHT)

    def _action_delete_staff(self):
        sel = self.tree_staff.selection()
        if not sel:
            messagebox.showwarning("Select Staff", "Please select a staff member to deactivate.")
            return
        item = self.tree_staff.item(sel[0])['values']
        uid, name = str(item[0]), str(item[1])

        confirm = messagebox.askyesno(
            "Confirm Deactivation",
            f"Deactivate staff member '{name}' ({uid})?\n\n"
            f"• Past attendance history will be preserved in the database.\n"
            f"• If the biometric machine is online, their enrollment will also be removed from the terminal."
        )
        if not confirm:
            return

        conn = None
        try:
            conn = get_connection()
            conn.cursor().execute("UPDATE staff SET status = 'Inactive' WHERE user_id = ?", (uid,))
            conn.commit()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to deactivate staff: {e}")
            return
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        self._log(f"Deactivated: {name} ({uid})")

        def remove_from_device_worker():
            try:
                driver = self._get_driver()
                ok, msg = driver.delete_user(str(uid))
                if ok:
                    self._log(f"Device sync: Removed {name} ({uid}) from machine memory.")
                else:
                    self._log(f"Device removal notice: {msg}")
            except Exception as e:
                self._log(f"Device removal skipped: {e}")

        threading.Thread(target=remove_from_device_worker, daemon=True).start()

        self._refresh_staff_tab()
        self._refresh_dashboard()
        self._populate_staff_dropdown()
        messagebox.showinfo(
            "Deactivation Complete",
            f"Staff member '{name}' ({uid}) has been deactivated.\n\n"
            f"Their past attendance records remain safely preserved in the database."
        )

if __name__ == '__main__':
    app = AttendanceApp()
    app.mainloop()
