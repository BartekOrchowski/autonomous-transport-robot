
import cv2
import numpy as np
import subprocess

# Camera settings
WIDTH = 640
HEIGHT = 480
FPS = 5

# YUV420 frame size
Y_SIZE = WIDTH * HEIGHT
FRAME_SIZE = Y_SIZE * 3 // 2

# ArUco detector
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_50)
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(dictionary, parameters)

# Start camera stream
camera = subprocess.Popen(
    [
        "rpicam-vid",
        "--timeout", "0",
        "--nopreview",
        "--codec", "yuv420",
        "--width", str(WIDTH),
        "--height", str(HEIGHT),
        "--framerate", str(FPS),
        "--output", "-"
    ],
    stdout=subprocess.PIPE
)

print("ArUco detection started")
print("Press Ctrl+C to stop")

previous_ids = None

try:
    while True:
        # Read one frame from camera
        frame = camera.stdout.read(FRAME_SIZE)

        if len(frame) != FRAME_SIZE:
            print("Camera stream interrupted")
            break

        # Extract grayscale (Y) channel
        gray = np.frombuffer(
            frame, dtype=np.uint8, count=Y_SIZE
        ).reshape(HEIGHT, WIDTH)

        # Detect ArUco markers
        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is not None:
            detected_ids = tuple(sorted(ids.flatten().tolist()))
        else:
            detected_ids = ()

        # Print only when detection changes
        if detected_ids != previous_ids:
            if detected_ids:
                print("Detected ArUco:", detected_ids, flush=True)
            else:
                print("No marker detected", flush=True)

            previous_ids = detected_ids

except KeyboardInterrupt:
    print("\nDetection stopped")

finally:
    camera.terminate()
    camera.stdout.close()

    try:
        camera.wait(timeout=3)
    except subprocess.TimeoutExpired:
        camera.kill()
        camera.wait()
