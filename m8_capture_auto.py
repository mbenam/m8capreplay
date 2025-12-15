import serial
import time
import threading
import sys

# CONFIGURATION
# Replace with your Teensy Serial Port (e.g. 'COM5' or '/dev/ttyACM0')
M8_PORT = 'COM4'  
BAUD_RATE = 115200
OUTPUT_FILE = 'm8_nav_test.bin'

# M8 Input Bitmasks
KEY_EDIT   = 0x01 # Alt
KEY_OPT    = 0x02 # Ctrl
KEY_RIGHT  = 0x04
KEY_START  = 0x08 # Space
KEY_SELECT = 0x10 # Shift
KEY_DOWN   = 0x20
KEY_UP     = 0x40
KEY_LEFT   = 0x80

NAV_RIGHT = KEY_SELECT | KEY_RIGHT 
NAV_LEFT  = KEY_SELECT | KEY_LEFT
NAV_DOWN  = KEY_SELECT | KEY_DOWN
NAV_UP    = KEY_SELECT | KEY_UP  

# Thread control flags
recording = True

# THROUGHPUT COUNTERS (Bytes)
rx_bytes_accumulated = 0
tx_bytes_accumulated = 0

def m8_write(ser, data):
    """
    Wrapper for serial.write to track TX throughput.
    """
    global tx_bytes_accumulated
    if ser.is_open:
        count = ser.write(data)
        tx_bytes_accumulated += count
        return count
    return 0

def throughput_monitor_thread():
    """
    Calculates and prints Mbps every 1 second.
    """
    global rx_bytes_accumulated, tx_bytes_accumulated, recording
    
    print(f" > Throughput Monitor Started...")
    
    while recording:
        # Reset counters for the new interval
        current_rx = rx_bytes_accumulated
        current_tx = tx_bytes_accumulated
        rx_bytes_accumulated = 0
        tx_bytes_accumulated = 0
        
        # Sleep for exactly 1 second
        time.sleep(1.0)
        
        # Calculate Mbps: (Bytes * 8 bits) / 1,000,000
        rx_mbps = (current_rx * 8) / 1_000_000.0
        tx_mbps = (current_tx * 8) / 1_000_000.0
        
        # Print status (Overwrites previous line slightly for cleaner log, or just new lines)
        # Using simple print to keep history visible
        print(f"[Mbps] RX (Display/Audio): {rx_mbps:.4f} Mbps | TX (Controls): {tx_mbps:.4f} Mbps")

def reader_thread(ser, filename):
    """
    Constantly reads display data from M8, saves it, and counts bytes.
    """
    global recording, rx_bytes_accumulated
    print(f" > Recording started: {filename}")
    
    # We use a larger buffer size request to try and drain the OS buffer faster
    READ_CHUNK_SIZE = 4096 
    
    with open(filename, 'wb') as f:
        while recording:
            if ser.in_waiting > 0:
                # Read whatever is available
                data = ser.read(ser.in_waiting)
                
                # Update Counter
                rx_bytes_accumulated += len(data)
                
                # Write to file
                f.write(data)
                # f.flush() # Flushing every write slows down Python; let OS handle buffering for speed
            else:
                time.sleep(0.001) # Short sleep to prevent CPU hogging
    print("\n > Recording saved.")

def send_key(ser, mask, duration=0.1):
    # Press
    cmd = b'C' + bytes([mask])
    m8_write(ser, cmd)
    time.sleep(duration)
    
    # Release
    m8_write(ser, b'C' + b'\x00')
    time.sleep(0.1) 

def main():
    global recording
    
    try:
        # Note: rtscts=False, dsrdtr=False often helps with raw Teensy throughput
        ser = serial.Serial(M8_PORT, BAUD_RATE, timeout=0.1)
    except Exception as e:
        print(f"Error opening port: {e}")
        sys.exit(1)

    print(f"Connected to M8 on {M8_PORT}")

    # 1. Start Throughput Monitor
    t_stats = threading.Thread(target=throughput_monitor_thread)
    t_stats.daemon = True # Kill thread if main exits
    t_stats.start()

    # 2. Handshake
    print(" > Sending Handshake (D, E, R)...")
    m8_write(ser, b'D')
    time.sleep(0.05)
    m8_write(ser, b'E')
    time.sleep(0.05)
    m8_write(ser, b'R')
    time.sleep(0.5) 

    # 3. Start Recording in background
    t_reader = threading.Thread(target=reader_thread, args=(ser, OUTPUT_FILE))
    t_reader.start()

    # 4. Perform Automated Actions
    try:
        print(" > Action: Move Cursor Right")
        send_key(ser, KEY_RIGHT)
        time.sleep(1)

        print(" > Action: Play (Space)")
        send_key(ser, KEY_START)
        
        print(" > Capturing waveform (Song View)...")
        time.sleep(3)

        # --- Drill Down ---
        print(" > Action: Go to Chain View")
        send_key(ser, NAV_RIGHT)
        time.sleep(2)

        print(" > Action: Go to Phrase View")
        send_key(ser, NAV_RIGHT)
        time.sleep(2)

        print(" > Action: Go to Instrument View")
        send_key(ser, NAV_RIGHT)
        time.sleep(2)

        # --- Go Back Up ---
        print(" > Action: Back to Phrase View")
        send_key(ser, NAV_LEFT)
        time.sleep(1.5)

        print(" > Action: Back to Chain View")
        send_key(ser, NAV_LEFT)
        time.sleep(1.5)

        print(" > Action: Back to Song View")
        send_key(ser, NAV_LEFT)
        time.sleep(1.5)

        print(" > Action: Go to EQqualizer View")
        send_key(ser, NAV_DOWN)
        time.sleep(3)

        print(" > Action: Go Back to Song View")
        send_key(ser, NAV_UP)
        time.sleep(1.5)

        # Stop Playing
        print(" > Action: Stop")
        send_key(ser, KEY_START)
        time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nInterrupted by user!")
    finally:
        recording = False
        t_reader.join()
        ser.close()
        print("Done.")

if __name__ == "__main__":
    main()
