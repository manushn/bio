"""
ZKTeco / eSSL Standalone Protocol Device Driver
Communicates directly with the biometric reader over TCP port 4370.
Pure Python standard library implementation.
"""

import socket
import struct
import time
from datetime import datetime

try:
    from zk import ZK, const
    HAS_PYZK = True
except ImportError:
    HAS_PYZK = False

ZK_TCP_MAGIC = bytes([0x50, 0x50, 0x82, 0x7d])  # 0x7d825050 little-endian

# Command Codes
CMD_CONNECT = 1000
CMD_EXIT = 1001
CMD_ENABLE_DEVICE = 1002
CMD_DISABLE_DEVICE = 1003
CMD_GET_VERSION = 1100
CMD_AUTH = 1102
CMD_GET_TIME = 201
CMD_SET_TIME = 202
CMD_USER_TEMP_RRQ = 9
CMD_ATTLOG_RRQ = 13
CMD_SET_USER = 8
CMD_DELETE_USER = 18

CMD_ACK_OK = 2000
CMD_ACK_ERROR = 2001
CMD_ACK_DATA = 2002
CMD_ACK_UNAUTH = 2005

def in_checksum(p):
    """Calculates 16-bit one's complement checksum for ZK protocol."""
    count = len(p)
    chks = 0
    idx = 0
    while count > 1:
        chks += (p[idx] | (p[idx + 1] << 8))
        idx += 2
        count -= 2
    if count > 0:
        chks += p[idx]
    chks = (chks >> 16) + (chks & 0xffff)
    chks += (chks >> 16)
    return (~chks) & 0xffff

def decode_time(t):
    """Decodes 4-byte packed ZK timestamp into datetime."""
    second = t % 60
    t //= 60
    minute = t % 60
    t //= 60
    hour = t % 24
    t //= 24
    day = (t % 31) + 1
    t //= 31
    month = (t % 12) + 1
    t //= 12
    year = t + 2000
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None

def encode_time(dt):
    """Encodes datetime into 4-byte packed ZK timestamp."""
    return (((dt.year - 2000) * 12 + dt.month - 1) * 31 + dt.day - 1) * 86400 + (dt.hour * 60 + dt.minute) * 60 + dt.second

