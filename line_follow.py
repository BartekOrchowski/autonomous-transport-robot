
import cv2
import numpy as np
import subprocess
import time
from pathlib import Path

# Camera settings
WIDTH = 640
HEIGHT = 480
FPS = 5

Y_SIZE = WIDTH * HEIGHT
FRAME_SIZE = Y_SIZE * 3 // 2

# Region of interest - lower part of the image
ROI_TOP = int(HEIGHT * 0.65)
ROI_BOTTOM = int(HEIGHT * 0.90)

# Line detection settings
MIN_AREA = 250
TOLERANCE = 20

# Folder for preview images
image_dir = Path(__file__).resolve().parent / "images"
image_dir.mkdir(exist_ok=True)

# Start camera
camera = subprocess.Popen(
    [
        "rpicam-vid",
        "--timeout", "0",
        "--nopreview",
        "--codec", "yuv420",
        "--mode", "1640:1232",
        "--width", str(WIDTH),
        "--height", str(HEIGHT),
        "--framerate", str(FPS),
        "--output", "-"
    ],
    stdout=subprocess.PIPE
)

print("Line following started")
print("Press Ctrl+C to stop")

last_output = 0
last_preview = 0

try:
    while True:

        # 1. Read camera frame
        frame = camera.stdout.read(FRAME_SIZE)

        if len(frame) != FRAME_SIZE:
            print("Camera stream interrupted")
            break

        # 2. Extract grayscale image
        gray = np.frombuffer(
            frame, dtype=np.uint8, count=Y_SIZE
        ).reshape(HEIGHT, WIDTH)

        # 3. Select region of interest
        roi = gray[ROI_TOP:ROI_BOTTOM, :]

        # 4. Separate dark line from light background
        blurred = cv2.GaussianBlur(roi, (5, 5), 0)

        _, mask = cv2.threshold(
            blurred,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # Remove small noise
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, kernel
        )

        # 5. Find dark contours
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Ignore very small objects
        contours = [
            c for c in contours
            if cv2.contourArea(c) > MIN_AREA
        ]

        # Prepare preview image
        preview = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        camera_center = WIDTH // 2

        cv2.line(
            preview,
            (camera_center, 0),
            (camera_center, HEIGHT),
            (255, 0, 0),
            2
        )

        cv2.rectangle(
            preview,
            (0, ROI_TOP),
            (WIDTH - 1, ROI_BOTTOM),
            (0, 255, 255),
            2
        )

        # 6. Calculate line position
        if contours:

            # Choose largest dark contour
            line = max(contours, key=cv2.contourArea)

            # Calculate centroid
            M = cv2.moments(line)

            if M["m00"] > 0:
                x_line = int(M["m10"] / M["m00"])
                y_line = int(M["m01"] / M["m00"]) + ROI_TOP

                # Calculate error
                error = x_line - camera_center

                # Determine suggested direction
                if error < -TOLERANCE:
                    direction = "LEFT"
                elif error > TOLERANCE:
                    direction = "RIGHT"
                else:
                    direction = "STRAIGHT"

                message = f"{direction} | error = {error:+d} px"

                # Draw detected line
                shifted_line = line.copy()
                shifted_line[:, :, 1] += ROI_TOP

                cv2.drawContours(
                    preview,
                    [shifted_line],
                    -1,
                    (0, 255, 0),
                    2
                )

                # Draw center of detected line
                cv2.circle(
                    preview,
                    (x_line, y_line),
                    6,
                    (0, 0, 255),
                    -1
                )

            else:
                message = "LINE LOST"

        else:
            message = "LINE LOST"

        now = time.monotonic()

        # 7. Print result once per second
        if now - last_output >= 1:
            print(message, flush=True)
            last_output = now

        # 8. Save preview every 2 seconds
        if now - last_preview >= 2:
            cv2.putText(
                preview,
                message,
                (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.imwrite(
                str(image_dir / "line_preview.jpg"),
                preview
            )

            cv2.imwrite(
                str(image_dir / "line_mask.jpg"),
                mask
            )

            last_preview = now

except KeyboardInterrupt:
    print("\nLine following stopped")

finally:
    camera.terminate()
    camera.stdout.close()

    try:
        camera.wait(timeout=3)
    except subprocess.TimeoutExpired:
        camera.kill()
        camera.wait()
