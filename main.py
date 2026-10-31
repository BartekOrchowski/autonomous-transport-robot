
import subprocess
import time
from datetime import datetime
from pathlib import Path

INTERVAL = 10  # Czas pomiędzy rozpoczęciem zdjęć [s]
IMAGE_DIR = Path(__file__).resolve().parent / "images"

IMAGE_DIR.mkdir(exist_ok=True)

print("Robot transportowy - START")
print("Kamera: zdjęcie co 10 sekund")
print("Zatrzymanie: Ctrl+C")

try:
    while True:
        start = time.monotonic()

        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.jpg")
        image_path = IMAGE_DIR / filename

        subprocess.run(
            [
                "rpicam-still",
                "--nopreview",
                "--timeout", "1000",
                "--width", "640",
                "--height", "480",
                "--output", str(image_path),
            ],
            check=True,
        )

        print(f"Zapisano: {image_path.name}", flush=True)

        elapsed = time.monotonic() - start
        time.sleep(max(0, INTERVAL - elapsed))

except KeyboardInterrupt:
    print("\nZatrzymano wykonywanie zdjęć.")