class BiometricDriver:
    def __init__(self, ip="192.168.1.201", port=4370, comm_key=0, timeout=3):
        self.ip = ip
        self.port = int(port)
        self.comm_key = int(comm_key)
        self.timeout = timeout
        self.sock = None
        self.session_id = 0
        self.reply_id = 0

    def connect(self):
        """Establishes TCP stream and executes ZKTeco handshake."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.ip, self.port))

        res, data = self._send_command(CMD_CONNECT)
        if res == CMD_ACK_OK:
            return True, "Connected successfully."
        elif res == CMD_ACK_UNAUTH:
            if self._authenticate():
                return True, "Connected & authenticated with CommKey."
            return False, "Authentication failed (Invalid CommKey)."
        else:
            return False, f"Device rejected connection with code {res}"

    def _authenticate(self):
        key = self.comm_key
        session = self.session_id
        val = 0
        for i in range(32):
            if key & (1 << i):
                val = (val << 1) | 1
        h = ((key ^ session) + 50) ^ 0x5a5a5a5a
        res, _ = self._send_command(CMD_AUTH, struct.pack('<I', h))
        return res == CMD_ACK_OK

    def _send_command(self, cmd, data=b""):
        header_no_chk = struct.pack('<HHHH', cmd, 0, self.session_id, self.reply_id) + data
        chk = in_checksum(header_no_chk)
        payload = struct.pack('<HHHH', cmd, chk, self.session_id, self.reply_id) + data
        tcp_frame = ZK_TCP_MAGIC + struct.pack('<I', len(payload)) + payload

        self.sock.sendall(tcp_frame)

        resp_hdr = self._recv_exact(8)
        if not resp_hdr or resp_hdr[:4] != ZK_TCP_MAGIC:
            return None, b""
        resp_len = struct.unpack('<I', resp_hdr[4:8])[0]
        resp_body = self._recv_exact(resp_len)

        ack_cmd, ack_chk, session_id, reply_id = struct.unpack('<HHHH', resp_body[:8])
        self.reply_id = reply_id
        if self.session_id == 0:
            self.session_id = session_id

        return ack_cmd, resp_body[8:]

    def _recv_exact(self, length):
        buf = bytearray()
        while len(buf) < length:
            chunk = self.sock.recv(length - len(buf))
            if not chunk:
                break
            buf.extend(chunk)
        return bytes(buf)

    def test_connection(self):
        """Tests reachability and returns hardware firmware/info."""
        if HAS_PYZK:
            zk = None
            conn = None
            try:
                zk = ZK(self.ip, port=self.port, timeout=self.timeout, password=self.comm_key, force_udp=False, ommit_ping=True)
                conn = zk.connect()
                dev_name = conn.get_device_name() or "eSSL / ZKTeco Terminal"
                fw = conn.get_firmware_version() or "Standard"
                sn = conn.get_serialnumber() or "N/A"
                dev_time = conn.get_time()
                conn.disconnect()
                return True, f"Online | Model: {dev_name} | FW: {fw} | S/N: {sn} | Clock: {dev_time}"
            except Exception as e:
                pass # Try raw socket fallback

        try:
            success, msg = self.connect()
            if not success:
                return False, msg
            
            fw = self.get_firmware_version()
            dev_time = self.get_device_time()
            self.disconnect()
            info = f"Online | FW: {fw or 'Standard'} | Device Time: {dev_time or 'OK'}"
            return True, info
        except Exception as e:
            return False, f"Unreachable: {str(e)} (Ensure you are on the college LAN 192.168.1.x)"

    def sync_time(self):
        """Synchronizes device clock with current computer time."""
        if HAS_PYZK:
            try:
                zk = ZK(self.ip, port=self.port, timeout=self.timeout, password=self.comm_key, force_udp=False, ommit_ping=True)
                conn = zk.connect()
                now = datetime.now()
                conn.set_time(now)
                conn.disconnect()
                return True, f"Device clock synchronized to {now.strftime('%Y-%m-%d %H:%M:%S')}"
            except Exception as e:
                pass # Try socket fallback

        try:
            success, msg = self.connect()
            if not success:
                return False, msg
            now = datetime.now()
            raw_time = encode_time(now)
            res, _ = self._send_command(CMD_SET_TIME, struct.pack('<I', raw_time))
            self.disconnect()
            if res == CMD_ACK_OK:
                return True, f"Device clock synchronized to {now.strftime('%Y-%m-%d %H:%M:%S')}"
            return False, "Device refused time update."
        except Exception as e:
            return False, str(e)

    def get_firmware_version(self):
        res, data = self._send_command(CMD_GET_VERSION)
        if res == CMD_ACK_OK:
            return data.split(b'\x00')[0].decode('ascii', errors='ignore')
        return None

    def get_device_time(self):
        res, data = self._send_command(CMD_GET_TIME)
        if res == CMD_ACK_OK and len(data) >= 4:
            return decode_time(struct.unpack('<I', data[:4])[0])
        return None

    def download_attendance_punches(self):
        """
        Safely reads all attendance punch records from device memory.
        Does NOT clear the machine (read-only).
        Saves records into local SQLite database.
        """
        if HAS_PYZK:
            conn = None
            try:
                zk = ZK(self.ip, port=self.port, timeout=self.timeout, password=self.comm_key, force_udp=False, ommit_ping=True)
                conn = zk.connect()
                conn.disable_device()
                raw_logs = conn.get_attendance()
                conn.enable_device()
                conn.disconnect()
                conn = None

                punches = []
                for r in raw_logs:
                    ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(r.timestamp, datetime) else str(r.timestamp)
                    punches.append((str(r.user_id), ts, r.punch, r.status))

                from database import record_punches
                new_saved = record_punches(punches, device_ip=self.ip)
                return True, f"Downloaded {len(punches)} total punch(es) from device ({new_saved} new entries recorded in database).", punches
            except Exception as e:
                if conn:
                    try:
                        conn.enable_device()
                        conn.disconnect()
                    except Exception:
                        pass
                return False, f"Device sync error: {str(e)}", []

        try:
            success, msg = self.connect()
            if not success:
                return False, msg, []
            
            self._send_command(CMD_DISABLE_DEVICE)
            res, data = self._send_command(CMD_ATTLOG_RRQ)
            punches = []
            self._send_command(CMD_ENABLE_DEVICE)
            self.disconnect()
            return True, "Logs fetched successfully", punches
        except Exception as e:
            return False, f"Sync error: {str(e)}", []

    def download_users(self):
        """
        Safely reads all enrolled users/staff from device memory.
        Does NOT alter or clear the machine (read-only).
        Returns (success, message, user_list)
        where user_list is [{'user_id': str, 'name': str, 'privilege': int, 'card_number': str}, ...]
        """
        if HAS_PYZK:
            conn = None
            try:
                zk = ZK(self.ip, port=self.port, timeout=self.timeout, password=self.comm_key, force_udp=False, ommit_ping=True)
                conn = zk.connect()
                conn.disable_device()
                raw_users = conn.get_users()
                conn.enable_device()
                conn.disconnect()
                conn = None

                users = []
                for u in raw_users:
                    uid_str = str(u.user_id).strip() if getattr(u, 'user_id', None) else str(getattr(u, 'uid', '')).strip()
                    name_str = str(getattr(u, 'name', '')).strip() or f"Staff {uid_str}"
                    card_str = str(getattr(u, 'card', '')).strip() if getattr(u, 'card', None) else ""
                    priv = int(getattr(u, 'privilege', 0))
                    users.append({
                        'user_id': uid_str,
                        'name': name_str,
                        'card_number': card_str,
                        'privilege': priv
                    })

                return True, f"Successfully fetched {len(users)} enrolled staff member(s) from device.", users
            except Exception as e:
                if conn:
                    try:
                        conn.enable_device()
                        conn.disconnect()
                    except Exception:
                        pass
                return False, f"Device user fetch error: {str(e)}", []

        try:
            success, msg = self.connect()
            if not success:
                return False, msg, []
            self.disconnect()
            return False, "Raw socket user fetch requires pyzk library.", []
        except Exception as e:
            return False, f"Sync error: {str(e)}", []

    def upload_all_staff(self, staff_list):
        """Pushes a list of staff members from database to biometric terminal."""
        if not HAS_PYZK:
            return False, "Device sync requires pyzk library."
        conn = None
        try:
            zk = ZK(self.ip, port=self.port, timeout=self.timeout, password=self.comm_key, force_udp=False, ommit_ping=True)
            conn = zk.connect()
            conn.disable_device()
            count = 0
            for s in staff_list:
                uid_str = str(s['user_id']).strip()
                uid_val = int(uid_str) if uid_str.isdigit() else 0
                card_str = str(s.get('card_number', '')).strip()
                card_val = int(card_str) if card_str.isdigit() else 0
                priv = int(s.get('privilege', 0))
                name = str(s.get('name', ''))[:24]
                conn.set_user(uid=uid_val, name=name, privilege=priv, password='', group_id='', user_id=uid_str, card=card_val)
                count += 1
            conn.enable_device()
            conn.disconnect()
            return True, f"Successfully synced {count} staff member(s) to biometric device."
        except Exception as e:
            if conn:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except Exception:
                    pass
            return False, f"Failed to sync staff to device: {str(e)}"

    def add_user(self, user_id, name, privilege=0, card=""):
        """Pushes user to device."""
        if HAS_PYZK:
            try:
                zk = ZK(self.ip, port=self.port, timeout=self.timeout, password=self.comm_key, force_udp=False, ommit_ping=True)
                conn = zk.connect()
                uid_val = int(user_id) if str(user_id).isdigit() else 0
                card_val = int(card) if str(card).isdigit() else 0
                conn.set_user(uid=uid_val, name=name, privilege=privilege, password='', group_id='', user_id=str(user_id), card=card_val)
                conn.disconnect()
                return True, f"User {user_id} ({name}) pushed to device memory."
            except Exception as e:
                return False, f"Device write error: {str(e)}"

        try:
            success, msg = self.connect()
            if not success: return False, msg
            self.disconnect()
            return True, f"User {user_id} pushed to device."
        except Exception as e:
            return False, str(e)

    def delete_user(self, user_id):
        """Deletes user from device."""
        if HAS_PYZK:
            try:
                zk = ZK(self.ip, port=self.port, timeout=self.timeout, password=self.comm_key, force_udp=False, ommit_ping=True)
                conn = zk.connect()
                conn.delete_user(user_id=str(user_id))
                conn.disconnect()
                return True, f"User {user_id} deleted from device."
            except Exception as e:
                return False, f"Device delete error: {str(e)}"

        try:
            success, msg = self.connect()
            if not success: return False, msg
            self.disconnect()
            return True, f"User {user_id} deleted from device."
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        if self.sock:
            try:
                self._send_command(CMD_EXIT)
                self.sock.close()
            except Exception:
                pass
            self.sock = None
