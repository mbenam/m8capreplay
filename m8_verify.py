import pygame
import sys
import struct
import time
import os

# --- CONFIGURATION ---
SCALE = 3             # Window scale (3x = 960x720)
INPUT_FILE = 'm8_nav_test.bin' # The file to play back
PLAYBACK_SPEED = 1.0  # 1.0 = Realtime, 0.5 = Slow Motion, 0.0 = Instant

# --- CONSTANTS ---
WIDTH = 320
HEIGHT = 240

# SLIP Protocol
SLIP_END = 0xC0
SLIP_ESC = 0xDB
SLIP_ESC_END = 0xDC
SLIP_ESC_ESC = 0xDD

# M8 Commands
CMD_DRAW_RECT = 0xFE
CMD_DRAW_CHAR = 0xFD
CMD_DRAW_WAVE = 0xFC
CMD_SYSTEM_INFO = 0xFF

class M8Simulator:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH * SCALE, HEIGHT * SCALE))
        pygame.display.set_caption(f"M8 Capture Verifier - {INPUT_FILE}")
        
        # Internal framebuffer (320x240)
        self.surface = pygame.Surface((WIDTH, HEIGHT))
        
        # Use a monospace font
        self.font = pygame.font.SysFont("Courier New", 10, bold=True)
        
        # State Tracking
        self.last_color = (255, 255, 255) # Default draw color
        self.bg_color = (0, 0, 0)         # Default background
        self.prev_wave_size = 0           # Track waveform width for clearing
        self.running = True

    def decode_slip_packet(self, raw_data):
        """Decode a raw byte array containing SLIP escape sequences."""
        decoded = bytearray()
        i = 0
        while i < len(raw_data):
            byte = raw_data[i]
            if byte == SLIP_ESC:
                i += 1
                if i < len(raw_data):
                    if raw_data[i] == SLIP_ESC_END:
                        decoded.append(SLIP_END)
                    elif raw_data[i] == SLIP_ESC_ESC:
                        decoded.append(SLIP_ESC)
            else:
                decoded.append(byte)
            i += 1
        return decoded

    def process_command(self, data):
        if not data: return

        cmd = data[0]

        if cmd == CMD_DRAW_RECT:
            # Parse Variable Length Rect Command
            # Min length: CMD(1) + X(2) + Y(2) = 5
            if len(data) < 5: return
            
            x = struct.unpack('<H', data[1:3])[0]
            y = struct.unpack('<H', data[3:5])[0]
            w, h = 1, 1
            
            # Determine format based on packet length
            if len(data) >= 12: # Pos + Size + Color
                w = struct.unpack('<H', data[5:7])[0]
                h = struct.unpack('<H', data[7:9])[0]
                self.last_color = (data[9], data[10], data[11])
            elif len(data) >= 9: # Pos + Size (Keep last color)
                w = struct.unpack('<H', data[5:7])[0]
                h = struct.unpack('<H', data[7:9])[0]
            elif len(data) >= 8: # Pos + Color (Size 1x1)
                self.last_color = (data[5], data[6], data[7])
            
            # Logic: If a rect covers the whole screen, it sets the background color
            if w >= WIDTH and h >= HEIGHT:
                self.bg_color = self.last_color

            pygame.draw.rect(self.surface, self.last_color, (x, y, w, h))

        elif cmd == CMD_DRAW_CHAR:
            # CMD(1) + CHAR(1) + X(2) + Y(2) + FG(3) + BG(3)
            if len(data) < 12: return
            
            char_code = data[1]
            try:
                char_str = chr(char_code)
            except:
                char_str = '?'

            x = struct.unpack('<H', data[2:4])[0]
            y = struct.unpack('<H', data[4:6])[0]
            fg = (data[6], data[7], data[8])
            bg = (data[9], data[10], data[11])

            # 1. Clear the character background
            # Approx size 8x12 for standard font
            pygame.draw.rect(self.surface, bg, (x, y, 8, 12))
            
            # 2. Render Text
            # Note: System font alignment won't match M8 pixel-perfectly
            text = self.font.render(char_str, False, fg)
            self.surface.blit(text, (x, y))

        elif cmd == CMD_DRAW_WAVE:
            # CMD(1) + COLOR(3) + DATA(...)
            if len(data) < 5: return
            
            r, g, b = data[1], data[2], data[3]
            wave_data = data[4:]
            current_size = len(wave_data)
            
            # Calculate clearing area
            # If current size is 0, we still need to clear using previous size
            clear_w = current_size if current_size > 0 else self.prev_wave_size
            
            # Hardcoded limit for the header area height to protect VU meters below
            MAX_WAVE_HEIGHT = 32
            
            clear_x = WIDTH - clear_w
            
            # 1. Clear background behind waveform
            pygame.draw.rect(self.surface, self.bg_color, 
                           (clear_x, 0, clear_w, MAX_WAVE_HEIGHT))
            
            self.prev_wave_size = current_size
            if current_size == 0: return

            # 2. Draw Waveform Lines
            prev_x = WIDTH - current_size
            prev_y = wave_data[0]
            
            for i in range(1, current_size):
                curr_x = (WIDTH - current_size) + i
                curr_y = wave_data[i]
                
                # Clip Y to max height
                if curr_y > MAX_WAVE_HEIGHT: curr_y = MAX_WAVE_HEIGHT
                
                pygame.draw.line(self.surface, (r, g, b), 
                                 (prev_x, prev_y), (curr_x, curr_y))
                prev_x = curr_x
                prev_y = curr_y

    def run(self):
        print(f"Opening {INPUT_FILE}...")
        if not os.path.exists(INPUT_FILE):
            print("Error: File not found.")
            return

        with open(INPUT_FILE, 'rb') as f:
            content = f.read()

        # Split stream into packets by SLIP_END (0xC0)
        packets = content.split(bytes([SLIP_END]))
        print(f"Found {len(packets)} packets. Starting playback...")

        for raw_packet in packets:
            if not self.running: break
            
            # Pygame Event Loop (Keep window responsive)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            if len(raw_packet) == 0: continue

            # Decode SLIP and Process
            packet = self.decode_slip_packet(raw_packet)
            self.process_command(packet)

            # Update Display
            # Scale up to make it readable on PC
            scaled = pygame.transform.scale(self.surface, (WIDTH * SCALE, HEIGHT * SCALE))
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()

            # Throttle playback
            if PLAYBACK_SPEED > 0:
                time.sleep(0.001 * PLAYBACK_SPEED)

        print("Playback finished.")
        # Keep window open until closed
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
        pygame.quit()

if __name__ == "__main__":
    sim = M8Simulator()
    sim.run()