#!/bin/bash

# --- Configuration ---
# Standard icon sizes to generate (in pixels)
ICON_SIZES=(22 24 32 48 64 72 96 128 256)
ICON_BASE_DIR="./hicolor" # <--- CHANGED: Create hierarchy in current directory
ICON_FORMAT="png"

# --- Script Logic ---

# Check for correct number of arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_image_filepath> <program_name>"
    echo "  <input_image_filepath>: Path to the high-resolution source image (e.g., .png, .svg)"
    echo "  <program_name>: The name of your program (e.g., my-wallpaper-app)"
    exit 1
fi

INPUT_IMAGE="$1"
PROGRAM_NAME="$2"

# Validate input image existence
if [ ! -f "$INPUT_IMAGE" ]; then
    echo "Error: Input image file '$INPUT_IMAGE' not found."
    exit 1
fi

# Check if 'magick' command (ImageMagick 7) or 'convert' (ImageMagick 6) is available
if command -v magick &> /dev/null; then
    CONVERT_CMD="magick convert"
elif command -v convert &> /dev/null; then
    CONVERT_CMD="convert"
else
    echo "Error: ImageMagick (magick or convert command) is not installed or not in your PATH."
    echo "Please install it (e.g., sudo apt install imagemagick on Debian/Ubuntu)."
    exit 1
fi

echo "Generating icons for '$PROGRAM_NAME' from '$INPUT_IMAGE'..."
echo "Target hierarchy root: $ICON_BASE_DIR"

for SIZE in "${ICON_SIZES[@]}"; do
    TARGET_DIR="$ICON_BASE_DIR/${SIZE}x${SIZE}/apps"
    OUTPUT_FILE="$TARGET_DIR/${PROGRAM_NAME}.${ICON_FORMAT}"

    # Create target directory if it doesn't exist
    mkdir -p "$TARGET_DIR"

    if [ $? -ne 0 ]; then
        echo "Error: Could not create directory '$TARGET_DIR'. Check permissions."
        exit 1
    fi

    echo "  Generating ${SIZE}x${SIZE} icon: $OUTPUT_FILE"
    $CONVERT_CMD "$INPUT_IMAGE" -resize "${SIZE}x${SIZE}" "$OUTPUT_FILE"

    if [ $? -ne 0 ]; then
        echo "Error: ImageMagick conversion failed for size ${SIZE}x${SIZE}."
        exit 1
    fi
done

echo ""
echo "Icon generation complete."
echo "---------------------------------------------------------"
echo "Important Notes for Development/Testing:"
echo "1. The icons are now in: $(pwd)/$ICON_BASE_DIR"
echo "2. For your application to find these icons *during development*,"
echo "   you might need to set the XDG_DATA_DIRS environment variable."
echo "   Example (add the current directory to the search path temporarily):"
echo "   export XDG_DATA_DIRS=\"$(pwd):\$XDG_DATA_DIRS\""
echo "   Then run your application from the same terminal."
echo ""
echo "   Alternatively, you can manually copy these generated icons"
echo "   to ~/.local/share/icons/hicolor/ for system-wide testing later."
echo ""
echo "3. Updating the system-wide icon cache (only needed if you copy to ~/.local/share):"
echo "   gtk-update-icon-cache -f -t \"$HOME/.local/share/icons/hicolor\""
echo ""
echo "4. For a desktop entry (.desktop file) to find the icon, it still needs to be"
echo "   installed in a standard location like ~/.local/share/icons/hicolor/."
echo "   If you're just running your app, the XDG_DATA_DIRS trick can work."
echo "   If you want an actual .desktop file to pick it up, it's best to install the icons."
