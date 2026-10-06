"""
Database Manager for College Attendance System
Manages SQLite database (college_attendance.db)
"""

import sqlite3
import os
import hashlib
import shutil
import sys
from datetime import datetime, timedelta

if getattr(sys, 'frozen', False):
    # When packaged as a standalone Windows executable (.exe),
    # store database next to the .exe file so data persists across reboots.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(BASE_DIR, "college_attendance.db")

def get_connection(db_path=DB_FILE):
    conn = sqlite3.connect(db_path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 60000;")
    except Exception:
        pass
    return conn

def init_db(db_path=DB_FILE):
    """Initializes tables, creates performance indexes, and configures WAL journal mode."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute("PRAGMA busy_timeout = 60000;")
        except Exception:
            pass

        # 1. Staff Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                designation TEXT NOT NULL,
                card_number TEXT DEFAULT '',
                privilege INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Raw Device Punches (Immutable Audit Trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_punches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                punch_time TIMESTAMP NOT NULL,
                punch_type INTEGER DEFAULT 0,
                verify_type INTEGER DEFAULT 1,
                device_ip TEXT DEFAULT '192.168.1.201',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, punch_time)
            )
        """)

        # 3. Processed Daily Attendance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date DATE NOT NULL,
                first_in TIME,
                last_out TIME,
                total_hours REAL,
                status TEXT,
                UNIQUE(user_id, date)
            )
        """)

        # Performance Indexes to guarantee instant sub-millisecond lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_punches_uid_time ON attendance_punches (user_id, punch_time);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_punches_time ON attendance_punches (punch_time);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_uid_date ON daily_attendance (user_id, date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_attendance (date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_staff_uid ON staff (user_id);")

        # 4. Device Settings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_settings (
                id INTEGER PRIMARY KEY,
                ip_address TEXT DEFAULT '192.168.1.201',
                port INTEGER DEFAULT 4370,
                comm_key INTEGER DEFAULT 0,
                college_name TEXT DEFAULT 'NICETECH BIOMETRIC SYSTEM',
                last_sync TIMESTAMP
            )
        """)

        # Insert default settings if not exists
        cursor.execute("SELECT COUNT(*) FROM device_settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO device_settings (id, ip_address, port, comm_key, college_name)
                VALUES (1, '192.168.1.201', 4370, 0, 'NICETECH BIOMETRIC SYSTEM')
            """)

        # 5. Administrator Accounts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'Administrator',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed default admin (niadmin / ni2027) if empty
        cursor.execute("SELECT COUNT(*) FROM admin_users")
        if cursor.fetchone()[0] == 0:
            default_hash = hashlib.sha256("ni2027".encode('utf-8')).hexdigest()
            cursor.execute("""
                INSERT INTO admin_users (username, password_hash, role)
                VALUES ('niadmin', ?, 'Administrator')
            """, (default_hash,))

        # 6. Shift & Attendance Rules Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance_rules (
                id INTEGER PRIMARY KEY,
                punch_mode TEXT DEFAULT 'First-In / Last-Out',
                shift_start TEXT DEFAULT '09:00:00',
                shift_end TEXT DEFAULT '17:00:00',
                min_full_hours REAL DEFAULT 7.0,
                min_half_hours REAL DEFAULT 4.0,
                grace_minutes INTEGER DEFAULT 15
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM attendance_rules")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO attendance_rules (id, punch_mode, shift_start, shift_end, min_full_hours, min_half_hours, grace_minutes)
                VALUES (1, 'First-In / Last-Out', '09:00:00', '17:00:00', 7.0, 4.0, 15)
            """)

        conn.commit()
    finally:
        conn.close()

