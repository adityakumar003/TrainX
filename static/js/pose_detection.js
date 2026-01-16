// MediaPipe Pose Detection - Web Implementation
// Real-time pose detection in browser using MediaPipe Pose

let camera = null;
let pose = null;
let canvasCtx = null;
let currentPose = "Front Double Biceps";
let holdStartTime = null;
let screenshotTaken = false;

// Audio elements
let correctSound = null;
let coachSound = null;

// Initialize audio
function initAudio() {
    correctSound = new Audio('/static/audio/correct.mp3');
    coachSound = new Audio('/static/audio/coach.mp3');

    // Preload audio
    correctSound.load();
    coachSound.load();
}

// Initialize MediaPipe Pose
function initPoseDetection() {
    const videoElement = document.getElementById('webcam');
    const canvasElement = document.getElementById('output-canvas');
    canvasCtx = canvasElement.getContext('2d');

    // Initialize MediaPipe Pose
    pose = new Pose({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
        }
    });

    pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.7
    });

    pose.onResults(onPoseResults);

    // Initialize camera
    camera = new Camera(videoElement, {
        onFrame: async () => {
            await pose.send({ image: videoElement });
        },
        width: 1280,
        height: 720
    });

    camera.start();
}

// Process pose detection results
function onPoseResults(results) {
    const videoElement = document.getElementById('webcam');
    const canvasElement = document.getElementById('output-canvas');

    // Set canvas size to match video
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;

    // Clear canvas
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

    // Draw the video frame
    canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);

    if (results.poseLandmarks) {
        // Draw pose landmarks
        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, { color: '#00FF00', lineWidth: 4 });
        drawLandmarks(canvasCtx, results.poseLandmarks, { color: '#FF0000', lineWidth: 2, radius: 6 });

        // Convert landmarks to array format for scoring
        const landmarks = results.poseLandmarks.map(lm => [lm.x, lm.y, lm.z]);

        // Score the current pose
        const result = scorePose(currentPose, landmarks);
        const score = result.score;
        const feedback = result.feedback;

        // Update UI
        updateScoreDisplay(score, feedback);

        // Handle hold timer and screenshot
        handleHoldTimer(score, canvasElement);

        // Draw overlay information
        drawOverlay(score, feedback);
    }

    canvasCtx.restore();
}

// Draw overlay information on canvas - REMOVED to keep camera view clean
// All UI elements are now in the HTML sidebar
function drawOverlay(score, feedback) {
    // No overlay drawing - camera view stays clean
    // Score, feedback, and controls are all in the sidebar
}

// Update score display in UI
function updateScoreDisplay(score, feedback) {
    const scoreElement = document.getElementById('score-value');
    const feedbackElement = document.getElementById('feedback-text');
    const scoreBar = document.getElementById('score-bar');
    const holdTimerContainer = document.getElementById('hold-timer-container');
    const holdTimerElement = document.getElementById('hold-timer');

    if (scoreElement) scoreElement.textContent = score;
    if (feedbackElement) feedbackElement.textContent = feedback;
    if (scoreBar) {
        scoreBar.style.width = `${score}%`;
        scoreBar.className = 'score-bar ' + (score >= 80 ? 'good' : 'poor');
    }

    // Update hold timer display
    if (holdStartTime && holdTimerContainer && holdTimerElement) {
        const holdTime = Math.floor((Date.now() - holdStartTime) / 1000);
        holdTimerContainer.style.display = 'block';
        holdTimerElement.textContent = `${holdTime}s`;
    } else if (holdTimerContainer) {
        holdTimerContainer.style.display = 'none';
    }
}

// Handle hold timer and screenshot
function handleHoldTimer(score, canvasElement) {
    const now = Date.now();

    if (score >= 80) {
        if (holdStartTime === null) {
            holdStartTime = now;
            screenshotTaken = false;
        } else if ((now - holdStartTime) >= 3000 && !screenshotTaken) {
            // Take screenshot after 3 seconds of good pose
            takeScreenshot(canvasElement);
            screenshotTaken = true;

            // Play success sound
            if (correctSound) {
                correctSound.play().catch(e => console.log('Audio play failed:', e));
            }

            // Show success message
            showNotification('Perfect! Screenshot captured! 📸', 'success');
        }
    } else {
        if (holdStartTime !== null && !screenshotTaken) {
            // Play coach sound when losing good pose
            if (coachSound && score > 0) {
                coachSound.play().catch(e => console.log('Audio play failed:', e));
            }
        }
        holdStartTime = null;
        screenshotTaken = false;
    }
}

// Take screenshot of current pose
function takeScreenshot(canvasElement) {
    const link = document.createElement('a');
    link.download = `${currentPose.replace(/\s+/g, '_')}_${Date.now()}.png`;
    link.href = canvasElement.toDataURL('image/png');
    link.click();
}

// Manual screenshot button
function captureManualScreenshot() {
    const canvasElement = document.getElementById('output-canvas');
    takeScreenshot(canvasElement);
    showNotification('Screenshot saved! 📸', 'success');
}

// Switch pose
function switchPose(poseName) {
    currentPose = poseName;
    holdStartTime = null;
    screenshotTaken = false;

    // Update active button
    document.querySelectorAll('.pose-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update pose name display
    document.getElementById('current-pose').textContent = poseName;

    showNotification(`Switched to: ${poseName}`, 'info');
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    if (!notification) return;

    notification.textContent = message;
    notification.className = `notification ${type} show`;

    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initAudio();
    initPoseDetection();

    // Set initial pose display
    document.getElementById('current-pose').textContent = currentPose;
});

// Stop camera when leaving page
window.addEventListener('beforeunload', () => {
    if (camera) {
        camera.stop();
    }
});
