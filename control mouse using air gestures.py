import cv2
import mediapipe as mp
import pyautogui
import time
import math
from collections import deque

# --- Settings ---
CAM_W, CAM_H = 640, 360
SMOOTHING_BUFFER = 3
CLICK_DISTANCE_RATIO = 0.035
MAX_CURSOR_DEADZONE = 0.02

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
pyautogui.FAILSAFE = False

screen_w, screen_h = pyautogui.size()
screen_diag = math.hypot(screen_w, screen_h)

# Use DirectShow backend on Windows for potentially lower latency
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
cap.set(cv2.CAP_PROP_FPS, 15)

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

pos_buffer = deque(maxlen=SMOOTHING_BUFFER)

left_clicked = False
right_clicked = False
scroll_ref = None

# Anchoring state: prevent cursor snapping when hand re-enters frame
hand_active = False
hand_anchor = None     # normalized coords (x,y) of fingertip when hand re-entered
screen_anchor = None   # screen coords (x,y) corresponding to hand_anchor

def distance(p1, p2):
    return math.hypot(p1[0]-p2[0], p1[1]-p2[1])

def normalized_to_screen(x, y):
    # Map mediapipe normalized coords directly to screen coords.
    sx = int(x * screen_w)
    sy = int(y * screen_h)
    sx = max(0, min(screen_w - 1, sx))
    sy = max(0, min(screen_h - 1, sy))
    return sx, sy

prev_time = 0
print("Hand Mouse Active. Press 'q' to quit.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read error.")
            break

        # Mirror preview so it feels like a mirror to the user
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        h, w, _ = frame.shape
        action = "Idle"

        if result.multi_hand_landmarks:
            lm = result.multi_hand_landmarks[0]
            mp_drawing.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)

            # Mediapipe landmarks are normalized [0..1] relative to the processed image (mirrored above).
            landmarks = [(p.x, p.y) for p in lm.landmark]
            thumb = landmarks[4]
            index = landmarks[8]
            middle = landmarks[12]

            thumb_px = (int(thumb[0]*w), int(thumb[1]*h))
            index_px = (int(index[0]*w), int(index[1]*h))
            middle_px = (int(middle[0]*w), int(middle[1]*h))

            cv2.circle(frame, thumb_px, 8, (0,255,255), -1)
            cv2.circle(frame, index_px, 8, (0,0,255), -1)
            cv2.circle(frame, middle_px, 8, (255,0,0), -1)

            d_idx_thumb = distance(index_px, thumb_px)
            d_mid_thumb = distance(middle_px, thumb_px)
            d_idx_mid = distance(index_px, middle_px)

            frame_diag = math.hypot(w, h)
            pinch_thresh = CLICK_DISTANCE_RATIO * frame_diag

            # -------- Cursor movement with anchoring --------
            # index is normalized (x,y)
            if not hand_active:
                # hand just appeared -> set anchors
                hand_active = True
                hand_anchor = (index[0], index[1])
                p = pyautogui.position()
                screen_anchor = (p.x, p.y)
                # seed smoothing buffer with current cursor to avoid a jump
                pos_buffer.clear()
                for _ in range(max(1, SMOOTHING_BUFFER)):
                    pos_buffer.append(screen_anchor)
            else:
                # compute offset from anchor in screen pixels
                dx = (index[0] - hand_anchor[0]) * screen_w
                dy = (index[1] - hand_anchor[1]) * screen_h
                target_x = int(screen_anchor[0] + dx)
                target_y = int(screen_anchor[1] + dy)

                # clamp to screen
                target_x = max(0, min(screen_w - 1, target_x))
                target_y = max(0, min(screen_h - 1, target_y))

                pos_buffer.append((target_x, target_y))
                avg_x = int(sum(p[0] for p in pos_buffer) / len(pos_buffer))
                avg_y = int(sum(p[1] for p in pos_buffer) / len(pos_buffer))

                # Only move if outside small deadzone to avoid jitter
                cur_px = pyautogui.position()
                if abs(avg_x - cur_px.x)/screen_w > MAX_CURSOR_DEADZONE or \
                   abs(avg_y - cur_px.y)/screen_h > MAX_CURSOR_DEADZONE:
                    pyautogui.moveTo(avg_x, avg_y, duration=0)

            # -------- Left Click (Index + Thumb) --------
            if d_idx_thumb < pinch_thresh:
                if not left_clicked:
                    pyautogui.click(button='left')
                    left_clicked = True
                    action = "Left Click"
            else:
                left_clicked = False

            # -------- Right Click (Middle + Thumb) --------
            if d_mid_thumb < pinch_thresh:
                if not right_clicked:
                    pyautogui.click(button="right")
                    right_clicked = True
                    action = "Right Click"
            else:
                right_clicked = False

            # -------- Two-finger Scroll (Index + Middle) --------
            SCROLL_THRESHOLD = pinch_thresh * 1.3

            if d_idx_mid < SCROLL_THRESHOLD:
                mid_y = (index_px[1] + middle_px[1]) // 2

                if scroll_ref is None:
                    scroll_ref = mid_y

                delta = mid_y - scroll_ref
                if abs(delta) > 8:
                    pyautogui.scroll(int(-delta * 1.2))
                    scroll_ref = mid_y

                action = "Scrolling"
            else:
                scroll_ref = None

            # Debug info
            cv2.putText(frame, f"Index-Thumb: {int(d_idx_thumb)}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(0,255,0),2)
            cv2.putText(frame, f"Mid-Thumb: {int(d_mid_thumb)}", (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(0,255,0),2)
            cv2.putText(frame, f"Index-Mid: {int(d_idx_mid)}", (10,90), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(0,255,0),2)

        else:
            # hand lost -> clear anchors so next re-entry will re-anchor
            hand_active = False
            hand_anchor = None
            screen_anchor = None
            pos_buffer.clear()
            scroll_ref = None

        # FPS
        cur = time.time()
        fps = 1/(cur-prev_time) if prev_time else 0
        prev_time = cur
        cv2.putText(frame, f"FPS: {int(fps)}", (w-150,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,(255,255,0),2)
        cv2.putText(frame, f"Action: {action}", (10,h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8,(200,200,200),2)

        cv2.imshow("Hand Mouse - Press Q to Quit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass

cap.release()
cv2.destroyAllWindows()
# filepath: