// Pose Scoring Algorithms - JavaScript Port from Python
// Ported from pose_detection1/app1.py

// Utility function to calculate angle between three points
function calculateAngle(a, b, c) {
    const ba = [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
    const bc = [c[0] - b[0], c[1] - b[1], c[2] - b[2]];

    const dotProduct = ba[0] * bc[0] + ba[1] * bc[1] + ba[2] * bc[2];
    const magnitudeBA = Math.sqrt(ba[0] ** 2 + ba[1] ** 2 + ba[2] ** 2);
    const magnitudeBC = Math.sqrt(bc[0] ** 2 + bc[1] ** 2 + bc[2] ** 2);

    const cosine = dotProduct / (magnitudeBA * magnitudeBC);
    const clampedCosine = Math.max(-1.0, Math.min(1.0, cosine));

    return Math.acos(clampedCosine) * (180 / Math.PI);
}

// Check if pose is ready (hands above shoulders)
function isPoseReady(landmarks) {
    const leftWristY = landmarks[15][1];
    const rightWristY = landmarks[16][1];
    const leftShoulderY = landmarks[11][1];
    const rightShoulderY = landmarks[12][1];

    return (leftWristY < leftShoulderY - 0.02 &&
        rightWristY < rightShoulderY - 0.02);
}

// FRONT DOUBLE BICEPS
function scoreFrontDoubleBiceps(landmarks) {
    if (!isPoseReady(landmarks)) {
        return { score: 0, feedback: "Lift arms above shoulders" };
    }

    const leftAngle = calculateAngle(landmarks[11], landmarks[13], landmarks[15]);
    const rightAngle = calculateAngle(landmarks[12], landmarks[14], landmarks[16]);

    // Human arm scoring function
    function humanArmScore(angle) {
        if (angle >= 50 && angle <= 100) {
            return 100;
        } else if ((angle >= 40 && angle < 50) || (angle > 100 && angle <= 115)) {
            return 85;
        } else if ((angle >= 30 && angle < 40) || (angle > 115 && angle <= 130)) {
            return 65;
        } else {
            return 40;
        }
    }

    const leftScore = humanArmScore(leftAngle);
    const rightScore = humanArmScore(rightAngle);

    const symmetryDiff = Math.abs(leftAngle - rightAngle);
    const symmetryPenalty = Math.max(0, symmetryDiff - 20) * 0.7;

    let score = (leftScore + rightScore) / 2 - symmetryPenalty;
    score = Math.max(0, Math.min(100, score));

    let feedback;
    if (score >= 85) {
        feedback = "Strong double biceps!";
    } else if (symmetryDiff > 25) {
        feedback = "Match arm angles";
    } else {
        feedback = "Flex biceps more";
    }

    return { score: Math.round(score), feedback, leftAngle, rightAngle };
}

// BACK DOUBLE BICEPS
function scoreBackDoubleBiceps(landmarks) {
    if (!isPoseReady(landmarks)) {
        return { score: 0, feedback: "Raise arms and flex back" };
    }

    const leftAngle = calculateAngle(landmarks[11], landmarks[13], landmarks[15]);
    const rightAngle = calculateAngle(landmarks[12], landmarks[14], landmarks[16]);

    // Back arm scoring function
    function backArmScore(angle) {
        if (angle >= 65 && angle <= 110) {
            return 100;
        } else if ((angle >= 55 && angle < 65) || (angle > 110 && angle <= 125)) {
            return 85;
        } else if ((angle >= 45 && angle < 55) || (angle > 125 && angle <= 140)) {
            return 65;
        } else {
            return 40;
        }
    }

    const leftScore = backArmScore(leftAngle);
    const rightScore = backArmScore(rightAngle);

    const symmetryDiff = Math.abs(leftAngle - rightAngle);
    const symmetryPenalty = Math.max(0, symmetryDiff - 30) * 0.5;

    let score = (leftScore + rightScore) / 2 - symmetryPenalty;
    score = Math.max(0, Math.min(100, score));

    let feedback;
    if (score >= 85) {
        feedback = "Strong back double biceps!";
    } else if (symmetryDiff > 35) {
        feedback = "Balance both arms";
    } else if (leftAngle > 125 || rightAngle > 125) {
        feedback = "Bend elbows slightly more";
    } else if (leftAngle < 55 || rightAngle < 55) {
        feedback = "Flex arms and back harder";
    } else {
        feedback = "Tighten back and raise elbows";
    }

    return { score: Math.round(score), feedback, leftAngle, rightAngle };
}

// SIDE CHEST
function scoreSideChest(landmarks) {
    const leftWristY = landmarks[15][1];
    const rightWristY = landmarks[16][1];
    const leftShoulderY = landmarks[11][1];
    const rightShoulderY = landmarks[12][1];
    const leftHipY = landmarks[23][1];
    const rightHipY = landmarks[24][1];

    // Chest-height zone
    const chestTop = Math.min(leftShoulderY, rightShoulderY) + 0.05;
    const chestBottom = Math.max(leftHipY, rightHipY) - 0.05;

    if (!((chestTop < leftWristY && leftWristY < chestBottom) ||
        (chestTop < rightWristY && rightWristY < chestBottom))) {
        return { score: 0, feedback: "Bring arms in front of chest" };
    }

    const leftElbow = calculateAngle(landmarks[11], landmarks[13], landmarks[15]);
    const rightElbow = calculateAngle(landmarks[12], landmarks[14], landmarks[16]);

    // Identify front arm (more bent)
    const frontAngle = Math.min(leftElbow, rightElbow);
    const backAngle = Math.max(leftElbow, rightElbow);

    // Front arm scoring
    let frontScore;
    if (frontAngle >= 50 && frontAngle <= 100) {
        frontScore = 100;
    } else if ((frontAngle >= 40 && frontAngle < 50) || (frontAngle > 100 && frontAngle <= 120)) {
        frontScore = 80;
    } else {
        frontScore = 55;
    }

    // Back arm scoring
    let backScore;
    if (backAngle >= 70 && backAngle <= 140) {
        backScore = 100;
    } else if ((backAngle >= 60 && backAngle < 70) || (backAngle > 140 && backAngle <= 160)) {
        backScore = 80;
    } else {
        backScore = 60;
    }

    let score = 0.7 * frontScore + 0.3 * backScore;
    score = Math.max(0, Math.min(100, score));

    let feedback;
    if (score >= 85) {
        feedback = "Nice side chest!";
    } else if (frontAngle < 50) {
        feedback = "Squeeze chest more";
    } else {
        feedback = "Adjust arm position";
    }

    return { score: Math.round(score), feedback, frontAngle, backAngle };
}

// LAT FLEX / LAT SPREAD
function scoreLatFlex(landmarks) {
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const leftWrist = landmarks[15];
    const rightWrist = landmarks[16];

    // Calculate shoulder width
    const shoulderWidth = Math.sqrt(
        (leftShoulder[0] - rightShoulder[0]) ** 2 +
        (leftShoulder[1] - rightShoulder[1]) ** 2 +
        (leftShoulder[2] - rightShoulder[2]) ** 2
    );

    // Calculate wrist width
    const wristWidth = Math.sqrt(
        (leftWrist[0] - rightWrist[0]) ** 2 +
        (leftWrist[1] - rightWrist[1]) ** 2 +
        (leftWrist[2] - rightWrist[2]) ** 2
    );

    const ratio = wristWidth / (shoulderWidth + 1e-6);

    // Check that arms are at ribcage level
    const leftWristY = landmarks[15][1];
    const rightWristY = landmarks[16][1];
    const leftHipY = landmarks[23][1];
    const rightHipY = landmarks[24][1];
    const leftShoulderY = landmarks[11][1];
    const rightShoulderY = landmarks[12][1];

    const chestTop = Math.min(leftShoulderY, rightShoulderY) + 0.05;
    const hipLine = Math.max(leftHipY, rightHipY) - 0.02;

    const handsInZone = (chestTop < leftWristY && leftWristY < hipLine) &&
        (chestTop < rightWristY && rightWristY < hipLine);

    if (!handsInZone) {
        return { score: 0, feedback: "Keep elbows wide at ribcage level" };
    }

    let score, feedback;

    if (ratio >= 1.25) {
        score = 100;
        feedback = "Huge lat spread!";
    } else if (ratio >= 1.15) {
        score = Math.round(90 + (ratio - 1.15) * 100);
        feedback = "Great lat spread";
    } else if (ratio >= 1.05) {
        score = Math.round(75 + (ratio - 1.05) * 150);
        feedback = "Good, flare lats a bit more";
    } else {
        score = Math.max(50, Math.round(ratio * 60));
        feedback = "Spread elbows out and widen back";
    }

    score = Math.max(0, Math.min(100, score));

    return { score, feedback, ratio };
}

// Main scoring function - routes to appropriate pose scorer
function scorePose(poseName, landmarks) {
    switch (poseName) {
        case "Front Double Biceps":
            return scoreFrontDoubleBiceps(landmarks);
        case "Back Double Biceps":
            return scoreBackDoubleBiceps(landmarks);
        case "Side Chest":
            return scoreSideChest(landmarks);
        case "Lat Flex":
            return scoreLatFlex(landmarks);
        default:
            return { score: 0, feedback: "Unknown pose" };
    }
}
