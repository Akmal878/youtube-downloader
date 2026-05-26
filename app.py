from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from flask_cors import CORS
import subprocess
import json
import os
import sys
from pathlib import Path
import tempfile
import shutil
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get proxy from environment (optional)
PROXY = os.environ.get('YOUTUBE_PROXY', '')  # Format: http://ip:port or socks5://ip:port

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Use system temp directory for temporary downloads
TEMP_DIR = Path(tempfile.gettempdir()) / 'yt_dlp_downloads'
TEMP_DIR.mkdir(exist_ok=True)

# Use yt-dlp as an installed module (works on both local and Render)
YT_DLP_CMD = f"{sys.executable} -m yt_dlp"

def get_request_data():
    """Safely get JSON data from request, handling Render proxy issues"""
    try:
        # Try standard request.json first
        if request.json:
            return request.json
    except:
        pass
    
    # If that fails, try parsing raw body as JSON
    try:
        if request.data:
            return json.loads(request.data.decode('utf-8'))
    except:
        pass
    
    return None

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Get video information including thumbnail and available formats"""
    try:
        data = get_request_data()
        
        if not data:
            logger.error("No JSON data in request")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        url = data.get('url', '').strip()
        logger.info(f"Processing URL: {url}")
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Get video info using yt-dlp
        # Use comprehensive headers and extractor args to bypass YouTube bot detection
        cmd = f'{YT_DLP_CMD} --js-runtimes node -j --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" --extractor-args "youtube:player_client=web,tv" --socket-timeout 30'
        
        if PROXY:
            cmd += f' --proxy "{PROXY}"'
        
        cmd += f' "{url}"'
        logger.info(f"Running command: {cmd}")
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=60)
        
        logger.info(f"yt-dlp return code: {result.returncode}")
        logger.info(f"yt-dlp stdout: {result.stdout[:500]}")
        logger.info(f"yt-dlp stderr: {result.stderr[:500]}")
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"yt-dlp failed: {error_msg}")
            return jsonify({'error': f'Failed to fetch video info: {error_msg}'}), 400
        
        try:
            video_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}, stdout: {result.stdout}")
            return jsonify({'error': 'Invalid video data received'}), 400
        
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
        data = get_request_data()
        
        if not data:
            logger.error("No JSON data in download request")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        url = data.get('url', '').strip()
        height = data.get('height', 0)
        logger.info(f"Download - URL: {url}, Height: {height}")
        
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
        # Use comprehensive headers and extractor args to bypass YouTube bot detection
        cmd = [
            sys.executable,
            '-m', 'yt_dlp',
            '--js-runtimes', 'node',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--extractor-args', 'youtube:player_client=web,tv',
            '--socket-timeout', '30',
            '--no-cache-dir',
            '-f', format_str,
            '-o', output_path,
            '--merge-output-format', 'mp4',
            '--postprocessor-args', '-c:a aac',
        ]
        
        if PROXY:
            cmd.extend(['--proxy', PROXY])
        
        cmd.append(url)
        
        logger.info(f"Download command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        logger.info(f"Download return code: {result.returncode}")
        logger.info(f"Download stderr: {result.stderr[:200] if result.stderr else 'None'}")
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else 'Unknown error'
            logger.error(f"Download failed: {error_msg}")
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
