
import subprocess
import time
import spidev


class RFIDReader:
    def __init__(self):
        # RST -> GPIO2 (physical pin 3)
        subprocess.run(
            ["pinctrl", "set", "2", "op", "dh"],
            check=True
        )
        time.sleep(0.05)

        # SPI0 CE0 -> GPIO8 (physical pin 24)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 1_000_000
        self.spi.mode = 0

        self.write(0x01, 0x0F)  # Software reset
        time.sleep(0.1)

        # Timer and communication settings
        self.write(0x2A, 0x8D)
        self.write(0x2B, 0x3E)
        self.write(0x2C, 0x00)
        self.write(0x2D, 30)
        self.write(0x15, 0x40)
        self.write(0x11, 0x3D)

        # Enable antenna
        self.set_bits(0x14, 0x03)

    def write(self, reg, value):
        self.spi.xfer2([(reg << 1) & 0x7E, value])

    def read(self, reg):
        return self.spi.xfer2(
            [((reg << 1) & 0x7E) | 0x80, 0]
        )[1]

    def set_bits(self, reg, mask):
        self.write(reg, self.read(reg) | mask)

    def transceive(self, data, last_bits=0):
        # Clear interrupts and FIFO
        self.write(0x01, 0x00)
        self.write(0x04, 0x7F)
        self.write(0x0A, 0x80)

        for byte in data:
            self.write(0x09, byte)

        # Start RF communication
        self.write(0x0D, last_bits)
        self.write(0x01, 0x0C)
        self.set_bits(0x0D, 0x80)

        deadline = time.monotonic() + 0.1

        while time.monotonic() < deadline:
            irq = self.read(0x04)

            if irq & 0x30:
                break

            if irq & 0x01:
                return None
        else:
            return None

        self.write(0x0D, last_bits)

        if self.read(0x06) & 0x1B:
            return None

        count = self.read(0x0A)

        if count == 0 or count > 16:
            return None

        valid_bits = self.read(0x0C) & 0x07
        result = [self.read(0x09) for _ in range(count)]

        bit_count = (count - 1) * 8
        bit_count += valid_bits if valid_bits else 8

        return result, bit_count

    def crc(self, data):
        self.write(0x01, 0x00)
        self.write(0x05, 0x04)
        self.write(0x0A, 0x80)

        for byte in data:
            self.write(0x09, byte)

        self.write(0x01, 0x03)

        deadline = time.monotonic() + 0.1

        while time.monotonic() < deadline:
            if self.read(0x05) & 0x04:
                return [self.read(0x22), self.read(0x21)]

        return None

    def read_uid(self):
        # Wake up a nearby ISO14443A card
        response = self.transceive([0x52], 7)

        if response is None or response[1] != 16:
            return None

        uid = []

        # Support 4, 7 and 10-byte UIDs
        for level in (0x93, 0x95, 0x97):
            response = self.transceive([level, 0x20])

            if response is None:
                return None

            data, bits = response

            if len(data) != 5 or bits != 40:
                return None

            # Verify BCC checksum
            bcc = data[0] ^ data[1] ^ data[2] ^ data[3]

            if bcc != data[4]:
                return None

            # Select card at this cascade level
            select = [level, 0x70] + data
            checksum = self.crc(select)

            if checksum is None:
                return None

            response = self.transceive(select + checksum)

            if response is None or response[1] != 24:
                return None

            sak = response[0][0]

            # 0x88 is the cascade tag, not UID data
            if data[0] == 0x88:
                uid.extend(data[1:4])
            else:
                uid.extend(data[:4])

            if not (sak & 0x04):
                return uid

        return None

    def close(self):
        self.spi.close()


def main():
    reader = RFIDReader()

    version = reader.read(0x37)
    print(f"RFID chip version: 0x{version:02X}", flush=True)

    if version in (0x00, 0xFF):
        reader.close()
        raise RuntimeError("No communication with RFID reader")

    print("RFID reader ready")
    print("Place a card near the reader")
    print("Press Ctrl+C to stop")

    last_uid = None

    try:
        while True:
            uid = reader.read_uid()

            if uid is not None:
                uid_hex = ":".join(f"{byte:02X}" for byte in uid)

                if uid_hex != last_uid:
                    print(f"Card detected | UID: {uid_hex}", flush=True)
                    last_uid = uid_hex
            else:
                last_uid = None

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nRFID test stopped")

    finally:
        reader.close()


if __name__ == "__main__":
    main()
