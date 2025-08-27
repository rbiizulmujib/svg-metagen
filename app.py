import sys
import os
import zipfile
from pathlib import Path
from typing import List, Dict
import shutil
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QFileDialog, QCheckBox, 
                            QProgressBar, QTextEdit, QSpinBox, QGroupBox, QGridLayout,
                            QMessageBox, QLineEdit, QComboBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
import cairosvg
from cairosvg import svg2eps
from PIL import Image
import subprocess
import tempfile

class ConversionWorker(QThread):
    progress_update = pyqtSignal(int, str)
    log_update = pyqtSignal(str)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, svg_files, output_dir, selected_formats, scale_factor, force_1x1):
        super().__init__()
        self.svg_files = svg_files
        self.output_dir = output_dir
        self.selected_formats = selected_formats
        self.scale_factor = scale_factor
        self.force_1x1 = force_1x1
        
    def run(self):
        try:
            total_files = len(self.svg_files)
            
            # Create output directories
            self.create_output_directories()
            
            for i, svg_file in enumerate(self.svg_files):
                current_progress = int((i / total_files) * 100)
                file_name = os.path.basename(svg_file)
                
                self.progress_update.emit(current_progress, f"[{i+1}/{total_files}] Processing {file_name}")
                self.log_update.emit(f"Processing: {file_name}")
                
                # Process each selected format
                self.process_file(svg_file, file_name)
                
            self.progress_update.emit(100, "Conversion completed!")
            self.log_update.emit("All conversions completed successfully!")
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def create_output_directories(self):
        """Create output directories for each platform"""
        platforms = {
            'shutterstock': 'Shutterstock',
            'vectorstock': 'Vectorstock', 
            'pngtree': 'PNGTree',
            'dreamstime': 'Dreamstime',
            'adobestock': 'AdobeStock',
            'canva': 'Canva',
            'miricanvas': 'MiriCanvas',
            'desainstock': 'Desainstock'
        }
        
        for platform_key, platform_name in platforms.items():
            if platform_key in self.selected_formats:
                platform_dir = os.path.join(self.output_dir, platform_name)
                os.makedirs(platform_dir, exist_ok=True)
                self.log_update.emit(f"Created directory: {platform_dir}")
    
    def process_file(self, svg_file, file_name):
        """Process a single SVG file for all selected formats"""
        base_name = os.path.splitext(file_name)[0]
        
        # Shutterstock - EPS
        if 'shutterstock' in self.selected_formats:
            self.convert_to_eps(svg_file, base_name, 'Shutterstock')
            
        # Vectorstock - EPS + JPG
        if 'vectorstock' in self.selected_formats:
            self.convert_to_eps(svg_file, base_name, 'Vectorstock')
            self.convert_to_jpg(svg_file, base_name, 'Vectorstock')
            
        # PNGTree - PNG + EPS + ZIP
        if 'pngtree' in self.selected_formats:
            png_path = self.convert_to_png(svg_file, base_name, 'PNGTree')
            eps_path = self.convert_to_eps(svg_file, base_name, 'PNGTree')
            zip_path = self.create_zip_file([png_path, eps_path], base_name, 'PNGTree')
            
            # Delete PNG and EPS files after ZIP creation
            self.delete_files([png_path, eps_path])
            
        # Dreamstime - JPG + EPS
        if 'dreamstime' in self.selected_formats:
            self.convert_to_jpg(svg_file, base_name, 'Dreamstime')
            self.convert_to_eps(svg_file, base_name, 'Dreamstime')
            
        # AdobeStock - SVG only
        if 'adobestock' in self.selected_formats:
            self.copy_svg(svg_file, base_name, 'AdobeStock')
            
        # Canva - PNG
        if 'canva' in self.selected_formats:
            self.convert_to_png(svg_file, base_name, 'Canva')
            
        # MiriCanvas - SVG cropped
        if 'miricanvas' in self.selected_formats:
            self.convert_svg_cropped(svg_file, base_name, 'MiriCanvas')
            
        # Desainstock - JPG
        if 'desainstock' in self.selected_formats:
            self.convert_to_jpg(svg_file, base_name, 'Desainstock')
    
    def _get_svg_dimensions(self, svg_file):
        """Parse SVG to get its dimensions."""
        try:
            import re
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(svg_file)
            root = tree.getroot()
            
            width_str = root.get('width')
            height_str = root.get('height')
            
            width = None
            height = None

            if width_str:
                match = re.search(r'(\d+\.?\d*)', width_str)
                if match:
                    width = float(match.group(1))
            
            if height_str:
                match = re.search(r'(\d+\.?\d*)', height_str)
                if match:
                    height = float(match.group(1))

            if width and height:
                return width, height

            # Fallback to viewBox if width/height are not present
            viewBox = root.get('viewBox')
            if viewBox:
                parts = viewBox.split()
                if len(parts) == 4:
                    return float(parts[2]), float(parts[3])
            
            return None, None # Could not determine dimensions
        except Exception as e:
            self.log_update.emit(f"Could not parse SVG dimensions for {os.path.basename(svg_file)}: {e}")
            return None, None
    
    def convert_to_png(self, svg_file, base_name, platform):
        """Convert SVG to PNG with transparency, with optional 1:1 aspect ratio."""
        output_path = os.path.join(self.output_dir, platform, f"{base_name}.png")
        
        if self.force_1x1:
            base_dim = int(1000 * self.scale_factor)
            cairosvg.svg2png(
                url=svg_file,
                write_to=output_path,
                output_width=base_dim,
                output_height=base_dim
            )
            self.log_update.emit(f"Created PNG (transparent, {base_dim}x{base_dim}px): {output_path}")
        else:
            cairosvg.svg2png(
                url=svg_file,
                write_to=output_path,
                scale=self.scale_factor
            )
            self.log_update.emit(f"Created PNG (transparent, scaled by {self.scale_factor}x): {output_path}")
            
        return output_path
    
    def convert_to_jpg(self, svg_file, base_name, platform):
        """Convert SVG to JPG, with optional 1:1 aspect ratio."""
        output_path = os.path.join(self.output_dir, platform, f"{base_name}.jpg")
        
        # Convert to PNG first, then to JPG
        temp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        if self.force_1x1:
            base_dim = int(1000 * self.scale_factor)
            cairosvg.svg2png(
                url=svg_file,
                write_to=temp_png.name,
                output_width=base_dim,
                output_height=base_dim
            )
        else:
            cairosvg.svg2png(
                url=svg_file,
                write_to=temp_png.name,
                scale=self.scale_factor
            )
        
        # Convert PNG to JPG with white background
        img = Image.open(temp_png.name)
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        img.save(output_path, 'JPEG', quality=95)
        os.unlink(temp_png.name)
        
        self.log_update.emit(f"Created JPG: {output_path}")
        return output_path
    
    def convert_to_eps(self, svg_file, base_name, platform):
        """Convert SVG to EPS using cairosvg with scaling support"""
        output_path = os.path.join(self.output_dir, platform, f"{base_name}.eps")
        
        try:
            if self.force_1x1:
                base_dim = int(1000 * self.scale_factor)
                svg2eps(
                    url=svg_file,
                    write_to=output_path,
                    output_width=base_dim,
                    output_height=base_dim
                )
                self.log_update.emit(f"Created EPS ({base_dim}x{base_dim}px): {output_path}")
            else:
                svg2eps(
                    url=svg_file,
                    write_to=output_path,
                    scale=self.scale_factor
                )
                self.log_update.emit(f"Created EPS (scaled by {self.scale_factor}x): {output_path}")
        except Exception as e:
            self.log_update.emit(f"ERROR creating EPS with cairosvg: {e}")
            # Fallback to Inkscape if cairosvg fails, as it might handle complex SVGs better
            self.log_update.emit("cairosvg failed, falling back to Inkscape for EPS conversion.")
            try:
                inkscape_exe = self.find_inkscape()
                if not inkscape_exe:
                    raise FileNotFoundError("Inkscape executable not found for fallback")
                
                # Get original dimensions and scale width, preserving aspect ratio
                width, _ = self._get_svg_dimensions(svg_file)
                cmd = [inkscape_exe]
                if width:
                    cmd.append(f"--export-width={int(width * self.scale_factor)}")
                else:
                    # Fallback if dimensions can't be parsed: use a default scaled width
                    self.log_update.emit(f"Could not determine SVG width, using default for scaling.")
                    cmd.append(f"--export-width={int(1000 * self.scale_factor)}")

                cmd.extend([
                    "--export-type=eps",
                    "-o", output_path,
                    svg_file
                ])
                
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                self.log_update.emit(f"Created EPS (via Inkscape fallback): {output_path}")
            except Exception as e2:
                self.log_update.emit(f"ERROR creating EPS with Inkscape fallback: {e2}")
                return None

        return output_path

    def copy_svg(self, svg_file, base_name, platform):
        """Copy SVG file as-is"""
        output_path = os.path.join(self.output_dir, platform, f"{base_name}.svg")
        
        with open(svg_file, 'rb') as src, open(output_path, 'wb') as dst:
            dst.write(src.read())
            
        self.log_update.emit(f"Copied SVG: {output_path}")
        return output_path
    
    def convert_svg_cropped(self, svg_file, base_name, platform):
        """Convert SVG with cropping using Inkscape CLI (fit canvas to drawing)"""
        output_path = os.path.join(self.output_dir, platform, f"{base_name}.svg")
        
        try:
            # Find Inkscape executable
            inkscape_exe = self.find_inkscape()
            if not inkscape_exe:
                self.log_update.emit("WARNING: Inkscape not found, falling back to basic cropping")
                return self.copy_svg(svg_file, base_name, platform)
            
            # Use Inkscape to crop (fit canvas to drawing)
            cmd = [
                inkscape_exe,
                "--export-area-drawing",
                "--export-type=svg",
                "-o", output_path,
                svg_file
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.log_update.emit(f"Created cropped SVG using Inkscape: {output_path}")
            return output_path
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.log_update.emit(f"WARNING: Inkscape cropping failed: {e}, falling back to basic cropping")
            # Fallback to basic cropping
            return self.copy_svg(svg_file, base_name, platform)
    
    def find_inkscape(self):
    # Hardcode untuk Windows
        possible_paths = [
            r"C:\Program Files\Inkscape\bin\inkscape.exe",
            r"C:\Program Files\Inkscape\inkscape.exe"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p

        # Hardcode untuk macOS
        mac_path = "/Applications/Inkscape.app/Contents/MacOS/inkscape"
        if os.path.exists(mac_path):
            return mac_path

        # fallback
        return shutil.which("inkscape")
    
    def create_zip_file(self, file_paths, base_name, platform):
        """Create ZIP file containing specified files"""
        zip_path = os.path.join(self.output_dir, platform, f"{base_name}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    zipf.write(file_path, os.path.basename(file_path))
        
        self.log_update.emit(f"Created ZIP: {zip_path}")
        return zip_path
    
    def delete_files(self, file_paths):
        """Delete specified files"""
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.log_update.emit(f"Deleted file: {file_path}")
                except Exception as e:
                    self.log_update.emit(f"ERROR deleting file {file_path}: {e}")


class SVGConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.svg_files = []
        self.input_dir = ""
        self.output_dir = ""
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("SVG Converter for Microstock Platforms")
        self.setGeometry(100, 100, 800, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("SVG Converter for Microstock Platforms")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # File selection section
        file_section = self.create_file_section()
        layout.addWidget(file_section)
        
        # Output directory section
        # output_section = self.create_output_section()
        # layout.addWidget(output_section)
        
        # Scale factor section
        scale_section = self.create_scale_section()
        layout.addWidget(scale_section)
        
        # Platform selection section
        platform_section = self.create_platform_section()
        layout.addWidget(platform_section)
        
        # Progress section
        progress_section = self.create_progress_section()
        layout.addWidget(progress_section)
        
        # Control buttons
        button_section = self.create_button_section()
        layout.addWidget(button_section)
        
        # Log section
        log_section = self.create_log_section()
        layout.addWidget(log_section)

        # Footer
        footer = QLabel('Develop by <a href="http://www.designtools.my.id">www.designtools.my.id</a><br>Donate to support development <a href="https://saweria.co/mujibanget">Saweria</a><br> Report issue and Feature feedback? <a href="mailto:rbiizulmujib@gmail.com">Send feedback</a><br>Version 0.01')
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("font-size: 10px; color: #666;")
        footer.setOpenExternalLinks(True)
        layout.addWidget(footer)
    
    def create_file_section(self):
        group = QGroupBox("Input Folder")
        layout = QVBoxLayout(group)
        
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No folder selected")
        file_layout.addWidget(self.file_label)
        
        browse_btn = QPushButton("Select Folder with SVG Files")
        browse_btn.clicked.connect(self.browse_folder)
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        return group
    
    def create_output_section(self):
        group = QGroupBox("Output Information")
        layout = QVBoxLayout(group)
        
        self.output_label = QLabel("Output will be created in the selected input folder")
        self.output_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.output_label)
        
        return group
    
    def create_scale_section(self):
        group = QGroupBox("Scale Factor (Optional)")
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("Resolution Scale:"))
        
        self.scale_combo = QComboBox()
        scale_options = [
            ("1x", 1),
            ("2x", 2),
            ("3x", 3),
            ("4x", 4),
            ("5x", 5),
            ("6x", 6),
            ("7x", 7),
            ("8x", 8),
            ("9x", 9),
            ("10x", 10)
        ]
        
        for text, value in scale_options:
            self.scale_combo.addItem(text, value)
        
        self.scale_combo.setCurrentIndex(0)  # Default to 1x
        layout.addWidget(self.scale_combo)
        
        self.force_1x1_checkbox = QCheckBox("Force 1:1 Aspect Ratio")
        layout.addWidget(self.force_1x1_checkbox)
        
        layout.addStretch()
        
        return group
    
    def create_platform_section(self):
        group = QGroupBox("Select Output Platforms")
        layout = QGridLayout(group)
        
        self.platform_checkboxes = {}
        
        platforms = [
            ('shutterstock', 'Shutterstock (EPS)', 0, 0),
            ('vectorstock', 'Vectorstock (JPG + EPS)', 0, 1),
            ('pngtree', 'PNGTree (PNG + EPS Zipped)', 1, 0),
            ('dreamstime', 'Dreamstime (JPG + EPS)', 1, 1),
            ('adobestock', 'AdobeStock (SVG)', 2, 0),
            ('canva', 'Canva (PNG)', 2, 1),
            ('miricanvas', 'MiriCanvas (SVG Cropped)', 3, 0),
            ('desainstock', 'Desainstock (JPG)', 3, 1),
        ]
        
        for platform_key, platform_text, row, col in platforms:
            checkbox = QCheckBox(platform_text)
            checkbox.stateChanged.connect(self._update_start_button_state)
            self.platform_checkboxes[platform_key] = checkbox
            layout.addWidget(checkbox, row, col)
        
        # Select All / Deselect All buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_platforms)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_platforms)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout, 4, 0, 1, 2)
        
        return group
    
    def create_progress_section(self):
        group = QGroupBox("Progress")
        layout = QVBoxLayout(group)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready to start conversion")
        layout.addWidget(self.progress_label)
        
        return group
    
    def create_button_section(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.start_btn = QPushButton("Start Conversion")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF; /* biru */
                color: white;
                border-radius: 4px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #0056b3; /* biru lebih gelap saat hover */
            }
            QPushButton:pressed {
                background-color: #004085; /* biru tua saat ditekan */
            }
            QPushButton:disabled {
                background-color: #CCCCCC; /* abu-abu */
                color: #666666;
            }
        """)
        self.start_btn.clicked.connect(self.start_conversion)
        self.start_btn.setEnabled(False)  # Disable by default
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        self.open_folder_btn = QPushButton("Open Output Folder")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.setEnabled(False)
        layout.addWidget(self.open_folder_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_log_section(self):
        group = QGroupBox("Conversion Log")
        layout = QVBoxLayout(group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        return group
    
    def _update_start_button_state(self):
        """Enable or disable the start button based on conditions."""
        folder_selected = bool(self.svg_files)
        platform_selected = any(checkbox.isChecked() for checkbox in self.platform_checkboxes.values())
        
        self.start_btn.setEnabled(folder_selected and platform_selected)
    
    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder with SVG Files")
        
        if directory:
            self.input_dir = directory
            # Find all SVG files in the directory
            svg_files = []
            for file in os.listdir(directory):
                if file.lower().endswith('.svg'):
                    svg_files.append(os.path.join(directory, file))
            
            self.svg_files = svg_files
            
            if svg_files:
                self.file_label.setText(f"Folder: {directory}\n{len(svg_files)} SVG files found")
                # Auto-generate output directory
                self.output_dir = os.path.join(directory, "Microstock_Ready")
                self.log_text.append(f"Selected folder: {directory}")
                self.log_text.append(f"Found {len(svg_files)} SVG files")
                self.log_text.append(f"Output directory: {self.output_dir}")
            else:
                self.file_label.setText(f"Folder: {directory}\nNo SVG files found")
                self.svg_files = []
                self.output_dir = ""
                self.log_text.append(f"Selected folder: {directory}")
                self.log_text.append("WARNING: No SVG files found in the selected folder")
            
            self._update_start_button_state()
    
    def select_all_platforms(self):
        for checkbox in self.platform_checkboxes.values():
            checkbox.setChecked(True)
    
    def deselect_all_platforms(self):
        for checkbox in self.platform_checkboxes.values():
            checkbox.setChecked(False)
    
    def open_output_folder(self):
        """Open the output folder in the system file manager"""
        if self.output_dir and os.path.exists(self.output_dir):
            import platform
            system = platform.system()
            
            try:
                if system == "Darwin":  # macOS
                    subprocess.run(["open", self.output_dir])
                elif system == "Windows":
                    subprocess.run(["explorer", self.output_dir])
                else:  # Linux and others
                    subprocess.run(["xdg-open", self.output_dir])
                
                self.log_text.append(f"Opened output folder: {self.output_dir}")
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not open output folder: {e}")
                self.log_text.append(f"ERROR: Could not open output folder: {e}")
        else:
            QMessageBox.warning(self, "Warning", "Output folder does not exist!")
    
    def start_conversion(self):
        # Validation
        if not self.svg_files:
            QMessageBox.warning(self, "Warning", "Please select SVG files first!")
            return
        
        if not self.output_dir:
            QMessageBox.warning(self, "Warning", "Please select output directory first!")
            return
        
        selected_formats = [key for key, checkbox in self.platform_checkboxes.items() 
                          if checkbox.isChecked()]
        
        if not selected_formats:
            QMessageBox.warning(self, "Warning", "Please select at least one output platform!")
            return
        
        # Start conversion
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        scale_factor = self.scale_combo.currentData()
        force_1x1 = self.force_1x1_checkbox.isChecked()
        
        self.worker = ConversionWorker(
            self.svg_files, 
            self.output_dir, 
            selected_formats, 
            scale_factor,
            force_1x1
        )
        
        self.worker.progress_update.connect(self.update_progress)
        self.worker.log_update.connect(self.update_log)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.error_occurred.connect(self.conversion_error)
        
        self.worker.start()
        
        self.log_text.append("=== Starting Conversion ===")
        self.log_text.append(f"Files to process: {len(self.svg_files)}")
        self.log_text.append(f"Selected platforms: {', '.join(selected_formats)}")
        self.log_text.append(f"Scale factor: {scale_factor}x")
    
    def stop_conversion(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.conversion_finished()
            self.log_text.append("Conversion stopped by user")
    
    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)
    
    def update_log(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def conversion_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(True)
        self.progress_label.setText("Conversion completed!")
        QMessageBox.information(self, "Success", "Conversion completed successfully!")
    
    def conversion_error(self, error_message):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("Error occurred during conversion")
        self.log_text.append(f"ERROR: {error_message}")
        QMessageBox.critical(self, "Error", f"An error occurred: {error_message}")


def main():
    app = QApplication(sys.argv)
    window = SVGConverterApp()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
