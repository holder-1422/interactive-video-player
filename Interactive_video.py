########################################################################
# Interactive Video player
# Version v2.9.6.1 (YAML version) – Modified for transparent interruption overlay
# with a semi-transparent background behind small, fully opaque interruption choices.
# Overlays are completely redrawn on scene changes. If there are no temporary
# choices, the overlay windows are withdrawn (or set to minimal size).
# When resuming an interruption, the overlay is drawn from the base scene.
# Base scene settings are preserved if multiple interruptions are clicked.
# The skip interruption now pauses, sets the time, and then resumes playback,
# so the video starts at the correct spot.
# Date 02/27/2025
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
        
        # Start playing video and set up overlays.
        self.play_video()
        # Periodically update overlay positions.
        self.periodic_update_overlay()
        
        #v.2.9.7 changes below
        
        # Ensure the video container has updated dimensions
        self.video_container.update_idletasks()
        
        # Get video container dimensions
        vc_width = self.video_container.winfo_width()
        vc_height = self.video_container.winfo_height()
        
        # Create dimming background overlay attached to the video container
        self.cq_bg_overlay = tk.Frame(self.video_container, bg='black')
        self.cq_bg_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.cq_bg_overlay.lower()  # Keep the overlay hidden for now
        
        # Create overlay frame for choices attached to the video container
        self.cq_options_frame = tk.Frame(self.video_container, bg='white')
        
        # Calculate position (centered, 60% down the screen)
        frame_width = 300
        frame_height = 100
        pos_x = (vc_width - frame_width) // 2
        pos_y = int(vc_height * 0.6)
        
        self.cq_options_frame.place(x=pos_x, y=pos_y, width=frame_width, height=frame_height)
        self.cq_options_frame.lower()  # Keep the overlay hidden for now
        
        # Populate choices from YAML config
        options_data = self.config.get("options", {}).get(self.current_video, {})
        choices = options_data.get("choices", {})
        
        button_frame = tk.Frame(self.cq_options_frame, bg='white')
        button_frame.pack(padx=10, pady=10)
        
        for text, option in choices.items():
            if not option.get("temporary", False):  # Only show non-temporary choices
                self.create_option_button(button_frame, text, option)
        
        # Show the overlays when the video ends
        self.root.after(100, lambda: self._reveal_cq_overlay())

    
    def clear_interrupt_overlays(self):
        """Withdraw both interruption overlay windows."""
        self.interrupt_fg.withdraw()
        self.interrupt_bg.withdraw()
    
    def periodic_update_overlay(self):
        # Determine the base scene: if resuming, use that; otherwise, current scene.
        base_scene = self.resume_video if self.resume_video else self.current_video
        if self.temporary_choices_exist(base_scene):
            self.update_interrupt_geometry()
            self.interrupt_bg.deiconify()
            self.interrupt_fg.deiconify()
            self.interrupt_bg.lift()
            self.interrupt_fg.lift()
        else:
            self.interrupt_bg.geometry("1x1+0+0")
            self.interrupt_fg.geometry("1x1+0+0")
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
        # Withdraw any existing interruption overlays.
        self.clear_interrupt_overlays()
        self.clear_subframes()
        video_path = resource_path(self.config.get("videos", {}).get(self.current_video, ""))
        if video_path and os.path.exists(video_path):
            media = self.instance.media_new(video_path)
            self.player.stop()
            self.player.set_hwnd(self.video_frame.winfo_id())
            self.player.set_media(media)
            self.player.play()
            self.set_volume(self.volume_var.get())
            self.root.after(500, self.adjust_window_size)
            self.root.after(500, self.check_video_end)
            self.root.after(1000, self.update_seek_bar)
            
            self.update_interrupt_geometry()
            
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
                # Pause briefly, set the desired start time, then resume playback.
                self.player.pause()
                self.root.after(50, lambda: self.player.set_time(start_time))
                self.root.after(100, lambda: self.player.play())
        else:
            messagebox.showerror("Error", f"Video file not found: {video_path}")
            if self.resume_video:
                self.ensure_skip_button()
            else:
                self.hide_skip_button()
            if self.temporary_choices_exist():
                self.show_interrupt_section()
    
    def adjust_window_size(self):
        width = self.player.video_get_width()
        height = self.player.video_get_height()
        if width > 0 and height > 0:
            self.video_frame.config(width=width, height=height)
    
    def check_video_end(self):
        state = self.player.get_state()
        if state == vlc.State.Ended or state == vlc.State.Error:
            if self.resume_video:
                self.root.after(500, self.skip_interrupt)
            else:
                scene_type = self.get_scene_type()
                if scene_type == "main":
                    options_data = self.config.get("options", {}).get(self.current_video, {})
                    default_next_scene = options_data.get("default_next_scene")
                    if default_next_scene:
                        self.root.after(1000, lambda: self.auto_advance_main_scene(default_next_scene))
                    else:
                        self.clear_subframes()
                        self.show_normal_section()
                else:
                    self.clear_subframes()
                    self.show_normal_section()
        else:
            self.root.after(500, self.check_video_end)
    
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
        for frame in (self.normal_section,):
            for widget in list(frame.winfo_children()):
                try:
                    widget.destroy()
                except:
                    pass
        for widget in list(self.interrupt_fg.winfo_children()):
            try:
                widget.destroy()
            except:
                pass
    
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
        bg_color = "#ff6666" if option.get("temporary", False) else "#007ACC"
        btn = tk.Button(parent, text=text,
                        command=lambda opt=option: self.handle_option(opt),
                        bg=bg_color, fg="white",
                        font=("Helvetica", 10, "bold"), wraplength=230)
        btn.pack()
    
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
        for widget in list(self.interrupt_fg.winfo_children()):
            try:
                widget.destroy()
            except:
                pass
        if scene_id is None:
            scene_id = self.current_video
        options_data = self.config.get("options", {}).get(scene_id, {})
        heading = options_data.get("interrupt_heading", "")
        if heading:
            lbl = tk.Label(self.interrupt_fg, text=heading,
                           font=("Arial", 14, "bold"), wraplength=230, bg='white')
            lbl.pack(pady=5)
        choices = options_data.get("choices", {})
        for text, option in choices.items():
            if option.get("temporary", False):
                self.create_option_frame(text, option, self.interrupt_fg)
        self.ensure_skip_button()
        self.interrupt_fg.deiconify()
        self.update_interrupt_geometry()
    
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
        next_video = option.get("next")
        if option.get("temporary", False):
            if self.resume_video is None:
                self.resume_video = self.current_video
                self.resume_time = self.player.get_time()
            self.current_video = next_video
            self.clear_options()
            self.clear_subframes()
            self.play_video()
        else:
            if self.resume_video:
                self.current_video = next_video
                self.clear_options()
                self.clear_subframes()
                self.play_video()
                self.player.set_time(self.resume_time)
                self.resume_video = None
            else:
                self.current_video = next_video
                self.clear_options()
                self.clear_subframes()
                self.play_video()
        if self.temporary_choices_exist():
            self.show_interrupt_section()
    
if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveVideoApp(root, "config.yaml")
    root.mainloop()
