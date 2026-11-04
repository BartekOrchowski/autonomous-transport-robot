
import cv2
import subprocess
from pathlib import Path

# Folder na zdjęcia
image_dir = Path(__file__).resolve().parent / "images"
image_dir.mkdir(exist_ok=True)

image_path = image_dir / "aruco_raw.jpg"
result_path = image_dir / "aruco_detected.jpg"

# 1. Wykonanie zdjęcia kamerą Raspberry Pi
subprocess.run([
    "rpicam-still",
    "--nopreview",
    "--timeout", "2000",
    "--width", "1640",
    "--height", "1232",
    "--output", str(image_path)
], check=True)

# 2. Wczytanie zdjęcia
image = cv2.imread(str(image_path))

if image is None:
    raise RuntimeError("Nie udało się wczytać zdjęcia")

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# 3. Konfiguracja detektora ArUco
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_50)
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(dictionary, parameters)

# 4. Wykrywanie znaczników
corners, ids, rejected = detector.detectMarkers(gray)

# 5. Wyświetlenie wyników
if ids is not None:
    detected_ids = sorted(ids.flatten().tolist())

    print("Wykryte znaczniki ArUco:", detected_ids)
    print("Liczba znaczników:", len(detected_ids))

    cv2.aruco.drawDetectedMarkers(image, corners, ids)
else:
    print("Nie wykryto żadnych znaczników ArUco")

# 6. Zapis zdjęcia z zaznaczonymi znacznikami
cv2.imwrite(str(result_path), image)
print("Zapisano:", result_path)
