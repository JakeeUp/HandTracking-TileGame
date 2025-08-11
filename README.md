# Memory Tiles (Hand-Pinch)

Webcam memory game using OpenCV + MediaPipe.
- Dual pinch to start (both hands)
- Right-hand pinch to select tiles in order

## Run from source

### macOS notes
1) Download the .zip for your Mac (Apple Silicon = mac-arm, Intel = mac-intel).
2) Unzip → you'll get `MemoryTiles.app`.
3) First run: right-click the app → Open → Open (bypasses Gatekeeper since it’s unsigned).
4) If camera prompt doesn’t appear, enable it in System Settings → Privacy & Security → Camera.
(If macOS quarantines it, you can run: `xattr -dr com.apple.quarantine MemoryTiles.app`)
