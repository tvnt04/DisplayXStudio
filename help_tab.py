from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QApplication
import os
import json
import html as html_module

_MODE_TITLES = {
    "onboarding": "Display X Studio – User Manual & Quick Start",
    "band": "Band Mode – User Manual",
    "raw": "Raw Mode – User Manual",
    "video": "Video Mode – User Manual",
    "tiled": "Tiled Mode – User Manual",
    "editor": "Image Editor – User Manual",
    "global": "Global Controls & Shortcuts Reference",
}


def _get_css(is_dark=True):
    if is_dark:
        return """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 13px;
        line-height: 1.6;
        color: #D4D4D4;
        background-color: #1E1E1E;
        padding: 12px;
    }
    h2 {
        color: #4FC3F7;
        font-size: 18px;
        border-bottom: 2px solid #0288D1;
        padding-bottom: 6px;
        margin-top: 4px;
        margin-bottom: 12px;
    }
    h3 {
        color: #81D4FA;
        font-size: 15px;
        margin-top: 18px;
        margin-bottom: 6px;
        border-bottom: 1px solid #37474F;
        padding-bottom: 4px;
    }
    h4 {
        color: #FFB74D;
        font-size: 13px;
        margin-top: 14px;
        margin-bottom: 4px;
    }
    p, li {
        color: #CCCCCC;
    }
    ul, ol {
        margin-top: 4px;
        margin-bottom: 8px;
        padding-left: 22px;
    }
    li {
        margin-bottom: 4px;
    }
    strong {
        color: #FFFFFF;
        font-weight: 700;
    }
    code {
        background-color: #2D2D2D;
        color: #FFCC80;
        padding: 2px 5px;
        border-radius: 3px;
        border: 1px solid #3E3E3E;
        font-family: Consolas, Monaco, "Courier New", monospace;
        font-size: 12px;
    }
    kbd {
        background-color: #37474F;
        color: #ECEFF1;
        border: 1px solid #546E7A;
        border-radius: 3px;
        padding: 1px 5px;
        font-size: 11px;
        font-family: Consolas, monospace;
        font-weight: 600;
    }
    .badge {
        display: inline-block;
        padding: 2px 6px;
        font-size: 11px;
        font-weight: bold;
        border-radius: 3px;
        color: white;
    }
    .badge-ruler { background-color: #4CAF50; }
    .badge-roi { background-color: #FF9800; }
    .badge-purple { background-color: #8E24AA; }
    .badge-blue { background-color: #0288D1; }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 10px 0 16px 0;
    }
    th, td {
        border: 1px solid #3E3E3E;
        padding: 6px 10px;
        text-align: left;
        font-size: 12px;
    }
    th {
        background-color: #263238;
        color: #4FC3F7;
    }
    tr:nth-child(even) {
        background-color: #252525;
    }
    .tip-box {
        background-color: #1A2733;
        border-left: 4px solid #0288D1;
        padding: 8px 12px;
        margin: 10px 0;
        border-radius: 0 4px 4px 0;
        color: #E0E0E0;
    }
</style>
"""
    else:
        return """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 13px;
        line-height: 1.6;
        color: #212121;
        background-color: #FFFFFF;
        padding: 12px;
    }
    h2 {
        color: #01579B;
        font-size: 18px;
        border-bottom: 2px solid #0288D1;
        padding-bottom: 6px;
        margin-top: 4px;
        margin-bottom: 12px;
    }
    h3 {
        color: #0277BD;
        font-size: 15px;
        margin-top: 18px;
        margin-bottom: 6px;
        border-bottom: 1px solid #CFD8DC;
        padding-bottom: 4px;
    }
    h4 {
        color: #D84315;
        font-size: 13px;
        margin-top: 14px;
        margin-bottom: 4px;
    }
    p, li {
        color: #37474F;
    }
    ul, ol {
        margin-top: 4px;
        margin-bottom: 8px;
        padding-left: 22px;
    }
    li {
        margin-bottom: 4px;
    }
    strong {
        color: #000000;
        font-weight: 700;
    }
    code {
        background-color: #ECEFF1;
        color: #BF360C;
        padding: 2px 5px;
        border-radius: 3px;
        border: 1px solid #CFD8DC;
        font-family: Consolas, Monaco, "Courier New", monospace;
        font-size: 12px;
        font-weight: 600;
    }
    kbd {
        background-color: #ECEFF1;
        color: #263238;
        border: 1px solid #B0BEC5;
        border-radius: 3px;
        padding: 1px 5px;
        font-size: 11px;
        font-family: Consolas, monospace;
        font-weight: 700;
    }
    .badge {
        display: inline-block;
        padding: 2px 6px;
        font-size: 11px;
        font-weight: bold;
        border-radius: 3px;
        color: white;
    }
    .badge-ruler { background-color: #2E7D32; }
    .badge-roi { background-color: #E65100; }
    .badge-purple { background-color: #6A1B9A; }
    .badge-blue { background-color: #0277BD; }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 10px 0 16px 0;
    }
    th, td {
        border: 1px solid #CFD8DC;
        padding: 6px 10px;
        text-align: left;
        font-size: 12px;
        color: #263238;
    }
    th {
        background-color: #ECEFF1;
        color: #01579B;
        font-weight: 700;
    }
    tr:nth-child(even) {
        background-color: #F8F9FA;
    }
    .tip-box {
        background-color: #E1F5FE;
        border-left: 4px solid #0288D1;
        padding: 8px 12px;
        margin: 10px 0;
        border-radius: 0 4px 4px 0;
        color: #01579B;
    }
</style>
"""


