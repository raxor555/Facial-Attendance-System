import tkinter as tk
from database import setup_database, load_known_faces, save_face_data, register_employee, log_attendance, get_attendance_records, export_attendance
from camera import CameraProcessor
from gui import AttendanceGUI

class FacialAttendanceSystem:
    def __init__(self):
        self.root = tk.Tk()
        self.conn, self.cursor = setup_database()
        self.known_face_encodings, self.known_face_names, self.known_face_rollnos, self.known_face_ids = load_known_faces(self.conn, self.cursor)
        self.camera = CameraProcessor()
        self.gui = AttendanceGUI(
            self.root,
            self.register_callback,
            self.log_attendance_callback,
            self.get_attendance_callback,
            self.export_attendance_callback
        )
        self.update_camera()

    def register_callback(self, *args):
        """Handle registration callback"""
        if len(args) == 0:
            return self.camera.get_face_encoding()
        name, department, roll_no, email, phone, face_encoding = args
        emp_id = register_employee(self.conn, self.cursor, name, department, roll_no, email, phone, face_encoding)
        self.known_face_encodings.append(face_encoding)
        self.known_face_names.append(name)
        self.known_face_rollnos.append(roll_no)
        self.known_face_ids.append(emp_id)
        save_face_data(self.known_face_encodings, self.known_face_names, self.known_face_rollnos, self.known_face_ids)
        return emp_id

    def log_attendance_callback(self, emp_id, name):
        """Handle attendance logging"""
        log_attendance(self.conn, self.cursor, emp_id, name)

    def get_attendance_callback(self):
        """Retrieve attendance records"""
        return get_attendance_records(self.conn, self.cursor)

    def export_attendance_callback(self, file_path):
        """Export attendance to CSV"""
        return export_attendance(self.conn, self.cursor, file_path)

    def update_camera(self):
        """Update camera feed"""
        img = self.camera.update_frame(
            self.gui.mode,
            self.known_face_encodings,
            self.known_face_names,
            self.known_face_rollnos,
            self.known_face_ids,
            self.log_attendance_callback
        )
        self.gui.update_camera(img)
        self.root.after(20, self.update_camera)

    def run(self):
        """Run the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        """Cleanup resources"""
        self.camera.cleanup()
        self.conn.close()
        self.root.destroy()

if __name__ == "__main__":
    try:
        import face_recognition
        import mediapipe
        import aiohttp
    except ImportError as e:
        print(f"Error: Required package missing: {str(e)}")
        print("Run: pip install face-recognition mediapipe opencv-python pillow numpy aiohttp")
        exit()
    
    app = FacialAttendanceSystem()
    app.run()