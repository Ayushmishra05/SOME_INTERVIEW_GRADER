import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque

class VideoAnalyzer:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.mp_face_detection = mp.solutions.face_detection
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False, max_num_faces=1, refine_landmarks=False,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self.pose = self.mp_pose.Pose(
            static_image_mode=False, model_complexity=0, smooth_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.5
        )
        self.left_eye_indices = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        self.right_eye_indices = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        self.mouth_indices = [61, 291, 13, 14, 269, 270, 267, 271, 272]

    def calculate_eye_aspect_ratio(self, eye_landmarks):
        if len(eye_landmarks) < 6:
            return 0.2
        A = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
        B = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))
        C = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))
        return (A + B) / (2.0 * C) if C != 0 else 0.2

    def calculate_gaze_direction(self, face_landmarks, frame_shape):
        try:
            h, w = frame_shape[:2]
            left_eye_center = np.mean([(int(face_landmarks.landmark[i].x * w), 
                                      int(face_landmarks.landmark[i].y * h)) 
                                     for i in [33, 133]], axis=0)
            right_eye_center = np.mean([(int(face_landmarks.landmark[i].x * w), 
                                       int(face_landmarks.landmark[i].y * h)) 
                                      for i in [362, 263]], axis=0)
            nose_tip = (int(face_landmarks.landmark[1].x * w), 
                       int(face_landmarks.landmark[1].y * h))
            face_center_x = (left_eye_center[0] + right_eye_center[0]) / 2
            face_center_y = (left_eye_center[1] + right_eye_center[1]) / 2
            frame_center_x, frame_center_y = w / 2, h / 2
            horizontal_deviation = abs(face_center_x - frame_center_x) / (w / 2)
            vertical_deviation = abs(face_center_y - frame_center_y) / (h / 2)
            eye_line_center = face_center_x
            nose_alignment = abs(nose_tip[0] - eye_line_center) / (w / 2)
            gaze_score = 1.0 - min(1.0, (horizontal_deviation * 0.6 + 
                                        vertical_deviation * 0.3 + 
                                        nose_alignment * 0.4))
            return max(0.0, gaze_score)
        except:
            return 0.3

    def detect_smile(self, mouth_landmarks):
        if len(mouth_landmarks) < 7:
            return 0
        try:
            left_corner = np.array(mouth_landmarks[0])
            right_corner = np.array(mouth_landmarks[4])
            top_lip = np.array(mouth_landmarks[2])
            bottom_lip = np.array(mouth_landmarks[6])
            corner_avg_y = (left_corner[1] + right_corner[1]) / 2
            lip_center_y = (top_lip[1] + bottom_lip[1]) / 2
            elevation_diff = lip_center_y - corner_avg_y
            if elevation_diff <= 3:
                return 0
            lip_separation = np.linalg.norm(top_lip - bottom_lip)
            mouth_width = np.linalg.norm(left_corner - right_corner)
            if mouth_width > 0:
                separation_ratio = lip_separation / mouth_width
                if not (0.08 <= separation_ratio <= 0.20):
                    return 0
            corner_height_diff = abs(left_corner[1] - right_corner[1])
            if corner_height_diff > 3:
                return 0
            return 1
        except:
            return 0

    def calculate_posture_score(self, pose_landmarks):
        if not pose_landmarks:
            return 2.5
        try:
            left_shoulder = [pose_landmarks.landmark[11].x, pose_landmarks.landmark[11].y]
            right_shoulder = [pose_landmarks.landmark[12].x, pose_landmarks.landmark[12].y]
            left_hip = [pose_landmarks.landmark[23].x, pose_landmarks.landmark[23].y]
            right_hip = [pose_landmarks.landmark[24].x, pose_landmarks.landmark[24].y]
            nose = [pose_landmarks.landmark[0].x, pose_landmarks.landmark[0].y]
            shoulder_slope = abs(left_shoulder[1] - right_shoulder[1])
            body_center_x = (left_shoulder[0] + right_shoulder[0]) / 2
            head_alignment = abs(nose[0] - body_center_x)
            shoulder_center_y = (left_shoulder[1] + right_shoulder[1]) / 2
            hip_center_y = (left_hip[1] + right_hip[1]) / 2
            forward_lean = abs(shoulder_center_y - hip_center_y)
            shoulder_score = max(0, 5 - (shoulder_slope * 50))
            alignment_score = max(0, 5 - (head_alignment * 20))
            lean_score = max(0, 5 - (forward_lean * 10))
            return min(5, max(1, (shoulder_score + alignment_score + lean_score) / 3))
        except:
            return 2.5

    def calculate_energetic_start(self, motion_history, pose_history, face_activity):
        if not motion_history:
            return 3.0
        start_frames = max(1, int(len(motion_history) * 0.3))
        start_motion = motion_history[:start_frames]
        energy_indicators = []
        if start_motion:
            avg_motion = np.mean(start_motion)
            energy_indicators.append(min(5.0, avg_motion * 25))
        if len(start_motion) > 1:
            energy_indicators.append(min(5.0, np.std(start_motion) * 30))
        if len(start_motion) >= 3:
            motion_peaks = [start_motion[i] for i in range(1, len(start_motion) - 1)
                           if start_motion[i] > start_motion[i-1] and start_motion[i] > start_motion[i+1]]
            energy_indicators.append(min(5.0, np.mean(motion_peaks) * 20) if motion_peaks else 2.0)
        if len(start_motion) >= 5:
            first_half = start_motion[:len(start_motion)//2]
            second_half = start_motion[len(start_motion)//2:]
            if first_half and second_half:
                progression = np.mean(second_half) - np.mean(first_half)
                energy_indicators.append(min(5.0, max(1.0, 3.0 + progression * 15)))
        if face_activity:
            start_face_activity = face_activity[:start_frames]
            if start_face_activity:
                energy_indicators.append(sum(start_face_activity) / len(start_face_activity) * 5)
        if energy_indicators:
            weights = [0.3, 0.25, 0.2, 0.15, 0.1][:len(energy_indicators)]
            final_energy = sum(score * weight for score, weight in zip(energy_indicators, weights))
            return min(5.0, max(1.0, final_energy * 1.2))
        return 3.0

    def analyze_video(self, video_path, max_frames=150):  # Reduced for speed
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            return None
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_skip = max(1, total_frames // max_frames)
        posture_scores = []
        eye_contact_ratios = []
        smile_count = 0
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
            if frame_count % frame_skip != 0:
                frame_count += 1
                continue
            height, width = frame.shape[:2]
            if width > 480:  # Reduced resolution for speed
                scale = 480 / width
                frame = cv2.resize(frame, (480, int(height * scale)))
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if prev_frame is not None:
                diff = cv2.absdiff(cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY), 
                                  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
                motion_history.append(np.mean(diff) / 255.0)
            prev_frame = frame.copy()
            pose_results = self.pose.process(rgb_frame)
            face_results = self.face_mesh.process(rgb_frame)
            if pose_results.pose_landmarks:
                posture_scores.append(self.calculate_posture_score(pose_results.pose_landmarks))
                current_pose = [pose_results.pose_landmarks.landmark[i] for i in [11, 12, 13, 14, 15, 16]]
                if prev_pose is not None:
                    pose_change = sum(abs(curr.x - prev.x) + abs(curr.y - prev.y) 
                                    for curr, prev in zip(current_pose, prev_pose))
                    pose_history.append(pose_change)
                prev_pose = current_pose
            if face_results.multi_face_landmarks:
                for face_landmarks in face_results.multi_face_landmarks:
                    landmarks = face_landmarks.landmark
                    h, w = frame.shape[:2]
                    left_eye = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) 
                               for i in self.left_eye_indices[:6]]
                    right_eye = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) 
                                for i in self.right_eye_indices[:6]]
                    left_ear = self.calculate_eye_aspect_ratio(left_eye)
                    right_ear = self.calculate_eye_aspect_ratio(right_eye)
                    avg_ear = (left_ear + right_ear) / 2
                    eye_openness_score = 0.1 if avg_ear < 0.2 else 0.4 if avg_ear < 0.25 else 0.7 if avg_ear > 0.35 else 1.0
                    gaze_score = self.calculate_gaze_direction(face_landmarks, frame.shape)
                    eye_contact_score = min(2.0, eye_openness_score * 2) if gaze_score < 0.4 else \
                                      min(3.5, (eye_openness_score + gaze_score) * 2) if gaze_score < 0.6 else \
                                      min(5.0, (eye_openness_score * 0.4 + gaze_score * 0.6) * 5)
                    eye_contact_ratios.append(eye_contact_score)
                    mouth_landmarks = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) 
                                     for i in self.mouth_indices]
                    smile_count += self.detect_smile(mouth_landmarks)
                    face_activity.append(self.detect_smile(mouth_landmarks) + (eye_contact_score / 5))
            processed_frames += 1
            frame_count += 1
            if processed_frames % 50 == 0:
                print(f"Progress: {(processed_frames / max_frames) * 100:.1f}%")
        cap.release()
        final_posture = np.mean(posture_scores) if posture_scores else 2.5
        final_eye_contact = np.mean(eye_contact_ratios) * max(0.5, 1.0 - (sum(1 for score in eye_contact_ratios if score < 2.5) / len(eye_contact_ratios) * 0.8)) if eye_contact_ratios else 2.0
        final_smile = 5.0 if smile_count >= 75 else 4.0 + (smile_count - 50) / 50 if smile_count >= 50 else \
                     3.0 + (smile_count - 25) / 25 if smile_count >= 25 else 2.0 + (smile_count - 10) / 25 if smile_count >= 10 else 1.0 + smile_count / 10
        final_smile = min(5.0, max(1.0, final_smile))
        final_energetic_start = self.calculate_energetic_start(motion_history, pose_history, face_activity)
        return {
            'posture': round(min(5, max(1, final_posture))),
            'Energetic Start': round(min(5, max(1, final_energetic_start))),
            'Eye Contact': round(min(5, max(1, final_eye_contact))),
            'Smile Score': round((round(min(5, max(1, final_posture))) + round(min(5, max(1, final_energetic_start))) + round(min(5, max(1, final_eye_contact)))) / 3)
        }

def analyze_video_file(video_path):
    print(f"Starting analysis of: {video_path}")
    start_time = time.time()
    analyzer = VideoAnalyzer()
    scores = analyzer.analyze_video(video_path)
    end_time = time.time()
    print(f"\n--- Video Analysis Results ---")
    print(f"Processing time: {end_time - start_time:.2f} seconds")
    if scores:
        print(f"Posture Score: {scores['posture']}/5")
        print(f"Energetic Start: {scores['Energetic Start']}/5")
        print(f"Smile Score: {scores['Smile Score']}/5")
        print(f"Eye Contact Score: {scores['Eye Contact']}/5")
        print(f"Overall Average: {sum(scores.values())/4:.2f}/5")
        return scores
    print("Failed to analyze video")
    return None