def _detect_dark_mode(main_app=None):
    if main_app is not None and hasattr(main_app, "_is_dark_mode"):
        return bool(main_app._is_dark_mode)

    # Try reading session file directly
    try:
        from app_paths import get_app_data_path
        session_file = get_app_data_path("last_session.json")
        if os.path.exists(session_file):
            with open(session_file, "r", encoding="utf-8") as sf:
                data = json.load(sf)
                if "dark_mode" in data:
                    return bool(data["dark_mode"])
    except Exception:
        pass

    app = QApplication.instance()
    if app is not None:
        for w in app.topLevelWidgets():
            if hasattr(w, "_is_dark_mode"):
                return bool(w._is_dark_mode)
        # Fallback to palette brightness
        return app.palette().window().color().value() < 128
    return True


_MODE_RAW_CONTENT = {
    "onboarding": """
<h3>Display X Studio — Workstation Overview</h3>
<p>Display X Studio is an advanced visual analysis software designed for multi-spectral satellite imagery, raw sensor stream inspection, tile matrix stitching, and video sequence generation.</p>

<div class="tip-box">
  <strong>Quick Start:</strong> Click the <kbd>+</kbd> button in the top-left toolbar to create a new tab and choose the operating mode that matches your data type.
</div>

<h3>Operating Modes &amp; Their Purposes</h3>
<table>
  <tr><th>Mode</th><th>Purpose</th><th>Common File Types</th></tr>
  <tr>
    <td><strong>Band Mode</strong></td>
    <td>Multi-spectral satellite data processing. Performs automated band stitching, individual band inspection, false/true-color RGB fusion, parallax offset correction, and radiometric histogram profiling.</td>
    <td><code>.bandXX</code>, <code>.hdr</code>, <code>.meta</code>, <code>.log</code></td>
  </tr>
  <tr>
    <td><strong>Raw Mode</strong></td>
    <td>Direct raw sensor stream inspection. Browse multi-frame recordings frame-by-frame, build temporal stack composites, inspect single-pixel DN values, and apply dynamic range stretching.</td>
    <td><code>.raw</code>, <code>.bin</code>, <code>.dat</code></td>
  </tr>
  <tr>
    <td><strong>Video Mode</strong></td>
    <td>Generate and playback animated multi-frame RGB video sequences with variable speed, seeking, channel registration offsets, and direct video export.</td>
    <td><code>.bandXX</code> datasets, multi-frame streams</td>
  </tr>
  <tr>
    <td><strong>Tiled Mode</strong></td>
    <td>Assemble large-format composite images from matrices of sensor tiles across various scanning patterns (Row/Col Major, Serpentine) with edge overlap compensation.</td>
    <td>Tile matrices, flat tile folders</td>
  </tr>
  <tr>
    <td><strong>Image Editor</strong></td>
    <td>Post-processing canvas for cropping, rotating, contrast/gamma adjustments, sharpening, edge detection, and filtering.</td>
    <td>Exported frames, PNG, TIFF, BMP</td>
  </tr>
</table>

<h3>Global Features &amp; User Interface Elements</h3>
<ul>
  <li><strong>Multi-Tab Navigation</strong>: Open multiple datasets simultaneously. Click any top tab to switch views, or click <kbd>×</kbd> on a tab to close it.</li>
  <li><strong>Theme Toggle (Sun/Moon Icon)</strong>: Click the icon in the top toolbar to switch between Dark Mode and Light Mode.</li>
  <li><strong>Background Color Swatch (Top-Right Circle in Viewport)</strong>: Click the circular color button in the top-right corner of any viewer to choose background colors (Navy, Blue Grey, Dark Gray, Light Gray, White, Custom). Your choice is synchronized across all tabs and remembered when reopening the app.</li>
  <li><strong>Bottom Drawer Terminal</strong>: Expandable terminal panel at the bottom of the window showing processing logs, export progress, and real-time status.</li>
  <li><strong>Floating Pixel Info Box</strong>: Displays live cursor coordinates (X, Y), digital number (DN) values, matrix statistics, and geolocation (Lat/Lon). Can be docked or freely dragged.</li>
</ul>
""",

    "band": """
<h3>Band Mode — Multi-Spectral Analysis User Manual</h3>
<p>Band Mode allows you to load, align, stitch, and analyze multi-spectral satellite imagery with full radiometric and geospatial measurement tools.</p>

<h3>Step-by-Step Workflow</h3>
<ol>
  <li>Click <strong>Select Folder &amp; Stitch</strong> on the left panel and select your dataset directory containing <code>.bandXX</code> files.</li>
  <li>The <strong>Parameter Dialog</strong> opens automatically populated with the Width, RegionHeight, TDI Stage, and Bit Depth. Review the values and click <strong>OK</strong>.</li>
  <li>Navigate through the top view tabs: <strong>All Bands</strong>, <strong>Individual Bands</strong> (b0–b6 sub-tabs), <strong>RGB Fusion</strong>, and <strong>Histogram</strong>.</li>
  <li>Use <strong>Band Offsets</strong> and <strong>Stack Order</strong> on the left panel to align and reorder bands as needed.</li>
  <li>Click <strong>Save Progress</strong> to store your alignment and contrast settings for this dataset.</li>
</ol>

<h3>Left Control Panel Reference</h3>

<h4>1. Folder &amp; Dataset Selection</h4>
<ul>
  <li><strong>Select Folder &amp; Stitch</strong>: Opens the folder picker to select a multi-band dataset.</li>
  <li><strong>Recent Dropdown (▼)</strong>: Lists recently opened folders for instant 1-click loading.</li>
  <li><strong>Folder Label</strong>: Displays the name of the currently active dataset.</li>
  <li><strong>Change Params</strong>: Opens the parameter dialog to modify Width, Height, TDI, or Bit Depth without reselecting the folder.</li>
</ul>

<h4>2. Display Modes &amp; View Selectors</h4>
<ul>
  <li><strong>All Bands Checkbox</strong>: Enables the unified vertical stitched view of all active bands.</li>
  <li><strong>Individual Bands Checkbox</strong>: Generates dedicated per-band sub-tabs for detailed single-band inspection (raw, left/right split, or binned sub-views).</li>
  <li><strong>RGB Fusion Checkbox</strong>: Opens the RGB synthesis tab to composite 3 spectral bands into Red, Green, and Blue channels.</li>
  <li><strong>Histogram Checkbox</strong>: Opens the radiometric histogram analyzer.</li>
</ul>

<h4>3. Frame Navigation &amp; Range Controls</h4>
<ul>
  <li><strong>Frame Slider &amp; Number Spinbox</strong>: Scrub or jump to any specific frame index (0 to Max Frames).</li>
  <li><strong>Play (▶) / Pause (⏸)</strong>: Animate frame playback continuously.</li>
  <li><strong>Step Backward (◀) / Step Forward (▶)</strong>: Advance frames one step at a time.</li>
  <li><strong>Single Frame vs. Frame Range</strong>: Toggle between viewing one frame or setting a <strong>Start Frame</strong> and <strong>End Frame</strong> range for bulk processing.</li>
  <li><strong>Video Mode Button</strong>: Opens the current dataset directly in Video Mode for video generation.</li>
</ul>

<h4>4. Stacking, Offsets &amp; Layout</h4>
<ul>
  <li><strong>Stack Order (Collapsible ▶)</strong>: Click to expand. Use <kbd>▲</kbd> and <kbd>▼</kbd> buttons next to each band to reorder them vertically in the stitched composite. Click <strong>Reset Order</strong> to restore default ordering.</li>
  <li><strong>Band Offsets (Collapsible ▶)</strong>: Click to expand. Adjust X and Y pixel offsets for each band to correct physical sensor registration shifts.</li>
  <li><strong>Band Gap Slider</strong>: Adjusts the vertical pixel spacing (gap) between stitched bands.</li>
  <li><strong>1:4 Layout Toggle</strong>: Toggles 1:4 aspect ratio scaling for panoramic sensor strips.</li>
</ul>

<h4>5. Contrast &amp; Dynamic Range Controls</h4>
<ul>
  <li><strong>Contrast Enhance Checkbox</strong>: Enables dynamic range contrast stretching.</li>
  <li><strong>Min / Max Spinboxes</strong>: Manually sets the black level (Min) and white level (Max) display threshold.</li>
  <li><strong>Auto Button</strong>: Computes the optimal Min and Max intensity thresholds for the current frame automatically.</li>
  <li><strong>Fit to Screen / Actual Size</strong>: Toggles between fitting the full image into the window or displaying 100% native 1:1 pixel scale.</li>
</ul>

<h4>6. Data Actions</h4>
<ul>
  <li><strong>Save Progress</strong>: Saves your offsets, gaps, stack order, and contrast settings into the application database.</li>
  <li><strong>Export Image</strong>: Exports the current stitched view or individual band to PNG, BMP, or TIFF.</li>
  <li><strong>Reload</strong>: Re-reads files from disk (useful if files were modified externally).</li>
  <li><strong>Refresh</strong>: Re-renders the display using current in-memory settings.</li>
</ul>

<h3>Viewer &amp; Bottom Toolbar Tools</h3>
<table>
  <tr><th>Tool</th><th>Purpose</th><th>How to Use</th></tr>
  <tr>
    <td><strong>Spatial Ruler 📏</strong></td>
    <td>Measures linear distance, coordinate deltas (ΔX, ΔY), angle, and real-world ground distance (meters/km).</td>
    <td>Select <em>Spatial Ruler</em> from the Toolbox menu, then click Point 1 (start) and Point 2 (end) on the image. Exact pixel distance and physical ground distance appear in the Pixel Info Box.</td>
  </tr>
  <tr>
    <td><strong>ROI Statistics 📊</strong></td>
    <td>Measures radiometric intensity statistics over a Region of Interest.</td>
    <td>Select <em>ROI Statistics</em> from the Toolbox menu, then click and drag a rectangle over any image area. The Mean, Variance, StdDev, Min/Max DN, and Pixel Count appear in the Pixel Info Box.</td>
  </tr>
  <tr>
    <td><strong>Magnifier</strong></td>
    <td>High-magnification floating inspection lens.</td>
    <td>Check <em>Magnifier</em> in the bottom toolbar. Hover over the image to view sub-pixel details. Adjust the zoom factor with the slider.</td>
  </tr>
  <tr>
    <td><strong>Torch</strong></td>
    <td>Darkened spotlight mode.</td>
    <td>Check <em>Torch</em> while Magnifier is active to dim surrounding areas and spotlight the inspection area.</td>
  </tr>
  <tr>
    <td><strong>Grid Overlay (#)</strong></td>
    <td>Interactive alignment grid.</td>
    <td>Click the <strong>#</strong> button in the bottom-left corner. Drag the grid to position it over visual landmarks.</td>
  </tr>
  <tr>
    <td><strong>Background Swatch</strong></td>
    <td>Changes viewport background color.</td>
    <td>Click the circular color swatch in the top-right corner of the image view. Select any preset or choose a custom color.</td>
  </tr>
  <tr>
    <td><strong>Rotate &amp; Flip</strong></td>
    <td>Orientation adjustment.</td>
    <td>Click <strong>Rotate</strong> to cycle 0° → 90° → 180° → 270°. Click <strong>Flip</strong> to mirror horizontally or vertically.</td>
  </tr>
  <tr>
    <td><strong>Fullscreen (⛶)</strong></td>
    <td>Expands viewer to full monitor.</td>
    <td>Click the <strong>⛶</strong> button in the top-right corner of the viewport. Press <kbd>Esc</kbd> to exit fullscreen.</td>
  </tr>
</table>
""",

    "raw": """
<h3>Raw Mode — Direct Sensor Stream Inspection User Manual</h3>
<p>Raw Mode is designed for direct inspection, frame-by-frame navigation, and temporal stack analysis of raw binary sensor stream files (<code>.raw</code>, <code>.bin</code>, <code>.dat</code>).</p>

<h3>Step-by-Step Workflow</h3>
<ol>
  <li>Click <strong>Load Raw File</strong> and select your raw binary file.</li>
  <li>The <strong>Raw Parameter Dialog</strong> opens pre-populated with your last used Width, Height, and Bit Depth. To change a value, simply click into the box and type (digits overwrite immediately). Click <strong>OK</strong> or press <kbd>Enter</kbd>.</li>
  <li>Use the <strong>Frame Slider</strong>, frame spinbox, or animation controls (<kbd>▶</kbd>) to scrub through frames.</li>
  <li>Click <strong>Create Stack View</strong> to generate an all-frame temporal stack composite.</li>
  <li>Use the <strong>Spatial Ruler 📏</strong> or <strong>ROI Statistics 📊</strong> tools to inspect image features.</li>
</ol>

<h3>Controls &amp; Features Reference</h3>

<h4>1. File &amp; Parameter Controls</h4>
<ul>
  <li><strong>Load Raw File</strong>: Opens a raw binary sensor file.</li>
  <li><strong>Edit Parameters</strong>: Re-opens the parameter dialog to change dimensions or bit depth without re-selecting the file.</li>
  <li><strong>Instant Overwrite</strong>: Clicking or tabbing into Width or Height auto-selects all text, so you can re-type dimensions immediately without pressing backspace.</li>
  <li><strong>Session Parameter Memory</strong>: The app remembers the Width, Height, and Bit Depth used on your previous raw files across launches, allowing 1-click loading for identical files.</li>
  <li><strong>Supported Bit Depths</strong>: <code>8-bit</code>, <code>10-bit packed</code>, <code>12-bit packed</code>, <code>16-bit</code> (little/big-endian), and <code>32-bit</code>.</li>
</ul>

<h4>2. Frame Navigation &amp; Playback</h4>
<ul>
  <li><strong>Frame Index Spinbox</strong>: Jump directly to any frame number.</li>
  <li><strong>Frame Scrubbing Slider</strong>: Drag to scrub smoothly through multi-frame captures.</li>
  <li><strong>Play (▶) / Pause (⏸)</strong>: Plays frame sequence as continuous video.</li>
  <li><strong>Speed Selector</strong>: Adjusts animation playback speed (0.5×, 1×, 2×, 4×).</li>
  <li><strong>Step Buttons (◀ / ▶)</strong>: Steps one frame backward or forward.</li>
  <li><strong>Range Controls (Start / End)</strong>: Restricts playback or processing to a specific frame range.</li>
</ul>

<h4>3. Analysis &amp; Stacking</h4>
<ul>
  <li><strong>Create Stack View</strong>: Assembles all frames into a vertical temporal overview stack with automatic memory stride management.</li>
  <li><strong>Histogram Tab</strong>: Real-time intensity distribution graph displaying Min, Max, Mean, and Standard Deviation.</li>
  <li><strong>Spatial Ruler 📏</strong>: Click 2 points to measure linear pixel length, ΔX/ΔY deltas, and angle.</li>
  <li><strong>ROI Statistics 📊</strong>: Drag a box to compute radiometric statistics (Mean, Variance, StdDev, Min/Max DN, Pixel count).</li>
  <li><strong>Export Image Button</strong>: Exports the current frame or stack composite to PNG, BMP, or TIFF.</li>
</ul>
""",

    "video": """
<h3>Video Mode — Multi-Frame Sequence Generator User Manual</h3>
<p>Video Mode allows you to synthesize multi-spectral band sequences into color video animations with sub-pixel channel registration and video export options.</p>

<h3>Step-by-Step Workflow</h3>
<ol>
  <li>Click <strong>Select Folder</strong> to pick a directory containing multi-spectral <code>.bandXX</code> files.</li>
  <li>In the <strong>RGB Composition</strong> section, assign which bands map to the <strong>Red</strong>, <strong>Green</strong>, and <strong>Blue</strong> channels.</li>
  <li>Adjust per-channel <strong>X / Y Offsets</strong> to align channels and eliminate color fringing.</li>
  <li>Click <strong>Preview RGB</strong> (or check <strong>Auto Preview</strong>) to inspect the color composite at the current frame.</li>
  <li>Set the desired <strong>Frame Range</strong> (Start / End), <strong>FPS</strong> (Frames Per Second), and output format, then click <strong>Generate Video</strong>.</li>
</ol>

<h3>Controls Reference</h3>
<ul>
  <li><strong>Seek Slider &amp; Frame Counter</strong>: Scrub through the video sequence.</li>
  <li><strong>Playback Controls</strong>: Play, pause, step forward/backward, and set playback speed (0.5× to 4×).</li>
  <li><strong>Loop Toggle</strong>: Automatically repeats the video upon reaching the last frame.</li>
  <li><strong>Video Export Formats</strong>: Save output as MP4, AVI, or sequential frame folders.</li>
</ul>
""",

    "tiled": """
<h3>Tiled Mode — Multi-Tile Matrix Stitching User Manual</h3>
<p>Tiled Mode stitches arrays of sensor tiles into full composite frames, supporting flexible scan patterns and edge overlap compensation.</p>

<h3>Step-by-Step Workflow</h3>
<ol>
  <li>Click <strong>Load / Settings</strong> on the top toolbar.</li>
  <li>Select your tile dataset folder and choose the directory structure (<em>Folder per Frame</em> or <em>Flat Tile Directory</em>).</li>
  <li>Specify the matrix dimensions (<strong>Rows</strong> and <strong>Columns</strong>), individual <strong>Tile Width / Height</strong>, <strong>Overlap (pixels)</strong>, and <strong>Bit Depth</strong>.</li>
  <li>Select the sensor scanning pattern (Row-Major, Column-Major, Row Serpentine, Column Serpentine).</li>
  <li>Click <strong>OK</strong> to render the full stitched composite.</li>
  <li>Use the <strong>Tile View</strong> inspector panel to examine individual tiles and their coordinate placement.</li>
</ol>

<h3>Controls Reference</h3>
<ul>
  <li><strong>Scanning Patterns</strong>: Supports standard Row-Major, Column-Major, and alternating Serpentine (zigzag) scan orders.</li>
  <li><strong>Overlap Compensation</strong>: Blends adjacent tile edges seamlessly by removing overlapping pixel columns/rows.</li>
  <li><strong>Tile View Inspector (▶)</strong>: Interactive visual tile matrix showing tile status, coordinates, and raw data.</li>
  <li><strong>Export Options</strong>: Save current stitched composite or batch-export complete frame sequences.</li>
</ul>
""",

    "editor": """
<h3>Image Editor — Post-Processing User Manual</h3>
<p>The integrated Image Editor provides direct post-processing, geometric adjustments, and enhancement filters.</p>

<h3>Available Tools &amp; Operations</h3>
<ul>
  <li><strong>Crop Tool</strong>: Click and drag to crop a custom region, or choose fixed aspect ratios.</li>
  <li><strong>Resize &amp; Scale</strong>: Scale dimensions with bicubic or bilinear resampling.</li>
  <li><strong>Orientation</strong>: Rotate in 90° steps or flip horizontally/vertically.</li>
  <li><strong>Radiometric Filters</strong>: Apply Unsharp Mask sharpening, Gaussian blur, edge detection, and noise reduction.</li>
  <li><strong>Color &amp; Tone Adjustments</strong>: Modify brightness, contrast, gamma curve, saturation, and invert color channels.</li>
  <li><strong>Export</strong>: Save processed images directly to high-resolution PNG, TIFF, or BMP.</li>
</ul>
""",

    "global": """
<h3>Global Shortcuts &amp; User Reference Guide</h3>

<h3>Keyboard Shortcuts Table</h3>
<table>
  <tr><th>Shortcut</th><th>Action</th><th>Context</th></tr>
  <tr><td><kbd>Shift</kbd> + <kbd>N</kbd></td><td>Create New Dataset Tab</td><td>Global</td></tr>
  <tr><td><kbd>Shift</kbd> + <kbd>Q</kbd></td><td>Close Current Tab</td><td>Global</td></tr>
  <tr><td><kbd>Shift</kbd> + <kbd>Enter</kbd></td><td>Open Folder Selection Dialog</td><td>Band Mode</td></tr>
  <tr><td><kbd>Ctrl</kbd> + <kbd>S</kbd></td><td>Save Parameters / Dataset Settings</td><td>Global</td></tr>
  <tr><td><kbd>Space</kbd></td><td>Play / Pause Frame Animation</td><td>All Modes</td></tr>
  <tr><td><kbd>←</kbd> / <kbd>→</kbd></td><td>Step Previous / Next Frame</td><td>All Modes</td></tr>
  <tr><td><kbd>Ctrl</kbd> + <kbd>↑</kbd> / <kbd>↓</kbd></td><td>Zoom In / Zoom Out</td><td>Image Viewers</td></tr>
  <tr><td><kbd>Ctrl</kbd> + Scroll Wheel</td><td>Smooth Mouse Zoom at Cursor</td><td>Image Viewers</td></tr>
  <tr><td><kbd>Ctrl</kbd> + <kbd>Space</kbd></td><td>Export Current Image</td><td>Global</td></tr>
  <tr><td><kbd>Ctrl</kbd> + <kbd>Enter</kbd></td><td>Toggle Contrast Enhancement</td><td>Band Mode</td></tr>
  <tr><td><kbd>Tab</kbd> / <kbd>Shift</kbd>+<kbd>Tab</kbd></td><td>Cycle to Next / Previous View Tab</td><td>Band Mode</td></tr>
  <tr><td><kbd>Esc</kbd></td><td>Exit Fullscreen View</td><td>Image Viewers</td></tr>
</table>

<h3>Quick Tips for Maximum Productivity</h3>
<ul>
  <li><strong>Instant Value Overwrite</strong>: When editing parameters (Width, Height, TDI), you do not need to press backspace. Just click the box or press <kbd>Tab</kbd>—the text is selected automatically so typing instantly replaces it.</li>
  <li><strong>Viewport Background Color</strong>: Click the circular button in the top-right corner of any image viewer to change the background canvas color. Your chosen color automatically stays synchronized across all views and persists when you restart the app.</li>
  <li><strong>Draggable Pixel Info Box</strong>: You can float the Pixel Info Box and drag it anywhere over your workspace to keep measurements visible without obstructing the main view.</li>
  <li><strong>Measuring Distance &amp; Ground Size</strong>: Turn on <em>Spatial Ruler</em> in the Toolbox menu and click two points on the image. When geospatial metadata is available, the physical distance on the ground is automatically calculated and shown in meters or kilometers.</li>
</ul>
"""
}


