import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import time

class AttendanceGUI:
    def __init__(self, root, register_callback, log_attendance_callback, get_attendance_callback, export_attendance_callback):
        self.root = root
        self.root.title("Facial Attendance System")
        self.root.geometry("1200x700")
        self.register_callback = register_callback
        self.log_attendance_callback = log_attendance_callback
        self.get_attendance_callback = get_attendance_callback
        self.export_attendance_callback = export_attendance_callback
        self.mode = "registration"
        self.last_display_update = 0
        self.create_gui()

    def create_gui(self):
        """Create the graphical user interface"""
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0')
        style.configure('TButton', padding=5)
        style.configure('Accent.TButton', foreground='white', background='#0078d7')
        
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.camera_label = ttk.Label(left_frame)
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        mode_frame = ttk.Frame(left_frame)
        mode_frame.pack(fill=tk.X, pady=10)
        
        self.reg_btn = ttk.Button(
            mode_frame, 
            text="Registration Mode", 
            command=lambda: self.set_mode("registration"),
            style='Accent.TButton'
        )
        self.reg_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        self.attend_btn = ttk.Button(
            mode_frame, 
            text="Attendance Mode", 
            command=lambda: self.set_mode("attendance"),
            style='Accent.TButton'
        )
        self.attend_btn.pack(side=tk.LEFT, padx=5, expand=True)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        self.reg_controls = ttk.LabelFrame(right_frame, text="Employee Registration")
        
        ttk.Label(self.reg_controls, text="Full Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.name_entry = ttk.Entry(self.reg_controls)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(self.reg_controls, text="Department:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.dept_entry = ttk.Entry(self.reg_controls)
        self.dept_entry.grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(self.reg_controls, text="Roll No:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.roll_no_entry = ttk.Entry(self.reg_controls)
        self.roll_no_entry.grid(row=2, column=1, padx=5, pady=2)
        
        ttk.Label(self.reg_controls, text="Email:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.email_entry = ttk.Entry(self.reg_controls)
        self.email_entry.grid(row=3, column=1, padx=5, pady=2)
        
        ttk.Label(self.reg_controls, text="Phone:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.phone_entry = ttk.Entry(self.reg_controls)
        self.phone_entry.grid(row=4, column=1, padx=5, pady=2)
        
        self.register_btn = ttk.Button(
            self.reg_controls, 
            text="Register Employee", 
            command=self.register_employee
        )
        self.register_btn.grid(row=5, column=0, columnspan=2, pady=5)
        
        self.attend_controls = ttk.LabelFrame(right_frame, text="Today's Attendance Log")
        
        self.attendance_text = tk.Text(
            self.attend_controls, 
            height=15, 
            width=40,
            state=tk.DISABLED
        )
        scrollbar = ttk.Scrollbar(self.attend_controls, command=self.attendance_text.yview)
        self.attendance_text.configure(yscrollcommand=scrollbar.set)
        
        self.attendance_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = ttk.Frame(self.attend_controls)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            btn_frame,
            text="Export to CSV",
            command=self.export_csv
        ).pack(side=tk.LEFT, padx=5, expand=True)
        
        ttk.Button(
            btn_frame,
            text="Clear Log",
            command=self.clear_log
        ).pack(side=tk.LEFT, padx=5, expand=True)
        
        self.reg_controls.pack(fill=tk.X, pady=5)
        self.attend_controls.pack_forget()

    def set_mode(self, mode):
        """Switch between registration and attendance modes"""
        self.mode = mode
        print(f"Switched to {mode} mode")
        
        self.reg_controls.pack(fill=tk.X, pady=5) if mode == "registration" else self.reg_controls.pack_forget()
        self.attend_controls.pack(fill=tk.BOTH, expand=True) if mode == "attendance" else self.attend_controls.pack_forget()
        if mode == "attendance":
            self.update_attendance_display()

    def update_camera(self, img):
        """Update camera feed in GUI"""
        if img:
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.imgtk = imgtk
            self.camera_label.configure(image=imgtk)

    def register_employee(self):
        """Register a new employee"""
        name = self.name_entry.get()
        department = self.dept_entry.get()
        roll_no = self.roll_no_entry.get()
        email = self.email_entry.get()
        phone = self.phone_entry.get()
        
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        
        if not roll_no:
            messagebox.showerror("Error", "Roll No is required")
            return
        
        if not email:
            messagebox.showerror("Error", "Email is required")
            return
        
        try:
            face_encoding, face_rgb = self.register_callback()
            if face_encoding is None:
                messagebox.showerror("Error", "No face detected or encoding failed")
                return
            
            # Show preview
            preview = tk.Toplevel(self.root)
            preview.title("Captured Image Preview")
            img = Image.fromarray(face_rgb)
            img.thumbnail((300, 300))
            imgtk = ImageTk.PhotoImage(image=img)
            ttk.Label(preview, image=imgtk).pack()
            preview.image = imgtk
            
            emp_id = self.register_callback(name, department, roll_no, email, phone, face_encoding)
            
            preview.destroy()
            messagebox.showinfo("Success", f"Employee {name} registered successfully!")
            
            self.name_entry.delete(0, tk.END)
            self.dept_entry.delete(0, tk.END)
            self.roll_no_entry.delete(0, tk.END)
            self.email_entry.delete(0, tk.END)
            self.phone_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_attendance_display(self):
        """Update the attendance log display with throttling"""
        try:
            current_time = time.time()
            if current_time - self.last_display_update < 2:
                return
            
            self.attendance_text.config(state=tk.NORMAL)
            self.attendance_text.delete(1.0, tk.END)
            
            records = self.get_attendance_callback()
            if records:
                for timestamp, name, roll_no in records:
                    self.attendance_text.insert(tk.END, f"{timestamp} - {name} (Roll No: {roll_no})\n")
            
            self.attendance_text.config(state=tk.DISABLED)
            self.attendance_text.see(tk.END)
            self.last_display_update = current_time
        except Exception as e:
            print(f"Error updating attendance display: {str(e)}")

    def clear_log(self):
        """Clear the attendance log display"""
        self.attendance_text.config(state=tk.NORMAL)
        self.attendance_text.delete(1.0, tk.END)
        self.attendance_text.config(state=tk.DISABLED)

    def export_csv(self):
        """Export attendance to CSV"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Attendance Report"
        )
        
        if file_path:
            success = self.export_attendance_callback(file_path)
            if success:
                messagebox.showinfo("Success", f"Attendance exported to:\n{file_path}")
            else:
                messagebox.showerror("Error", "Export failed")