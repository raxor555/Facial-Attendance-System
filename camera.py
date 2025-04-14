import cv2
import numpy as np
import face_recognition
import mediapipe as mp
import time
from PIL import Image

class CameraProcessor:
    def __init__(self):
        self.video_capture = cv2.VideoCapture(0)
        self.current_frame = None
        self.last_attendance_time = {}
        self.recent_face_encodings = {}  # Stores (encoding, timestamp, name, roll_no, emp_id)
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.15)
        self.last_fps_time = time.time()
        self.frame_count = 0

    def update_frame(self, mode, known_face_encodings, known_face_names, known_face_rollnos, known_face_ids, log_attendance_callback):
        """Update camera feed and return processed frame"""
        if not self.video_capture.isOpened():
            print("Camera disconnected, attempting to reconnect...")
            self.video_capture.release()
            self.video_capture = cv2.VideoCapture(0)
        
        ret, frame = self.video_capture.read()
        
        if ret:
            self.current_frame = frame.copy()
            self.frame_count += 1
            
            # Process every other frame
            if self.frame_count % 2 == 0:
                display_frame = frame if mode == "registration" else self.process_attendance(
                    frame, known_face_encodings, known_face_names, known_face_rollnos, known_face_ids, log_attendance_callback
                )
            else:
                display_frame = frame
            
            # Convert for display
            img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
            img.thumbnail((640, 480), Image.Resampling.LANCZOS)
            
            # Log FPS
            current_time = time.time()
            if current_time - self.last_fps_time >= 1:
                fps = 1 / (current_time - self.last_fps_time)
                print(f"FPS: {fps:.2f}")
                self.last_fps_time = current_time
            
            # Clear frame buffer
            self.current_frame = None
            return img
        return None

    def process_attendance(self, frame, known_face_encodings, known_face_names, known_face_rollnos, known_face_ids, log_attendance_callback):
        """Process face recognition for attendance mode"""
        try:
            current_time = time.time()
            
            process_frame = cv2.resize(frame, (240, 180))
            rgb_frame = cv2.cvtColor(process_frame, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(rgb_frame)
            
            if results.detections:
                print(f"Detected {len(results.detections)} faces in frame")
                
                for detection in results.detections:
                    bboxC = detection.location_data.relative_bounding_box
                    ih, iw, _ = process_frame.shape
                    x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                                int(bboxC.width * iw), int(bboxC.height * ih)
                    
                    x = max(0, x - 10)
                    y = max(0, y - 10)
                    w = min(w + 20, iw - x)
                    h = min(h + 20, ih - y)
                    
                    face_img = process_frame[y:y+h, x:x+w]
                    if face_img.size == 0:
                        print("Empty face region, skipping")
                        continue
                    
                    face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                    
                    name = "Unknown"
                    roll_no = ""
                    emp_id = None
                    should_log = False
                    
                    for recent_id, (recent_encoding, timestamp, r_name, r_roll_no, r_emp_id) in list(self.recent_face_encodings.items()):
                        if current_time - timestamp > 120:
                            del self.recent_face_encodings[recent_id]
                            continue
                        name = r_name
                        roll_no = r_roll_no
                        emp_id = r_emp_id
                        should_log = False
                        print(f"Using cached recognition: {name} (Roll No: {roll_no})")
                        break
                    
                    if name == "Unknown":
                        face_encodings = face_recognition.face_encodings(face_rgb, num_jitters=1)
                        if not face_encodings:
                            print("No face encoding generated")
                            continue
                        
                        face_encoding = face_encodings[0]
                        
                        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
                        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                        if len(face_distances) > 0:
                            best_match_index = np.argmin(face_distances)
                            distance = face_distances[best_match_index]
                            print(f"Best match distance: {distance}")
                            
                            if matches[best_match_index]:
                                name = known_face_names[best_match_index]
                                roll_no = known_face_rollnos[best_match_index]
                                emp_id = known_face_ids[best_match_index]
                                print(f"Recognized: {name} (Roll No: {roll_no})")
                                
                                self.recent_face_encodings[emp_id] = (face_encoding, current_time, name, roll_no, emp_id)
                                
                                should_log = emp_id not in self.last_attendance_time or (current_time - self.last_attendance_time.get(emp_id, 0)) > 60
                    
                    if should_log and emp_id is not None:
                        log_attendance_callback(emp_id, name)
                        self.last_attendance_time[emp_id] = current_time
                    
                    scale_x = frame.shape[1] / 240
                    scale_y = frame.shape[0] / 180
                    x = int(x * scale_x)
                    y = int(y * scale_y)
                    w = int(w * scale_x)
                    h = int(h * scale_y)
                    
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.rectangle(frame, (x, y+h-70), (x+w, y+h), (0, 255, 0), cv2.FILLED)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(frame, name, (x+6, y+h-45), font, 0.8, (0, 0, 0), 1)
                    cv2.putText(frame, f"Roll No: {roll_no}", (x+6, y+h-15), font, 0.8, (0, 0, 0), 1)
            
            else:
                print("No faces detected")
                cv2.putText(frame, "No face detected", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            return frame
        
        except Exception as e:
            print(f"Error in process_attendance: {str(e)}")
            return frame

    def get_face_encoding(self):
        """Capture and encode a face from the current frame"""
        if self.current_frame is None:
            return None, None
        
        try:
            process_frame = cv2.resize(self.current_frame, (240, 180))
            rgb_frame = cv2.cvtColor(process_frame, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(rgb_frame)
            
            if not results.detections:
                return None, None
            
            detection = results.detections[0]
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = process_frame.shape
            x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                        int(bboxC.width * iw), int(bboxC.height * ih)
            
            x = max(0, x - 10)
            y = max(0, y - 10)
            w = min(w + 20, iw - x)
            h = min(h + 20, ih - y)
            
            face_img = process_frame[y:y+h, x:x+w]
            if face_img.size == 0:
                return None, None
            
            face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(face_rgb, num_jitters=5)
            
            if not face_encodings:
                return None, None
            
            return face_encodings[0], face_rgb
        except Exception as e:
            print(f"Error encoding face: {str(e)}")
            return None, None

    def cleanup(self):
        """Release camera resources"""
        self.video_capture.release()
        self.face_detection.close()