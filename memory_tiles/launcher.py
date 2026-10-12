"""Settings window shown before the game: choose a camera, with a live preview."""
import base64
import tkinter as tk
from tkinter import ttk
from typing import List, Optional

import cv2
import numpy as np

from .cameras import CameraInfo, fit_frame, list_cameras, open_camera, pick_default

PREVIEW_W, PREVIEW_H = 480, 360
BLACK_LEVEL = 4          # mean pixel value below which a preview counts as black
ERROR_FG, OK_FG = "#c62828", "#555555"


class Launcher:
    """Run with `.run()`; returns the chosen camera, or None if the window was closed."""

    def __init__(self, saved_camera: Optional[str] = None, error: Optional[str] = None):
        self.cameras: List[CameraInfo] = []
        self.choice: Optional[CameraInfo] = None
        self.cap = None
        self.cap_index: Optional[int] = None

        self.root = root = tk.Tk()
        root.title("Memory Tiles - Settings")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self._close)

        body = ttk.Frame(root, padding=16)
        body.grid()
        ttk.Label(body, text="Memory Tiles", font=("TkDefaultFont", 18, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(body, text="Camera:").grid(row=1, column=0, sticky="w")
        self.combo = ttk.Combobox(body, state="readonly", width=42)
        self.combo.grid(row=1, column=1, sticky="we", padx=8)
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self._select(self.combo.current()))
        ttk.Button(body, text="Refresh", command=self._refresh).grid(row=1, column=2)

        self.blank = tk.PhotoImage(width=PREVIEW_W, height=PREVIEW_H)
        self.preview = tk.Label(body, image=self.blank, bg="black")
        self.preview.grid(row=2, column=0, columnspan=3, pady=12)

        self.status = ttk.Label(body, text=error or "", foreground=ERROR_FG if error else OK_FG,
                                wraplength=PREVIEW_W)
        self.status.grid(row=3, column=0, columnspan=3, sticky="w")

        self.start_btn = ttk.Button(body, text="Start game", command=self._start)
        self.start_btn.grid(row=4, column=0, columnspan=3, pady=(12, 0), sticky="e")
        root.bind("<Return>", lambda _e: self._start())
        root.bind("<Escape>", lambda _e: self._close())

        self._refresh(saved_camera, keep_status=bool(error))
        root.after(15, self._tick)

    def run(self) -> Optional[CameraInfo]:
        self.root.mainloop()
        return self.choice

    # --- camera selection --------------------------------------------------

    def _refresh(self, prefer: Optional[str] = None, keep_status=False):
        current = self.cameras[self.combo.current()].name if self.cameras else None
        self._release()
        self._set_status("Looking for cameras...")
        self.cameras = list_cameras()
        self.combo["values"] = [str(c) for c in self.cameras]
        if not self.cameras:
            self.combo.set("")
            self.start_btn.state(["disabled"])
            self._set_status("No cameras found. Connect one and press Refresh.", error=True)
            return
        self.start_btn.state(["!disabled"])
        pos = pick_default(self.cameras, prefer or current)
        self.combo.current(pos)
        status = self.status.cget("text") if keep_status else None
        self._select(pos)
        if keep_status:
            self._set_status(status, error=True)

    def _select(self, pos: int):
        if pos < 0:
            return
        cam = self.cameras[pos]
        self._release()
        self._set_status(f"Opening {cam.name}...")
        cap = open_camera(cam.index)
        if cap.isOpened():
            self.cap, self.cap_index = cap, cam.index
            self._set_status("")
        else:
            cap.release()
            self._set_status(f"Could not open {cam.name}. It may be in use by another app "
                             "(OBS, Teams, Zoom...) or disconnected.", error=True)

    def _release(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = self.cap_index = None
        self.preview.configure(image=self.blank)

    # --- preview -----------------------------------------------------------

    def _tick(self):
        if self.cap is not None:
            ok, frame = self.cap.read()
            if ok:
                frame = fit_frame(cv2.flip(frame, 1), PREVIEW_W, PREVIEW_H)
                self._show(frame)
                if frame.mean() < BLACK_LEVEL:
                    self._set_status("This camera is sending a black picture. "
                                     "Try another one from the list.", error=True)
                elif "black picture" in self.status.cget("text"):
                    self._set_status("")
        self.root.after(15, self._tick)

    def _show(self, frame: np.ndarray):
        ok, png = cv2.imencode(".png", frame)
        if ok:
            self.photo = tk.PhotoImage(data=base64.b64encode(png.tobytes()))
            self.preview.configure(image=self.photo)

    # --- buttons -----------------------------------------------------------

    def _set_status(self, text: str, error=False):
        self.status.configure(text=text, foreground=ERROR_FG if error else OK_FG)
        self.root.update_idletasks()

    def _start(self):
        if not self.cameras or self.combo.current() < 0:
            return
        self.choice = self.cameras[self.combo.current()]
        self._close()

    def _close(self):
        self._release()   # the game opens the camera itself; some devices allow one user
        self.root.destroy()
