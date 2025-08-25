# SVG Stocker - Microstock SVG Converter

A application designed to convert SVG files for various microstock platforms, generating platform-specific formats (EPS, JPG, PNG) with appropriate resolutions and packaging.

## Features
- Convert SVG files for Shutterstock (EPS), Vectorstock (JPG + EPS), PNGTree (PNG + EPS Zipped), Dreamstime (JPG + EPS), AdobeStock (SVG), Canva (PNG), MiriCanvas (SVG Cropped), and Desainstock (JPG)
- Batch processing of multiple SVG files
- Adjustable resolution scale factor (1x-10x)
- Progress tracking and detailed conversion logs

## Requirements
- Python 3.12
- [Inkscape](https://inkscape.org/) (must be installed and accessible in PATH or at default locations)
- Required Python packages (see `requirements.txt`)

## Installation
1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the application:
```bash
python svg_inkscape.py
```

1. Select a folder containing SVG files
2. Choose output platforms
3. Adjust scale factor if needed
4. Click "Start Conversion"
5. Output files will be generated in a `svg_converted_output` subdirectory within your selected input folder

## Building the Executable

### For macOS
```bash
pyinstaller --onefile --windowed --name "SVG Stocker" --icon=icon.icns app.py
```
- Ensure `icon.icns` is present in the project root
- The executable will be created in the `dist` directory

### For Windows
```bash
pyinstaller --onefile --windowed --name "SVG Stocker" --icon=icon.ico app.py
```
- Convert `icon.icns` to `icon.ico` using an icon converter tool
- Place `icon.ico` in the project root
- The executable will be created in the `dist` directory

## Notes
- Inkscape must be installed at one of these locations:
  - Windows: `C:\Program Files\Inkscape\bin\inkscape.exe` or `C:\Program Files\Inkscape\inkscape.exe`
  - macOS: `/Applications/Inkscape.app/Contents/MacOS/inkscape`
- If Inkscape is installed elsewhere, ensure it's in your system PATH
- The application automatically creates platform-specific output directories within the output folder
