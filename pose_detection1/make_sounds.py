import cv2
import mediapipe as mp
import numpy as np
import time
import pygame
import os

print("Running from:", os.getcwd())

# ---------- SOUND SYSTEM ----------
pygame.mixer.init()

correct_sound = None
coach_sound = None

# Load correct.wav
try:
    correct_path = os.path.join(os.getcwd(), "correct.wav")
    correct_sound = pygame.mixer.Sound(correct_path)
    print("✅ Loaded:", correct_path)
except Exception as e:
    print("❌ Could not load correct.wav:", e)

# Load coach.wav (optional)
try:
    coach_path = os.path.join(os.getcwd(), "coach.wav")
    coach_sound = pygame.mixer.Sound(coach_path)
    print("✅ Loaded:", coach_path)
except Exception as e:
    print("⚠️ coach.wav not loaded (optional):", e)

# ---------- Mediapipe Setup ----------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose


# ---------- Utility Functions ----------
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))


def is_pose_ready(lm):
    left_wrist_y, right_wrist_y = lm[15][1], lm[16][1]
    left_shoulder_y, right_shoulder_y = lm[11][1], lm[12][1]
    return left_wrist_y < left_shoulder_y - 0.05 and right_wrist_y < right_shoulder_y - 0.05


# ---------- Pose Scoring Functions ----------
def score_front_double_biceps(lm):
    if not is_pose_ready(lm):
        return 0, "Lift arms"

    left_elbow = calculate_angle(lm[11], lm[13], lm[15])
    right_elbow = calculate_angle(lm[12], lm[14], lm[16])

    ideal = 90
    diff_left = abs(left_elbow - ideal)
    diff_right = abs(right_elbow - ideal)

    score = 100 - (diff_left + diff_right) / 2

    if diff_left > 20:
        feedback = "Raise left arm"
    elif diff_right > 20:
        feedback = "Raise right arm"
    else:
        feedback = "Perfect form"

    return max(0, min(100, int(score))), feedback


def score_back_double_biceps(lm):
    return score_front_double_biceps(lm)


def score_side_chest(lm):
    if not is_pose_ready(lm):
        return 0, "Lift arms"

    elbow_angle = calculate_angle(lm[11], lm[13], lm[15])
    ideal = 90
    diff = abs(elbow_angle - ideal)

    score = 100 - diff
    feedback = "Open chest more" if diff > 20 else "Great pose"

    return max(0, int(score)), feedback


def score_lat_flex(lm):
    if not is_pose_ready(lm):
        return 0, "Lift arms"

    shoulder_width = np.linalg.norm(np.array(lm[11]) - np.array(lm[12]))
    wrist_width = np.linalg.norm(np.array(lm[15]) - np.array(lm[16]))

    ratio = wrist_width / (shoulder_width + 1e-6)
    score = int(ratio * 100)

    if ratio < 1.2:
        feedback = "Spread lats more"
    else:
        feedback = "Massive lats!"

    return max(0, min(score, 100)), feedback


POSES = {
    "1": ("Front Double Biceps", score_front_double_biceps),
    "2": ("Back Double Biceps", score_back_double_biceps),
    "3": ("Side Chest", score_side_chest),
    "4": ("Lat Flex", score_lat_flex),
}

print("\nSelect Pose:")
print("1) Front Double Biceps")
print("2) Back Double Biceps")
print("3) Side Chest")
print("4) Lat Flex")
choice = input("Enter Pose Number: ")

if choice not in POSES:
    print("Invalid Option. Exiting.")
    raise SystemExit

pose_name, pose_scoring = POSES[choice]
print(f"\n🔥 Selected: {pose_name}\nStarting camera...\n")

# ---------- Camera & Tracking ----------
cap = cv2.VideoCapture(0)

best_score = 0
last_correct_sound_time = 0
last_coach_sound_time = 0
sound_cooldown = 2  # seconds

os.makedirs("snapshots", exist_ok=True)

with mp_pose.Pose(min_detection_confidence=0.7,
                  min_tracking_confidence=0.7) as pose:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if result.pose_landmarks:
            mp_drawing.draw_landmarks(
                image, result.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            lm = [[lm.x, lm.y, lm.z]
                  for lm in result.pose_landmarks.landmark]

            score, feedback = pose_scoring(lm)

            now = time.time()

            # Play "correct" sound on high score
            if correct_sound and score >= 90 and now - last_correct_sound_time > sound_cooldown:
                correct_sound.play()
                last_correct_sound_time = now

            # Play coaching sound on low score
            if coach_sound and score < 50 and now - last_coach_sound_time > sound_cooldown:
                coach_sound.play()
                last_coach_sound_time = now

            # Save best snapshot
            if score > best_score:
                best_score = score
                snap_path = os.path.join("snapshots", f"{pose_name}_best_{best_score}.jpg")
                cv2.imwrite(snap_path, image)

            # Color based on score
            if score > 80:
                color = (0, 255, 0)
            elif score > 50:
                color = (0, 255, 255)
            else:
                color = (0, 0, 255)

            cv2.putText(image, f"{pose_name} | Score: {score}",
                        (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

            cv2.putText(image, f"Feedback: {feedback}",
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imshow("AI Bodybuilding Coach", image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
