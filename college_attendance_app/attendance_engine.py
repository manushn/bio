"""
Attendance Business Logic Engine
Calculates First In, Last Out, Total Working Hours, and Attendance Status
High-performance batch processing with guaranteed database connection closure.
"""

import sqlite3
from datetime import datetime
from database import get_connection, DB_FILE

def calculate_daily_attendance(target_date=None, db_path=DB_FILE):
    """
    Computes daily attendance for active staff on a given date (or all dates in punch log).
    Supports configurable punch modes:
    1. 'First-In / Last-Out': Earliest punch of day = IN, latest punch of day = OUT.
    2. 'Terminal Key Mode (F1=In, F2=Out)': Uses machine punch state key.
    Applies configurable minimum hours for Full Day and Half Day.
    Uses high-speed batch queries and guarantees connection closure.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()

        # 1. Fetch rules using current cursor (no secondary connection)
        r_row = cursor.execute("SELECT * FROM attendance_rules WHERE id = 1").fetchone()
        rules = dict(r_row) if r_row else {}
        punch_mode = rules.get('punch_mode', 'First-In / Last-Out')
        min_full = float(rules.get('min_full_hours', 7.0))
        min_half = float(rules.get('min_half_hours', 4.0))

        # 2. Get active staff user IDs
        cursor.execute("SELECT user_id FROM staff WHERE status = 'Active'")
        active_staff = [r[0] for r in cursor.fetchall()]
        if not active_staff:
            return

        # 3. Determine dates to compute
        if target_date:
            dates = [target_date]
        else:
            cursor.execute("SELECT DISTINCT date(punch_time) FROM attendance_punches ORDER BY date(punch_time) ASC")
            dates = [r[0] for r in cursor.fetchall()]

        if not dates:
            return

        # 4. Process each date in fast memory batches
        for d in dates:
            cursor.execute("""
                SELECT user_id, punch_time, punch_type 
                FROM attendance_punches
                WHERE punch_time >= ? AND punch_time <= ?
                ORDER BY punch_time ASC
            """, (f"{d} 00:00:00", f"{d} 23:59:59"))
            day_punches = cursor.fetchall()

            # Group punches by user_id
            user_punches_map = {}
            for p in day_punches:
                uid = p['user_id']
                if uid not in user_punches_map:
                    user_punches_map[uid] = []
                user_punches_map[uid].append(p)

            daily_records = []
            for user_id in active_staff:
                raw_rows = user_punches_map.get(user_id, [])
                if not raw_rows:
                    first_in = None
                    last_out = None
                    total_hours = 0.0
                    status = "Absent"
                else:
                    punches = [datetime.strptime(r['punch_time'], "%Y-%m-%d %H:%M:%S") for r in raw_rows]

                    if "Terminal Key" in punch_mode:
                        in_punches = [datetime.strptime(r['punch_time'], "%Y-%m-%d %H:%M:%S") for r in raw_rows if r['punch_type'] == 0]
                        out_punches = [datetime.strptime(r['punch_time'], "%Y-%m-%d %H:%M:%S") for r in raw_rows if r['punch_type'] == 1]
                        if in_punches and out_punches:
                            in_dt = in_punches[0]
                            out_dt = out_punches[-1]
                        elif len(punches) >= 2:
                            in_dt = punches[0]
                            out_dt = punches[-1]
                        else:
                            in_dt = punches[0]
                            out_dt = None
                    else:
                        # Standard First-In / Last-Out
                        if len(punches) == 1:
                            in_dt = punches[0]
                            out_dt = None
                        else:
                            in_dt = punches[0]
                            out_dt = punches[-1]

                    first_in = in_dt.strftime("%H:%M:%S") if in_dt else None
                    last_out = out_dt.strftime("%H:%M:%S") if out_dt else None

                    if in_dt and out_dt and out_dt > in_dt:
                        duration = (out_dt - in_dt).total_seconds() / 3600.0
                        total_hours = round(duration, 2)
                        if total_hours >= min_full:
                            status = "Present"
                        elif total_hours >= min_half:
                            status = "Half Day"
                        else:
                            status = "Short Leave"
                    elif in_dt:
                        total_hours = 0.0
                        status = "Missed Out"
                    else:
                        total_hours = 0.0
                        status = "Absent"

                daily_records.append((user_id, d, first_in, last_out, total_hours, status))

            # Batch upsert all staff for this date
            cursor.executemany("""
                INSERT INTO daily_attendance (user_id, date, first_in, last_out, total_hours, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, date) DO UPDATE SET
                    first_in = excluded.first_in,
                    last_out = excluded.last_out,
                    total_hours = excluded.total_hours,
                    status = excluded.status
            """, daily_records)
            conn.commit()

    finally:
        conn.close()

def get_attendance_report(start_date, end_date, department="All", status="All", staff_id="All", db_path=DB_FILE):
    """
    Fetches processed attendance for date-range and filters.
    Guarantees database connection closure.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()

        query = """
            SELECT a.date, s.user_id, s.name, s.department, s.designation, 
                   a.first_in, a.last_out, a.total_hours, a.status
            FROM daily_attendance a
            JOIN staff s ON a.user_id = s.user_id
            WHERE a.date BETWEEN ? AND ?
        """
        params = [start_date, end_date]

        if department and department != "All":
            query += " AND s.department = ?"
            params.append(department)

        if status and status != "All":
            query += " AND a.status = ?"
            params.append(status)

        if staff_id and staff_id != "All":
            query += " AND s.user_id = ?"
            params.append(staff_id)

        query += " ORDER BY a.date DESC, s.name ASC"

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        return rows
    finally:
        conn.close()

def get_report_statistics(rows):
    """Computes summary KPI stats from query rows."""
    total = len(rows)
    present = sum(1 for r in rows if r['status'] == 'Present')
    half_day = sum(1 for r in rows if r['status'] == 'Half Day')
    missed_out = sum(1 for r in rows if r['status'] == 'Missed Out')
    absent = sum(1 for r in rows if r['status'] == 'Absent')
    short_leave = sum(1 for r in rows if r['status'] == 'Short Leave')

    attendance_pct = round(((present + 0.5 * half_day) / total * 100), 1) if total > 0 else 0.0

    return {
        'total': total,
        'present': present,
        'half_day': half_day,
        'missed_out': missed_out,
        'absent': absent,
        'short_leave': short_leave,
        'attendance_pct': attendance_pct
    }
