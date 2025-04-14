# Facial Attendance System


An AI-powered contactless attendance system using facial recognition to automate employee/student tracking with real-time notifications.

## ✨ Key Features

- **Face Registration** - One-time enrollment via camera
- **Real-time Recognition** - Detects faces in live video feed
- **Multi-channel Alerts** - Instant notifications via:
  - 📧 Email (Gmail)
  - 📱 WhatsApp
  - 🔔 In-app notifications
- **Attendance Reports** - Daily/Monthly analytics export
- **Anti-Spoofing** - Basic liveness detection

## 🛠️ Tech Stack

- **Core**: Python 3.8+
- **Computer Vision**: OpenCV, MediaPipe, face_recognition
- **Backend**: SQLite database
- **Notifications**: 
  - SMTP (Gmail) 
  - Twilio API (WhatsApp)
- **GUI**: Tkinter

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Webcam

### Installation
```bash
git clone https://github.com/yourusername/facial-attendance-system.git
cd facial-attendance-system
pip install -r requirements.txt
