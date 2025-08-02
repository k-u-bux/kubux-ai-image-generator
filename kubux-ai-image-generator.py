# Copyright 2025 [Kai-Uwe Bux]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import json
import os
import math
import platform
import secrets
import queue
import threading
import subprocess
import time
import tkinter as tk
import tkinter.font as tkFont
from collections import OrderedDict
from datetime import datetime
from tkinter import TclError
from tkinter import messagebox
from tkinter import ttk

import requests
from PIL import Image, ImageTk
from dotenv import load_dotenv
from together import Together

# Load environment variables
load_dotenv()
# --- Configuration ---
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
ai_features_enabled = bool(TOGETHER_API_KEY)

MODEL_STRINGS = [
    ("FLUX.1 Pro", "black-forest-labs/FLUX.1-pro"),
    ("Stable Diffusion XL 1.0", "stabilityai/stable-diffusion-xl-base-1.0"),
    ("FLUX.1 Schnell", "black-forest-labs/FLUX.1-schnell"),
    ("FLUX.1.1 Pro", "black-forest-labs/FLUX.1.1-pro"),
    ("FLUX.1 Dev", "black-forest-labs/FLUX.1-dev"),
    ("FLUX.1 Schnell (Free)", "black-forest-labs/FLUX.1-schnell-Free"),
    ("FLUX.1 Canny (for edge based conditions)", "black-forest-labs/FLUX.1-canny"),
    ("FLUX.1 Depth (for depth based conditioning)", "black-forest-labs/FLUX.1-depth"),
    ("FLUX.1 Redux (image variation, restyling)", "black-forest-labs/FLUX.1-redux"),
    ("FLUX.1 Dev (LoRA support)", "black-forest-labs/FLUX.1-dev-lora"),
    ("FLUX.1 Kontext Dev (text and image input)", "black-forest-labs/FLUX.1-kontext-dev"),
]

SUPPORTED_IMAGE_EXTENSIONS = (
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff', '.webp',
    '.ico', '.icns', '.avif', '.dds', '.msp', '.pcx', '.ppm',
    '.pbm', '.pgm', '.sgi', '.tga', '.xbm', '.xpm'
)
    
HOME_DIR = os.path.expanduser('~')
CONFIG_DIR = os.path.join(HOME_DIR, ".config", "kubux-ai-image-generator")
DOWNLOAD_DIR = os.path.join(HOME_DIR, "Pictures", "kubux-ai-image-generator")
PROMPT_HISTORY_FILE = os.path.join(CONFIG_DIR, "prompt_history.json")
APP_SETTINGS_FILE = os.path.join(CONFIG_DIR, "app_settings.json")    

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# --- probe font ---

def get_gtk_ui_font():
    """
    Queries the system's default UI font and size for GTK-based desktops
    using gsettings.
    """
    try:
        # Check if gsettings is available
        subprocess.run(["which", "gsettings"], check=True, capture_output=True)

        # Get the font name string from GNOME's desktop interface settings
        font_info_str = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "font-name"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip().strip("'") # Remove leading/trailing whitespace and single quotes

        # Example output: 'Noto Sans 10', 'Ubuntu 11', 'Cantarell 11'
        parts = font_info_str.rsplit(' ', 1) # Split only on the last space

        font_name = "Sans" # Default fallback
        font_size = 10     # Default fallback

        if len(parts) == 2 and parts[1].isdigit():
            font_name = parts[0]
            font_size = int(parts[1])
        else:
            # Handle cases like "Font Name" 10 or unexpected formats
            # Attempt to split assuming format "Font Name Size"
            try:
                # Common scenario: "Font Name X" where X is size
                # Sometimes font names have spaces (e.g., "Noto Sans CJK JP")
                # So finding the *last* space before digits is key.
                last_space_idx = font_info_str.rfind(' ')
                if last_space_idx != -1 and font_info_str[last_space_idx+1:].isdigit():
                    font_name = font_info_str[:last_space_idx]
                    font_size = int(font_info_str[last_space_idx+1:])
                else:
                    print(f"Warning: Unexpected gsettings font format: '{font_info_str}'")
            except Exception as e:
                print(f"Error parsing gsettings font: {e}")

        return font_name, font_size

    except subprocess.CalledProcessError:
        print("gsettings command not found or failed. Are you on a GTK-based desktop with dconf/gsettings installed?")
        return "Sans", 10 # Fallback for non-GTK or missing gsettings
    except Exception as e:
        print(f"An error occurred while getting GTK font settings: {e}")
        return "Sans", 10 # General fallback

