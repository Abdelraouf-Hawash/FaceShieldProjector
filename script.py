import cv2
import mediapipe as mp
import tkinter as tk
import ctypes
import threading
import sys
import os
import json
from skimage.transform import ProjectiveTransform
import numpy as np
import argparse

# === Command-line Arguments ===
parser = argparse.ArgumentParser(description="Face window projection with camera input")
parser.add_argument("--cam", type=int, default=0, help="Camera ID (default: 0)")
parser.add_argument("--hflip", action="store_true", help="Flip camera image horizontally")
parser.add_argument("--vflip", action="store_true", help="Flip camera image vertically")
parser.add_argument("--opacity", type=float, default=1.0, help="Face window opacity (0.0 to 1.0)")
parser.add_argument("--corners", type=str, default="./projection_corners.json", help="Path to corners file")
args = parser.parse_args()

# === Face Detection Setup ===
mp_face = mp.solutions.face_detection
face_detection = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.6)
mp_drawing = mp.solutions.drawing_utils

# === Tkinter GUI Setup ===
root = tk.Tk()
root.withdraw()  # Hide main window

# === Get Screen Size ===
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
screen_corners = np.array([[0, 0], [screen_w, 0], [screen_w, screen_h], [0, screen_h]])

# === Projection Area Setup ===
projection_corners = np.array([[100, 100], [400, 100], [400, 400], [100, 400]], dtype=np.float32)

# === Load saved corner positions (if they exist) ===
def load_projection_corners(path):
    global projection_corners
    if os.path.exists(path):
        with open(path, "r") as f:
            projection_corners[:] = np.array(json.load(f), dtype=np.float32)

# === Save current projection corners ===
def save_projection_corners(path):
    with open(path, "w") as f:
        json.dump(projection_corners.tolist(), f)

# Load at startup
load_projection_corners(args.corners)

# === Face Window Handling ===
face_windows = {}

# Corner dragging state
selected_corner_index = None
dragging = False

# === Hide window from taskbar (Windows only) ===
def hide_from_taskbar(hwnd):
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style | WS_EX_TOOLWINDOW)

# === Create a black window to block the projector light ===
def create_face_window():
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.configure(bg="black")
    win.attributes("-topmost", True)
    win.attributes("-alpha", max(0.0, min(args.opacity, 1.0)))  # Control opacity
    win.geometry("1x1+-100+-100")  # Hide off-screen initially
    if sys.platform.startswith("win"):
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        hide_from_taskbar(hwnd)
    return win

# === Update face-blocking windows ===
def update_face_windows(face_boxes):
    # Destroy unused windows
    while len(face_windows) > len(face_boxes):
        _, win = face_windows.popitem()
        win.destroy()

    for i, (x, y, w, h) in enumerate(face_boxes):
        if i not in face_windows:
            face_windows[i] = create_face_window()
        face_windows[i].geometry(f"{w}x{h}+{x}+{y}")

# === Hide all face-blocking windows ===
def hide_all_windows():
    for win in face_windows.values():
        win.geometry("1x1+-100+-100")

# === Map points using projective transform ===
def ProjTranseform(src_corners, dst_corners, src_point):
    transformer = ProjectiveTransform()
    transformer.estimate(src_corners, dst_corners)
    dst_point = transformer(src_point)
    return dst_point

# === Handle mouse events for corner adjustment ===
def mouse_event_handler(event, x, y, flags, param):
    global selected_corner_index, dragging, projection_corners
    if event == cv2.EVENT_LBUTTONDOWN:
        for i, corner in enumerate(projection_corners):
            if np.linalg.norm([x - corner[0], y - corner[1]]) < 15:
                selected_corner_index = i
                dragging = True
                break
    elif event == cv2.EVENT_MOUSEMOVE and dragging:
        if selected_corner_index is not None:
            projection_corners[selected_corner_index] = [x, y]
    elif event == cv2.EVENT_LBUTTONUP:
        dragging = False
        selected_corner_index = None

# === Camera Loop ===
def camera_loop(cam_id):
    cap = cv2.VideoCapture(cam_id)
    cv2.namedWindow("Camera View")
    cv2.setMouseCallback("ProjectorBlocker", mouse_event_handler)

    show_face_windows = True  # Toggle with 'h'

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Flip if needed
        if args.hflip:
            frame = cv2.flip(frame, 1)
        if args.vflip:
            frame = cv2.flip(frame, 0)

        # Face detection
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb)

        # Draw adjustable corner markers
        for idx, c in enumerate(projection_corners):
            cv2.circle(frame, (int(c[0]), int(c[1])), 6, (255, 255, 0), -1)
            cv2.putText(frame, str(idx + 1), (int(c[0]) + 5, int(c[1]) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        frame_h, frame_w = frame.shape[:2]
        face_boxes = []

        if results.detections:
            for det in results.detections:
                mp_drawing.draw_detection(frame, det)
                bbox = det.location_data.relative_bounding_box

                # Transform bounding box to screen space
                TL = ProjTranseform(projection_corners, screen_corners,
                                    np.array([[bbox.xmin * frame_w, bbox.ymin * frame_h]]))
                BR = ProjTranseform(projection_corners, screen_corners,
                                    np.array([[(bbox.xmin + bbox.width) * frame_w,
                                               (bbox.ymin + bbox.height) * frame_h]]))

                x, y = int(TL[0][0]), int(TL[0][1])
                w = int(BR[0][0] - TL[0][0])
                h = int(BR[0][1] - TL[0][1])
                face_boxes.append((x, y, w, h))

            if show_face_windows:
                root.after(0, update_face_windows, face_boxes)
            else:
                root.after(0, hide_all_windows)
        else:
            root.after(0, hide_all_windows)

        # Show camera
        cv2.imshow("Camera View", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('h'):
            show_face_windows = not show_face_windows
        elif key == ord('s'):
            save_projection_corners(args.corners)
            print(f"[INFO] Projection corners saved to {args.corners}")

        # Exit if user closes the window
        if cv2.getWindowProperty("Camera View", cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()
    root.destroy()

# === Start Camera Thread ===
threading.Thread(target=camera_loop, args=(args.cam,), daemon=True).start()

# === Tkinter Main Loop ===
root.mainloop()
