ProjectorBlocker

Projector Face Protector

This Python project tracks a lecturer’s face using a webcam and places a floating black window over it to block projector light during presentations.

Features

- Real-time face detection using MediaPipe
- Adjustable projection corners using mouse
- Supports horizontal and vertical camera flipping
- Saves and loads calibration data (projection corners)
- Adjustable black window opacity
- Simple keyboard controls

Requirements

- Python 3.8+
- Install dependencies:
  pip install opencv-python mediapipe numpy scikit-image

Usage
Run the script:
python script.py [options]

Available Options:

- --cam : Camera index (default: 0)
- --hflip : Flip camera image horizontally
- --vflip : Flip camera image vertically
- --opacity : Face window opacity from 0.0 to 1.0 (default: 1.0)
- --corners : JSON file path for saving/loading projection corners (default: projection_corners.json)

Controls

- Drag yellow corner markers with mouse to adjust projection area
- Press 's' to save corners to file
- Press 'h' to toggle horizontal flip
- Press 'q' or close the window to quit

Corners File
The corners file is a JSON file with four 2D coordinates, e.g.:
[
[100.0, 100.0],
[400.0, 100.0],
[400.0, 400.0],
[100.0, 400.0]
]
These represent the corners of the projected area to transform face positions.

Notes

- Works on Windows and Linux
- Designed to help lecturers avoid projector glare by covering their face with a dynamic window
