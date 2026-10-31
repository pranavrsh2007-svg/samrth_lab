import sqlite3
import os
from flask import g
from werkzeug.security import generate_password_hash
from config import Config

from flask import g, has_app_context, current_app

def _get_active_db_path():
    """Gets the active database path from Flask config or Config fallback."""
    if has_app_context() and 'DATABASE' in current_app.config:
        db_path = current_app.config['DATABASE']
    else:
        db_path = Config.DATABASE

    # If the database file does not exist in serverless /tmp environment
    import tempfile
    is_serverless_tmp = (getattr(Config, 'IS_VERCEL', False) or db_path.startswith(tempfile.gettempdir()))
    if is_serverless_tmp and not os.path.exists(db_path):
        bundled_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'labfix.db')
        if os.path.exists(bundled_db) and os.path.abspath(db_path) != os.path.abspath(bundled_db):
            try:
                db_dir = os.path.dirname(db_path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)
                import shutil
                shutil.copy2(bundled_db, db_path)
            except Exception:
                pass
    return db_path

def get_db():
    """Opens a new database connection for the current app context, or a direct connection if standalone."""
    db_path = _get_active_db_path()

    if has_app_context():
        if 'db' not in g:
            g.db = sqlite3.connect(
                db_path,
                timeout=30.0,
                check_same_thread=False
            )
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
            try:
                g.db.execute("PRAGMA journal_mode = WAL")
            except sqlite3.OperationalError:
                pass
            g.db.execute("PRAGMA busy_timeout = 30000")
        return g.db
    else:
        conn = sqlite3.connect(
            db_path,
            timeout=30.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError:
            pass
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

def close_db(e=None):
    """Closes the database again at the end of the request."""
    if has_app_context():
        db = g.pop('db', None)
        if db is not None:
            db.close()

def query_db(query, args=(), one=False):
    """Convenience method to execute a read query."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), commit=True):
    """Convenience method to execute an insert/update/delete query."""
    db = get_db()
    cur = db.cursor()
    cur.execute(query, args)
    lastrowid = cur.lastrowid
    rowcount = cur.rowcount
    cur.close()
    if commit:
        db.commit()
    return lastrowid, rowcount

def init_db():
    """Initializes schema and seeds baseline college data and demo accounts."""
    db_path = _get_active_db_path()
    upload_folder = current_app.config['UPLOAD_FOLDER'] if (has_app_context() and 'UPLOAD_FOLDER' in current_app.config) else Config.UPLOAD_FOLDER

    db_dir = os.path.dirname(db_path)
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError:
            pass
    try:
        os.makedirs(upload_folder, exist_ok=True)
    except OSError:
        pass

    db = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        db.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass
    db.execute("PRAGMA busy_timeout = 30000")
    cursor = db.cursor()

    # Create tables
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('hod', 'faculty', 'technician')),
        department TEXT DEFAULT 'Computer Science',
        phone TEXT DEFAULT '',
        avatar_url TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS wings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        code TEXT UNIQUE NOT NULL,
        description TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS floors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wing_id INTEGER NOT NULL,
        floor_number INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (wing_id) REFERENCES wings (id) ON DELETE CASCADE,
        UNIQUE (wing_id, floor_number)
    );

    CREATE TABLE IF NOT EXISTS laboratories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        floor_id INTEGER NOT NULL,
        lab_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        capacity INTEGER DEFAULT 20,
        department TEXT DEFAULT 'Computer Science & Engineering',
        in_charge_faculty_id INTEGER,
        FOREIGN KEY (floor_id) REFERENCES floors (id) ON DELETE CASCADE,
        FOREIGN KEY (in_charge_faculty_id) REFERENCES users (id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS computers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lab_id INTEGER NOT NULL,
        pc_number TEXT NOT NULL,
        computer_id_code TEXT UNIQUE NOT NULL,
        brand TEXT NOT NULL,
        model TEXT NOT NULL,
        serial_number TEXT UNIQUE NOT NULL,
        processor TEXT DEFAULT 'Intel Core i7-11700 2.50GHz',
        ram TEXT DEFAULT '16 GB DDR4',
        storage TEXT DEFAULT '512 GB NVMe SSD',
        os TEXT DEFAULT 'Windows 11 Pro 64-bit',
        installation_date DATE DEFAULT CURRENT_DATE,
        operational_status TEXT NOT NULL DEFAULT 'Working' 
            CHECK(operational_status IN ('Working', 'Fault Reported', 'Under Repair', 'Repaired', 'Decommissioned')),
        last_maintenance_date TIMESTAMP,
        decommissioned_at TIMESTAMP,
        decommission_reason TEXT,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (lab_id) REFERENCES laboratories (id) ON DELETE RESTRICT,
        UNIQUE (lab_id, pc_number)
    );

    CREATE TABLE IF NOT EXISTS computer_replacements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        old_computer_id INTEGER NOT NULL,
        new_computer_id INTEGER NOT NULL,
        replacement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reason TEXT NOT NULL,
        performed_by_user_id INTEGER NOT NULL,
        notes TEXT DEFAULT '',
        FOREIGN KEY (old_computer_id) REFERENCES computers (id),
        FOREIGN KEY (new_computer_id) REFERENCES computers (id),
        FOREIGN KEY (performed_by_user_id) REFERENCES users (id)
    );

    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_code TEXT UNIQUE NOT NULL,
        faculty_id INTEGER NOT NULL,
        computer_id INTEGER NOT NULL,
        problem_category TEXT NOT NULL,
        priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High', 'Critical')),
        description TEXT NOT NULL,
        attachment_filename TEXT,
        status TEXT NOT NULL DEFAULT 'Pending' 
            CHECK(status IN ('Pending', 'Accepted', 'In Progress', 'Resolved', 'Closed')),
        reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        accepted_at TIMESTAMP,
        resolved_at TIMESTAMP,
        assigned_technician_id INTEGER,
        FOREIGN KEY (faculty_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (computer_id) REFERENCES computers (id) ON DELETE CASCADE,
        FOREIGN KEY (assigned_technician_id) REFERENCES users (id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS maintenance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        computer_id INTEGER NOT NULL,
        technician_id INTEGER NOT NULL,
        diagnosis TEXT NOT NULL,
        action_taken TEXT NOT NULL,
        parts_replaced TEXT DEFAULT 'None',
        solution_description TEXT NOT NULL,
        repair_notes TEXT DEFAULT '',
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        verification_status TEXT DEFAULT 'Verified',
        FOREIGN KEY (complaint_id) REFERENCES complaints (id) ON DELETE CASCADE,
        FOREIGN KEY (computer_id) REFERENCES computers (id) ON DELETE CASCADE,
        FOREIGN KEY (technician_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        target_role TEXT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        link TEXT DEFAULT '#',
        type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        details TEXT,
        ip_address TEXT DEFAULT '127.0.0.1',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS sms_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER,
        recipient_user_id INTEGER,
        recipient_name TEXT NOT NULL,
        recipient_phone TEXT NOT NULL,
        message TEXT NOT NULL,
        gateway_provider TEXT DEFAULT 'SIMULATED',
        status TEXT NOT NULL CHECK(status IN ('SENT', 'DELIVERED', 'FAILED', 'SIMULATED')),
        response_data TEXT DEFAULT '',
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (complaint_id) REFERENCES complaints (id) ON DELETE SET NULL,
        FOREIGN KEY (recipient_user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    ''')

    db.commit()

    # Seed Baseline College Structure if not yet seeded
    cursor.execute("SELECT COUNT(*) as count FROM wings")
    if cursor.fetchone()['count'] == 0:
        seed_initial_data(db)

    db.close()

def seed_initial_data(db):
    """Populates wings, floors, laboratories, 360 computers, accounts, and demo reports."""
    cursor = db.cursor()

    # 1. Seed Accounts
    users_data = [
        ('hod', 'hod@labfix.edu', generate_password_hash('Password@123'), 'Dr. Sarah Jenkins', 'hod', 'Computer Science & Engineering', '+1 (555) 234-5678'),
        ('faculty', 'faculty@labfix.edu', generate_password_hash('Password@123'), 'Prof. Alan Turing', 'faculty', 'Computer Science & Engineering', '+1 (555) 345-6789'),
        ('faculty2', 'grace.hopper@labfix.edu', generate_password_hash('Password@123'), 'Dr. Grace Hopper', 'faculty', 'Information Technology', '+1 (555) 456-7890'),
        ('tech', 'tech@labfix.edu', generate_password_hash('Password@123'), 'Alex Rivera', 'technician', 'IT Maintenance Operations', '+1 (555) 567-8901'),
        ('tech2', 'tech2@labfix.edu', generate_password_hash('Password@123'), 'Marcus Vance', 'technician', 'Hardware & Networking', '+1 (555) 678-9012'),
    ]

    cursor.executemany('''
        INSERT INTO users (username, email, password_hash, full_name, role, department, phone)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', users_data)

    fac1 = cursor.execute("SELECT id FROM users WHERE username = 'faculty'").fetchone()
    fac2 = cursor.execute("SELECT id FROM users WHERE username = 'faculty2'").fetchone()
    t1 = cursor.execute("SELECT id FROM users WHERE username = 'tech'").fetchone()
    t2 = cursor.execute("SELECT id FROM users WHERE username = 'tech2'").fetchone()
    faculty1_id = fac1['id'] if fac1 else 2
    faculty2_id = fac2['id'] if fac2 else 3
    tech1_id = t1['id'] if t1 else 4
    tech2_id = t2['id'] if t2 else 5

    # 2. Seed Wings
    wings_data = [
        ('Wing A', 'A', 'North Academic Block - Computing & Data Sciences'),
        ('Wing B', 'B', 'Central Technology Hub - AI & Software Engineering'),
        ('Wing C', 'C', 'South Engineering Complex - Networking & Cyber Security'),
    ]
    cursor.executemany('INSERT INTO wings (name, code, description) VALUES (?, ?, ?)', wings_data)

    # 3. Seed Floors & Laboratories & 360 Computers
    # 3 wings, 3 floors each, 2 labs per floor = 18 labs
    # 20 computers each = 360 computers
    brands = ['Dell', 'HP', 'Lenovo']
    models = {
        'Dell': 'OptiPlex 7090 Tower',
        'HP': 'EliteDesk 800 G6',
        'Lenovo': 'ThinkCentre M70q'
    }
    processors = ['Intel Core i7-11700 (8-Core 2.50GHz)', 'Intel Core i5-11500 (6-Core 2.70GHz)', 'AMD Ryzen 7 PRO 5750G']
    rams = ['16 GB DDR4 3200MHz', '32 GB DDR4 3200MHz', '16 GB DDR4 3200MHz']
    storages = ['512 GB M.2 NVMe SSD', '1 TB NVMe SSD', '512 GB NVMe SSD + 1TB HDD']
    oses = ['Windows 11 Pro 64-bit', 'Ubuntu 22.04 LTS 64-bit', 'Windows 11 Pro 64-bit']

    wing_rows = cursor.execute('SELECT id, code, name FROM wings ORDER BY code').fetchall()

    computer_records = []
    
    for wing in wing_rows:
        wing_id = wing['id']
        wing_code = wing['code']

        for floor_num in [1, 2, 3]:
            floor_name = f'Floor {floor_num}'
            cursor.execute('INSERT INTO floors (wing_id, floor_number, name) VALUES (?, ?, ?)',
                           (wing_id, floor_num, floor_name))
            floor_id = cursor.lastrowid

            # 2 laboratories per floor: e.g. A1-01, A1-02
            for lab_idx in [1, 2]:
                lab_code = f"{wing_code}{floor_num}-0{lab_idx}"
                lab_name = f"Lab {lab_code}"
                dept = 'Computer Science & Engineering' if wing_code == 'A' else ('Information Technology' if wing_code == 'B' else 'Electronics & Networking')
                
                cursor.execute('''
                    INSERT INTO laboratories (floor_id, lab_code, name, capacity, department, in_charge_faculty_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (floor_id, lab_code, lab_name, 20, dept, faculty1_id if lab_idx == 1 else faculty2_id))
                lab_id = cursor.lastrowid

                # 20 computers per lab: PC-01 through PC-20
                for pc_idx in range(1, 21):
                    pc_num = f"PC-{pc_idx:02d}"
                    comp_id_code = f"COMP-{lab_code}-{pc_num}"
                    serial = f"SN-{wing_code}{floor_num}{lab_idx:02d}-{pc_idx:03d}"
                    brand_idx = (wing_id + floor_num + pc_idx) % 3
                    brand = brands[brand_idx]
                    model = models[brand]
                    proc = processors[brand_idx]
                    ram = rams[brand_idx]
                    storage = storages[brand_idx]
                    os_name = oses[brand_idx]
                    install_date = '2024-06-15'

                    computer_records.append((
                        lab_id, pc_num, comp_id_code, brand, model, serial,
                        proc, ram, storage, os_name, install_date, 'Working'
                    ))

    cursor.executemany('''
        INSERT INTO computers (
            lab_id, pc_number, computer_id_code, brand, model, serial_number,
            processor, ram, storage, os, installation_date, operational_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', computer_records)

    db.commit()

    # 4. Seed a few realistic demonstration complaints across different stages
    # This ensures the dashboard statistics, charts, and queues look lively and authentic right away
    demo_complaints = [
        # 1: High priority Pending complaint
        ('LF-1001', faculty1_id, 'COMP-A1-01-PC-05', 'Computer Not Starting', 'High',
         'System does not power on after pressing power button. Front LED blinks orange three times.',
         'Pending', '2026-10-10 09:30:00', None, None, None, 'Fault Reported'),
        
        # 2: Critical priority Accepted complaint
        ('LF-1002', faculty2_id, 'COMP-B2-01-PC-12', 'Network Problem', 'Critical',
         'Ethernet port damaged and no internet connection during lab session. IP configuration fails.',
         'Accepted', '2026-10-10 11:15:00', '2026-10-10 11:45:00', None, tech1_id, 'Fault Reported'),

        # 3: Medium priority In Progress complaint
        ('LF-1003', faculty1_id, 'COMP-C3-02-PC-08', 'Monitor Problem', 'Medium',
         'Display flickers continuously and exhibits horizontal colored scan lines after 10 minutes of use.',
         'In Progress', '2026-10-09 14:20:00', '2026-10-09 15:00:00', None, tech2_id, 'Under Repair'),

        # 4: Resolved complaint with maintenance record
        ('LF-1004', faculty2_id, 'COMP-A2-02-PC-03', 'Keyboard Problem', 'Low',
         'Multiple keys (W, A, S, Spacebar) are unresponsive and sticky.',
         'Resolved', '2026-10-08 10:00:00', '2026-10-08 10:30:00', '2026-10-08 13:45:00', tech1_id, 'Repaired'),

        # 5: Resolved complaint with maintenance record
        ('LF-1005', faculty1_id, 'COMP-B1-02-PC-18', 'Slow Performance', 'Medium',
         'Excessive thermal throttling and system freezes when running IDEs.',
         'Resolved', '2026-10-07 13:00:00', '2026-10-07 13:30:00', '2026-10-07 16:15:00', tech2_id, 'Working'),
    ]

    for code, fac_id, comp_code, cat, prio, desc, status, rep_at, acc_at, res_at, tech_id, comp_status in demo_complaints:
        # Find computer_id
        comp = cursor.execute('SELECT id FROM computers WHERE computer_id_code = ?', (comp_code,)).fetchone()
        if comp:
            comp_id = comp['id']
            cursor.execute('''
                INSERT INTO complaints (
                    complaint_code, faculty_id, computer_id, problem_category, priority,
                    description, status, reported_at, accepted_at, resolved_at, assigned_technician_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (code, fac_id, comp_id, cat, prio, desc, status, rep_at, acc_at, res_at, tech_id))
            complaint_id = cursor.lastrowid

            # Update computer status
            cursor.execute('UPDATE computers SET operational_status = ? WHERE id = ?', (comp_status, comp_id))

            # If resolved, add maintenance record
            if status == 'Resolved':
                cursor.execute('''
                    INSERT INTO maintenance_records (
                        complaint_id, computer_id, technician_id, diagnosis, action_taken,
                        parts_replaced, solution_description, repair_notes, started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    complaint_id, comp_id, tech_id,
                    'Defective peripheral switches / thermal paste degradation',
                    'Disassembled unit, replaced component and performed 30-minute stress testing.',
                    'Dell Membrane Keyboard Assembly' if 'Keyboard' in cat else 'Thermal Paste Arctic MX-4 & CPU Cooler Fan',
                    'Hardware replaced and verified full operational stability under peak load.',
                    'Unit bench-tested successfully. Returned to service.',
                    acc_at, res_at
                ))
                cursor.execute('UPDATE computers SET last_maintenance_date = ? WHERE id = ?', (res_at, comp_id))

    # 5. Seed initial notifications
    notifications_data = [
        (1, 'hod', 'High Priority Issue Reported', 'Complaint LF-1001: Computer Not Starting reported in Lab A1-01 (PC-05)', '/hod/complaints', 'alert', 0),
        (tech1_id, 'technician', 'New Complaint in Queue', 'New complaint LF-1001 awaiting technician pickup in Wing A.', '/technician/dashboard', 'info', 0),
        (faculty2_id, 'faculty', 'Complaint Accepted', 'Technician Alex Rivera accepted your complaint LF-1002 for Lab B2-01.', '/faculty/my-complaints', 'success', 0),
    ]
    cursor.executemany('''
        INSERT INTO notifications (user_id, target_role, title, message, link, type, is_read)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', notifications_data)

    # 6. Seed initial audit log
    cursor.execute('''
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details)
        VALUES (1, 'SYSTEM_INITIALIZATION', 'SYSTEM', '0', 'Initial college structure initialized with 3 wings, 9 floors, 18 laboratories, and 360 computers.')
    ''')

    db.commit()
