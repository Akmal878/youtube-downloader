# YouTube Video Downloader

A simple web application to download YouTube videos in your preferred quality with audio.

## Features

- **Clean Interface**: Simple white theme, no clutter
- **Multiple Qualities**: Download videos in resolutions from 144p and up
- **Audio Support**: Automatic audio codec conversion to AAC for compatibility
- **Browser Downloads**: Videos save to your browser's default downloads folder
- **Real-time Progress**: Visual progress bar during downloads

## Local Development

### Requirements

- Python 3.11+
- FFmpeg (installed automatically via yt-dlp)

### Setup

1. Clone or download the project
2. Create virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run locally:
   ```bash
   python app.py
   ```

5. Open http://localhost:5000 in your browser

## Deployment on Render

### Step 1: Prepare GitHub Repository

1. Initialize git:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. Push to GitHub (create repo on github.com first)

### Step 2: Deploy to Render

1. Go to [render.com](https://render.com)
2. Sign up (free account)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Fill in settings:
   - **Name**: youtube-downloader
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. Click "Create Web Service"

Your app will be live in 2-3 minutes at: `https://youtube-downloader-xxx.onrender.com`

## WordPress Integration

### Method 1: Simple Shortcode Plugin

Create a WordPress plugin file `video-downloader-plugin.php`:

```php
<?php
/*
Plugin Name: Video Downloader
Description: Embed YouTube downloader
Version: 1.0
*/

add_shortcode('video_downloader', 'vd_shortcode');

function vd_shortcode() {
    wp_enqueue_style('vd-style', plugin_dir_url(__FILE__) . 'style.css');
    wp_enqueue_script('vd-script', plugin_dir_url(__FILE__) . 'script.js', [], false, true);
    
    wp_localize_script('vd-script', 'vdConfig', [
        'apiUrl' => 'https://your-render-url.onrender.com'
    ]);
    
    return '<div id="video-downloader"></div>';
}
```

Then in WordPress pages/posts, use: `[video_downloader]`

### Method 2: iFrame Embed

Simply add to any WordPress page:

```html
<iframe src="https://your-render-url.onrender.com" width="100%" height="900" frameborder="0"></iframe>
```

## Technical Details

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Video Tool**: yt-dlp
- **Audio Processing**: FFmpeg (automatic AAC conversion)
- **Deployment**: Render.com (free tier)

## Environment Variables

- `PORT`: Server port (default: 5000)
- `FLASK_ENV`: Set to "development" for debug mode

## License

Open source. Feel free to use and modify.
