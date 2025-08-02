# kubux-ai-image-generator

A streamlined desktop application for generating AI images using Together.ai's image generation models. Create high-quality, custom images directly from text prompts with precise control over dimensions and generation parameters.

![Screenshot of kubux-ai-image-generator](screenshots/ai-generator.png)

## Features

- **Simple Text-to-Image Generation**: Turn your text descriptions into images
- **Intelligent Aspect Ratio Management**: Select the aspect ratio by resizing the view window
- **Full-Screen Image Viewer**: View generated images with zoom, pan, and fullscreen capabilities
- **Prompt History**: Save and reuse successful prompts
- **Native Look and Feel**: Automatically detects and uses your system's UI font settings
- **Adjustable Parameters**:
  - Control the number of generation steps for quality vs. speed
  - Adjust image size/resolution scale
  - Customize UI scaling to suit your display
  - Choose from a menu of available AI models
- **Organized Storage**: Images are saved in categorized directories based on prompts

## Installation

### From Source (Nix)

Kubux AI Image Generator includes a `flake.nix` for easy installation on NixOS and other systems with Nix package manager:

```bash
# Clone the repository
git clone https://github.com/yourusername/kubux-ai-image-generator
cd kubux-ai-image-generator

# Build and install using Nix flakes
nix profile install .
```

Alternatively, you can run or install by pointing nix directly to the project url.


### From Source (Manual, untested)

#### Prerequisites

- Python 3.8 or higher
- Together.ai API key (get one at [together.ai](https://together.ai))

#### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/kubux-ai-image-generator.git
   cd kubux-ai-image-generator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project directory with your API key:
   ```
   TOGETHER_API_KEY=your_api_key_here
   ```

## Usage

### Running the Application

```bash
python kubux-ai-image-generator.py
```

### Generating Images

1. Enter a detailed text prompt in the input area
2. Adjust generation settings as needed:
   - **Steps**: Higher values (20-48) for more detailed images, lower values (12-20) for faster generation
   - **Size**: Adjust the scale to control resolution (higher values create larger, more detailed images)
   - **Aspect**: You adjust the aspect ratio by resizing the image window.
3. Click "Generate" to create your image
4. View, zoom and explore your generated image in the viewer

### Tips for Better Results

- Be specific and detailed in your prompts
- Include art style references (e.g., "oil painting", "digital art", "photorealistic")
- Specify lighting, mood, and composition details
- Use the history feature to refine successful prompts

## Configuration

The application stores its configuration in:
- `~/.config/kubux-ai-image-generator/app_settings.json` - Application settings
- `~/.config/kubux-ai-image-generator/prompt_history.json` - Saved prompts

Generated images are saved to:
- `~/Pictures/kubux-ai-image-generator/`

## Requirements

- Python 3.8+
- tkinter
- PIL/Pillow
- python-dotenv
- requests
- together

## Troubleshooting

### API Key Issues
If you see "API Error" messages, check that your Together.ai API key is valid and correctly set in the `.env` file.

### Missing UI Elements
If UI elements appear too small or too large, use the UI scale slider in the top-right to adjust the interface size.

## About the Project

This application was developed to provide a simple, desktop-native interface for AI image generation without requiring technical knowledge of APIs or command-line tools. It focuses on making the image generation process as straightforward as possible while providing the necessary controls for high-quality results.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgments

- Built with the Together.ai API for image generation
- Uses the FLUX.1-pro model from Black Forest Labs

---

## Development Notes

### System Requirements

The application is designed for Linux desktop environments and includes automatic detection of system UI fonts for native integration with:

- GNOME-based desktops (Ubuntu, Fedora Workstation, etc.)
- KDE Plasma
- XFCE
- Cinnamon
- MATE
