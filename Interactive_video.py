########################################################################
# Interactive Video player
# Version v2.9.15 (YAML version) –
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
        """Initialize the interactive video player app."""
        self.root = root
        self.root.title("Interactive Video Player")
        self.config_file = config_file
    
        # Initialize VLC player instance
        self.instance = vlc.Instance("--no-xlib")
        self.player = self.instance.media_player_new()
    
        # Main video container setup
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
    
        # Video container where the video will be rendered
        self.video_container = tk.Frame(self.main_frame, bg='black')
        self.video_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Overlay initialization section
        # Interrupt overlays (right section)
        self.interrupt_bg = tk.Canvas(self.video_container, bg='black', highlightthickness=0)
        self.interrupt_bg.place_forget()  # Hide initially
        print("[DEBUG] Initialized interrupt_bg (Canvas)")
        
        self.interrupt_fg = tk.Frame(self.video_container, bg='white')
        self.interrupt_fg.place_forget()  # Hide initially
        print("[DEBUG] Initialized interrupt_fg (Frame)")
        
        # Center overlay (continue/question section)
        self.cq_options_frame = tk.Canvas(self.video_container, bg='black', highlightthickness=0)
        self.cq_options_frame.place_forget()  # Hide initially
        print("[DEBUG] Initialized cq_options_frame (Canvas)")
        
        # Foreground interrupt frame to hold buttons
        self.interrupt_fg = tk.Frame(self.video_container, bg='white')
        self.interrupt_fg.place_forget()  # Hide initially
        print("[DEBUG] Initialized interrupt_fg (Frame)")
        
        
        # Video frame inside the container where VLC will render the video
        self.video_frame = tk.Frame(self.video_container, bg='black')
        self.video_frame.pack(fill=tk.BOTH, expand=True)

        
        # Initialize volume control
        self.volume_var = tk.IntVar(value=100)  # Set default volume to 100%
    
    
        # Load configuration from YAML
        self.load_config()
    
        # Set up other initial values
        self.current_video = self.config.get("start", "")
        self.resume_video = None
        self.resume_time = 0
    
        # Event manager for VLC to detect when video ends
        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_video_end)
    
        # Start playing the first video
        self.play_video()
    
        # Start periodic overlay updates
        self.periodic_update_overlay()
        # Initialize normal_section for main scenes
        self.normal_section = None

        
        # VLC Control Bar
        self.control_frame = tk.Frame(self.root, bg='gray')
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Play/Pause button
        self.is_playing = True
        self.play_pause_btn = tk.Button(self.control_frame, text="Pause", command=self.toggle_play_pause)
        self.play_pause_btn.pack(side=tk.LEFT)
        
        # Mute button
        self.is_muted = False
        self.mute_btn = tk.Button(self.control_frame, text="Mute", command=self.toggle_mute)
        self.mute_btn.pack(side=tk.LEFT)
        
        # Volume slider
        self.volume_var = tk.IntVar(value=100)
        self.volume_slider = tk.Scale(self.control_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.volume_var, command=self.set_volume)
        self.volume_slider.pack(side=tk.LEFT)
        
        # Seek bar
        self.seek_var = tk.DoubleVar()
        self.seek_bar = tk.Scale(self.control_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.seek_var, command=self.seek_video)
        self.seek_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Skip button for interruptions
        self.skip_button = tk.Button(
            self.control_frame, text="Skip Interruption",
            command=self.skip_interrupt
        )
        self.skip_button.place_forget()  # Hide initially
        print("[DEBUG] Initialized skip_button and hidden by default")
        
        
    
        
    def load_config(self):
        """Load the video configuration from the YAML file."""
        try:
            with open(self.config_file, 'r') as file:
                self.config = yaml.safe_load(file)
                print(f"[DEBUG] Successfully loaded configuration from {self.config_file}")
        except FileNotFoundError:
            print(f"[ERROR] Config file not found: {self.config_file}")
            self.config = {}
        except yaml.YAMLError as e:
            print(f"[ERROR] Error parsing YAML config: {e}")
            self.config = {}
    

    def show_cq_options_overlay(self):
        """Display the continue/question overlay after video ends."""
        print("[DEBUG] Triggered show_cq_options_overlay()")
        self.clear_all_overlays()
    
        # Calculate size dynamically based on choices
        options_data = self.config.get("options", {}).get(self.current_video, {})
        choices = options_data.get("choices", {})
        num_choices = len([opt for opt in choices.items() if not opt[1].get("temporary", False)])
    
        frame_width = max(300, 300 * num_choices)
        frame_height = 200  # Increased height to prevent squishing
    
        vc_width = self.video_container.winfo_width()
        vc_height = self.video_container.winfo_height()
        pos_x = (vc_width - frame_width) // 2
        pos_y = int(vc_height * 0.6)
    
        # Draw semi-transparent background
        self.cq_options_frame.place(x=pos_x, y=pos_y, width=frame_width, height=frame_height)
        self.cq_options_frame.delete("all")  # Clear previous drawings
        self.cq_options_frame.create_rectangle(
            0, 0, frame_width, frame_height,
            fill="#000000", stipple="gray50", outline=""
        )
        print("[DEBUG] Drawing overlay rectangle for cq_options_frame")
    
        # Populate choices
        button_frame = tk.Frame(self.cq_options_frame, bg='white')
        button_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        print(f"[DEBUG] Loaded choices: {choices}")
    
        for idx, (text, option) in enumerate(choices.items()):
            if not option.get("temporary", False):
                print(f"[DEBUG] Creating button for choice: {text}")
                button = self.create_option_button(button_frame, text, option)
                button.grid(row=0, column=idx, padx=10, pady=10)
    
        # Reveal the overlay after setup
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
                print("[DEBUG] Scene type detected as continue/question. Showing overlay.")
                self.show_cq_options_overlay()
            elif scene_type == "main":
                print("[DEBUG] Scene type detected as main. Showing main options overlay.")
                self.show_main_options_overlay()
            else:
                print("[DEBUG] Unknown scene type. Showing normal section.")
                self.clear_subframes()
                self.show_normal_section()
            
    
    def clear_interrupt_overlays(self):
        """Clear interrupt overlays attached to the video player."""
        if self.interrupt_fg:
            self.interrupt_fg.place_forget()
            self.interrupt_fg = None
            print("[DEBUG] Hiding and resetting interrupt_fg.")
    
        if self.interrupt_bg:
            self.interrupt_bg.place_forget()
            self.interrupt_bg = None
            print("[DEBUG] Hiding and resetting interrupt_bg.")

    def on_video_end(self, event):
        """Callback triggered when VLC reports the video has ended."""
        print("[DEBUG] VLC Event Triggered: Video has ended.")
        self.root.after(0, self.handle_video_end)  # Ensure it runs on the Tkinter main thread

    def on_video_end(self, event):
        """Callback triggered when VLC reports the video has ended."""
        print("[DEBUG] VLC Event Triggered: Video has ended.")
        self.root.after(0, self.handle_video_end)  # Ensures running on Tkinter's main thread
    
    
    def clear_interrupt_overlays(self):
        """Clear interrupt overlays attached to the video player."""
        if self.interrupt_fg:
            self.interrupt_fg.place_forget()
            self.interrupt_fg = None
    
        if self.interrupt_bg:
            self.interrupt_bg.place_forget()
            self.interrupt_bg = None
    
    def clear_all_overlays(self):
        """Clear all overlays from the video player."""
        print("[DEBUG] Clearing all overlays.")
    
        # Clear Continue/Question overlay
        if self.cq_options_frame:
            self.cq_options_frame.place_forget()
            print("[DEBUG] Hiding cq_options_frame.")
    
        # Clear interrupt overlays
        if self.interrupt_fg:
            self.interrupt_fg.place_forget()
            self.interrupt_fg = None
            print("[DEBUG] Hiding interrupt_fg.")
    
        if self.interrupt_bg:
            self.interrupt_bg.place_forget()
            self.interrupt_bg = None
            print("[DEBUG] Hiding interrupt_bg.")
       

    
    
    def periodic_update_overlay(self):
        """Periodically update the overlay position based on video container size."""
        try:
            self.video_container.update_idletasks()
            vc_width = self.video_container.winfo_width()
            vc_height = self.video_container.winfo_height()
    
            # Calculate position (centered, 60% down the screen)
            frame_width = 300
            frame_height = 100
            pos_x = (vc_width - frame_width) // 2
            pos_y = int(vc_height * 0.6)
    
            if self.cq_options_frame:
                self.cq_options_frame.place(x=pos_x, y=pos_y, width=frame_width, height=frame_height)
    
            # Continue updating periodically
            self.root.after(1000, self.periodic_update_overlay)
        except Exception as e:
            print(f"Error updating overlay geometry: {e}")
    
    
    
    
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
        """Set the VLC player's volume."""
        volume = int(value)
        self.player.audio_set_volume(volume)
    
    
    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.player.audio_set_mute(self.is_muted)
        self.mute_button.config(text="Unmute" if self.is_muted else "Mute")
    
    def play_video(self, resume_time=None):
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
            # Ensure skip button is available if we're resuming an interruption
            if self.resume_video:
                print("[DEBUG] Resuming from interruption, showing skip button.")
                self.ensure_skip_button()
            else:
                print("[DEBUG] No interruption, hiding skip button.")
                self.hide_skip_button()
            
            
    
            # Resume video from the correct timestamp if applicable
            if resume_time is not None:
                self.player.pause()
                self.root.after(50, lambda: self.player.set_time(resume_time))
                self.root.after(100, lambda: self.player.play())
    
            # Ensure skip button is available if we're resuming an interruption
            if self.resume_video:
                self.ensure_skip_button()
            else:
                self.hide_skip_button()
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
        """Hide the skip interruption button if it exists."""
        if self.skip_button and self.skip_button.winfo_exists():
            self.skip_button.place_forget()
            print("[DEBUG] Skip button hidden.")
    
    
    
    def ensure_skip_button(self):
        """Show the skip button only if an interruption is active."""
        if self.skip_button and not self.skip_button.winfo_ismapped():
            self.skip_button.place(relx=0.85, rely=0.9)  # Position near bottom-right
            print("[DEBUG] Skip button shown.")
    
    
    def skip_interrupt(self):
        """Skip the interruption and resume the base video."""
        print("[DEBUG] Skip interruption button clicked.")
        if self.resume_video:
            self.clear_all_overlays()
            self.current_video = self.resume_video
            self.resume_video = None
            self.play_video(resume_time=self.resume_time)

    
    def clear_options(self):
        for widget in list(self.options_frame.winfo_children()):
            if widget not in [self.options_controls_frame, self.normal_section]:
                if widget.winfo_exists():
                    widget.destroy()
        self.image_refs = []
    
    def clear_subframes(self):
        """Clear all subframes and overlays."""
        if self.interrupt_fg is not None:
            for widget in list(self.interrupt_fg.winfo_children()):
                widget.destroy()
            # Correct way to hide a Frame using place_forget()
            if self.interrupt_fg:
                self.interrupt_fg.place_forget()
                print("[DEBUG] Hiding interrupt_fg using place_forget()")
            
    
        if self.interrupt_bg is not None:
            self.interrupt_bg.place_forget()
    

    
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
    
    def show_interrupt_section(self, scene_id):
        """Display the interrupt section for a given scene attached to the video container."""
        print("[DEBUG] Triggered show_interrupt_section()")
    
        # Ensure interrupt_bg is initialized
        if self.interrupt_bg is None or not isinstance(self.interrupt_bg, tk.Canvas):
            print("[DEBUG] Re-initializing interrupt_bg (Canvas)")
            self.interrupt_bg = tk.Canvas(self.video_container, bg='black', highlightthickness=0)
            self.interrupt_bg.place_forget()
    
        # Ensure interrupt_fg is initialized
        if self.interrupt_fg is None or not isinstance(self.interrupt_fg, tk.Frame):
            print("[DEBUG] Re-initializing interrupt_fg (Frame)")
            self.interrupt_fg = tk.Frame(self.video_container, bg='white')
            self.interrupt_fg.place_forget()
    
        # Load scene options from YAML
        options_data = self.config.get("options", {}).get(scene_id, {})
        choices = options_data.get("choices", {})
        print(f"[DEBUG] Loaded choices for interrupt: {choices}")
    
        # Clear previous interrupt options
        for widget in list(self.interrupt_fg.winfo_children()):
            widget.destroy()
    
        # Populate choices
        if any(option.get("temporary", False) for option in choices.values()):
            for text, option in choices.items():
                if option.get("temporary", False):
                    print(f"[DEBUG] Adding interrupt choice button: {text}")
                    button = self.create_option_button(self.interrupt_fg, text, option)
                    button.pack(padx=5, pady=5)
    
            # Draw semi-transparent background for interrupts
            self.interrupt_bg.place(relx=0.75, rely=0.1, relwidth=0.2, relheight=0.8)
            self.interrupt_bg.delete("all")  # Clear existing drawings
            width = self.interrupt_bg.winfo_width()
            height = self.interrupt_bg.winfo_height()
            self.interrupt_bg.create_rectangle(
                0, 0, width, height,
                fill="#000000", stipple="gray50", outline=""
            )
            print("[DEBUG] Drawing semi-transparent background for interrupt_fg")
    
            self.interrupt_fg.place(relx=0.75, rely=0.1, relwidth=0.2, relheight=0.8)
        else:
            print("[DEBUG] No temporary choices found, clearing overlays.")
            self.clear_interrupt_overlays()

    def ensure_skip_button(self):
        """Ensure the skip interruption button exists and is visible."""
        if not self.skip_button or not self.skip_button.winfo_exists():
            print("[DEBUG] Initializing skip button.")
            self.skip_button = tk.Button(
                self.control_frame, text="Skip Interruption",
                command=self.skip_interrupt
            )
            self.skip_button.pack(side=tk.RIGHT)

    def skip_interrupt(self):
        """Skip the interruption and resume the base video."""
        print("[DEBUG] Skip interruption button clicked.")
        if self.resume_video:
            self.clear_all_overlays()
            self.current_video = self.resume_video
            self.resume_video = None
            self.play_video(resume_time=self.resume_time)
       
    
    
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
    def show_main_options_overlay(self):
        """Display the main scene options."""
        print("[DEBUG] Showing main scene options")
        self.clear_all_overlays()
    
        if self.normal_section is None:
            self.normal_section = tk.Frame(self.video_container, bg='white')
        
        self.normal_section.place(relx=0.1, rely=0.7, relwidth=0.3, relheight=0.2)
    
        # Example button for main options
        button = tk.Button(self.normal_section, text="Go Back", command=lambda: self.handle_option({'next': 'previous_scene'}))
        button.pack(padx=5, pady=5)
    
    
    def handle_option(self, option):
        """Handle user choice and transition to the next scene."""
        next_scene = option.get("next")
        print(f"[DEBUG] Handling option selection: {next_scene}")
    
        if next_scene:
            if option.get("temporary", False):
                # Handle temporary choices
                if self.resume_video is None:
                    self.resume_video = self.current_video
                    self.resume_time = self.player.get_time()
                self.current_video = next_scene
            else:
                # Handle regular scene transition
                self.current_video = next_scene
                self.resume_video = None
                self.resume_time = 0
    
            self.clear_all_overlays()
            self.play_video()
        else:
            print("[DEBUG] No next scene defined in option.")
    
            
    def toggle_play_pause(self):
        """Toggle play and pause for the VLC player."""
        if self.is_playing:
            self.player.pause()
            self.play_pause_btn.config(text="Play")
        else:
            self.player.play()
            self.play_pause_btn.config(text="Pause")
        self.is_playing = not self.is_playing
    
    def toggle_mute(self):
        """Toggle mute/unmute."""
        self.is_muted = not self.is_muted
        self.player.audio_toggle_mute()
        self.mute_btn.config(text="Unmute" if self.is_muted else "Mute")
    
    def set_volume(self, value):
        """Adjust the VLC player volume."""
        volume = int(value)
        self.player.audio_set_volume(volume)
    
    def seek_video(self, value):
        """Seek video position."""
        if self.player.is_playing():
            new_position = float(value) / 100
            self.player.set_position(new_position)
    
    def update_seek_bar(self):
        """Update the seek bar as the video plays."""
        if self.player.is_playing():
            current_time = self.player.get_time()
            duration = self.player.get_length()
            if duration > 0:
                self.seek_var.set((current_time / duration) * 100)
        self.root.after(1000, self.update_seek_bar)
    
    
    
    
    
if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveVideoApp(root, "config.yaml")
    root.mainloop()
