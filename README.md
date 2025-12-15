
---

# m8capreplay

**m8capreplay** is a Python-based toolset designed to capture, verify, and replay the serial display data from the [Dirtywave M8](https://dirtywave.com/) (Headless).

## 🎯 Why do this?

Developing custom hardware displays or porting the M8 Headless client to new embedded platforms (like microcontrollers or FPGAs) can be difficult if you have to have the actual M8 hardware connected at all times.

This toolset allows you to:
1.  **Capture** real-world session data (animations, waveforms, partial screen updates) from the M8 to a binary file.
2.  **Verify** the integrity of the captured data on your PC using a simulator.
3.  **Replay** that data stream to your target hardware over a serial connection.

This creates a **reproducible test bench**. You can debug your embedded display drivers and optimization logic (dirty rectangles) using complex, identical data every time, without needing the physical M8 connected to the target.

## 📦 Prerequisites

You need Python 3 and a few dependencies:

```bash
pip install pyserial pygame
```

*   **pyserial**: Used for communicating with the M8 and your target hardware.
*   **pygame**: Used by the verifier script to render the M8 screen on your PC.

## 🛠 The Scripts

### 1. `m8_capture.py` (Manual Capture)
Listens to the M8 Headless serial port and saves the display stream to a file. Use this if you want to manually navigate the M8 (press buttons yourself) to capture specific screens or workflows.

*   **Usage:** Run the script, interact with your M8, and press `Ctrl+C` to stop.
*   **Key Action:** Sends the M8 initialization handshake (`D`, `E`, `R`) automatically.

### 2. `m8_capture_auto.py` (Automated Stress Test)
This script is a "bot" that connects to the M8, starts recording, and automatically sends input commands (Play, Navigation, View Switching) to generate a standardized test pattern.

*   **Why use it:** Great for generating stress-test data with heavy waveform usage and rapid screen transitions.
*   **Behavior:** Plays the current song, drills down into Instrument views, goes back up to Song view, and stops.

### 3. `m8_verify.py` (PC Simulator)
**Always run this before trying to replay to hardware.**
This script parses the captured binary file (SLIP encoded) and renders it to a Pygame window on your computer.

*   **Features:**
    *   Visualizes exactly what the M8 sent.
    *   Verifies that your capture file isn't corrupted.
    *   Simulates the M8's "dirty rectangle" and waveform clearing logic.
*   **Controls:** The window plays back the recording. You can adjust `PLAYBACK_SPEED` in the script to watch frame-by-frame.

### 4. `m8_play.py` (Hardware Replay)
Streams the captured binary file over a serial port to your target custom hardware.

*   **Flow Control:** Includes a tunable delay (`DELAY_PER_CHUNK`) to prevent overflowing the serial buffers on smaller microcontrollers that lack hardware flow control.

## ⚙️ Configuration & Customization

All scripts have a **CONFIGURATION** section at the top. You will likely need to adjust these variables:

### Serial Ports
You must set the correct COM port for your OS:
```python
# Windows Example
M8_PORT = 'COM5'
TARGET_PORT = 'COM9'

# Linux/Mac Example
M8_PORT = '/dev/ttyACM0'
TARGET_PORT = '/dev/ttyUSB0'
```

### Tuning Replay Speed
In `m8_play.py`, if your target hardware's screen is glitching or freezing, you may be sending data too fast. Adjust these values:

```python
CHUNK_SIZE = 64        # Size of data packets sent at once
DELAY_PER_CHUNK = 0.002 # Delay (seconds) between packets
```

### Protocol Details
The M8 uses **SLIP (Serial Line Internet Protocol)** to encode packets.
*   **0xC0 (END):** Marks the end of a packet.
*   **0xDB (ESC):** Escapes special bytes.
*   If you open the `.bin` files in a text editor, they will look like garbage. This is normal. Use `m8_verify.py` to view them.

## 📝 License

This project is open source. Feel free to modify it to suit your specific hardware display projects.
