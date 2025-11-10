# ...existing code...
import tkinter as tk
import ctypes
import sys

def _get_long_ptr(hwnd, index):
    user32 = ctypes.windll.user32
    try:
        return user32.GetWindowLongPtrW(hwnd, index)
    except AttributeError:
        return user32.GetWindowLongW(hwnd, index)

def _set_long_ptr(hwnd, index, value):
    user32 = ctypes.windll.user32
    try:
        return user32.SetWindowLongPtrW(hwnd, index, value)
    except AttributeError:
        return user32.SetWindowLongW(hwnd, index, value)

def _rgb_from_hex(hexcol):
    hexcol = hexcol.lstrip('#')
    r = int(hexcol[0:2], 16)
    g = int(hexcol[2:4], 16)
    b = int(hexcol[4:6], 16)
    return (r) | (g << 8) | (b << 16)

def create_crosshair(line_length=30, line_thickness=3, color='red'):
    if sys.platform != "win32":
        raise RuntimeError("This script requires Windows.")

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    # fullscreen-sized transparent window
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}+0+0")

    # force window to be realized so we can get a valid HWND
    root.update_idletasks()
    root.update()

    # use a magenta color as color-key
    bg_color = "#ff00ff"
    root.config(bg=bg_color)

    canvas = tk.Canvas(root, width=screen_width, height=screen_height,
                       bg=bg_color, highlightthickness=0)
    canvas.pack()

    cx = screen_width // 2
    cy = screen_height // 2

    canvas.create_line(cx, cy - line_length, cx, cy + line_length,
                       fill=color, width=line_thickness)
    canvas.create_line(cx - line_length, cy, cx + line_length, cy,
                       fill=color, width=line_thickness)

    # Make window click-through using Win32 extended styles
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOOLWINDOW = 0x00000080      # hide from alt-tab/taskbar
    WS_EX_NOACTIVATE = 0x08000000      # don't activate (no focus stealing)
    LWA_COLORKEY = 0x00000001

    user32 = ctypes.windll.user32

    # on some Tk builds the real top-level HWND is the parent of the returned id
    hwnd = int(root.winfo_id())
    try:
        parent = user32.GetParent(hwnd)
        if parent:
            hwnd = parent
    except Exception:
        pass

    prev = _get_long_ptr(hwnd, GWL_EXSTYLE)
    new = prev | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    _set_long_ptr(hwnd, GWL_EXSTYLE, new)

    # Ensure color-key transparency is applied for layered window
    colorref = _rgb_from_hex(bg_color)
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, colorref, 0, LWA_COLORKEY)

    # Refresh window position/styles so changes take effect
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    HWND_TOPMOST = -1
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)

    root.bind("<Escape>", lambda e: root.destroy())

    root.mainloop()

if __name__ == "__main__":
    create_crosshair()
# ...existing code...