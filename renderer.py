# renderer.py
import cv2, time
from config import *
from geometry import tile_xy

def draw_bg(frame, x, y, w, h, alpha=0.3):
    overlay = frame.copy()
    cv2.rectangle(overlay, (int(x),int(y)), (int(x+w),int(y+h)), (0,0,0), -1)
    cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)

def draw_start(frame, model):
    draw_bg(frame, 0, 0, model.win_w, model.win_h)
    # Title
    title = "MEMORY TILES"
    size,_ = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 3.0, 4)
    cv2.putText(frame, title, ((model.win_w-size[0])//2, 200),
                cv2.FONT_HERSHEY_DUPLEX, 3.0, (0,255,255), 4)

    # Dual pinch progress
    prog = 0.0
    if model.hands.both_start_time:
        prog = min(1.0, (time.time()-model.hands.both_start_time)/DUAL_PINCH_HOLD_S)
    txt = f"PINCH WITH BOTH HANDS TO START{f'... {int(prog*100)}%' if prog>0 else ''}"
    size,_ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
    cv2.putText(frame, txt, ((model.win_w-size[0])//2, 400),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 2)
    if prog>0:
        w,h = 400,20
        x = (model.win_w-w)//2; y = 450
        cv2.rectangle(frame,(x,y),(x+w,y+h),(50,50,50),-1)
        cv2.rectangle(frame,(x,y),(x+w,y+h),(150,150,150),2)
        cv2.rectangle(frame,(x,y),(x+int(prog*w),y+h),(0,255,0),-1)

    # Controls
    controls = [
        "GAME CONTROLS:",
        " Use RIGHT hand to pinch and select tiles",
        " Remember the pattern shown",
        " Select tiles in the correct order",
        " R = Restart | Q = Quit | D = Debug"
    ]
    sy = 550
    for i, line in enumerate(controls):
        color = (0,255,255) if i==0 else (200,200,200)
        scale = 1.0 if i==0 else 0.8
        thick = 2 if i==0 else 1
        size,_ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        cv2.putText(frame, line, ((model.win_w-size[0])//2, sy+i*40),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick)

def draw_tiles(frame, model):
    now = time.time()
    for i in range(model.grid*model.grid):
        x,y = tile_xy(i, model.grid, model.start_x, model.start_y, model.tile_size, model.spacing)
        color, border, thick = CLR_DEFAULT, CLR_BORDER, 2

        if model.state.name == "SHOWING_PATTERN":
            if model.show_idx < len(model.pattern) and i == model.pattern[model.show_idx]:
                if now - model.last_mark < TILE_SHOW_DURATION:
                    color, thick = CLR_HILITE, 4
        elif model.state.name == "PLAYER_INPUT":
            if i in model.player_input:
                color, thick = CLR_SELECTED, 3
        elif model.state.name == "LEVEL_SUCCESS":
            if i in model.pattern:
                color, thick = CLR_SUCCESS, 4
        elif model.state.name == "LEVEL_FAILED":
            if i in model.pattern:
                color, thick = CLR_FAIL, 4
            elif i in model.player_input:
                color = (100,100,100)

        cv2.rectangle(frame, (x,y), (x+model.tile_size, y+model.tile_size), color, -1)
        cv2.rectangle(frame, (x,y), (x+model.tile_size, y+model.tile_size), border, thick)
        cv2.rectangle(frame, (x+5,y+5), (x+model.tile_size-5, y+model.tile_size-5), (255,255,255), 1)

def draw_game_ui(frame, model):
    draw_bg(frame, 0, 0, model.win_w, 100)
    cv2.putText(frame, f"LEVEL {model.level}", (30,50),
                cv2.FONT_HERSHEY_DUPLEX, 1.5, CLR_TEXT, 3)
    cv2.putText(frame, f"Pattern Length: {len(model.pattern)}", (30,80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200,200,200), 2)

    # progress bar
    w,h = 300,25
    x = model.win_w - w - 30; y = 25
    cv2.rectangle(frame,(x,y),(x+w,y+h),(50,50,50),-1)
    cv2.rectangle(frame,(x,y),(x+w,y+h),(150,150,150),2)
    if model.state.name == "PLAYER_INPUT" and model.pattern:
        fill = int((len(model.player_input)/len(model.pattern))*w)
        cv2.rectangle(frame,(x,y),(x+fill,y+h),(0,255,100),-1)
    text = f"{len(model.player_input) if model.state.name=='PLAYER_INPUT' else 0}/{len(model.pattern)}"
    sz,_ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.putText(frame, text, (x+(w-sz[0])//2, y+17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, CLR_TEXT, 2)

def draw_cursor(frame, model, pinching):
    c = model.cursor
    if not c.cursor: return
    x,y = c.cursor
    if pinching:
        cv2.circle(frame, (x,y), 15, (255,0,255), -1)
        cv2.circle(frame, (x,y), 20, (255,255,255), 2)
        cv2.putText(frame, "PINCH!", (x+25,y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,255), 2)
    else:
        s=20; t=2
        cv2.line(frame, (x-s,y), (x+s,y), (0,255,0), t)
        cv2.line(frame, (x,y-s), (x,y+s), (0,255,0), t)
        cv2.circle(frame,(x,y),5,(0,255,0),2)
        cv2.circle(frame,(x,y),2,(255,255,255),-1)
