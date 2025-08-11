# geometry.py
def grid_anchor(win_w, win_h, grid, tile, spacing):
    start_x = (win_w - (grid*tile + (grid-1)*spacing)) // 2
    start_y = (win_h - (grid*tile + (grid-1)*spacing)) // 2 + 60
    return start_x, start_y

def tile_xy(index, grid, start_x, start_y, tile, spacing):
    r, c = divmod(index, grid)
    x = start_x + c * (tile + spacing)
    y = start_y + r * (tile + spacing)
    return x, y

def tile_at(px, py, grid, start_x, start_y, tile, spacing):
    for i in range(grid*grid):
        x, y = tile_xy(i, grid, start_x, start_y, tile, spacing)
        if x <= px <= x+tile and y <= py <= y+tile:
            return i
    return -1
