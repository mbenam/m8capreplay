import serial
import time
import threading
import sys

# CONFIGURATION
# Replace with your Teensy Serial Port (e.g. 'COM5' or '/dev/ttyACM0')
M8_PORT = 'COM4'  
BAUD_RATE = 115200
OUTPUT_FILE = 'm8_nav_test.bin'

# M8 Input Bitmasks (Derived from src/input.c)
KEY_EDIT   = 0x01 # Alt
KEY_OPT    = 0x02 # Ctrl
KEY_RIGHT  = 0x04
KEY_START  = 0x08 # Space
KEY_SELECT = 0x10 # Shift
KEY_DOWN   = 0x20
KEY_UP     = 0x40
KEY_LEFT   = 0x80

# Combined Masks for Navigation
NAV_RIGHT = KEY_SELECT | KEY_RIGHT # Go Deeper (Song -> Chain -> Phrase)
NAV_LEFT  = KEY_SELECT | KEY_LEFT  # Go Back   (Phrase -> Chain -> Song)

# Flag to stop the recording thread
recording = True

def reader_thread(ser, filename):
    """
    Constantly reads display data from M8 and saves it to file.
    """
    global recording
    print(f" > Recording started: {filename}")
    with open(filename, 'wb') as f:
        while recording:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                f.write(data)
                f.flush()
            else:
                time.sleep(0.002)
    print("\n > Recording saved.")

def send_key(ser, mask, duration=0.1):
    """
    Simulates a key press:
    1. Send 'C' + mask (Press)
    2. Wait duration
    3. Send 'C' + 0 (Release)
    """
    # Press
    cmd = b'C' + bytes([mask])
    ser.write(cmd)
    time.sleep(duration)
    
    # Release
    ser.write(b'C' + b'\x00')
    time.sleep(0.1) # Debounce/Pause between actions

def main():
    global recording
    
    try:
        ser = serial.Serial(M8_PORT, BAUD_RATE, timeout=0.1)
    except Exception as e:
        print(f"Error opening port: {e}")
        sys.exit(1)

    print(f"Connected to M8 on {M8_PORT}")

    # 1. Handshake
    print(" > Sending Handshake (D, E, R)...")
    ser.write(b'D')
    time.sleep(0.05)
    ser.write(b'E')
    time.sleep(0.05)
    ser.write(b'R')
    time.sleep(0.5) 

    # 2. Start Recording in background
    t = threading.Thread(target=reader_thread, args=(ser, OUTPUT_FILE))
    t.start()

    # 3. Perform Automated Actions
    try:
        print(" > Action: Move Cursor Right")
        send_key(ser, KEY_RIGHT)
        time.sleep(1)

        print(" > Action: Play (Space)")
        send_key(ser, KEY_START)
        
        # Let it play for a moment to establish waveforms
        print(" > Capturing waveform (Song View)...")
        time.sleep(3)

        # --- Drill Down ---
        print(" > Action: Go to Chain View (Select + Right)")
        send_key(ser, NAV_RIGHT)
        time.sleep(2)

        print(" > Action: Go to Phrase View (Select + Right)")
        send_key(ser, NAV_RIGHT)
        time.sleep(2)

        print(" > Action: Go to Instrument View (Select + Right)")
        send_key(ser, NAV_RIGHT)
        time.sleep(2)

        # --- Go Back Up ---
        print(" > Action: Back to Phrase View (Select + Left)")
        send_key(ser, NAV_LEFT)
        time.sleep(1.5)

        print(" > Action: Back to Chain View (Select + Left)")
        send_key(ser, NAV_LEFT)
        time.sleep(1.5)

        print(" > Action: Back to Song View (Select + Left)")
        send_key(ser, NAV_LEFT)
        time.sleep(1.5)

        # Stop Playing
        print(" > Action: Stop (Space)")
        send_key(ser, KEY_START)
        time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nInterrupted by user!")
    finally:
        # Cleanup
        recording = False
        t.join()
        ser.close()
        print("Done.")

if __name__ == "__main__":
    main()