def get_kde_ui_font():
    """
    Queries the system's default UI font and size for KDE Plasma desktops
    using kreadconfig5.
    """
    try:
        # Check if kreadconfig5 is available
        subprocess.run(["which", "kreadconfig5"], check=True, capture_output=True)

        # Get the font string from the kdeglobals file
        # This typically looks like "Font Name,points,weight,slant,underline,strikeout"
        font_string = subprocess.run(
            ["kreadconfig5", "--file", "kdeglobals", "--group", "General", "--key", "font", "--default", "Sans,10,-1,5,50,0,0,0,0,0"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()

        parts = font_string.split(',')
        if len(parts) >= 2:
            font_name = parts[0].strip()
            # Font size is in points. kreadconfig often gives it as an int directly.
            font_size = int(parts[1].strip())
            return font_name, font_size
        else:
            print(f"Warning: Unexpected KDE font format: '{font_string}'")
            return "Sans", 10 # Fallback

    except subprocess.CalledProcessError:
        print("kreadconfig5 command not found or failed. Are you on KDE Plasma?")
        return "Sans", 10 # Fallback for non-KDE or missing kreadconfig5
    except Exception as e:
        print(f"An error occurred while getting KDE font settings: {e}")
        return "Sans", 10 # General fallback

def get_linux_system_ui_font_info():
    """
    Attempts to detect the Linux desktop environment and return its
    configured default UI font family and size.
    Returns (font_family, font_size) or (None, None) if undetectable.
    """
    # Check for common desktop environment indicators
    desktop_session = os.environ.get("XDG_CURRENT_DESKTOP")
    if not desktop_session:
        desktop_session = os.environ.get("DESKTOP_SESSION")

    print(f"Detected desktop session: {desktop_session}")

    if desktop_session and ("GNOME" in desktop_session.upper() or
                            "CINNAMON" in desktop_session.upper() or
                            "XFCE" in desktop_session.upper() or
                            "MATE" in desktop_session.upper()):
        print("Attempting to get GTK font...")
        return get_gtk_ui_font()
    elif desktop_session and "KDE" in desktop_session.upper():
        print("Attempting to get KDE font...")
        return get_kde_ui_font()
    else:
        # Fallback for other desktops or if detection fails
        print("Could not reliably detect desktop environment. Trying common defaults or gsettings as fallback.")
        # Try gsettings anyway, as it's common even outside "full" GNOME
        font_name, font_size = get_gtk_ui_font()
        if font_name != "Sans" or font_size != 10: # If gsettings returned something more specific
            return font_name, font_size
        return "Sans", 10 # Final generic fallback

def get_linux_ui_font():
    font_name, font_size = get_linux_ui_font_info()
    return tkFont.Font(family=font_name, size=font_size)
    

# --- dealing with image names ---

def unique_name(original_path, category):
    _, ext = os.path.splitext(original_path)
    timestamp_str = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
    random_raw_part = secrets.token_urlsafe(18)
    sanitized_random_part = random_raw_part.replace('/', '_').replace('+', '-')
    base_name = f"{timestamp_str}_{category}_{sanitized_random_part}"
    return f"{base_name}{ext}"

def resize_image(image, target_width, target_height):
    original_width, original_height = image.size

    if target_width <= 0 or target_height <= 0:
        return image.copy() # Return a copy of the original or a small placeholder

    target_aspect = target_width / target_height
    image_aspect = original_width / original_height

    if image_aspect > target_aspect:
        new_width = target_width
        new_height = int(target_width / image_aspect)
    else:
        new_height = target_height
        new_width = int(target_height * image_aspect)

    new_width = max(1, new_width)
    new_height = max(1, new_height)

    return image.resize((new_width, new_height), resample=Image.LANCZOS)

def uniq_file_id(img_path, width=-1):
    try:
        mtime = os.path.getmtime(img_path)
    except FileNotFoundError:
        print(f"Error: Original image file not found for thumbnail generation: {img_path}")
        return None
    except Exception as e:
        print(f"Warning: Could not get modification time for {img_path}: {e}. Using a default value.")
        mtime = 0
    key = f"{img_path}_{width}_{mtime}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()

PIL_CACHE = OrderedDict()

def get_full_size_image(img_path):
    cache_key = uniq_file_id(img_path)
    if cache_key in PIL_CACHE:
        PIL_CACHE.move_to_end(cache_key)
        return PIL_CACHE[cache_key]
    try:
        full_image = Image.open(img_path)
        PIL_CACHE[cache_key] = full_image
        if len( PIL_CACHE ) > 2000:
            PIL_CACHE.popitem(last=False)
            assert len( PIL_CACHE ) == 2000
        return full_image
    except Exception as e:
        print(f"Error loading of for {img_path}: {e}")
        return None
        
def make_tk_image( pil_image ):
    if pil_image.mode not in ("RGB", "RGBA", "L", "1"):
        pil_image = pil_image.convert("RGBA")
    return ImageTk.PhotoImage(pil_image)


# --- dialogue box ---
def fallback_show_error(title, message):
    messagebox.showerror(title, message)
    
def custom_message_dialog(parent, title, message, font=("Arial", 12)):
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)  # Set to be on top of the parent window
    
    # Calculate position to center the dialog on parent
    x = parent.winfo_rootx() + parent.winfo_width() // 2 - 200
    y = parent.winfo_rooty() + parent.winfo_height() // 2 - 100
    dialog.geometry(f"400x300+{x}+{y}")
    
    # Message area
    msg_frame = ttk.Frame(dialog, padding=20)
    msg_frame.pack(fill=tk.BOTH, expand=True)
    
    # Text widget with scrollbar for the message
    text_widget = tk.Text(msg_frame, wrap=tk.WORD, font=font, 
                          highlightthickness=0, borderwidth=0)
    scrollbar = ttk.Scrollbar(msg_frame, orient="vertical", 
                              command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Insert the message text
    text_widget.insert(tk.END, message)
    text_widget.configure(state="disabled")  # Make read-only
    
    # OK button
    button_frame = ttk.Frame(dialog, padding=10)
    button_frame.pack(fill=tk.X)
    ok_button = ttk.Button(button_frame, text="OK", 
                          command=dialog.destroy, width=10)
    ok_button.pack(side=tk.RIGHT, padx=5)
    
    # Center dialog on screen
    dialog.update_idletasks()
    dialog.grab_set()  # Modal: user must interact with this window
    
    # Set focus and wait for window to close
    ok_button.focus_set()
    dialog.wait_window()

    
# --- Together.ai Image Generation ---

def best_dimensions(image_width, image_height, scale=1.0):
    ratio = image_width / image_height
    best_h = 20;
    best_w = best_h * math.ceil(ratio)
    max_size = max( 8, int(scale * 46.5) )
    for w in range(8,max_size):
        for h in range(8,max_size):
            r = w / h
            if not r < ratio:
                if not ( best_w / best_h ) < r:
                    best_w = w
                    best_h = h
    return best_w * 32, best_h * 32
                
def good_dimensions(image_width, image_height, scale=1.0, delta=0.05):
    ratio = image_width / image_height
    best_h = 1
    best_w = 0
    max_size = max( 8, int(scale * 46.5) )
    for w in range(8,max_size):
        for h in range(8,max_size):
            r = w / h
            if not r < ratio - delta and not ratio + delta < r:
                best_w = w
                best_h = h
    return best_w * 32, best_h * 32


def generate_image(prompt, width, height, model, steps,
                   error_callback=fallback_show_error):
    client = Together(api_key=TOGETHER_API_KEY)
    try:
        response = client.images.generate(
            prompt=prompt,
            model=model,
            width=width,
            height=height,
            steps=steps
        )
        return response.data[0].url
    except Exception as e:
        message = f"Failed to download image: {e}"
        error_callback("API Error", message)
        return None

def download_image(url, file_name, prompt, error_callback=fallback_show_error):
    key = f"{prompt}"
    prompt_dir = hashlib.sha256(key.encode('utf-8')).hexdigest()
    save_path = os.path.join(DOWNLOAD_DIR,prompt_dir,file_name)
    tmp_save_path = save_path + "-tmp"
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status() 
        dir_name = os.path.dirname(save_path)
        os.makedirs(dir_name, exist_ok=True)
        prompt_file = os.path.join( dir_name, "prompt.txt")
        try:
            with open(prompt_file, 'w') as file:
                file.write(prompt)
        except IOError as e:
            print(f"Error writing prompt {prompt} to file: {e}")
        with open(tmp_save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        os.replace(tmp_save_path, save_path)
    except Exception as e:
        try:
            os.remove(tmp_save_path)
            os.remove(save_path)
        except Exception: pass
        message = f"Failed to download image: {e}"
        error_callback("Download Error", message)
        return None
    try:
        link_path=os.path.join(DOWNLOAD_DIR, os.path.basename(file_name))
        os.symlink(save_path, link_path)
        return link_path
    except Exception as e:
        os.remove(link_path)
        message = f"Failed to link image: {e}"
        error_callback("File system error,", message)
        return None

# --- widgets ---

class FullscreenImageViewer(tk.Toplevel):
    """
    A widget for displaying an image with zooming and panning capabilities.
    """
    def __init__(self, master, image_path=None, title="change me", start_fullscreen=False):
        """
        Initialize the image viewer.
        
        Args:
            master: The parent widget
            image_path: Path to the image file to display
            title: Optional title for the window (defaults to filename)
            start_fullscreen: Whether to start in fullscreen mode
        """
        super().__init__(master,class_="kubux-ai-image-generator")

        self.master = master
        self.image_path = image_path
        self.original_image = None
        self.display_image = None
        self.photo_image = None
        self.is_fullscreen = False
        
        # Set window properties
        self.title(title or os.path.basename(image_path))
        self.minsize(400, 300)
        
        # Make it transient with parent, but allow window manager integration
        self.resizable(True, True)
        
        # Ensure proper window manager integration
        self.wm_attributes("-type", "normal")
        self.wm_attributes('-fullscreen', start_fullscreen)
        self.protocol("WM_DELETE_WINDOW", self._close)
        
        self.geometry(self.master.image_win_geometry)
        
        # Create a frame to hold the canvas and scrollbars
        self.frame = ttk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create horizontal and vertical scrollbars
        self.h_scrollbar = ttk.Scrollbar(self.frame, orient=tk.HORIZONTAL)
        self.v_scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL)
        
        # Create canvas for the image
        self.canvas = tk.Canvas(
            self.frame, 
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set,
            bg="black"
        )
        
        # Configure scrollbars
        self.h_scrollbar.config(command=self.canvas.xview)
        self.v_scrollbar.config(command=self.canvas.yview)
        
        # Grid layout for canvas and scrollbars
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure frame grid weights
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        
        # Image display state
        self.zoom_factor = 1.0
        self.fit_to_window = True  # Start in "fit to window" mode
        
        # Pan control variables
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.panning = False
        
        # Bind events
        self._bind_events()
        
        # Set fullscreen if requested (after window has been mapped)
        if start_fullscreen:
            self.update_idletasks()  # Make sure window is realized first
            self.toggle_fullscreen()
        
        # Set focus to receive key events
        self.canvas.focus_set()

    def set_image_path(self, image_path):
        self.image_path = image_path
        if self.image_path:
            self._load_image()
        
    def get_dimensions(self):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        return canvas_width, canvas_height

    def get_aspect_ratio(self, the_scale=1.0):
        w, h = self.get_dimensions()
        return good_dimensions( image_width=w, image_height=h, scale=the_scale)
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)
        self.update_idletasks()
        self._update_image()

    def _load_image(self):
        """Load the image from file and display it."""
        try:
            self.original_image = Image.open(self.image_path)
            self._update_image()
            self.update_idletasks()
            self._update_image()
        except Exception as e:
            print(f"Error loading image {self.image_path}: {e}")
            self.destroy()

    def _update_image(self):
        """Update the displayed image based on current zoom and size."""
        w, h = self.get_aspect_ratio( self.master.image_scale )
        self.title(f"set aspect ratio = {w} x {h}")
        # print(f"geometry = {self.geometry()}")
        self.master.image_win_geometry = self.geometry()
        
        if not self.original_image:
            return
                
        # Get current canvas size
        canvas_width, canvas_height = self.get_dimensions()
        
        # Use default size if canvas size not available yet
        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 600
                
        # Get original image dimensions
        orig_width, orig_height = self.original_image.size
        
        # Calculate dimensions based on fit mode or zoom
        if self.fit_to_window:
            # Calculate scale to fit the window
            scale_width = canvas_width / orig_width
            scale_height = canvas_height / orig_height
            scale = min(scale_width, scale_height)
            self.zoom_factor = scale
            
            # Apply the scale
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
        else:
            # Apply the current zoom factor
            new_width = int(orig_width * self.zoom_factor)
            new_height = int(orig_height * self.zoom_factor)
        
        # Resize image
        self.display_image = self.original_image.resize(
            (new_width, new_height), 
            Image.LANCZOS
        )
        self.photo_image = ImageTk.PhotoImage(self.display_image)
        
        # Calculate the offset to center the image
        x_offset = max(0, (canvas_width - new_width) // 2)
        y_offset = max(0, (canvas_height - new_height) // 2)
        
        # Update canvas with new image
        self.canvas.delete("all")
        self.image_id = self.canvas.create_image(
            x_offset, y_offset, 
            anchor=tk.NW, 
            image=self.photo_image
        )
        
        # Set the scroll region - determine if scrolling is needed
        if new_width > canvas_width or new_height > canvas_height:
            # Image is larger than canvas, set scroll region to image size
            self.canvas.config(scrollregion=(0, 0, new_width, new_height))
            
            # When image is larger than canvas, we don't need the offset
            # We'll reposition the image at the origin for proper scrolling
            self.canvas.coords(self.image_id, 0, 0)
        else:
            # Image fits within canvas, include the offset in the scroll region
            self.canvas.config(scrollregion=(0, 0, 
                                            max(canvas_width, x_offset + new_width), 
                                            max(canvas_height, y_offset + new_height)))
        
        # Update scrollbars visibility based on image vs canvas size
        self._update_scrollbars()
        
        # If in fit mode or image is smaller than canvas, center the view
        if self.fit_to_window or (new_width <= canvas_width and new_height <= canvas_height):
            # Reset scroll position to start
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)

    def _update_scrollbars(self):
        """Show or hide scrollbars based on the image size compared to canvas."""
        # Get image and canvas dimensions
        img_width = self.display_image.width
        img_height = self.display_image.height
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Show/hide horizontal scrollbar
        if img_width <= canvas_width:
            self.h_scrollbar.grid_remove()
            self.canvas.xview_moveto(0)  # Reset horizontal scroll position
        else:
            self.h_scrollbar.grid()
            
        # Show/hide vertical scrollbar
        if img_height <= canvas_height:
            self.v_scrollbar.grid_remove()
            self.canvas.yview_moveto(0)  # Reset vertical scroll position
        else:
            self.v_scrollbar.grid()
                                
    def _bind_events(self):
        """Bind all event handlers."""
        # Keyboard events
        self.bind("<Key>", self._on_key)
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", self._on_escape)
        
        # Mouse events
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        
        # Mouse wheel events
        if platform.system() == "Windows":
            self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        else:
            self.canvas.bind("<Button-4>", self._on_mouse_wheel)
            self.canvas.bind("<Button-5>", self._on_mouse_wheel)
            
        # Window events
        self.bind("<Configure>", self._on_configure)
    
    def _on_escape(self, event):
        self._close()
    
    def _close(self):
        if self.is_fullscreen:
            self.toggle_fullscreen()
        self.grab_release()
        self.master.spawn_image_frame()
        self.destroy()
        
    def _on_key(self, event):
        """Handle keyboard events."""
        key = event.char
        
        if key == '+' or key == '=':  # Zoom in
            self._zoom_in()
        elif key == '-' or key == '_':  # Zoom out
            self._zoom_out()
        elif key == '0':  # Reset zoom
            self.fit_to_window = True
            self._update_image()
    
    def _on_mouse_down(self, event):
        """Handle mouse button press."""
        self.panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor="fleur")  # Change cursor to indicate panning
        
    def _on_mouse_drag(self, event):
        """Handle mouse drag for panning."""
        if not self.panning:
            return
            
        # Calculate the distance moved
        dx = self.pan_start_x - event.x
        dy = self.pan_start_y - event.y
        
        # Move the canvas view
        self.canvas.xview_scroll(dx, "units")
        self.canvas.yview_scroll(dy, "units")
        
        # Update the starting position
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def _on_mouse_up(self, event):
        """Handle mouse button release."""
        self.panning = False
        self.canvas.config(cursor="")  # Reset cursor
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel events for zooming."""
        if platform.system() == "Windows":
            delta = event.delta
            if delta > 0:
                self._zoom_in(event.x, event.y)
            else:
                self._zoom_out(event.x, event.y)
        else:
            # For Linux/Unix/Mac
            if event.num == 4:  # Scroll up
                self._zoom_in(event.x, event.y)
            elif event.num == 5:  # Scroll down
                self._zoom_out(event.x, event.y)
                
    def _on_configure(self, event):
        """Handle window resize events."""
        # Only process events for the main window, not child widgets
        if event.widget == self and self.fit_to_window:
            # Delay update to avoid excessive redraws during resize
            self.after_cancel(getattr(self, '_resize_job', 'break'))
            self._resize_job = self.after(100, self._update_image)
    
    def _zoom_in(self, x=None, y=None):
        """Zoom in on the image."""
        self.fit_to_window = False
        self.zoom_factor *= 1.25
        
        # Save current view fractions before zooming
        if x is not None and y is not None:
            # Calculate the fractions to maintain zoom point
            x_fraction = self.canvas.canvasx(x) / (self.display_image.width)
            y_fraction = self.canvas.canvasy(y) / (self.display_image.height)
            
        # Update the image with new zoom
        self._update_image()
        
        # After zoom, scroll to maintain focus point
        if x is not None and y is not None:
            # Calculate new position in the zoomed image
            new_x = x_fraction * self.display_image.width
            new_y = y_fraction * self.display_image.height
            
            # Calculate canvas center
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Calculate scroll fractions
            x_view_fraction = (new_x - canvas_width / 2) / self.display_image.width
            y_view_fraction = (new_y - canvas_height / 2) / self.display_image.height
            
            # Apply the scroll
            self.canvas.xview_moveto(max(0, min(1, x_view_fraction)))
            self.canvas.yview_moveto(max(0, min(1, y_view_fraction)))
    
    def _zoom_out(self, x=None, y=None):
        """Zoom out from the image."""
        self.fit_to_window = False
        self.zoom_factor /= 1.25
        
        # Minimum zoom factor - if we go below this, switch to fit mode
        min_zoom = 0.1
        if self.zoom_factor < min_zoom:
            self.fit_to_window = True
            self._update_image()
            return
            
        # Same logic as zoom in for maintaining focus point
        if x is not None and y is not None:
            x_fraction = self.canvas.canvasx(x) / (self.display_image.width)
            y_fraction = self.canvas.canvasy(y) / (self.display_image.height)
            
        self._update_image()
        
        if x is not None and y is not None:
            new_x = x_fraction * self.display_image.width
            new_y = y_fraction * self.display_image.height
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            x_view_fraction = (new_x - canvas_width / 2) / self.display_image.width
            y_view_fraction = (new_y - canvas_height / 2) / self.display_image.height
            
            self.canvas.xview_moveto(max(0, min(1, x_view_fraction)))
            self.canvas.yview_moveto(max(0, min(1, y_view_fraction)))

                
class ImageGenerator(tk.Tk):
    def __init__(self):
        super().__init__(className="kubux-ai-image-generator")
        self.title("kubux AI image generator")
        self.configure(background=self.cget("background"))
        self._gallery_scale_update_after_id = None
        self._ui_scale_job = None

        self._load_prompt_history()
        self._load_app_settings()
        font_name, font_size = get_linux_system_ui_font_info()
        self.base_font_size = font_size
        self.main_font = tkFont.Font(family=font_name, size=int(self.base_font_size * self.ui_scale))
        self.geometry(self.main_win_geometry)

        self._create_widgets()
        self.update_idletasks()
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.update_idletasks()

    def _load_prompt_history(self):
        try:
            if os.path.exists(PROMPT_HISTORY_FILE):
                with open(PROMPT_HISTORY_FILE, 'r') as f:
                    self.prompt_history = json.load(f)
            else: self.prompt_history = [] 
        except (json.JSONDecodeError, Exception): self.prompt_history = []

    def _save_prompt_history(self):
        try:
            with open(PROMPT_HISTORY_FILE, 'w') as f:
                json.dump(self.prompt_history, f, indent=4) 
        except Exception as e: print(f"Error saving prompt history: {e}")

    def _load_app_settings(self):
        try:
            if os.path.exists(APP_SETTINGS_FILE):
                with open(APP_SETTINGS_FILE, 'r') as f:
                    self.app_settings = json.load(f)
            else:
                self.app_settings = {}
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading app settings, initializing defaults: {e}")
            self.app_settings = {}
        
        self.ui_scale = self.app_settings.get("ui_scale", 1.0)
        self.main_win_geometry = self.app_settings.get("main_win_geometry", "1200x800")
        self.image_win_geometry = self.app_settings.get("image_win_geometry", "1200x800")
        self.n_steps = self.app_settings.get("n_steps", 28)
        self.image_scale = self.app_settings.get("image_scale", 1.0)
        self.model_index = self.app_settings.get("model_index", 0 )
        
    def _save_app_settings(self):
        try:
            if not hasattr(self, 'app_settings'):
                self.app_settings = {}

            self.app_settings["ui_scale"] = self.ui_scale
            self.app_settings["main_win_geometry"] = self.geometry()
            self.app_settings["image_win_geometry"] = self.image_frame.geometry()
            self.app_settings["n_steps"] = self.n_steps
            self.app_settings["image_scale"] = self.image_scale
            self.app_settings["model_index"] = self.model_index

            with open(APP_SETTINGS_FILE, 'w') as f:
                json.dump(self.app_settings, f, indent=4)
        except Exception as e:
            print(f"Error saving app settings: {e}")

    def _on_closing(self):
        self._save_prompt_history()
        self._save_app_settings()
        self.destroy() 

    def _create_widgets(self):
        self.style = ttk.Style()
        self.style.configure('.', font=self.main_font)

        self.main_container = tk.Frame(self)
        self.main_container.pack(side="top", fill="both", expand=True, padx=5, pady=(5, 0))

        if True:
            model_frame =  tk.Frame(self.main_container)
            model_frame.pack(side="top", expand=True, fill="x", pady=(5, 5), padx=(2,2))
            self.model_menubutton = tk.Menubutton(model_frame, text=MODEL_STRINGS[self.model_index][0], font=self.main_font)
            model_menu = tk.Menu( self.model_menubutton, font=self.main_font )
            self.model_menubutton.config( menu = model_menu )
            for i, (entry, model) in enumerate(MODEL_STRINGS):
                model_menu.add_command( label=entry, command=lambda idx = i : self._set_model_index(idx))
            self.model_menubutton.pack(side="left", fill="x", expand=True, padx=(2,2), pady=(5,5))
        if True:
            controls_frame = tk.Frame(self.main_container)
            controls_frame.pack(side="top", fill="x", pady=(5, 5), padx=5)
            if True:
                self.generate_button = ttk.Button(controls_frame, text="Generate", command=self._on_generate_button_click)
                self.generate_button.pack(side="left", padx=(2,0))
                dummy_A_label = tk.Label(controls_frame, text="# steps:", font=self.main_font)
                dummy_A_label.pack(side="left", padx=(24,0))
                dummy_A_frame = tk.Frame(controls_frame)
                dummy_A_frame.pack(side="left", expand=True, fill="x")
                self.steps_slider = tk.Scale(
                    dummy_A_frame, from_=1, to=64, orient="horizontal", 
                    resolution=1, showvalue=True, font=self.main_font
                )
                self.steps_slider.set(self.n_steps)
                self.steps_slider.config(command=lambda value : setattr(self, 'n_steps', int(value)))
                self.steps_slider.pack(anchor="w")

                dummy_B_label = tk.Label(controls_frame, text="size:", font=self.main_font)
                dummy_B_label.pack(side="left", padx=(24,0))
                dummy_B_frame = tk.Frame(controls_frame)
                dummy_B_frame.pack(side="left", expand=True, fill="x")
                self.scale_slider = tk.Scale(
                    dummy_B_frame, from_=0.2, to=1.0, orient="horizontal", 
                    resolution=0.05, showvalue=True, font=self.main_font
                )
                self.scale_slider.set(self.image_scale)
                self.scale_slider.config(command=self._update_image_scale)
                self.scale_slider.pack(anchor="w")
                
                self.history_button = ttk.Button(controls_frame, text="Prompt history", command=self._show_prompt_history)
                self.history_button.pack(side="left", padx=(24,12))
                dummy_C_frame = tk.Frame(controls_frame)
                dummy_C_frame.pack(side="right", expand=False, fill="x")
                self.ui_slider = tk.Scale(
                    dummy_C_frame, from_=0.5, to=3.5, orient="horizontal", 
                    resolution=0.1, showvalue=False
                )
                self.ui_slider.set(self.ui_scale)
                self.ui_slider.config(command=self._update_ui_scale)
                self.ui_slider.pack(anchor="e")
                dummy_C_label = tk.Label(controls_frame, text="UI:", font=self.main_font)
                dummy_C_label.pack(side="right", padx=(12,0))
                
        if True:
            prompt_frame_outer = ttk.LabelFrame(self.main_container, text="Image Prompt:")
            prompt_frame_outer.pack(side="top", expand=True, fill="both", pady=(5, 5), padx=5)
            prompt_frame_inner = tk.Frame(prompt_frame_outer)
            prompt_frame_inner.pack(fill="both", expand=True, padx=5, pady=5)
            self.prompt_text_widget = tk.Text(prompt_frame_inner, wrap="word", relief="sunken", borderwidth=2, font=self.main_font)
            self.prompt_text_widget.pack(fill="both", expand=True)
            self.prompt_text_widget.bind("<Return>", lambda event: self._on_generate_button_click())

        self.spawn_image_frame()

    def spawn_image_frame(self):
        self.image_frame = FullscreenImageViewer(self, title="set aspect ratio")
                
    def _update_ui_scale(self, value):
        if self._ui_scale_job: self.after_cancel(self._ui_scale_job)
        self._ui_scale_job = self.after(400, lambda: self._do_update_ui_scale(float(value)))

    def _update_image_scale(self, value):
        self.image_scale = float(value)
        self.image_frame._update_image()

    def _set_model_index(self, index):
        self.model_index = index;
        self.model_menubutton.config( text=MODEL_STRINGS[self.model_index][0] )
        
    def _do_update_ui_scale(self, scale_factor):
        self.ui_scale = scale_factor
        new_size = int(self.base_font_size * scale_factor)
        self.main_font.config(size=new_size)
        def update_widget_fonts(widget, font):
            try:
                if 'font' in widget.config(): widget.config(font=font)
            except tk.TclError: pass
            for child in widget.winfo_children(): update_widget_fonts(child, font)
        update_widget_fonts(self, self.main_font)
    
    def _add_prompt_to_history(self, prompt):
        if prompt in self.prompt_history: self.prompt_history.remove(prompt) 
        self.prompt_history.insert(0, prompt)
        self._save_prompt_history()
    
    def _center_toplevel_window(self, toplevel_window):
        toplevel_window.update_idletasks() 
        main_win_x = self.winfo_x()
        main_win_y = self.winfo_y()
        main_win_w = self.winfo_width()
        main_win_h = self.winfo_height()
        popup_w = toplevel_window.winfo_width()
        popup_h = toplevel_window.winfo_height()
        x_pos = main_win_x + (main_win_w // 2) - (popup_w // 2)
        y_pos = main_win_y + (main_win_h // 2) - (popup_h // 2)
        toplevel_window.geometry(f"+{x_pos}+{y_pos}")

    def _show_prompt_history(self):
        if not self.prompt_history:
            custom_message_dialog(parent=self, title="Prompt History", message="No saved prompts found.", font=self.main_font)
            return

        history_window = tk.Toplevel(self)
        history_window.title("Prompt History")
        history_window.transient(self)
        history_window.grab_set()

        listbox_frame = tk.Frame(history_window, padx=5, pady=5)
        listbox_frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(listbox_frame, font=self.main_font, height=15, width=100)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        for prompt in self.prompt_history: listbox.insert(tk.END, prompt)

        def _on_prompt_selected(event=None):
            selection_indices = listbox.curselection()
            if not selection_indices: return
            selected_prompt = listbox.get(selection_indices[0])
            self.prompt_text_widget.delete("1.0", tk.END)
            self.prompt_text_widget.insert("1.0", selected_prompt)
            history_window.destroy()

        listbox.bind("<Double-1>", _on_prompt_selected)

        button_frame = ttk.Frame(history_window)
        button_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Button(button_frame, text="Select", command=_on_prompt_selected).pack(side="right")
        ttk.Button(button_frame, text="Cancel", command=history_window.destroy).pack(side="right", padx=5)

        self._center_toplevel_window(history_window)

    def _on_generate_button_click(self):
        prompt = self.prompt_text_widget.get("1.0", tk.END).strip()
        if not prompt: return custom_message_dialog(parent=self, title="Input Error", message="Please enter a prompt.",font=self.main_font)
        self._add_prompt_to_history(prompt)
        self.generate_button.config(text="Generating...", state="disabled")
        img_width, img_height = self.image_frame.get_dimensions()
        w, h = good_dimensions( img_width, img_height, scale=self.image_scale )
        threading.Thread(target=self._run_generation_task, args=(prompt, w, h), daemon=True).start()

    def _run_generation_task(self, prompt, width, height):
        image_url = generate_image(prompt, width, height, model = MODEL_STRINGS[self.model_index][1], steps = self.n_steps,
                                   error_callback=lambda t, m : custom_message_dialog(parent=self,
                                                                                      title=t,
                                                                                      message=m,
                                                                                      font=self.main_font))
        if image_url:
            file_name = unique_name("dummy.png","generated")
            save_path = download_image(image_url, file_name, prompt,
                                       error_callback=lambda t, m : custom_message_dialog(parent=self,
                                                                                          title=t,
                                                                                          message=m,
                                                                                          font=self.main_font))
            if save_path:
                self.after(0, self.image_frame.set_image_path, save_path)
        self.after(0, self.generate_button.config, {'text':"Generate", 'state':"normal"})


if __name__ == "__main__":
    app = ImageGenerator()
    app.mainloop()