def _default_help_html(mode="band", is_dark=None, main_app=None):
    key = (mode or "band").strip().lower()
    if key not in _MODE_RAW_CONTENT:
        key = "band"

    if is_dark is None:
        is_dark = _detect_dark_mode(main_app)

    css = _get_css(is_dark=is_dark)
    title = _MODE_TITLES.get(key, "User Manual")
    body = _MODE_RAW_CONTENT.get(key, "")
    return f"{css}<h2>{title}</h2>{body}"


def load_help_file(path):
    try:
        if not path:
            return None, False
        if not os.path.exists(path):
            return None, False
        _, ext = os.path.splitext(path.lower())
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        if ext in (".html", ".htm"):
            return data, True
        safe = html_module.escape(data).replace("\n", "<br/>\n")
        return safe, True
    except Exception:
        return None, False


def create_help_tab(main_app=None, help_file_path=None, use_html=True, mode="band"):
    w = QWidget()
    layout = QVBoxLayout()
    w.setLayout(layout)

    help_text = QTextEdit()
    help_text.setReadOnly(True)
    help_text.setLineWrapMode(QTextEdit.WidgetWidth)

    is_dark = _detect_dark_mode(main_app)
    _apply_textedit_style(help_text, is_dark)

    file_content, file_is_html = load_help_file(help_file_path)
    if file_content:
        if use_html and file_is_html:
            help_text.setHtml(file_content)
        elif use_html and not file_is_html:
            help_text.setHtml(file_content)
        else:
            help_text.setPlainText(html_module.unescape(file_content).replace("<br/>\n", "\n"))
    else:
        if use_html:
            help_text.setHtml(_default_help_html(mode=mode, is_dark=is_dark, main_app=main_app))
        else:
            help_text.setPlainText(html_module.unescape(_default_help_html(mode=mode, is_dark=is_dark, main_app=main_app)))

    layout.addWidget(help_text)

    w._help_widget = help_text
    w._help_file_path = help_file_path
    w._help_mode = mode

    def update_help(new_text=None, as_html=True, new_mode=None, is_dark=None):
        active_mode = new_mode or w._help_mode
        if is_dark is None:
            is_dark = _detect_dark_mode(main_app)

        _apply_textedit_style(help_text, is_dark)

        if new_text is None:
            fc, _ = load_help_file(help_file_path)
            if fc:
                if as_html:
                    help_text.setHtml(fc)
                else:
                    help_text.setPlainText(html_module.unescape(fc).replace("<br/>\n", "\n"))
            else:
                rendered = _default_help_html(mode=active_mode, is_dark=is_dark, main_app=main_app)
                if as_html:
                    help_text.setHtml(rendered)
                else:
                    help_text.setPlainText(html_module.unescape(rendered))
        else:
            if as_html:
                css = _get_css(is_dark=is_dark)
                help_text.setHtml(f"{css}{new_text}")
            else:
                help_text.setPlainText(new_text)

    w.update_help = update_help
    return w


def _apply_textedit_style(help_text, is_dark):
    if is_dark:
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: none;
                selection-background-color: #0288D1;
                selection-color: #FFFFFF;
            }
        """)
    else:
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #212121;
                border: none;
                selection-background-color: #0288D1;
                selection-color: #FFFFFF;
            }
        """)
