// DOM Elements
const urlInput = document.getElementById('urlInput');
const fetchBtn = document.getElementById('fetchBtn');
const videoContent = document.getElementById('videoContent');
const emptyState = document.getElementById('emptyState');
const errorMessage = document.getElementById('errorMessage');
const videoTitle = document.getElementById('videoTitle');
const thumbnail = document.getElementById('thumbnail');
const uploader = document.getElementById('uploader');
const duration = document.getElementById('duration');
const qualityOptions = document.getElementById('qualityOptions');
const downloadBtn = document.getElementById('downloadBtn');
const downloadStatus = document.getElementById('downloadStatus');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressPercent = document.getElementById('progressPercent');

let currentVideoData = null;
let selectedFormat = null;

// Format seconds to readable time
function formatDuration(seconds) {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    setTimeout(() => {
        errorMessage.classList.add('hidden');
    }, 5000);
}

// Show download status
function showStatus(message, type = 'info') {
    downloadStatus.textContent = message;
    downloadStatus.className = `status-message ${type}`;
    downloadStatus.classList.remove('hidden');
    
    if (type === 'success') {
        setTimeout(() => {
            downloadStatus.classList.add('hidden');
        }, 5000);
    }
}

// Update progress bar
function updateProgress(percent) {
    progressFill.style.width = percent + '%';
    progressPercent.textContent = percent + '%';
}

// Fetch video information
async function fetchVideoInfo() {
    const url = urlInput.value.trim();
    
    if (!url) {
        showError('Please enter a video URL');
        return;
    }
    
    fetchBtn.disabled = true;
    
    try {
        const response = await fetch('/api/video-info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            showError(errorData.error || 'Failed to fetch video info');
            return;
        }
        
        currentVideoData = await response.json();
        displayVideoInfo();
        errorMessage.classList.add('hidden');
        
    } catch (error) {
        showError(`Error: ${error.message}`);
    } finally {
        fetchBtn.disabled = false;
    }
}

// Display video information
function displayVideoInfo() {
    if (!currentVideoData) return;
    
    // Update video info
    videoTitle.textContent = currentVideoData.title;
    thumbnail.src = currentVideoData.thumbnail;
    thumbnail.alt = currentVideoData.title;
    uploader.textContent = currentVideoData.uploader;
    duration.textContent = formatDuration(currentVideoData.duration);
    
    // Display quality options
    qualityOptions.innerHTML = '';
    currentVideoData.formats.forEach((format, index) => {
        const btn = document.createElement('button');
        btn.className = 'quality-btn';
        if (index === 0) {
            btn.classList.add('selected');
            selectedFormat = format;
        }
        btn.textContent = format.quality;
        btn.onclick = () => selectQuality(format, btn);
        qualityOptions.appendChild(btn);
    });
    
    // Show video content, hide empty state
    videoContent.classList.remove('hidden');
    emptyState.classList.add('hidden');
    downloadStatus.classList.add('hidden');
    progressContainer.classList.add('hidden');
}

// Select quality option
function selectQuality(format, element) {
    // Remove previous selection
    document.querySelectorAll('.quality-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    
    // Add selection to current
    element.classList.add('selected');
    selectedFormat = format;
}

// Download video
async function downloadVideo() {
    if (!currentVideoData || !selectedFormat) {
        showError('Please select a quality first');
        return;
    }
    
    const url = urlInput.value.trim();
    
    downloadBtn.disabled = true;
    progressContainer.classList.remove('hidden');
    updateProgress(0);
    showStatus('Preparing download...', 'info');
    
    try {
        // Simulate progress
        let progress = 10;
        const progressInterval = setInterval(() => {
            if (progress < 90) {
                progress += Math.random() * 30;
                updateProgress(Math.min(Math.floor(progress), 90));
            }
        }, 500);
        
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                height: selectedFormat.height
            })
        });
        
        clearInterval(progressInterval);
        
        if (!response.ok) {
            const errorData = await response.json();
            showStatus(`Error: ${errorData.error || 'Download failed'}`, 'error');
            updateProgress(0);
            return;
        }
        
        // Get the file from response
        const blob = await response.blob();
        
        // Create download link and trigger download
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = 'video.mp4';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
        
        updateProgress(100);
        showStatus('Download completed successfully', 'success');
        
        // Reset progress after delay
        setTimeout(() => {
            progressContainer.classList.add('hidden');
            updateProgress(0);
        }, 2000);
        
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        updateProgress(0);
    } finally {
        downloadBtn.disabled = false;
    }
}

// Event listeners
fetchBtn.addEventListener('click', fetchVideoInfo);
downloadBtn.addEventListener('click', downloadVideo);

// Allow Enter key to fetch video
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        fetchVideoInfo();
    }
});

// Clear error when user types
urlInput.addEventListener('input', () => {
    if (!errorMessage.classList.contains('hidden')) {
        errorMessage.classList.add('hidden');
    }
});
