import sqlite3
import os
import pickle
import asyncio
import aiohttp
from datetime import datetime
import csv
import threading

def setup_database():
    """Initialize the SQLite database and return connection/cursor"""
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department TEXT,
        roll_no TEXT,
        email TEXT,
        phone TEXT,
        face_data BLOB,
        registered_date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        timestamp TEXT,
        status TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )''')
    
    cursor.execute("PRAGMA table_info(employees)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'roll_no' not in columns:
        cursor.execute('ALTER TABLE employees ADD COLUMN roll_no TEXT')
    if 'email' not in columns:
        cursor.execute('ALTER TABLE employees ADD COLUMN email TEXT')
    if 'phone' not in columns:
        cursor.execute('ALTER TABLE employees ADD COLUMN phone TEXT')
    
    conn.commit()
    return conn, cursor

def load_known_faces(conn, cursor):
    """Load previously registered faces"""
    known_face_encodings = []
    known_face_names = []
    known_face_rollnos = []
    known_face_ids = []
    
    try:
        if os.path.exists('faces.dat'):
            with open('faces.dat', 'rb') as f:
                data = pickle.load(f)
                
                if isinstance(data, tuple):
                    known_face_encodings, known_face_names, known_face_ids = data
                    known_face_rollnos = [''] * len(known_face_names)
                elif isinstance(data, dict):
                    known_face_encodings = data.get('encodings', [])
                    known_face_names = data.get('names', [])
                    known_face_rollnos = data.get('rollnos', [])
                    known_face_ids = data.get('ids', [])
            print(f"Loaded {len(known_face_encodings)} known faces")
        else:
            cursor.execute("SELECT id, name, roll_no, email, phone, face_data FROM employees")
            for emp_id, name, roll_no, email, phone, face_data in cursor.fetchall():
                if face_data:
                    known_face_encodings.append(pickle.loads(face_data))
                    known_face_names.append(name)
                    known_face_rollnos.append(roll_no if roll_no else '')
                    known_face_ids.append(emp_id)
            print(f"Loaded {len(known_face_encodings)} faces from database")
            save_face_data(known_face_encodings, known_face_names, known_face_rollnos, known_face_ids)
    except Exception as e:
        print(f"Error loading face data: {str(e)}")
    
    return known_face_encodings, known_face_names, known_face_rollnos, known_face_ids

def save_face_data(known_face_encodings, known_face_names, known_face_rollnos, known_face_ids):
    """Save current face data to file"""
    try:
        with open('faces.dat', 'wb') as f:
            pickle.dump({
                'encodings': known_face_encodings,
                'names': known_face_names,
                'rollnos': known_face_rollnos,
                'ids': known_face_ids
            }, f)
    except Exception as e:
        print(f"Error saving face data: {str(e)}")

def register_employee(conn, cursor, name, department, roll_no, email, phone, face_encoding):
    """Register a new employee in the database"""
    try:
        cursor.execute(
            "INSERT INTO employees (name, department, roll_no, email, phone, face_data) VALUES (?, ?, ?, ?, ?, ?)",
            (name, department, roll_no, email, phone, pickle.dumps(face_encoding))
        )
        emp_id = cursor.lastrowid
        conn.commit()
        return emp_id
    except Exception as e:
        raise Exception(f"Registration failed: {str(e)}")

def log_attendance(conn, cursor, emp_id, name):
    """Log attendance and trigger webhook in a separate thread"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        SELECT id FROM attendance 
        WHERE employee_id=? AND date(timestamp)=date(?)
        ''', (emp_id, today))
        
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO attendance (employee_id, timestamp, status)
            VALUES (?, ?, ?)
            ''', (emp_id, now, "Present"))
            conn.commit()
            print(f"Logged attendance for {name} at {now}")
            
            cursor.execute('SELECT email, phone, roll_no FROM employees WHERE id=?', (emp_id,))
            result = cursor.fetchone()
            email, phone, roll_no = result if result else (None, None, None)
            
            if email or phone:
                webhook_data = {
                    "name": name,
                    "roll_no": roll_no or "",
                    "timestamp": now,
                    "email": email or "",
                    "phone": phone or ""
                }
                print(f"Preparing webhook data: {webhook_data}")
                
                def run_webhook():
                    async def send_webhook(attempt=1):
                        async with aiohttp.ClientSession() as session:
                            try:
                                async with session.post(
                                    "https://primary-production-28ec1.up.railway.app/webhook-test/8b2caefb-ea99-4774-b593-e9ff120d802c",
                                    json=webhook_data,
                                    timeout=10
                                ) as response:
                                    response_text = await response.text()
                                    print(f"Webhook attempt {attempt} for {name}: Status={response.status}, Response={response_text}, Headers={response.headers}")
                                    if response.status == 200:
                                        print(f"Webhook sent successfully for {name}")
                                    else:
                                        if attempt < 2:
                                            print(f"Retrying webhook for {name} (attempt {attempt + 1})")
                                            await asyncio.sleep(1)
                                            await send_webhook(attempt + 1)
                                        else:
                                            print(f"Webhook failed for {name} after {attempt} attempts")
                            except Exception as e:
                                print(f"Webhook error for {name} on attempt {attempt}: {str(e)}")
                                if attempt < 2:
                                    print(f"Retrying webhook for {name} (attempt {attempt + 1})")
                                    await asyncio.sleep(1)
                                    await send_webhook(attempt + 1)
                                else:
                                    print(f"Webhook failed for {name} after {attempt} attempts: {str(e)}")
                    
                    asyncio.run(send_webhook())
                
                threading.Thread(target=run_webhook, daemon=True).start()
        else:
            print(f"Attendance already logged for {name} today")
    except Exception as e:
        print(f"Error logging attendance: {str(e)}")

def get_attendance_records(conn, cursor):
    """Retrieve today's attendance records"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute('''
        SELECT a.timestamp, e.name, e.roll_no 
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE date(a.timestamp) = date(?)
        ORDER BY a.timestamp DESC
        ''', (today,))
        records = cursor.fetchall()
        print(f"Found {len(records)} attendance records for today")
        return records
    except Exception as e:
        print(f"Error retrieving attendance records: {str(e)}")
        return []

def export_attendance(conn, cursor, file_path):
    """Export attendance records to CSV"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute('''
        SELECT 
            a.timestamp,
            e.name,
            e.roll_no,
            e.department
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE date(a.timestamp) = date(?)
        ORDER BY a.timestamp DESC
        ''', (today,))
        
        records = cursor.fetchall()
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Name', 'Roll No', 'Department'])
            writer.writerows(records)
        return True
    except Exception as e:
        print(f"Export failed: {str(e)}")
        return False