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

try:
    correct_sound = pygame.mixer.Sound(os.path.join(os.getcwd(), "correct.wav"))
except:
    pass

try:
    coach_sound = pygame.mixer.Sound(os.path.join(os.getcwd(), "coach.wav"))
except:
    pass

# ---------- Mediapipe Setup ----------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# ---------- Utility Functions ----------
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

# READY = both hands generally up (for double-biceps)
def is_pose_ready(lm):
    left_wrist_y, right_wrist_y = lm[15][1], lm[16][1]
    left_shoulder_y, right_shoulder_y = lm[11][1], lm[12][1]
    return (left_wrist_y < left_shoulder_y - 0.02 and
            right_wrist_y < right_shoulder_y - 0.02)

# generic angle scorer: ideal +/- soft_tol is “good”, up to hard_tol is “okay”
def angle_score(angle, ideal, soft_tol=15, hard_tol=35):
    diff = abs(angle - ideal)

    if diff <= soft_tol:            # looks correct
        score = 100 - diff * 0.7
    elif diff <= hard_tol:          # acceptable for normal people
        score = 90 - (diff - soft_tol) * 1.5
    else:                           # far from pose
        score = 55

    return max(0, min(100, score))


# ---------- Pose Scoring Functions ----------

# FRONT DOUBLE BICEPS
# realistic: elbow flex ~ 60–90°, both arms high & symmetric
def score_front_double_biceps(lm):
    if not is_pose_ready(lm):
        return 0, "Lift arms above shoulders"

    left = calculate_angle(lm[11], lm[13], lm[15])
    right = calculate_angle(lm[12], lm[14], lm[16])

    # Broad human range
    def human_arm_score(angle):
        if 50 <= angle <= 100:
            return 100
        elif 40 <= angle < 50 or 100 < angle <= 115:
            return 85
        elif 30 <= angle < 40 or 115 < angle <= 130:
            return 65
        else:
            return 40

    left_score = human_arm_score(left)
    right_score = human_arm_score(right)

    symmetry_diff = abs(left - right)
    symmetry_penalty = max(0, symmetry_diff - 20) * 0.7

    score = (left_score + right_score) / 2 - symmetry_penalty
    score = max(0, min(100, score))

    if score >= 85:
        feedback = "Strong double biceps!"
    elif symmetry_diff > 25:
        feedback = "Match arm angles"
    else:
        feedback = "Flex biceps more"

    return int(score), feedback


# BACK DOUBLE BICEPS
def score_back_double_biceps(lm):
    if not is_pose_ready(lm):
        return 0, "Raise arms and flex back"

    left = calculate_angle(lm[11], lm[13], lm[15])
    right = calculate_angle(lm[12], lm[14], lm[16])

    # Human-friendly scoring for back pose
    def back_arm_score(angle):
        if 65 <= angle <= 110:
            return 100
        elif 55 <= angle < 65 or 110 < angle <= 125:
            return 85
        elif 45 <= angle < 55 or 125 < angle <= 140:
            return 65
        else:
            return 40

    left_score = back_arm_score(left)
    right_score = back_arm_score(right)

    # More forgiving symmetry (back pose is harder)
    symmetry_diff = abs(left - right)
    symmetry_penalty = max(0, symmetry_diff - 30) * 0.5

    score = (left_score + right_score) / 2 - symmetry_penalty
    score = max(0, min(100, score))

    # Feedback tuned for humans
    if score >= 85:
        feedback = "Strong back double biceps!"
    elif symmetry_diff > 35:
        feedback = "Balance both arms"
    elif left > 125 or right > 125:
        feedback = "Bend elbows slightly more"
    elif left < 55 or right < 55:
        feedback = "Flex arms and back harder"
    else:
        feedback = "Tighten back and raise elbows"

    return int(score), feedback


# SIDE CHEST
# idea: arms near chest height, front arm well bent (~60–90°)
def score_side_chest(lm):
    left_wrist_y, right_wrist_y = lm[15][1], lm[16][1]
    left_sh_y, right_sh_y = lm[11][1], lm[12][1]
    left_hip_y, right_hip_y = lm[23][1], lm[24][1]

    # Chest-height zone
    chest_top = min(left_sh_y, right_sh_y) + 0.05
    chest_bottom = max(left_hip_y, right_hip_y) - 0.05

    if not (chest_top < left_wrist_y < chest_bottom or
            chest_top < right_wrist_y < chest_bottom):
        return 0, "Bring arms in front of chest"

    left_elbow = calculate_angle(lm[11], lm[13], lm[15])
    right_elbow = calculate_angle(lm[12], lm[14], lm[16])

    # Identify front arm (more bent)
    front = min(left_elbow, right_elbow)
    back = max(left_elbow, right_elbow)

    # Very forgiving human ranges
    if 50 <= front <= 100:
        front_score = 100
    elif 40 <= front < 50 or 100 < front <= 120:
        front_score = 80
    else:
        front_score = 55

    if 70 <= back <= 140:
        back_score = 100
    elif 60 <= back < 70 or 140 < back <= 160:
        back_score = 80
    else:
        back_score = 60

    score = 0.7 * front_score + 0.3 * back_score
    score = max(0, min(100, score))

    if score >= 85:
        feedback = "Nice side chest!"
    elif front < 50:
        feedback = "Squeeze chest more"
    else:
        feedback = "Adjust arm position"

    return int(score), feedback


