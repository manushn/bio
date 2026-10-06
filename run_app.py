#!/usr/bin/env python3
"""
Launcher for College Biometric Attendance System
Includes auto-detection for Python environments with Tkinter support.
"""

import sys
import os

# Check if running as a compiled PyInstaller executable or normal python script
if not getattr(sys, 'frozen', False):
    try:
        import tkinter
    except ImportError:
        # Try to find a system Python that has Tkinter installed (common pyenv issue on macOS)
        candidates = [
            "/usr/local/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
            "/usr/bin/python3"
        ]
        re_executed = False
        for py in candidates:
            if os.path.exists(py) and py != sys.executable:
                if os.system(f'"{py}" -c "import tkinter" >/dev/null 2>&1') == 0:
                    print(f"[*] Note: Current Python ({sys.executable}) lacks Tkinter support.")
                    print(f"[*] Switching to compatible Python: {py}")
                    os.execv(py, [py] + sys.argv)
                    re_executed = True
                    break

        if not re_executed:
            print("\n[!] Error: No Python installation with Tkinter support found on your system.")
            print("To fix this in your pyenv environment, run:")
            print("    brew install tcl-tk")
            print("    pyenv install 3.12.2 --force")
            print("Or run using the system Python directly:")
            print("    /usr/local/bin/python3 run_app.py\n")
            sys.exit(1)

# Configure path resolution for both dev mode and PyInstaller frozen mode
if getattr(sys, 'frozen', False):
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    app_dir = os.path.join(bundle_dir, "college_attendance_app")
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(current_dir, "college_attendance_app")
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

from app import AttendanceApp

if __name__ == "__main__":
    app = AttendanceApp()
    app.mainloop()
