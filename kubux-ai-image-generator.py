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
    ("FLUX.2 Pro", "black-forest-labs/FLUX.2-pro"),
    ("FLUX.1 Dev", "black-forest-labs/FLUX.2-dev"),
    ("FLUX.1 Pro", "black-forest-labs/FLUX.1-pro"),
#    ("Stable Diffusion XL 1.0", "stabilityai/stable-diffusion-xl-base-1.0"),
    ("FLUX.1 Schnell", "black-forest-labs/FLUX.1-schnell"),
    ("FLUX.1 Krea Dev", "black-forest-labs/FLUX.1-krea-dev"),
    ("FLUX.1.1 Pro", "black-forest-labs/FLUX.1.1-pro"),
    ("FLUX.1 Dev", "black-forest-labs/FLUX.1-dev"),
    ("FLUX.1 Schnell (Free)", "black-forest-labs/FLUX.1-schnell-Free"),
    ("FLUX.1 Canny (for edge based conditions)", "black-forest-labs/FLUX.1-canny"),
    ("FLUX.1 Depth (for depth based conditioning)", "black-forest-labs/FLUX.1-depth"),
    ("FLUX.1 Redux (image variation, restyling)", "black-forest-labs/FLUX.1-redux"),
    ("FLUX.1 Dev (LoRA support)", "black-forest-labs/FLUX.1-dev-lora"),
    ("FLUX.1 Kontext Dev (text and image input)", "black-forest-labs/FLUX.1-kontext-dev"),
    ("FLUX.1 Kontext Pro (text and image input)", "black-forest-labs/FLUX.1-kontext-pro"),
    ("FLUX.1 Kontext Max (text and image input)", "black-forest-labs/FLUX.1-kontext-max"),
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
NEG_PROMPT_HISTORY_FILE = os.path.join(CONFIG_DIR, "neg_prompt_history.json")
CONTEXT_HISTORY_FILE = os.path.join(CONFIG_DIR, "context_history.json")
APP_SETTINGS_FILE = os.path.join(CONFIG_DIR, "app_settings.json")    

BUTTON_RELIEF="flat"
SCALE_RELIEF="flat"
SCROLLBAR_RELIEF="flat"


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


def generate_image(prompt, width, height, model, steps, neg_prompt, context,
                   error_callback=fallback_show_error):
    client = Together(api_key=TOGETHER_API_KEY)
    try:
        response = client.images.generate(
            prompt=prompt,
            model=model,
            width=width,
            height=height,
            steps=steps,
            negative_prompt=neg_prompt,
            image_url=context
        )
        return response.data[0].url
    except Exception as e:
        message = f"Failed to download image: {e}"
        error_callback("API Error", message)
        return None

