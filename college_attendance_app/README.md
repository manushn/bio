# College Biometric Attendance System (In-House eTimeTrackLite Replacement)

A modern, standalone, zero-license attendance management desktop application created to communicate directly with your college biometric terminal (`192.168.1.201:4370`).

---

## 🌟 Key Features

1. **Hardware Communication:**
   - Connects directly to ZKTeco / eSSL devices over TCP port 4370.
   - Live hardware status checks, firmware version queries, and clock synchronization.
   - Safe, non-destructive read-only log downloads (preserves device memory).

2. **Staff / Faculty Management:**
   - Add new faculty/staff (Staff ID, Name, Department, Designation, RFID Card, Privilege).
   - Edit existing staff details.
   - Deactivate (soft-delete) staff without losing historical attendance logs.
   - Filter and search by Name, ID, or Department.

3. **Intelligent Attendance Engine:**
   - Converts multiple daily punches into clean, structured records:
     - **First Punch of the Day** = Official `IN Time`.
     - **Last Punch of the Day** = Official `OUT Time`.
     - **Working Duration** = `OUT - IN`.
     - **Status Calculation:**
       - `>= 7.0 Hours` -> **Present**
       - `>= 4.0 Hours` -> **Half Day**
       - `< 4.0 Hours`  -> **Short Leave**
       - `1 Punch Only` -> **Missed Out**
       - `0 Punches`    -> **Absent**

4. **PDF Reports & Exports:**
   - Date-wise and Date-Range attendance reports.
   - Multi-page landscape PDF layout with College Header, Summary KPI Cards, and Signature Blocks (Prepared By, HOD, Principal).
   - Zero external library dependencies (uses pure Python PDF 1.4 generation).
   - One-click CSV / Excel spreadsheet export.

5. **Single-File Database (`college_attendance.db`):**
   - Full SQLite schema storing multi-year attendance history in a lightweight, portable file.

---

## 🚀 How to Run the Application

### On macOS / Linux:
```bash
python3 run_app.py
```

### On Windows:
```cmd
python run_app.py
```

---

## 📦 How to Compile to a Single Windows `.exe` (`NICETECH_biometric.exe`)

You can create `NICETECH_biometric.exe` using any of these two methods:

### Method 1: Using Any Windows Computer (One-Click)
1. Copy this project folder to any Windows computer.
2. Double-click **`build_windows_exe.bat`**.
3. It will automatically install `reportlab` and `pyinstaller` and compile the application.
4. Your standalone single-file executable will appear in:
   ```text
   Ready_To_Distribute\NICETECH_biometric.exe
   ```
5. You can now copy `NICETECH_biometric.exe` to any college computer (via USB or Google Drive). **No Python installation or setup is needed.**
6. On every new computer, `NICETECH_biometric.exe` automatically starts with a **100% fresh database** containing only the admin credentials:
   - **Username**: `niadmin`
   - **Password**: `ni2027`

### Method 2: Free Automated Cloud Build via GitHub Actions
If you push this repository to GitHub:
1. GitHub automatically runs the included `.github/workflows/build_windows_exe.yml` on a Windows cloud server.
2. Go to the **Actions** tab on your GitHub repository.
3. Download the built artifact: **`NICETECH_biometric-Windows-EXE`** directly to your Mac or Windows PC!

---

## 📂 Project Structure

```text
eTimeTrackLite/
├── run_app.py                    # Application launcher
├── NICETECH_biometric.spec       # PyInstaller standalone specification
├── build_windows_exe.bat         # One-click Windows executable builder
├── installer_script.iss          # Inno Setup Windows installer wizard
├── requirements.txt              # Dependencies (reportlab, pyinstaller)
├── .github/workflows/
│   └── build_windows_exe.yml    # Automated cloud build workflow
└── college_attendance_app/
    ├── app.py                   # Main Tkinter/TTK Desktop Application
    ├── database.py              # SQLite Database manager (WAL mode)
    ├── device_driver.py         # Biometric TCP socket driver
    ├── attendance_engine.py     # Attendance batch processing engine
    ├── pdf_generator.py         # ReportLab PDF report generator
    └── README.md                # Documentation
```
