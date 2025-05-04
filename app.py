import cv2
import mediapipe as mp
import numpy as np
import math
import threading
import time
import pyautogui
from flask import Flask, render_template, Response, jsonify, request

app = Flask(__name__, template_folder='templates', static_folder='static')

# Global variables
cap = None
hand_detector = None
drawing_utils = None
screen_w, screen_h = pyautogui.size()
is_running = False
is_tracking = False
click_distance_threshold = 20
frame_lock = threading.Lock()
processed_frame = None

# Initialize MediaPipe Hands once
def initialize_hand_tracking():
    global hand_detector, drawing_utils
    if hand_detector is None:
        hand_detector = mp.solutions.hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        drawing_utils = mp.solutions.drawing_utils

# Start camera and processing thread
def start_camera():
    global cap, is_running
    if cap is None:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return False
        is_running = True
        threading.Thread(target=process_frames, daemon=True).start()
        return True
    return False

# Stop camera
def stop_camera():
    global cap, is_running
    is_running = False
    if cap is not None:
        cap.release()
        cap = None

# Process frames in background
def process_frames():
    global cap, hand_detector, drawing_utils, is_running, processed_frame, is_tracking

    last_left_click_time = 0
    last_right_click_time = 0
    debounce_time = 0.7

    while is_running:
        if cap is None:
            time.sleep(0.05)
            continue

        success, frame = cap.read()
        if not success:
            time.sleep(0.05)
            continue

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hand_detector.process(rgb_frame)
        frame_h, frame_w, _ = frame.shape
        processed = frame.copy()

        if result.multi_hand_landmarks:
            for hand in result.multi_hand_landmarks:
                drawing_utils.draw_landmarks(processed, hand, mp.solutions.hands.HAND_CONNECTIONS)
                landmarks = hand.landmark

                if is_tracking:
                    # Index finger for cursor
                    index_x = int(landmarks[8].x * frame_w)
                    index_y = int(landmarks[8].y * frame_h)
                    cv2.circle(processed, (index_x, index_y), 8, (0, 0, 255), -1)
                    screen_x = screen_w / frame_w * index_x
                    screen_y = screen_h / frame_h * index_y
                    pyautogui.moveTo(screen_x, screen_y)

                    # Thumb, middle, ring fingers
                    thumb_x = int(landmarks[4].x * frame_w)
                    thumb_y = int(landmarks[4].y * frame_h)
                    mid_x = int(landmarks[12].x * frame_w)
                    mid_y = int(landmarks[12].y * frame_h)
                    ring_x = int(landmarks[16].x * frame_w)
                    ring_y = int(landmarks[16].y * frame_h)

                    cv2.circle(processed, (thumb_x, thumb_y), 8, (0, 255, 0), -1)
                    cv2.circle(processed, (mid_x, mid_y), 8, (255, 0, 0), -1)
                    cv2.circle(processed, (ring_x, ring_y), 8, (255, 0, 0), -1)

                    # Left click detection (middle + thumb)
                    dist_mid_thumb = math.hypot(mid_x - thumb_x, mid_y - thumb_y)
                    current_time = time.time()
                    if dist_mid_thumb < click_distance_threshold and (current_time - last_left_click_time) > debounce_time:
                        pyautogui.click()
                        last_left_click_time = current_time
                        cv2.putText(processed, "LEFT CLICK", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                    # Right click detection (ring + thumb)
                    dist_ring_thumb = math.hypot(ring_x - thumb_x, ring_y - thumb_y)
                    if dist_ring_thumb < click_distance_threshold and (current_time - last_right_click_time) > debounce_time:
                        pyautogui.rightClick()
                        last_right_click_time = current_time
                        cv2.putText(processed, "RIGHT CLICK", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        with frame_lock:
            processed_frame = processed.copy()

        time.sleep(0.01)

# Video streaming generator
def generate_frames():
    global processed_frame, frame_lock
    while True:
        with frame_lock:
            if processed_frame is None:
                frame = np.zeros((480, 640, 3), np.uint8)
            else:
                frame = processed_frame.copy()

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.01)

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/start_camera', methods=['POST'])
def api_start_camera():
    initialize_hand_tracking()
    success = start_camera()
    if success:
        return jsonify({'status': 'success', 'message': 'Camera started'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to start camera'})

@app.route('/api/stop_camera', methods=['POST'])
def api_stop_camera():
    stop_camera()
    return jsonify({'status': 'success', 'message': 'Camera stopped'})

@app.route('/api/enable_tracking', methods=['POST'])
def api_enable_tracking():
    global is_tracking
    is_tracking = True
    return jsonify({'status': 'success', 'message': 'Tracking enabled'})

@app.route('/api/disable_tracking', methods=['POST'])
def api_disable_tracking():
    global is_tracking
    is_tracking = False
    return jsonify({'status': 'success', 'message': 'Tracking disabled'})

@app.route('/api/set_click_distance', methods=['POST'])
def api_set_click_distance():
    global click_distance_threshold
    data = request.json
    if 'distance' in data:
        click_distance_threshold = int(data['distance'])
        return jsonify({'status': 'success', 'message': f'Click distance set to {click_distance_threshold}'})
    return jsonify({'status': 'error', 'message': 'No distance provided'})

# Cleanup on exit
import atexit
@atexit.register
def cleanup():
    global cap
    if cap is not None:
        cap.release()

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
