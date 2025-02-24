# 🎥 Interactive Video Player

An interactive video player built with **Python**, **Tkinter**, and **VLC** that supports branching narratives using customizable YAML configuration files. The player allows users to make choices at key moments, dynamically affecting the video playback based on their selections.

---

## 🚀 Features

- 🔄 **Branching Video Narratives:** Play videos based on user choices that lead to different outcomes.
- 🖥️ **Custom Overlays:** Interactive overlays appear as choices during or after video playback.
  - **Temporary (Interrupt) Choices**: Branch off mid-video but return to the original scene.
  - **Final Choices**: Presented after the video ends with seamless transitions.
- 🎛️ **Scene Types:**
  - `Continue`: Auto-progress or allow quick selection of the next scene.
  - `Question`: Display user choices after video completion.
  - `Main`: Offers full control over scene navigation.
- 📄 **YAML Configuration:** Define scenes, video paths, choices, and scene types in a simple YAML file.
- 📦 **Cross-Platform Support:** Packaged as a standalone executable using **PyInstaller** (planned).
- 🎨 **Custom UI Overlays:** Responsive layout and visual customization.

---

## 📂 Project Structure

```
interactive-video-player/
│
├── videos/               # Folder containing video files
├── images/               # Folder for image assets used in choices
├── config.yaml           # YAML configuration defining scenes and choices
├── interactive_video.py  # Main application script
├── requirements.txt      # Project dependencies
├── README.md             # Project documentation
└── LICENSE               # License information (MIT recommended)
```

---

## ⚙️ Requirements

Make sure to install the following Python libraries:

```bash
pip install PyYAML python-vlc Pillow
```

Or install all dependencies using:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Usage

1. **Clone the repository:**

```bash
git clone https://github.com/holder-1422/interactive-video-player.git
cd interactive-video-player
```

2. **Run the application:**

```bash
python interactive_video.py
```

3. **Configure Scenes:**
   - Edit `config.yaml` to define your scenes, video paths, and user choices.
   - Example YAML snippet:
     ```yaml
     start: "scene1"
     videos:
       scene1: "videos/intro.mp4"
       scene2: "videos/ending.mp4"

     options:
       scene1:
         scene_type: Question
         question_heading: "Choose your path:"
         choices:
           "Go Left":
             next: "scene2"
             image: "images/left_option.jpg"
     ```

---

## 🔍 Roadmap

- [ ] Implement new overlay layouts for final choices (Continue/Question).
- [ ] Switch to event-based video end detection using VLC’s event manager.
- [ ] Add thorough scene validation and error handling for YAML files.
- [ ] Create a `.exe` build using PyInstaller for easy distribution.
- [ ] Polish UI design and responsiveness for different screen sizes.

---

## 🐛 Contributing

Contributions, bug reports, and feature suggestions are welcome!

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Create a new Pull Request

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- Built using **Python**, **Tkinter**, and **VLC**.
- Inspired by interactive video storytelling platforms.

