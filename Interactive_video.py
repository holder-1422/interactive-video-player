########################################################################
# Interactive Video player
# Version v2.9.8 (YAML version) –
# Date 02/24/2025
# Created By Jeremy Holder (Modified by ChatGPT)
########################################################################
import tkinter as tk
from tkinter import messagebox, Scale
from PIL import Image, ImageTk
import yaml   # <-- Added for YAML support
import os
import sys
import vlc

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class InteractiveVideoApp:
    def __init__(self, root, config_file):
        self.root = root
        self.root.title("Interactive Video Player")
        
        # Load configuration from YAML file.
        try:
            config_path = resource_path(config_file)
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print("Failed to load configuration:", e)
            self.config = {}
        
        # Initialize VLC with Direct3D9 and disable hardware acceleration.
        self.instance = vlc.Instance("--no-xlib", "--file-caching=2000", "--network-caching=2000",
                                     "--vout=direct3d9", "--avcodec-hw=none")
        self.player = self.instance.media_player_new()
        
        # Attach VLC end-of-video event after initializing the media player
        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_video_end)
        
        # Configure root window using grid.
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.columnconfigure(0, weight=1)
        
        # Main frame (contains video and options)
        self.main_frame = tk.Frame(root)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Options frame on the left (fixed width)
        self.options_frame = tk.Frame(self.main_frame, width=250)
        self.options_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.options_frame.pack_propagate(False)
        
        # Video container frame on the right.
        self.video_container = tk.Frame(self.main_frame, bg="black")
        self.video_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Video frame inside the container (for video output)
        self.video_frame = tk.Frame(self.video_container, bg="black")
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a Toplevel for the semi-transparent background overlay.
        self.interrupt_bg = tk.Toplevel(self.root)
        self.interrupt_bg.overrideredirect(True)
        self.interrupt_bg.attributes("-alpha", 0.7)  # 70% opaque background
        self.interrupt_bg.attributes("-topmost", True)
        self.interrupt_bg.configure(bg='gray')
        
        # Create a Toplevel for the fully opaque interruption choices.
        self.interrupt_fg = tk.Toplevel(self.root)
        self.interrupt_fg.overrideredirect(True)
        self.interrupt_fg.attributes("-topmost", True)
        self.interrupt_fg.configure(bg='white')
        
        # Normal section for non-temporary choices in the options_frame.
        self.normal_section = tk.Frame(self.options_frame)
        self.normal_section.pack(side=tk.TOP, fill=tk.X)
        
        # Permanent controls frame at the bottom of options.
        self.options_controls_frame = tk.Frame(self.options_frame)
        self.options_controls_frame.pack(side="bottom", fill="x")
        self.left_pause_button = tk.Button(self.options_controls_frame, text="Pause", command=self.toggle_pause)
        self.left_pause_button.pack(pady=5)
        
        # Bottom frame for seek bar, pause/play, volume, and mute.
        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.grid(row=1, column=0, sticky="ew")
        self.bottom_frame.columnconfigure(0, weight=1)
        self.bottom_frame.columnconfigure(1, weight=0)
        self.bottom_frame.columnconfigure(2, weight=0)
        self.bottom_frame.columnconfigure(3, weight=0)
        
        self.seek_var = tk.DoubleVar()
        self.seek_slider = Scale(self.bottom_frame, from_=0, to=100, orient="horizontal",
                                 variable=self.seek_var, command=self.seek_video)
        self.seek_slider.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.is_paused = False
        self.pause_button = tk.Button(self.bottom_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.volume_var = tk.IntVar(value=100)
        self.volume_slider = Scale(self.bottom_frame, from_=0, to=100, orient="horizontal",
                                   variable=self.volume_var, command=self.set_volume, label="Volume")
        self.volume_slider.grid(row=0, column=2, padx=5, pady=5)
        
        self.is_muted = False
        self.mute_button = tk.Button(self.bottom_frame, text="Mute", command=self.toggle_mute)
        self.mute_button.grid(row=0, column=3, padx=5, pady=5)
        
        self.current_video = self.config.get("start", "")
        self.resume_video = None  # Holds the base scene ID.
        self.resume_time = 0      # Holds the playback time of the base video.
        
        self.skip_button = None  # For skipping interruptions.
        self.image_refs = []     # To hold image references.
        
        # Initialize interrupt attributes to prevent errors
        self.interrupt_fg = None
        self.interrupt_bg = None
        
        
        # Start playing video and set up overlays.
        self.play_video()
        # Periodically update overlay positions.
        self.periodic_update_overlay()
        


    def show_cq_options_overlay(self):
        """Display a centered overlay for Continue/Question scenes attached to the video container after the video ends."""
        print("[DEBUG] Triggered show_cq_options_overlay()")
        self.clear_all_overlays()
    
        # Create dimming background overlay attached to the video container
        self.cq_bg_overlay = tk.Frame(self.video_container, bg='black')
        self.cq_bg_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.cq_bg_overlay.lower()
    
        # Create overlay frame for choices attached to the video container
        self.cq_options_frame = tk.Frame(self.video_container, bg='white')
    
        # Load choices from YAML config
        options_data = self.config.get("options", {}).get(self.current_video, {})
        choices = options_data.get("choices", {})
    
        button_frame = tk.Frame(self.cq_options_frame, bg='white')
        button_frame.pack(padx=20, pady=20)
    
        num_choices = len([opt for opt in choices.items() if not opt[1].get("temporary", False)])
        frame_width = 300 * num_choices  # Dynamically scale width based on number of buttons
        frame_height = 200  # Taller to prevent squished appearance
    
        # Calculate position (centered horizontally, 60% down the screen)
        vc_width = self.video_container.winfo_width()
        vc_height = self.video_container.winfo_height()
        pos_x = (vc_width - frame_width) // 2
        pos_y = int(vc_height * 0.6)
    
        self.cq_options_frame.place(x=pos_x, y=pos_y, width=frame_width, height=frame_height)
    
        # Arrange buttons side by side
        for idx, (text, option) in enumerate(choices.items()):
            if not option.get("temporary", False):
                print(f"[DEBUG] Creating button for choice: {text}")
                button = self.create_option_button(button_frame, text, option)
                button.grid(row=0, column=idx, padx=10, pady=10)
    
        # Show the overlay
        self.root.after(100, self._reveal_cq_overlay)
    
    
    
    def update_overlay_position(self):
        """Periodically update the overlay position based on video container size."""
        self.video_container.update_idletasks()
        vc_width = self.video_container.winfo_width()
        vc_height = self.video_container.winfo_height()
    
        # Calculate position (centered, 60% down the screen)
        frame_width = 300
        frame_height = 100
        pos_x = (vc_width - frame_width) // 2
        pos_y = int(vc_height * 0.6)
    
        print(f"[DEBUG] Updated overlay position: x={pos_x}, y={pos_y}, width={frame_width}, height={frame_height}")
    
        self.cq_options_frame.place(x=pos_x, y=pos_y, width=frame_width, height=frame_height)
        self.root.after(1000, self.update_overlay_position)
    


    def _reveal_cq_overlay(self):
        """Reveal the overlay after the video ends."""
        print("[DEBUG] Revealing overlay now.")
        if hasattr(self, 'cq_bg_overlay') and hasattr(self, 'cq_options_frame'):
            self.cq_bg_overlay.lift()
            self.cq_options_frame.lift()
    
       

    def handle_video_end(self):
        """Handle the video end based on the scene type."""
        print("[DEBUG] Handling video end logic.")
        if self.resume_video:
            print("[DEBUG] Resuming interrupted video.")
            self.root.after(500, self.skip_interrupt)
        else:
            scene_type = self.get_scene_type()
            print(f"[DEBUG] Scene type detected: {scene_type}")
            if scene_type in ["continue", "question"]:
                self.show_cq_options_overlay()
            elif scene_type == "main":
                self.show_main_options_overlay()
            else:
                print("[DEBUG] Unknown scene type. Showing normal section.")
                self.clear_subframes()
                self.show_normal_section()
    
    def clear_all_overlays(self):
        """Clear all overlays from the video player."""
        print("[DEBUG] Clearing all overlays.")
    
        # Clear Continue/Question overlay if it exists
        if hasattr(self, 'cq_bg_overlay'):
            self.cq_bg_overlay.destroy()
            del self.cq_bg_overlay
    
        if hasattr(self, 'cq_options_frame'):
            self.cq_options_frame.destroy()
            del self.cq_options_frame
    
        # Clear interrupt overlays if they exist
        if self.interrupt_fg:
            self.interrupt_fg.destroy()
            self.interrupt_fg = None
    
        if self.interrupt_bg:
            self.interrupt_bg.destroy()
            self.interrupt_bg = None
    
    
    

    def on_video_end(self, event):
        """Callback triggered when VLC reports the video has ended."""
        print("[DEBUG] VLC Event Triggered: Video has ended.")
        self.root.after(0, self.handle_video_end)  # Ensure it runs on the Tkinter main thread

    def on_video_end(self, event):
        """Callback triggered when VLC reports the video has ended."""
        print("[DEBUG] VLC Event Triggered: Video has ended.")
        self.root.after(0, self.handle_video_end)  # Ensures running on Tkinter's main thread
    
    
    def clear_interrupt_overlays(self):
        """Safely clear temporary interrupt overlays."""
        if self.interrupt_fg:
            self.interrupt_fg.place_forget()
            self.interrupt_fg = None
    
        if self.interrupt_bg:
            self.interrupt_bg.place_forget()
            self.interrupt_bg = None
    
        
    
    
    def periodic_update_overlay(self):
        """Safely update interrupt overlay position if they exist."""
        if self.interrupt_fg and self.interrupt_bg:
            self.interrupt_bg.deiconify()
            self.interrupt_fg.deiconify()
            self.update_interrupt_geometry()
        self.root.after(1000, self.periodic_update_overlay)
    
    
    def update_interrupt_geometry(self):
        """Position both interruption overlays based on the size of the foreground content."""
        try:
            self.interrupt_fg.update_idletasks()
            req_width = self.interrupt_fg.winfo_reqwidth()
            req_height = self.interrupt_fg.winfo_reqheight()
            margin = 10
            vc_x = self.video_container.winfo_rootx()
            vc_y = self.video_container.winfo_rooty()
            vc_width = self.video_container.winfo_width()
            fg_x = vc_x + vc_width - req_width - margin
            fg_y = vc_y + margin
            self.interrupt_fg.geometry(f"{req_width}x{req_height}+{fg_x}+{fg_y}")
            border = 4
            bg_width = req_width + 2 * border
            bg_height = req_height + 2 * border
            bg_x = fg_x - border
            bg_y = fg_y - border
            self.interrupt_bg.geometry(f"{bg_width}x{bg_height}+{bg_x}+{bg_y}")
        except Exception as e:
            print("Error updating overlay geometry:", e)
    
    def temporary_choices_exist(self, scene_id=None):
        if scene_id is None:
            scene_id = self.current_video
        options_data = self.config.get("options", {}).get(scene_id, {})
        choices = options_data.get("choices", {})
        return any(choice.get("temporary", False) for choice in choices.values())
    
    def get_scene_type(self):
        options_data = self.config.get("options", {}).get(self.current_video, {})
        return options_data.get("scene_type", "").lower()
    
    def get_scene_heading(self, options_data, section):
        scene_type = options_data.get("scene_type", "").lower()
        if section == "interrupt":
            return options_data.get("interrupt_heading", "")
        else:
            if scene_type == "continue":
                return options_data.get("continue_heading", "")
            elif scene_type == "question":
                return options_data.get("question_heading", "")
            else:
                return options_data.get("heading", "")
    
    def toggle_pause(self, event=None):
        self.player.pause()
        self.is_paused = not self.is_paused
        new_text = "Play" if self.is_paused else "Pause"
        self.pause_button.config(text=new_text)
        self.left_pause_button.config(text=new_text)
    
    def set_volume(self, value):
        volume = int(value)
        self.player.audio_set_volume(volume)
    
    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.player.audio_set_mute(self.is_muted)
        self.mute_button.config(text="Unmute" if self.is_muted else "Mute")
    
    def play_video(self, start_time=None):
        """Play the video and set up VLC event detection."""
        self.clear_interrupt_overlays()
        self.clear_subframes()
        
        video_path = resource_path(self.config.get("videos", {}).get(self.current_video, ""))
        if video_path and os.path.exists(video_path):
            media = self.instance.media_new(video_path)
            self.player.stop()
            self.player.set_hwnd(self.video_frame.winfo_id())
            self.player.set_media(media)
    
            # Attach the end-of-video event after initializing the media player
            self.event_manager = self.player.event_manager()
            self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_video_end)
    
            self.player.play()
            self.set_volume(self.volume_var.get())
            self.root.after(500, self.adjust_window_size)
    
            # Trigger overlay detection periodically
            self.root.after(500, self.update_seek_bar)
    
            if self.get_scene_type() == "main":
                self.show_normal_section()
    
            base_scene = self.resume_video if self.resume_video else self.current_video
            if self.temporary_choices_exist(base_scene):
                self.show_interrupt_section(scene_id=base_scene)
                if self.resume_video:
                    self.ensure_skip_button()
            else:
                self.hide_skip_button()
                self.clear_interrupt_overlays()
    
            if start_time is not None:
                self.player.pause()
                self.root.after(50, lambda: self.player.set_time(start_time))
                self.root.after(100, lambda: self.player.play())
        else:
            messagebox.showerror("Error", f"Video file not found: {video_path}")
    
    
    def adjust_window_size(self):
        width = self.player.video_get_width()
        height = self.player.video_get_height()
        if width > 0 and height > 0:
            self.video_frame.config(width=width, height=height)
    

    
    def auto_advance_main_scene(self, next_scene_id):
        if self.player.get_state() == vlc.State.Ended:
            self.current_video = next_scene_id
            self.clear_options()
            self.clear_subframes()
            self.play_video()
    
    def hide_skip_button(self):
        if self.skip_button and self.skip_button.winfo_exists():
            self.skip_button.destroy()
            self.skip_button = None
    
    def ensure_skip_button(self):
        if not self.skip_button or not self.skip_button.winfo_exists():
            self.skip_button = tk.Button(self.interrupt_fg, text="Skip Interruption",
                                          command=self.skip_interrupt, wraplength=230)
            self.skip_button.pack(pady=10)
    
    def skip_interrupt(self):
        if self.resume_video:
            base_scene = self.resume_video
            self.current_video = base_scene
            self.resume_video = None
            saved_time = self.resume_time
            self.resume_time = 0
            self.clear_subframes()
            self.play_video(start_time=saved_time)
    
    def clear_options(self):
        for widget in list(self.options_frame.winfo_children()):
            if widget not in [self.options_controls_frame, self.normal_section]:
                if widget.winfo_exists():
                    widget.destroy()
        self.image_refs = []
    
    def clear_subframes(self):
        """Clear any subframes including interrupt overlays."""
        if self.interrupt_fg:
            try:
                for widget in list(self.interrupt_fg.winfo_children()):
                    widget.destroy()
            except Exception as e:
                print(f"[DEBUG] Error clearing interrupt_fg widgets: {e}")
    
        if self.interrupt_bg:
            try:
                self.interrupt_fg.withdraw()
                self.interrupt_bg.withdraw()
            except Exception as e:
                print(f"[DEBUG] Error withdrawing interrupt overlays: {e}")
    
        # Clear any other subframes if necessary
        if hasattr(self, 'cq_options_frame'):
            try:
                self.cq_options_frame.destroy()
            except Exception as e:
                print(f"[DEBUG] Error clearing cq_options_frame: {e}")

    
    def update_seek_bar(self):
        if self.player.get_length() > 0:
            current_time = self.player.get_time()
            self.seek_var.set((current_time / self.player.get_length()) * 100)
        self.root.after(1000, self.update_seek_bar)
    
    def seek_video(self, value):
        if self.player.get_length() > 0:
            new_time = (float(value) / 100) * self.player.get_length()
            self.player.set_time(int(new_time))
    
    def create_option_button(self, parent, text, option):
        """Create a styled button with text and image."""
        bg_color = "#007ACC" if not option.get("temporary", False) else "#FF6666"
    
        # Load and attach the image
        image_path = option.get("image")
        if image_path:
            full_image_path = resource_path(image_path)
            if os.path.exists(full_image_path):
                img = Image.open(full_image_path)
                img = img.resize((80, 80), Image.LANCZOS)  # Resize image
                photo = ImageTk.PhotoImage(img)
                button = tk.Button(
                    parent,
                    text=text,
                    image=photo,
                    compound=tk.TOP,  # Image on top, text below
                    command=lambda opt=option: self.handle_option(opt),
                    bg=bg_color,
                    fg="white",
                    font=("Helvetica", 10, "bold"),
                    wraplength=150,
                    relief=tk.RAISED,
                    bd=3
                )
                button.image = photo  # Keep a reference to prevent garbage collection
            else:
                print(f"[DEBUG] Image not found: {image_path}")
                button = tk.Button(
                    parent,
                    text=text,
                    command=lambda opt=option: self.handle_option(opt),
                    bg=bg_color,
                    fg="white",
                    font=("Helvetica", 10, "bold"),
                    wraplength=150,
                    relief=tk.RAISED,
                    bd=3
                )
        else:
            button = tk.Button(
                parent,
                text=text,
                command=lambda opt=option: self.handle_option(opt),
                bg=bg_color,
                fg="white",
                font=("Helvetica", 10, "bold"),
                wraplength=150,
                relief=tk.RAISED,
                bd=3
            )
        
        return button
    
    
    def create_option_frame(self, text, option, parent):
        frame = tk.Frame(parent, bg='white')
        frame.pack(pady=5)
        image_path = option.get("image")
        if image_path:
            full_image_path = resource_path(image_path)
            if os.path.exists(full_image_path):
                try:
                    img = Image.open(full_image_path)
                    img = img.resize((119, 158), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    lbl = tk.Label(frame, image=photo, bg='white')
                    lbl.photo = photo
                    lbl.pack()
                    self.image_refs.append(photo)
                except Exception as e:
                    print(f"Error loading image {full_image_path}: {e}")
            else:
                print(f"Image not found: {full_image_path}")
        self.create_option_button(frame, text, option)
    
    def show_interrupt_section(self, scene_id=None):
        """Display interrupt options as an overlay."""
        if not self.interrupt_fg or not self.interrupt_bg:
            # Re-initialize if not already set
            self.interrupt_fg = tk.Frame(self.video_container, bg='white')
            self.interrupt_fg.place_forget()
    
            self.interrupt_bg = tk.Frame(self.video_container, bg='black')
            self.interrupt_bg.place_forget()
    
        if scene_id is None:
            scene_id = self.current_video
    
        options_data = self.config.get("options", {}).get(scene_id, {})
        choices = options_data.get("choices", {})
    
        for widget in list(self.interrupt_fg.winfo_children()):
            widget.destroy()
    
        for text, option in choices.items():
            if option.get("temporary", False):
                button = self.create_option_button(self.interrupt_fg, text, option)
                button.pack(padx=5, pady=5)
    
        # Display the interrupt overlay
        self.interrupt_bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.interrupt_fg.place(relx=0.75, rely=0.1, width=200, height=300)  # Position it on the right
    
    
    def show_normal_section(self):
        for widget in list(self.normal_section.winfo_children()):
            try:
                widget.destroy()
            except:
                pass
        options_data = self.config.get("options", {}).get(self.current_video, {})
        stype = options_data.get("scene_type", "").lower()
        if stype == "continue":
            heading = options_data.get("continue_heading", "")
        elif stype == "question":
            heading = options_data.get("question_heading", "")
        else:
            heading = options_data.get("heading", "")
        if heading:
            lbl = tk.Label(self.normal_section, text=heading,
                           font=("Arial", 14, "bold"), wraplength=230)
            lbl.pack(pady=5)
        choices = options_data.get("choices", {})
        for text, option in choices.items():
            if not option.get("temporary", False):
                self.create_option_frame(text, option, self.normal_section)
    
    def show_interrupt_options(self):
        self.clear_options()
        if self.temporary_choices_exist():
            self.show_interrupt_section()
    
    def handle_option(self, option):
        """Handle user choice and transition to the next scene."""
        next_scene = option.get("next")
        print(f"[DEBUG] Handling option selection: {next_scene}")
    
        if next_scene:
            if option.get("temporary", False):
                if self.resume_video is None:
                    self.resume_video = self.current_video
                    self.resume_time = self.player.get_time()
                self.current_video = next_scene
            else:
                self.current_video = next_scene
                self.resume_video = None
                self.resume_time = 0
    
            self.clear_all_overlays()
            self.play_video()
        else:
            print("[DEBUG] No next scene defined in option.")
    
    
    
    
if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveVideoApp(root, "config.yaml")
    root.mainloop()