def clear_all_operational_data():
    """
    Completely removes all staff profiles, raw punch logs, and calculated daily attendance.
    Preserves administrator login accounts, device connection settings, and shift rules.
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM daily_attendance")
        c.execute("DELETE FROM attendance_punches")
        c.execute("DELETE FROM staff")
        c.execute("DELETE FROM sqlite_sequence WHERE name IN ('attendance_punches', 'daily_attendance', 'staff')")
        conn.commit()
    finally:
        conn.close()

def seed_sample_data(cursor):
    """Seeds realistic faculty staff and punches so the UI is immediately functional."""
    sample_staff = [
        ('101', 'Dr. Rajesh Sharma', 'CSE', 'Professor & HOD', '00084321', 14),
        ('102', 'Prof. Priya Verma', 'AI & DS', 'Associate Professor', '00084322', 0),
        ('103', 'Prof. Amit Patel', 'MECH', 'Assistant Professor', '00084323', 0),
        ('104', 'Dr. Sunita Rao', 'ECE', 'Professor', '00084324', 0),
        ('105', 'Prof. Karthik Raja', 'EEE', 'Assistant Professor', '00084325', 0),
        ('106', 'Kavita Nair', 'Administration', 'Office Superintendent', '00084326', 0),
        ('107', 'Suresh Kumar', 'Maintenance', 'Supervisor', '00084327', 0),
        ('108', 'Meena Joshi', 'Library', 'Librarian', '00084328', 0),
        ('109', 'Dr. Ananya Iyer', 'Physics', 'Assistant Professor', '00084329', 0),
        ('110', 'Dr. Robert David', 'Chemistry', 'Assistant Professor', '00084330', 0),
        ('111', 'Dr. Mary Joseph', 'English', 'Associate Professor', '00084331', 0),
        ('112', 'Prof. Naveen Kumar', 'IT', 'Assistant Professor', '00084332', 0)
    ]
    cursor.executemany("""
        INSERT INTO staff (user_id, name, department, designation, card_number, privilege)
        VALUES (?, ?, ?, ?, ?, ?)
    """, sample_staff)

    # Seed punches for the last 3 days
    today = datetime.now().date()
    punches = []
    for day_offset in range(3, -1, -1):
        d = today - timedelta(days=day_offset)
        # Skip Sundays
        if d.weekday() == 6:
            continue
        # Staff 101: In 08:52, Out 17:15 (Present)
        punches.append(('101', f"{d} 08:52:14", 0, 1))
        punches.append(('101', f"{d} 17:15:30", 1, 1))

        # Staff 102: In 09:05, Out 17:02 (Present)
        punches.append(('102', f"{d} 09:05:40", 0, 1))
        punches.append(('102', f"{d} 17:02:18", 1, 1))

        # Staff 103: In 08:45, Out 13:10 (Half Day)
        punches.append(('103', f"{d} 08:45:00", 0, 1))
        punches.append(('103', f"{d} 13:10:45", 1, 1))

        # Staff 104: In 09:12, only in (Missed Out punch)
        if day_offset != 0:
            punches.append(('104', f"{d} 09:12:00", 0, 1))
            punches.append(('104', f"{d} 17:30:10", 1, 1))
        else:
            punches.append(('104', f"{d} 09:12:00", 0, 1))

        # Staff 105: Absent on day 2
        if day_offset != 2:
            punches.append(('105', f"{d} 08:58:20", 0, 1))
            punches.append(('105', f"{d} 17:05:10", 1, 1))

        # Staff 106: In 08:40, Out 16:45
        punches.append(('106', f"{d} 08:40:15", 0, 1))
        punches.append(('106', f"{d} 16:45:50", 1, 1))

        # Staff 107: In 08:50, Out 17:10
        punches.append(('107', f"{d} 08:50:30", 0, 1))
        punches.append(('107', f"{d} 17:10:00", 1, 1))

        # Staff 108: In 09:00, Out 17:00
        punches.append(('108', f"{d} 09:00:10", 0, 1))
        punches.append(('108', f"{d} 17:00:25", 1, 1))

    cursor.executemany("""
        INSERT OR IGNORE INTO attendance_punches (user_id, punch_time, punch_type, verify_type)
        VALUES (?, ?, ?, ?)
    """, punches)

def get_device_settings():
    conn = get_connection()
    try:
        row = conn.cursor().execute("SELECT * FROM device_settings WHERE id = 1").fetchone()
        return dict(row) if row else {'ip_address': '192.168.1.201', 'port': 4370, 'comm_key': 0, 'college_name': 'NICETECH BIOMETRIC SYSTEM'}
    finally:
        conn.close()

def update_device_settings(ip, port, comm_key, college_name):
    conn = get_connection()
    try:
        conn.cursor().execute("""
            UPDATE device_settings 
            SET ip_address = ?, port = ?, comm_key = ?, college_name = ?
            WHERE id = 1
        """, (ip, int(port), int(comm_key), college_name))
        conn.commit()
    finally:
        conn.close()

def update_last_sync():
    conn = get_connection()
    try:
        conn.cursor().execute("UPDATE device_settings SET last_sync = ? WHERE id = 1", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        conn.commit()
    finally:
        conn.close()

def record_punches(punches, device_ip='192.168.1.201'):
    """
    Inserts punch records [(user_id, timestamp_str, punch_type, verify_type), ...]
    into attendance_punches using INSERT OR IGNORE so duplicates are skipped.
    Returns the number of new records inserted.
    """
    if not punches:
        return 0
    conn = get_connection()
    try:
        c = conn.cursor()
        count_before = c.execute("SELECT COUNT(*) FROM attendance_punches").fetchone()[0]
        c.executemany("""
            INSERT OR IGNORE INTO attendance_punches (user_id, punch_time, punch_type, verify_type, device_ip)
            VALUES (?, ?, ?, ?, ?)
        """, [(p[0], str(p[1]), int(p[2]) if len(p) > 2 else 0, int(p[3]) if len(p) > 3 else 1, device_ip) for p in punches])
        conn.commit()
        count_after = c.execute("SELECT COUNT(*) FROM attendance_punches").fetchone()[0]
        return count_after - count_before
    finally:
        conn.close()

def sync_users_from_device(users_list):
    """
    Saves or merges users downloaded directly from the physical biometric terminal.
    - If user does not exist in local DB: inserts into 'staff' with default department and designation.
    - If user already exists: updates card_number and privilege while preserving their assigned college department and designation.
    Returns (new_count, updated_count).
    """
    if not users_list:
        return 0, 0
    conn = get_connection()
    try:
        c = conn.cursor()
        new_count = 0
        updated_count = 0

        for u in users_list:
            uid = str(u.get('user_id', '')).strip()
            if not uid:
                continue
            name = str(u.get('name', '')).strip() or f"Staff {uid}"
            card = str(u.get('card_number', '')).strip()
            priv = int(u.get('privilege', 0))

            row = c.execute("SELECT user_id FROM staff WHERE user_id = ?", (uid,)).fetchone()
            if row:
                c.execute("""
                    UPDATE staff 
                    SET card_number = CASE WHEN card_number = '' OR card_number IS NULL THEN ? ELSE card_number END,
                        privilege = ?
                    WHERE user_id = ?
                """, (card, priv, uid))
                updated_count += 1
            else:
                c.execute("""
                    INSERT INTO staff (user_id, name, department, designation, card_number, privilege, status)
                    VALUES (?, ?, 'Administration', 'Faculty / Staff', ?, ?, 'Active')
                """, (uid, name, card, priv))
                new_count += 1

        conn.commit()
        return new_count, updated_count
    finally:
        conn.close()

def get_all_active_staff_list():
    """Returns list of active staff dictionaries for device synchronization."""
    conn = get_connection()
    try:
        c = conn.cursor()
        rows = c.execute("SELECT user_id, name, department, designation, card_number, privilege FROM staff WHERE status = 'Active'").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

# =============================================================================
# SHIFT & PUNCH CALCULATION RULES
# =============================================================================
def get_attendance_rules():
    """Retrieves configurable shift timings and punch-in/out logic rules."""
    conn = get_connection()
    try:
        row = conn.cursor().execute("SELECT * FROM attendance_rules WHERE id = 1").fetchone()
        if row:
            return dict(row)
        return {
            'punch_mode': 'First-In / Last-Out',
            'shift_start': '09:00:00',
            'shift_end': '17:00:00',
            'min_full_hours': 7.0,
            'min_half_hours': 4.0,
            'grace_minutes': 15
        }
    finally:
        conn.close()

def update_attendance_rules(punch_mode, shift_start, shift_end, min_full_hours, min_half_hours, grace_minutes):
    """Updates configurable shift rules and calculation thresholds."""
    conn = get_connection()
    try:
        conn.cursor().execute("""
            UPDATE attendance_rules
            SET punch_mode = ?, shift_start = ?, shift_end = ?, min_full_hours = ?, min_half_hours = ?, grace_minutes = ?
            WHERE id = 1
        """, (
            str(punch_mode).strip(),
            str(shift_start).strip(),
            str(shift_end).strip(),
            float(min_full_hours),
            float(min_half_hours),
            int(grace_minutes)
        ))
        conn.commit()
    finally:
        conn.close()

# =============================================================================
# ADMIN AUTHENTICATION
# =============================================================================
def verify_admin_login(username, password):
    """Verifies credentials against admin_users table."""
    conn = get_connection()
    try:
        c = conn.cursor()
        pwd_hash = hashlib.sha256(str(password).strip().encode('utf-8')).hexdigest()
        row = c.execute(
            "SELECT id, username, role FROM admin_users WHERE LOWER(username) = LOWER(?) AND password_hash = ?",
            (str(username).strip(), pwd_hash)
        ).fetchone()
        if row:
            return True, dict(row)
        return False, None
    except Exception:
        return False, None
    finally:
        conn.close()

def change_admin_password(username, old_password, new_password):
    """Changes password for an admin user after verifying old password."""
    valid, user = verify_admin_login(username, old_password)
    if not valid:
        return False, "Current password is incorrect."
    if not new_password or len(str(new_password).strip()) < 4:
        return False, "New password must be at least 4 characters long."
    new_hash = hashlib.sha256(str(new_password).strip().encode('utf-8')).hexdigest()
    conn = get_connection()
    try:
        conn.cursor().execute(
            "UPDATE admin_users SET password_hash = ? WHERE LOWER(username) = LOWER(?)",
            (new_hash, str(username).strip())
        )
        conn.commit()
        return True, "Password updated successfully."
    except Exception as e:
        return False, f"Failed to update password: {str(e)}"
    finally:
        conn.close()

# =============================================================================
# DATABASE BACKUP & RESTORE (For Transferring to New PC or Cloud Storage)
# =============================================================================
def export_database_backup(destination_file):
    """
    Creates an exact, safe online backup copy of the SQLite database.
    Can be stored locally, copied to a USB drive, or uploaded to Google Drive.
    """
    src_conn = get_connection()
    try:
        try:
            src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        
        dest_dir = os.path.dirname(os.path.abspath(destination_file))
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
            
        dest_conn = sqlite3.connect(destination_file)
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
        
        c = src_conn.cursor()
        staff_count = c.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
        punch_count = c.execute("SELECT COUNT(*) FROM attendance_punches").fetchone()[0]
        
        file_size_kb = os.path.getsize(destination_file) / 1024.0
        return True, {
            'file': destination_file,
            'size_kb': round(file_size_kb, 1),
            'staff_count': staff_count,
            'punch_count': punch_count,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return False, f"Failed to export backup: {str(e)}"
    finally:
        src_conn.close()

def restore_database_backup(source_backup_file):
    """
    Restores the database from a backup file (.bak / .db).
    Validates tables before safely replacing active database.
    """
    if not os.path.exists(source_backup_file):
        return False, "Selected backup file does not exist."
        
    try:
        # Validate that the backup is a valid SQLite file with expected tables
        test_conn = sqlite3.connect(source_backup_file)
        c = test_conn.cursor()
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        required_tables = {'staff', 'attendance_punches', 'device_settings'}
        if not required_tables.issubset(set(tables)):
            test_conn.close()
            return False, f"Invalid backup file: Missing required tables."
            
        staff_count = c.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
        punch_count = c.execute("SELECT COUNT(*) FROM attendance_punches").fetchone()[0]
        test_conn.close()
        
        # Create a rollback safety copy of current DB in case something fails
        rollback_file = DB_FILE + ".pre_restore_bak"
        if os.path.exists(DB_FILE):
            shutil.copy2(DB_FILE, rollback_file)
            
        src_conn = sqlite3.connect(source_backup_file)
        dest_conn = sqlite3.connect(DB_FILE)
        src_conn.backup(dest_conn)
        src_conn.close()
        dest_conn.close()
        
        # Ensure schema updates and admin accounts exist
        init_db(DB_FILE)
        
        return True, {
            'staff_count': staff_count,
            'punch_count': punch_count,
            'restored_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return False, f"Restore failed: {str(e)}"