# LAT FLEX / LAT SPREAD
def score_lat_flex(lm):
    left_shoulder = np.array(lm[11])
    right_shoulder = np.array(lm[12])
    left_wrist = np.array(lm[15])
    right_wrist = np.array(lm[16])

    shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
    wrist_width = np.linalg.norm(left_wrist - right_wrist)
    ratio = wrist_width / (shoulder_width + 1e-6)

    # check that arms are roughly at ribcage level (not hanging totally down)
    left_wrist_y, right_wrist_y = lm[15][1], lm[16][1]
    left_hip_y, right_hip_y = lm[23][1], lm[24][1]
    left_sh_y, right_sh_y = lm[11][1], lm[12][1]

    chest_top = min(left_sh_y, right_sh_y) + 0.05
    hip_line = max(left_hip_y, right_hip_y) - 0.02

    hands_in_zone = ((chest_top < left_wrist_y < hip_line) and
                     (chest_top < right_wrist_y < hip_line))

    if not hands_in_zone:
        return 0, "Keep elbows wide at ribcage level"

    # ratio ~1.0 = normal, 1.1–1.2 = good, >1.25 = very wide
    if ratio >= 1.25:
        score = 100
        feedback = "Huge lat spread!"
    elif ratio >= 1.15:
        score = int(90 + (ratio - 1.15) * 100)  # 90–100
        feedback = "Great lat spread"
    elif ratio >= 1.05:
        score = int(75 + (ratio - 1.05) * 150)  # 75–90
        feedback = "Good, flare lats a bit more"
    else:
        score = max(50, int(ratio * 60))        # 50–63ish
        feedback = "Spread elbows out and widen back"

    score = max(0, min(100, score))
    return score, feedback


POSES = {
    "1": ("Front Double Biceps", score_front_double_biceps),
    "2": ("Back Double Biceps", score_back_double_biceps),
    "3": ("Side Chest", score_side_chest),
    "4": ("Lat Flex", score_lat_flex),
}

# Default to Front Double Biceps (1) to avoid blocking input when run from web app
choice = "1"

if choice not in POSES:
    print("Invalid option. Exiting.")
    raise SystemExit

current_pose_key = choice
pose_name, pose_scoring = POSES[current_pose_key]
print(f"\n🔥 Selected Pose: {pose_name}\n")

# ---------- Camera ----------
cap = cv2.VideoCapture(0)
os.makedirs("snapshots", exist_ok=True)

hold_start_time = None
screenshot_taken = False

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

            # ---------- HOLD + SCREENSHOT (3s at good score) ----------
            if score >= 80:
                if hold_start_time is None:
                    hold_start_time = now
                elif now - hold_start_time >= 3 and not screenshot_taken:
                    path = os.path.join("snapshots", f"{pose_name}_held.jpg")
                    cv2.imwrite(path, image)
                    screenshot_taken = True
                    if correct_sound:
                        correct_sound.play()
            else:
                hold_start_time = None
                screenshot_taken = False
                if coach_sound and score > 0:  # avoid spam when no pose
                    coach_sound.play()

            # ---------- UI ----------
            color = (0, 255, 0) if score >= 80 else (0, 0, 255)
            cv2.putText(image, f"{pose_name} | Score: {score}",
                        (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

            if hold_start_time:
                hold_time = int(now - hold_start_time)
                cv2.putText(image, f"Hold: {hold_time}s",
                            (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            (255, 255, 255), 2)

            cv2.putText(image, feedback,
                        (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (255, 255, 255), 2)

        # bottom help text (always visible)
        cv2.putText(image, "1:Front  2:Back  3:Side  4:Lat | Q:Quit",
                    (10, image.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("AI Bodybuilding Coach", image)

        # ---- KEYBOARD CONTROLS ----
        key = cv2.waitKey(1) & 0xFF

        # pose switching
        if key in [ord('1'), ord('2'), ord('3'), ord('4')]:
            new_key = chr(key)
            if new_key != current_pose_key:
                current_pose_key = new_key
                pose_name, pose_scoring = POSES[current_pose_key]

                # reset hold logic on pose change
                hold_start_time = None
                screenshot_taken = False

                print(f"Switched to pose: {pose_name}")

        # quit
        if key == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
