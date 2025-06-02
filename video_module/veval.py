import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque
import math

class VideoAnalyzer:
    def __init__(self):
        # Initialize MediaPipe components
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.mp_face_detection = mp.solutions.face_detection
        
        # Initialize face mesh with minimal complexity for speed
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize pose detection
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,  # Fastest model
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Initialize face detection for smile
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.5
        )
        
        # Landmark indices for facial features (more comprehensive)
        self.left_eye_indices = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        self.right_eye_indices = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        # Better mouth landmarks for smile detection
        self.mouth_indices = [61, 291, 13, 14, 269, 270, 267, 271, 272]  # Key mouth boundary points
        
    def calculate_eye_aspect_ratio(self, eye_landmarks):
        """Calculate Eye Aspect Ratio to determine if eyes are open"""
        if len(eye_landmarks) < 6:
            return 0.2
        
        # Vertical distances
        A = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
        B = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
        
        # Horizontal distance
        C = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
        
        if C == 0:
            return 0.2
        
        ear = (A + B) / (2.0 * C)
        return ear
    
    def calculate_gaze_direction(self, face_landmarks, frame_shape):
        """Calculate if person is looking at camera/center"""
        try:
            h, w = frame_shape[:2]
            
            # Get eye center points
            left_eye_center = np.mean([(int(face_landmarks.landmark[i].x * w), 
                                      int(face_landmarks.landmark[i].y * h)) 
                                     for i in [33, 133]], axis=0)
            right_eye_center = np.mean([(int(face_landmarks.landmark[i].x * w), 
                                       int(face_landmarks.landmark[i].y * h)) 
                                      for i in [362, 263]], axis=0)
            
            # Get nose tip for face direction
            nose_tip = (int(face_landmarks.landmark[1].x * w), 
                       int(face_landmarks.landmark[1].y * h))
            
            # Calculate face center
            face_center_x = (left_eye_center[0] + right_eye_center[0]) / 2
            face_center_y = (left_eye_center[1] + right_eye_center[1]) / 2
            
            # Frame center
            frame_center_x = w / 2
            frame_center_y = h / 2
            
            # Calculate gaze deviation from center
            horizontal_deviation = abs(face_center_x - frame_center_x) / (w / 2)
            vertical_deviation = abs(face_center_y - frame_center_y) / (h / 2)
            
            # Check if nose is aligned with eye centers (facing forward)
            eye_line_center = face_center_x
            nose_alignment = abs(nose_tip[0] - eye_line_center) / (w / 2)
            
            # Combined gaze score (lower deviation = better score)
            gaze_score = 1.0 - min(1.0, (horizontal_deviation * 0.6 + 
                                        vertical_deviation * 0.3 + 
                                        nose_alignment * 0.4))
            
            return max(0.0, gaze_score)
            
        except:
            return 0.3
    
    def detect_smile(self, mouth_landmarks):
        """Detect a genuine smile based on mouth landmarks with a strict threshold"""
        if len(mouth_landmarks) < 7:
            return 0  # No smile detected
        
        try:
            # Get key mouth points
            left_corner = np.array(mouth_landmarks[0])    
            right_corner = np.array(mouth_landmarks[4])   
            top_lip = np.array(mouth_landmarks[2])        
            bottom_lip = np.array(mouth_landmarks[6])     
            
            # 1. CORNER ELEVATION - Must be significant to count as a smile
            corner_avg_y = (left_corner[1] + right_corner[1]) / 2
            lip_center_y = (top_lip[1] + bottom_lip[1]) / 2
            elevation_diff = lip_center_y - corner_avg_y
            
            # Strict threshold for a genuine smile
            if elevation_diff <= 3:  # Not enough elevation
                return 0
            
            # 2. LIP SEPARATION - Must be in a reasonable range for a smile
            lip_separation = np.linalg.norm(top_lip - bottom_lip)
            mouth_width = np.linalg.norm(left_corner - right_corner)
            
            if mouth_width > 0:
                separation_ratio = lip_separation / mouth_width
                if not (0.08 <= separation_ratio <= 0.20):  # Outside smile range
                    return 0
            
            # 3. SYMMETRY - Ensure reasonable symmetry
            corner_height_diff = abs(left_corner[1] - right_corner[1])
            if corner_height_diff > 3:  # Too asymmetric
                return 0
            
            # If all conditions are met, count as a genuine smile
            return 1
        
        except Exception:
            return 0 # Very low default
    
    def calculate_posture_score(self, pose_landmarks):
        """Calculate posture score based on shoulder and spine alignment"""
        if not pose_landmarks:
            return 2.5
        
        try:
            # Get shoulder and hip landmarks
            left_shoulder = [pose_landmarks.landmark[11].x, pose_landmarks.landmark[11].y]
            right_shoulder = [pose_landmarks.landmark[12].x, pose_landmarks.landmark[12].y]
            left_hip = [pose_landmarks.landmark[23].x, pose_landmarks.landmark[23].y]
            right_hip = [pose_landmarks.landmark[24].x, pose_landmarks.landmark[24].y]
            nose = [pose_landmarks.landmark[0].x, pose_landmarks.landmark[0].y]
            
            # Calculate shoulder alignment
            shoulder_slope = abs(left_shoulder[1] - right_shoulder[1])
            
            # Calculate spine alignment (head to body center)
            body_center_x = (left_shoulder[0] + right_shoulder[0]) / 2
            head_alignment = abs(nose[0] - body_center_x)
            
            # Calculate forward lean
            shoulder_center_y = (left_shoulder[1] + right_shoulder[1]) / 2
            hip_center_y = (left_hip[1] + right_hip[1]) / 2
            forward_lean = abs(shoulder_center_y - hip_center_y)
            
            # Score calculation (inverse relationship with deviation)
            shoulder_score = max(0, 5 - (shoulder_slope * 50))
            alignment_score = max(0, 5 - (head_alignment * 20))
            lean_score = max(0, 5 - (forward_lean * 10))
            
            posture_score = (shoulder_score + alignment_score + lean_score) / 3
            return min(5, max(1, posture_score))
            
        except:
            return 2.5
    
    def calculate_energetic_start(self, motion_history, pose_history, face_activity):
        """Enhanced energetic start calculation with multiple energy indicators"""
        if len(motion_history) == 0:
            return 3.0  # Default neutral score
        
        # Focus on first 30% of video for "start" energy
        start_frames = max(1, int(len(motion_history) * 0.3))
        start_motion = motion_history[:start_frames]
        
        energy_indicators = []
        
        # 1. Motion Energy - overall movement
        if start_motion:
            avg_motion = np.mean(start_motion)
            motion_energy = min(5.0, avg_motion * 25)  # Boosted multiplier
            energy_indicators.append(motion_energy)
        
        # 2. Motion Variability - dynamic vs static
        if len(start_motion) > 1:
            motion_std = np.std(start_motion)
            variability_score = min(5.0, motion_std * 30)  # Reward varied movement
            energy_indicators.append(variability_score)
        
        # 3. Peak Motion Moments - sudden energetic bursts
        if len(start_motion) >= 3:
            motion_peaks = []
            for i in range(1, len(start_motion) - 1):
                if start_motion[i] > start_motion[i-1] and start_motion[i] > start_motion[i+1]:
                    motion_peaks.append(start_motion[i])
            
            if motion_peaks:
                peak_energy = min(5.0, np.mean(motion_peaks) * 20)
                energy_indicators.append(peak_energy)
            else:
                energy_indicators.append(2.0)  # No peaks detected
        
        # 4. Progressive Energy - building up energy
        if len(start_motion) >= 5:
            # Check if motion generally increases in first part
            first_half = start_motion[:len(start_motion)//2]
            second_half = start_motion[len(start_motion)//2:]
            
            if len(first_half) > 0 and len(second_half) > 0:
                progression = np.mean(second_half) - np.mean(first_half)
                progression_score = min(5.0, max(1.0, 3.0 + progression * 15))
                energy_indicators.append(progression_score)
        
        # 5. Face Activity Energy (if available)
        if face_activity:
            start_face_activity = face_activity[:start_frames]
            if start_face_activity:
                face_energy = sum(start_face_activity) / len(start_face_activity) * 5
                energy_indicators.append(face_energy)
        
        # Combine all indicators
        if energy_indicators:
            # Weight the different indicators
            if len(energy_indicators) == 1:
                final_energy = energy_indicators[0]
            elif len(energy_indicators) == 2:
                final_energy = (energy_indicators[0] * 0.6 + energy_indicators[1] * 0.4)
            else:
                # More comprehensive scoring
                weights = [0.3, 0.25, 0.2, 0.15, 0.1][:len(energy_indicators)]
                final_energy = sum(score * weight for score, weight in zip(energy_indicators, weights))
            
            # Apply boost for more generous scoring
            boosted_energy = min(5.0, max(1.0, final_energy * 1.2))
            return boosted_energy
        
        return 3.0  # Default if no indicators
    
    def analyze_video(self, video_path, max_frames=300):
        """Main function to analyze video and return scores"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            return None
        
        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Calculate frame skip for efficiency
        frame_skip = max(1, total_frames // max_frames)
        
        # Initialize tracking variables
        posture_scores = []
        eye_contact_ratios = []
        smile_count = 0  # Count genuine smiles
        motion_history = []
        face_activity = []
        pose_history = []
        prev_frame = None
        prev_pose = None
        
        frame_count = 0
        processed_frames = 0
        
        print(f"Processing video: {total_frames} frames, sampling every {frame_skip} frames")
        
        while cap.isOpened() and processed_frames < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Skip frames for efficiency
            if frame_count % frame_skip != 0:
                frame_count += 1
                continue
            
            # Resize frame for faster processing
            height, width = frame.shape[:2]
            if width > 640:
                scale = 640 / width
                new_width = 640
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Calculate motion
            if prev_frame is not None:
                diff = cv2.absdiff(cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY), 
                                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
                motion = np.mean(diff) / 255.0
                motion_history.append(motion)
            prev_frame = frame.copy()
            
            # Process with MediaPipe
            pose_results = self.pose.process(rgb_frame)
            face_results = self.face_mesh.process(rgb_frame)
            
            # Calculate posture score and track pose changes
            if pose_results.pose_landmarks:
                posture_score = self.calculate_posture_score(pose_results.pose_landmarks)
                posture_scores.append(posture_score)
                
                current_pose = [pose_results.pose_landmarks.landmark[i] for i in [11, 12, 13, 14, 15, 16]]
                if prev_pose is not None:
                    pose_change = sum([
                        abs(curr.x - prev.x) + abs(curr.y - prev.y) 
                        for curr, prev in zip(current_pose, prev_pose)
                    ])
                    pose_history.append(pose_change)
                prev_pose = current_pose
            
            # Process facial features
            if face_results.multi_face_landmarks:
                for face_landmarks in face_results.multi_face_landmarks:
                    landmarks = face_landmarks.landmark
                    h, w = frame.shape[:2]
                    
                    # Extract eye landmarks
                    left_eye = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) 
                            for i in self.left_eye_indices[:6]]
                    right_eye = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) 
                            for i in self.right_eye_indices[:6]]
                    
                    # Calculate eye contact score
                    left_ear = self.calculate_eye_aspect_ratio(left_eye)
                    right_ear = self.calculate_eye_aspect_ratio(right_eye)
                    avg_ear = (left_ear + right_ear) / 2
                    
                    if avg_ear < 0.2:
                        eye_openness_score = 0.1
                    elif avg_ear < 0.25:
                        eye_openness_score = 0.4
                    elif avg_ear > 0.35:
                        eye_openness_score = 0.7
                    else:
                        eye_openness_score = 1.0
                    
                    gaze_score = self.calculate_gaze_direction(face_landmarks, frame.shape)
                    
                    if gaze_score < 0.4:
                        eye_contact_score = min(2.0, eye_openness_score * 2)
                    elif gaze_score < 0.6:
                        eye_contact_score = min(3.5, (eye_openness_score + gaze_score) * 2)
                    else:
                        eye_contact_score = min(5.0, (eye_openness_score * 0.4 + gaze_score * 0.6) * 5)
                    
                    eye_contact_ratios.append(eye_contact_score)
                    
                    # Extract mouth landmarks for smile detection
                    mouth_landmarks = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) 
                                    for i in self.mouth_indices]
                    
                    # Detect smile and increment counter if genuine
                    smile_detected = self.detect_smile(mouth_landmarks)
                    smile_count += smile_detected
                    
                    # Track face activity for energy calculation
                    face_activity.append(smile_detected + (eye_contact_score / 5))
            
            processed_frames += 1
            frame_count += 1
            
            if processed_frames % 50 == 0:
                progress = (processed_frames / max_frames) * 100
                print(f"Progress: {progress:.1f}%")
        
        cap.release()
        
        # Calculate final scores
        final_posture = np.mean(posture_scores) if posture_scores else 2.5
        
        # Eye contact scoring
        if eye_contact_ratios:
            avg_eye_contact = np.mean(eye_contact_ratios)
            consistency_bonus = 1.0
            if len(eye_contact_ratios) > 5:
                low_scores = sum(1 for score in eye_contact_ratios if score < 2.5)
                consistency_bonus = max(0.5, 1.0 - (low_scores / len(eye_contact_ratios) * 0.8))
            final_eye_contact = avg_eye_contact * consistency_bonus
        else:
            final_eye_contact = 2.0
        
        # Smile scoring based on total smile count
        # Scoring logic:
        # - 75+ smiles: 5/5 (rare case)
        # - 50 smiles: ~4/5
        # - 25 smiles: ~3/5 (decent smiling)
        # - 10 smiles: ~2/5
        # - <10 smiles: ~1/5
        if smile_count >= 75:
            final_smile = 5.0
        elif smile_count >= 50:
            final_smile = 4.0 + (smile_count - 50) / 50  # Linear increase from 4 to 5
        elif smile_count >= 25:
            final_smile = 3.0 + (smile_count - 25) / 25  # Linear increase from 3 to 4
        elif smile_count >= 10:
            final_smile = 2.0 + (smile_count - 10) / 25  # Linear increase from 2 to 3
        else:
            final_smile = 1.0 + smile_count / 10  # Linear increase from 1 to 2
        
        final_smile = min(5.0, max(1.0, final_smile))
        
        # Energetic start calculation
        final_energetic_start = self.calculate_energetic_start(motion_history, pose_history, face_activity)
        
        # Final scores
        scores = {
            'posture': round(min(5, max(1, final_posture))),
            'Energetic Start': round(min(5, max(1, final_energetic_start))),
            'Eye Contact': round(min(5, max(1, final_eye_contact))), 
            "Smile Score" : round((round(min(5, max(1, final_posture))) + round(min(5, max(1, final_energetic_start))) + round(min(5, max(1, final_eye_contact)))) / 3 )
        }
        
        return scores
def analyze_video_file(video_path):
    """Main function to analyze a video file"""
    print(f"Starting analysis of: {video_path}")
    start_time = time.time()
    
    analyzer = VideoAnalyzer()
    scores = analyzer.analyze_video(video_path)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    if scores:
        print(f"\n--- Video Analysis Results ---")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Posture Score: {scores['posture']}/5")
        print(f"Energetic Start: {scores['Energetic Start']}/5")
        print(f"Smile Score: {scores['Smile Score']}/5")
        print(f"Eye Contact Score: {scores['Eye Contact']}/5")
        print(f"Overall Average: {sum(scores.values())/4:.2f}/5")
        return scores
    else:
        print("Failed to analyze video")
        return None

# # Example usage
# if __name__ == "__main__":
#     # Replace with your video file path
#     video_file = r"D:\SOME_UPDATED\SOME_\static\uploads\Nishant_Sharma_22386[1] (2).mp4"
    
#     # Analyze the video
#     results = analyze_video_file(video_file)
    
#     if results:
#         print("\nAnalysis completed successfully!")
#     else:
#         print("Analysis failed. Please check your video file path and format.")
