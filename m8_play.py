import serial
import time
import sys
import os

# --- CONFIGURATION ---
# Windows: 'COMx' (e.g., COM9)
# Mac/Linux: '/dev/ttyACMx' or '/dev/cu.usbmodem...'
RP2350_PORT = 'COM9' 
BAUD_RATE = 115200

# The file you captured using m8_capture_auto.py
INPUT_FILE = 'm8_nav_test.bin'

# Flow Control Tuning
# The RP2350 USB buffer is small (usually 64-1024 bytes).
# We break the file into small chunks and pause slightly to prevent 
# overflowing the RP2350 while it is busy drawing pixels.
CHUNK_SIZE = 64 
DELAY_PER_CHUNK = 0.002 # 2ms delay per 64 bytes

def main():
    # 1. Check Input File
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File '{INPUT_FILE}' not found.")
        print("Run 'm8_capture_auto.py' with your Teensy first to generate it.")
        sys.exit(1)

    # 2. Open Serial Port
    try:
        ser = serial.Serial(RP2350_PORT, BAUD_RATE)
        print(f"Connected to RP2350 on {RP2350_PORT}")
    except serial.SerialException:
        print(f"Error: Could not open {RP2350_PORT}.")
        print("Check your connection and make sure the RP2350 is flashed.")
        sys.exit(1)

    file_size = os.path.getsize(INPUT_FILE)
    print(f"Streaming {INPUT_FILE} ({file_size} bytes)...")
    print("Watch your RP2350 screen!")

    bytes_sent = 0
    start_time = time.time()

    try:
        with open(INPUT_FILE, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                ser.write(chunk)
                bytes_sent += len(chunk)
                
                # Progress Bar
                percent = (bytes_sent / file_size) * 100
                sys.stdout.write(f"\rProgress: [{percent:5.1f}%] - {bytes_sent} bytes sent")
                sys.stdout.flush()

                # Simulated Flow Control
                time.sleep(DELAY_PER_CHUNK)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"\nError during streaming: {e}")
    finally:
        ser.close()
        elapsed = time.time() - start_time
        print(f"\n\nDone! Streamed in {elapsed:.1f} seconds.")

if __name__ == "__main__":
    main()
