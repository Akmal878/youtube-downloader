from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from flask_cors import CORS
import subprocess
import json
import os
import sys
from pathlib import Path
import tempfile
import shutil

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Use system temp directory for temporary downloads
TEMP_DIR = Path(tempfile.gettempdir()) / 'yt_dlp_downloads'
TEMP_DIR.mkdir(exist_ok=True)

# Use yt-dlp as an installed module (works on both local and Render)
YT_DLP_CMD = f"{sys.executable} -m yt_dlp"

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Get video information including thumbnail and available formats"""
    try:
        # Handle both JSON and form data
        data = request.json or request.form
        if not data:
            # Try to parse raw body as JSON
            try:
                data = json.loads(request.data.decode('utf-8'))
            except:
                return jsonify({'error': 'Invalid request format'}), 400
        
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Get video info using yt-dlp
        cmd = f'{YT_DLP_CMD} -j "{url}"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode != 0:
            return jsonify({'error': 'Failed to fetch video info. Invalid URL?'}), 400
        
        video_data = json.loads(result.stdout)
        
        # Extract all unique heights (144p and higher only)
        formats_dict = {}
        
        if 'formats' in video_data:
            for fmt in video_data['formats']:
                height = fmt.get('height') or 0
                
                # Only process formats with valid heights >= 144p
                if height and height >= 144:
                    quality_label = f"{height}p"
                    
                    # Only add if we haven't seen this quality yet
                    if quality_label not in formats_dict:
                        formats_dict[quality_label] = {
                            'format_id': fmt.get('format_id'),
                            'quality': quality_label,
                            'height': height,
                            'ext': fmt.get('ext', 'mp4')
                        }
        
        # Sort by height in descending order
        formats = sorted(formats_dict.values(), key=lambda x: x.get('height', 0), reverse=True)
        
        return jsonify({
            'title': video_data.get('title', 'Unknown'),
            'thumbnail': video_data.get('thumbnail', ''),
            'duration': video_data.get('duration', 0),
            'uploader': video_data.get('uploader', 'Unknown'),
            'formats': formats
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    """Download video with selected quality"""
    try:
        # Handle both JSON and form data
        data = request.json or request.form
        if not data:
            # Try to parse raw body as JSON
            try:
                data = json.loads(request.data.decode('utf-8'))
            except:
                return jsonify({'error': 'Invalid request format'}), 400
        
        url = data.get('url', '').strip()
        height = data.get('height', 0)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Create temp directory if it doesn't exist
        TEMP_DIR.mkdir(exist_ok=True)
        
        # Build format string to get video + audio with height constraint
        # Prefer m4a/aac audio over opus (opus not widely supported)
        # Try: bestvideo+bestaudio[codec!=opus], then fallback to combined best
        format_str = f"bestvideo[height<={height}]+bestaudio[acodec=aac]/bestvideo[height<={height}]+bestaudio[acodec=mp4a]/bestvideo[height<={height}]+bestaudio[acodec!=opus]/best"
        
        # Create output path in temp directory with quality in filename
        # This ensures different qualities are saved as separate files
        output_path = str(TEMP_DIR / f'{height}p_%(title)s.%(ext)s')
        
        # Download using yt-dlp with selected format
        # Use FFmpeg to re-encode audio to AAC for compatibility
        cmd = [
            sys.executable,
            '-m', 'yt_dlp',
            '--no-cache-dir',
            '-f', format_str,
            '-o', output_path,
            '--merge-output-format', 'mp4',
            '--postprocessor-args', '-c:a aac',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else 'Unknown error'
            return jsonify({'error': f'Download failed: {error_msg}'}), 400
        
        # Find the downloaded file
        downloaded_files = list(TEMP_DIR.glob('*'))
        if not downloaded_files:
            return jsonify({'error': 'Download completed but file not found'}), 400
        
        # Get the most recently modified file
        video_file = max(downloaded_files, key=lambda x: x.stat().st_mtime)
        
        # Send file to browser with proper headers for download
        return send_file(
            video_file,
            as_attachment=True,
            download_name=video_file.name,
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Serve the frontend"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"Server starting on port {port}...")
    print(f"Open http://localhost:{port} in your browser")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