def download_image(url, file_name, prompt, neg_prompt, context, download_dir,
                   error_callback=fallback_show_error):
    key = f"{[ prompt, neg_prompt, context]}"
    prompt_dir = hashlib.sha256(key.encode('utf-8')).hexdigest()
    save_path = os.path.join(download_dir, prompt_dir, file_name)
    tmp_save_path = save_path + "-tmp"
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status() 
        dir_name = os.path.dirname(save_path)
        os.makedirs(dir_name, exist_ok=True)
        with open(tmp_save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        os.replace(tmp_save_path, save_path)

        def write_info(info_file, info):
            info_path = os.path.join( dir_name, info_file)
            try:
                with open(info_path, 'w') as file:
                    file.write(info)
            except IOError as e:
                print(f"Error writing {info} to file: {e}")
                
        write_info("prompt.txt", prompt)
        write_info("negative-prompt.txt", neg_prompt)
        write_info("context_url.txt", context)
    except Exception as e:
        try:
            os.remove(tmp_save_path)
            os.remove(save_path)
        except Exception: pass
        message = f"Failed to download image: {e}"
        error_callback("Download Error", message)
        return None
    try:
        link_path=os.path.join(download_dir, os.path.basename(file_name))
        os.symlink(save_path, link_path)
        return link_path
    except Exception as e:
        os.remove(link_path)
        message = f"Failed to link image: {e}"
        error_callback("File system error,", message)
        return None

# --- widgets ---

def get_to_root(widget):
    while widget.master is not None:
        widget = widget.master
    return widget


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
        screen_aspect_ratio = get_to_root(self).winfo_screenwidth() / get_to_root(self).winfo_screenheight()
        w, h = self.get_aspect_ratio( self.master.image_scale )
        image_aspect_ratio = w / h
        delta = screen_aspect_ratio - image_aspect_ratio
        is_close = ( -0.05 < delta ) and ( delta < 0.05 )
        if is_close:     
            settings_string = f"{w} / {h} = {(w/h):.3f} (roughly screen: {screen_aspect_ratio:.3f}) @ {self.master.n_steps} steps with {MODEL_STRINGS[self.master.model_index][1]}"
        else:
            settings_string = f"{w} / {h} ={(w/h):.3f} @ {self.master.n_steps} steps with {MODEL_STRINGS[self.master.model_index][1]}"

        self.title(settings_string)
        self.master.set_title(settings_string)
        if not self.is_fullscreen:
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


class LongMenu(tk.Toplevel):
    def __init__(self, master, default_option, other_options, font=None, x_pos=None, y_pos=None):
        super().__init__(master)
        self.overrideredirect(True) # Remove window decorations (title bar, borders)
        self.transient(master)      # Tie to master window
        # self.grab_set()             # Make it modal, redirect all input here

        self.result = default_option
        self._options = other_options

        self._main_font = font if font else ("TkDefaultFont", 12, "normal")

        self._listbox_frame = ttk.Frame(self)
        self._listbox_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self._listbox = tk.Listbox(
            self._listbox_frame,
            selectmode=tk.SINGLE,
            font=self._main_font,
            height=15
        )
        self._listbox.pack(side="left", fill="both", expand=True)

        self._scrollbar = tk.Scrollbar(self._listbox_frame, relief=SCROLLBAR_RELIEF, orient="vertical", command=self._listbox.yview)
        self._scrollbar.pack(side="right", fill="y")
        self._listbox.config(yscrollcommand=self._scrollbar.set)

        # Populate the _listbox
        for option_name in other_options:
            self._listbox.insert(tk.END, option_name)

        # --- Bindings ---
        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        self._listbox.bind("<Double-Button-1>", self._on_double_click) # Double-click to select and close
        self.bind("<Return>", self._on_return_key) # Enter key to select and close
        self.bind("<Escape>", self._cancel) # Close on Escape key
        self.bind("<FocusOut>", self._on_focus_out)
        
        # --- Positioning and Focus ---
        self.update_idletasks()
        self.grab_set() 

        if x_pos is None or y_pos is None:
            master_x = master.winfo_x()
            master_y = master.winfo_y()
            master_h = master.winfo_height()
            x_pos = master_x
            y_pos = master_y + master_h

        screen_width = self.winfo_screenwidth()
        popup_w = self.winfo_width()
        if x_pos + popup_w > screen_width:
            x_pos = screen_width - popup_w - 5 # 5 pixels margin
            
        # Adjust if menu would go off-screen downwards (or upwards if preferred)
        screen_height = self.winfo_screenheight()
        popup_h = self.winfo_height()
        if y_pos + popup_h > screen_height:
            y_pos = screen_height - popup_h - 5 # 5 pixels margin
            
        self.geometry(f"+{int(x_pos)}+{int(y_pos)}")        # Center the window relative to its master

        self._listbox.focus_set() # Set focus to the _listbox for immediate keyboard navigation
        self.wait_window(self) # Make the dialog modal until it's destroyed

    def _on_listbox_select(self, event):
        self._exit_ok()

    def _on_double_click(self, event):
        self._exit_ok()

    def _on_return_key(self, event):
        self._exit_ok()

    def _exit_ok(self):
        selected_indices = self._listbox.curselection()
        if selected_indices:
            # Store the selected directory name, not the full path yet
            self.result = self._options[selected_indices[0]]
        self.destroy()

    def _cancel(self, event=None):
        self.result = None
        self.destroy()

    def _on_focus_out(self, event):
        # If the widget losing focus is not a child of this menu (e.g., clicking outside)
        # then close the menu.
        if self.winfo_exists() and not self.focus_get() in self.winfo_children():
            self._cancel()

        
class BreadCrumNavigator(ttk.Frame):
    def __init__(self, master, on_navigate_callback=None,
                 long_press_threshold_ms=400, drag_threshold_pixels=5):
        
        super().__init__(master)
        self._on_navigate_callback = on_navigate_callback
        self._current_path = ""

        self._LONG_PRESS_THRESHOLD_MS = long_press_threshold_ms
        self._DRAG_THRESHOLD_PIXELS = drag_threshold_pixels

        self._long_press_timer_id = None
        self._press_start_time = 0
        self._press_x = 0
        self._press_y = 0
        self._active_button = None 

    def set_path(self, path):
        if not os.path.isdir(path):
            print(f"Warning: Path '{path}' is not a directory. Cannot set breadcrumbs.")
            return

        self._current_path = os.path.normpath(path)
        self._update_breadcrumbs()

    def _update_breadcrumbs(self):
        for widget in self.winfo_children():
            widget.destroy()

        btn_list = []
        current_display_path = self._current_path
        while len(current_display_path) > 1: 
            path = current_display_path
            current_display_path = os.path.dirname(path)
            btn_text = os.path.basename(path)
            if btn_text == '': 
                btn_text = os.path.sep
            btn = tk.Button(self, text=btn_text, relief=BUTTON_RELIEF, 
                            font=get_to_root(self).main_font)
            btn.path = path
            btn.bind("<ButtonPress-1>", self._on_button_press)
            btn.bind("<ButtonRelease-1>", self._on_button_release)
            btn.bind("<Motion>", self._on_button_motion)
            btn_list.insert( 0, btn )

        btn_text="//"
        btn = tk.Button(self, text=btn_text, relief=BUTTON_RELIEF, 
                        font=get_to_root(self).main_font)
        btn.path = current_display_path
        btn.bind("<ButtonPress-1>", self._on_button_press)
        btn.bind("<ButtonRelease-1>", self._on_button_release)
        btn.bind("<Motion>", self._on_button_motion)
        btn_list.insert( 0, btn )

        dummy_frame = tk.Frame(self)
        dummy_frame.pack(side="right", fill="x", expand=True)
        for i, btn in enumerate( reversed(btn_list) ):
            btn.pack(side="right")
            if i + 1< len(btn_list):
                ttk.Label(self, text="/").pack(side="right")
            if i == 0:
                btn.bind("<ButtonPress-1>", self._on_button_press_menu)

    def _trigger_navigate(self, path):
        if self._on_navigate_callback:
            self._on_navigate_callback(path)

    def _on_button_press_menu(self, event):
        self._show_subdirectory_menu( event.widget )
            
    def _on_button_press(self, event):
        self._press_start_time = time.time()
        self._press_x, self._press_y = event.x_root, event.y_root
        self._active_button = event.widget
        self._long_press_timer_id = self.after(self._LONG_PRESS_THRESHOLD_MS,
                                               lambda: self._on_long_press_timeout(self._active_button))

    def _on_button_release(self, event):
        if self._long_press_timer_id:
            self.after_cancel(self._long_press_timer_id)
            self._long_press_timer_id = None

        if self._active_button:
            dist = (abs(event.x_root - self._press_x)**2 + abs(event.y_root - self._press_y)**2)**0.5
            if dist < self._DRAG_THRESHOLD_PIXELS:
                if (time.time() - self._press_start_time) * 1000 < self._LONG_PRESS_THRESHOLD_MS:
                    path = self._active_button.path
                    if path and self._on_navigate_callback:
                        self._on_navigate_callback(path)
            self._active_button = None

    def _on_button_motion(self, event):
        if self._active_button and self._long_press_timer_id:
            dist = (abs(event.x_root - self._press_x)**2 + abs(event.y_root - self._press_y)**2)**0.5
            if dist > self._DRAG_THRESHOLD_PIXELS:
                self.after_cancel(self._long_press_timer_id)
                self._long_press_timer_id = None
                self._active_button = None

    def _on_long_press_timeout(self, button):
        if self._active_button is button:
            self._show_subdirectory_menu(button)
            self._long_press_timer_id = None

    def _show_subdirectory_menu(self, button):
        path = button.path
        selected_path = path

        all_entries = os.listdir(path)
        subdirs = []
        hidden_subdirs = []
        for entry in all_entries:
            full_path = os.path.join( path, entry )
            if os.path.isdir( full_path ):
                if entry.startswith('.'):
                    hidden_subdirs.append(entry)
                else:
                    subdirs.append(entry)
        subdirs.sort()
        hidden_subdirs.sort()
        sorted_subdirs = subdirs + hidden_subdirs
        
        if sorted_subdirs:
            button_x = button.winfo_rootx()
            button_y = button.winfo_rooty()
            button_height = button.winfo_height()
            menu_x = button_x
            menu_y = button_y + button_height
            selector_dialog = LongMenu(
                button,
                None,
                sorted_subdirs,
                font=get_to_root(self).main_font,
                x_pos=menu_x,
                y_pos=menu_y
            )
            selected_name = selector_dialog.result
            if selected_name:
                selected_path = os.path.join(path, selected_name)
                
        self._trigger_navigate(selected_path)

                
class ImageGenerator(tk.Tk):
    def __init__(self):
        super().__init__(className="kubux-ai-image-generator")
        self.title("kubux AI image generator")
        self.configure(background=self.cget("background"))
        self._gallery_scale_update_after_id = None
        self._ui_scale_job = None

        self.prompt_history = self._load_history(PROMPT_HISTORY_FILE)
        self.neg_prompt_history = self._load_history(NEG_PROMPT_HISTORY_FILE)
        self.context_history = self._load_history(CONTEXT_HISTORY_FILE)
        self._load_app_settings()
        
        font_name, font_size = get_linux_system_ui_font_info()
        self.base_font_size = font_size
        self.main_font = tkFont.Font(family=font_name, size=int(self.base_font_size * self.ui_scale))
        self.geometry(self.main_win_geometry)

        self._create_widgets()
        self.update_idletasks()
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.update_idletasks()

    def _load_history(self, file):
        history = []
        try:
            if os.path.exists(file):
                with open(file, 'r') as f:
                    history = json.load(f)
        except (json.JSONDecodeError, Exception):
            history = []
        return history
        
    def _save_history(self, file, history, name):
        try:
            with open(file, 'w') as f:
                json.dump(history, f, indent=4)
        except Exception as e: print(f"Error saving {name}: {e}")

    def _save_all_histories(self):
        self._save_history(PROMPT_HISTORY_FILE, self.prompt_history, "prompt history")
        self._save_history(NEG_PROMPT_HISTORY_FILE, self.neg_prompt_history, "negative prompt history")
        self._save_history(CONTEXT_HISTORY_FILE, self.context_history, "context history")

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

        self.download_dir = self.app_settings.get("download_dir", DOWNLOAD_DIR)
        self.ui_scale = self.app_settings.get("ui_scale", 1.0)
        self.main_win_geometry = self.app_settings.get("main_win_geometry", "1200x800")
        self.image_win_geometry = self.app_settings.get("image_win_geometry", "1200x800")
        self.n_steps = self.app_settings.get("n_steps", 28)
        self.image_scale = self.app_settings.get("image_scale", 1.0)
        self.model_index = self.app_settings.get("model_index", 0 )
        self.sash_pos_top = self.app_settings.get("sash_pos_top", 200)
        self.sash_pos_bot = self.app_settings.get("sash_pos_bot", 400)
        
    def _save_app_settings(self):
        try:
            if not hasattr(self, 'app_settings'):
                self.app_settings = {}

            self.app_settings["download_dir"] = self.download_dir
            self.app_settings["ui_scale"] = self.ui_scale
            self.app_settings["main_win_geometry"] = self.geometry()
            self.app_settings["image_win_geometry"] = self.image_frame.geometry()
            self.app_settings["n_steps"] = self.n_steps
            self.app_settings["image_scale"] = self.image_scale
            self.app_settings["model_index"] = self.model_index
            self.app_settings["sash_pos_top"] = self.paned_win.sashpos(0)
            self.app_settings["sash_pos_bot"] = self.paned_win.sashpos(1)

            with open(APP_SETTINGS_FILE, 'w') as f:
                json.dump(self.app_settings, f, indent=4)
        except Exception as e:
            print(f"Error saving app settings: {e}")

    def _on_closing(self):
        self._save_history(PROMPT_HISTORY_FILE, self.prompt_history, "prompt history")
        self._save_history(NEG_PROMPT_HISTORY_FILE, self.neg_prompt_history, "negative prompt history")
        self._save_history(CONTEXT_HISTORY_FILE, self.context_history, "context history")
        self._save_app_settings()
        self.destroy() 

    def _create_widgets(self):
        self.style = ttk.Style()
        self.style.configure('.', font=self.main_font)
        
        self.style.configure('Sash.TPanedwindow', sashthickness=10)
        self.style.configure('TButton', relief="flat")
        self.style.configure('TMenubutton', relief="flat")
        
        self.main_container = ttk.Frame(self)
        self.main_container.pack(side="top", fill="both", expand=True, padx=5, pady=(5, 0))

        if True:
            model_frame = ttk.Frame(self.main_container)
            model_frame.pack(side="top", expand=False, fill="x", pady=(5, 5), padx=(2,2))
            self.model_menubutton = ttk.Menubutton(model_frame, text=MODEL_STRINGS[self.model_index][0], style='TMenubutton')
            model_menu = tk.Menu(self.model_menubutton, font=self.main_font)  # Menu cannot be replaced with ttk
            self.model_menubutton.config(menu=model_menu)
            for i, (entry, model) in enumerate(MODEL_STRINGS):
                model_menu.add_command(label=entry, command=lambda idx = i : self._set_model_index(idx))
            self.model_menubutton.pack(side="left", fill="x", expand=True, padx=(2,2), pady=(5,5))
        if True:
            controls_frame = ttk.Frame(self.main_container)
            controls_frame.pack(side="top", expand=False, fill="x", pady=(5, 5), padx=5)
            if True:
                dummy_G_frame = ttk.Frame(controls_frame)
                dummy_G_frame.pack(side="left", expand=True, fill="x")
                self.generate_button = ttk.Button(dummy_G_frame, text="Generate", style='TButton', command=self._on_generate_button_click)
                self.generate_button.pack(side="left", padx=(2,0))
                dummy_A_label = ttk.Label(controls_frame, text="# steps:", style='TLabel')
                dummy_A_label.pack(side="left", padx=(24,0))
                dummy_A_frame = ttk.Frame(controls_frame)
                dummy_A_frame.pack(side="left", expand=True, fill="x")
                
                # ttk doesn't have Scale with showvalue; using a workaround
                self.steps_slider = tk.Scale(
                    dummy_A_frame, from_=1, to=64, resolution=1, orient="horizontal", showvalue=False
                )
                self.steps_slider.set(self.n_steps)
                self.steps_slider.config(command=self._update_n_steps_scale)
                self.steps_slider.pack(anchor="w")
                
                dummy_B_label = ttk.Label(controls_frame, text="size:", style='TLabel')
                dummy_B_label.pack(side="left", padx=(24,0))
                dummy_B_frame = ttk.Frame(controls_frame)
                dummy_B_frame.pack(side="left", expand=True, fill="x")
                
                self.scale_slider = tk.Scale(
                    dummy_B_frame, from_=0.2, to=1.0, resolution=0.025, orient="horizontal", showvalue=False
                )
                self.scale_slider.set(self.image_scale)
                self.scale_slider.config(command=self._update_image_scale)
                self.scale_slider.pack(anchor="w")
                
                dummy_C_frame = ttk.Frame(controls_frame)
                dummy_C_frame.pack(side="right", expand=False, fill="x")
                
                self.ui_slider = tk.Scale(
                    dummy_C_frame, from_=0.5, to=3.5, resolution=0.1, orient="horizontal", showvalue=False
                )
                self.ui_slider.set(self.ui_scale)
                self.ui_slider.config(command=self._update_ui_scale)
                self.ui_slider.pack(anchor="e")
                
                dummy_C_label = ttk.Label(controls_frame, text="UI:", style='TLabel')
                dummy_C_label.pack(side="right", padx=(12,0))

        if True:
            self.settings_label = ttk.Label(self.main_container, style='TLabel')
            self.settings_label.pack(side="top", padx=(2,2))

        if True:
            self.navigator = BreadCrumNavigator(
                self.main_container,
                on_navigate_callback=self._update_download_dir
            )
            self.navigator.pack(side="bottom", fill="x", expand=True, padx=5)            
            self.navigator.set_path(self.download_dir)
            
        if True:
            # Use style to control sash appearance
            self.paned_win = ttk.PanedWindow(self.main_container, orient="vertical", style='Sash.TPanedwindow')
            self.paned_win.pack(side="bottom", expand=True, fill="both")
            if True:
                prompt_button = ttk.Button(self, text="Image Prompt", style='TButton',
                                           command=self._select_from_prompt_history)
                prompt_frame_outer = ttk.LabelFrame(self.paned_win, labelwidget=prompt_button)
                # Setting the minimum size for the pane
                prompt_frame_outer.configure(height=200)
                self.paned_win.add(prompt_frame_outer, weight=1)
                prompt_frame_inner = ttk.Frame(prompt_frame_outer)
                prompt_frame_inner.pack(fill="both", expand=True, padx=5, pady=5)
                
                # ttk doesn't have Text widget, using tk.Text is necessary
                self.prompt_text_widget = tk.Text(prompt_frame_inner, wrap="word", relief="sunken", borderwidth=2, font=self.main_font)
                self.prompt_text_widget.pack(fill="both", expand=True)
                
            if True:
                neg_prompt_button = ttk.Button(self, text="Negative Prompt", style='TButton',
                                              command=self._select_from_neg_prompt_history)
                neg_prompt_frame_outer = ttk.LabelFrame(self.paned_win, labelwidget=neg_prompt_button)
                # Setting the minimum size for the pane
                neg_prompt_frame_outer.configure(height=200)
                self.paned_win.add(neg_prompt_frame_outer, weight=1)
                neg_prompt_frame_inner = ttk.Frame(neg_prompt_frame_outer)
                neg_prompt_frame_inner.pack(fill="both", expand=True, padx=5, pady=5)
                
                self.neg_prompt_text_widget = tk.Text(neg_prompt_frame_inner, wrap="word", relief="sunken", borderwidth=2, font=self.main_font)
                self.neg_prompt_text_widget.pack(fill="both", expand=True)

            if True:
                context_button = ttk.Button(self, text="Image URL (context)", style='TButton',
                                            command=self._select_from_context_history)
                context_frame_outer = ttk.LabelFrame(self.paned_win, labelwidget=context_button)
                # Setting the minimum size for the pane
                context_frame_outer.configure(height=200)
                self.paned_win.add(context_frame_outer, weight=1)
                context_frame_inner = ttk.Frame(context_frame_outer)
                context_frame_inner.pack(fill="both", expand=True, padx=5, pady=5)
                
                self.context_text_widget = tk.Text(context_frame_inner, wrap="word", relief="sunken", borderwidth=2, font=self.main_font)
                self.context_text_widget.pack(fill="both", expand=True)


        self.update_idletasks()
        self.paned_win.sashpos( 0, self.sash_pos_top )
        self.paned_win.sashpos( 1, self.sash_pos_bot )
                
        self.spawn_image_frame()

    def set_title(self, title):
        self.settings_label.config(text=title)
        
    def spawn_image_frame(self):
        self.image_frame = FullscreenImageViewer(self, title="set aspect ratio")

    def _update_download_dir(self, path):
        self.download_dir = path;
        self.navigator.set_path( self.download_dir )
        
    def _update_ui_scale(self, value):
        if self._ui_scale_job: self.after_cancel(self._ui_scale_job)
        self._ui_scale_job = self.after(400, lambda: self._do_update_ui_scale(float(value)))

    def _update_image_scale(self, value):
        self.image_scale = float(value)
        self.image_frame._update_image()

    def _update_n_steps_scale(self, value):
        self.n_steps = int(float(value))
        self.image_frame._update_image()
        
    def _set_model_index(self, index):
        self.model_index = index;
        self.model_menubutton.config( text=MODEL_STRINGS[self.model_index][0] )
        self.image_frame._update_image()
        
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
    
    def _add_to_history(self, history, entry):
        while entry in history: history.remove(entry)
        if entry:
            history.insert(0, entry)
    
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

    def _select_from_history(self, history, text_widget, name):
        if not history:
            custom_message_dialog(parent=self, title="name", message="No saved items found.", font=self.main_font)
            return

        history_window = tk.Toplevel(self)
        history_window.title(name)
        history_window.transient(self)
        history_window.grab_set()

        listbox_frame = tk.Frame(history_window, padx=5, pady=5)
        listbox_frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(listbox_frame, font=self.main_font, height=15, width=100)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        for entry in history: listbox.insert(tk.END, entry)

        def _on_prompt_selected(event=None):
            selection_indices = listbox.curselection()
            if not selection_indices: return
            selected_entry = listbox.get(selection_indices[0])
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", selected_entry)
            history_window.destroy()

        listbox.bind("<Double-1>", _on_prompt_selected)

        button_frame = ttk.Frame(history_window)
        button_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Button(button_frame, text="Select", command=_on_prompt_selected).pack(side="right")
        ttk.Button(button_frame, text="Cancel", command=history_window.destroy).pack(side="right", padx=5)

        self._center_toplevel_window(history_window)

    def _select_from_prompt_history(self):
        self._select_from_history( self.prompt_history, self.prompt_text_widget, "prompt history")        

    def _select_from_neg_prompt_history(self):
        self._select_from_history( self.neg_prompt_history, self.neg_prompt_text_widget, "neg_prompt prompt history")

    def _select_from_context_history(self):
        self._select_from_history( self.context_history, self.context_text_widget, "context history")
        
    def _on_generate_button_click(self):
        prompt = self.prompt_text_widget.get("1.0", tk.END).strip()
        if not prompt: return custom_message_dialog(parent=self, title="Input Error", message="Please enter a prompt.",font=self.main_font)
        neg_prompt = self.neg_prompt_text_widget.get("1.0", tk.END).strip()
        context = self.context_text_widget.get("1.0", tk.END).strip()
        self._add_to_history(self.prompt_history, prompt)
        self._add_to_history(self.neg_prompt_history, neg_prompt)
        self._add_to_history(self.context_history, context)
        self._save_all_histories()
        self.generate_button.config(text="Generating...", state="disabled")
        img_width, img_height = self.image_frame.get_dimensions()
        w, h = good_dimensions( img_width, img_height, scale=self.image_scale )
        threading.Thread(target=self._run_generation_task, args=(prompt, w, h, neg_prompt, context), daemon=True).start()

    def _run_generation_task(self, prompt, width, height, neg_prompt, context):
        image_url = generate_image(prompt, width, height, model = MODEL_STRINGS[self.model_index][1],
                                   steps = self.n_steps,
                                   neg_prompt = neg_prompt,
                                   context = context,
                                   error_callback=lambda t, m : custom_message_dialog(parent=self,
                                                                                      title=t,
                                                                                      message=m,
                                                                                      font=self.main_font))
        if image_url:
            file_name = unique_name("dummy.png","generated")
            save_path = download_image(image_url, file_name, prompt, neg_prompt, context, self.download_dir,
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
