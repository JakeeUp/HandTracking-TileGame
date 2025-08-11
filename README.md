#  Memory Tiles (Hand-Pinch)

**Memory Tiles** is an interactive webcam-based memory game built with **Python**, **OpenCV**, and **MediaPipe**.  
Use simple **hand pinch gestures** to start the game and select tiles in sequence — no mouse or keyboard required.

---

##  Features
-  **Dual pinch** (both hands) to start the game.
-  **Right-hand pinch** to select tiles in the correct order.
-  Real-time **hand tracking** powered by MediaPipe.
-  Fun and challenging gameplay that trains your memory.

---

## 📥 Download & Play
Get the latest builds from the [Releases](../../releases) page:

- **Windows**: [`MemoryTiles.exe`](../../releases/latest/download/MemoryTiles.exe)  
- **macOS (Apple Silicon)**: [`MemoryTiles-mac-arm.zip`](../../releases/latest/download/MemoryTiles-mac-arm.zip)  
- **macOS (Intel)**: [`MemoryTiles-mac-intel.zip`](../../releases/latest/download/MemoryTiles-mac-intel.zip)  

> **Note:**  
> - On **Windows**, you may see a SmartScreen warning. Click **More info → Run anyway** to start the game.  
> - On **macOS**, you may need to right-click → **Open** the first time you launch the app, and allow camera access in **System Settings → Privacy & Security → Camera**.

---

##  Run from Source
If you want to run the game directly from source:

```bash
# Clone the repository
git clone https://github.com/JakeeUp/TileGame.git
cd TileGame

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
