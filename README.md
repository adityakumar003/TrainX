# 🏋️ GymLife - AI-Powered Fitness Tracking Application

A full-stack web application built with Flask and MongoDB that helps users manage gym workouts, calculate BMI, track fitness progress, and explore exercises by body part. Features an integrated AI-based pose detection system for real-time form checking.

---

## ✨ Features

### 🔐 Authentication
- User signup & login with secure password hashing
- Session-based authentication
- User profile management

### 💪 Workout Management
- Add workouts with multiple exercises
- Track reps, sets, weight, and calories
- View workout history
- Edit or delete exercises
- Automatic calorie calculation

### 📊 BMI Calculator
- Calculate BMI using height & weight
- BMI categorization (Underweight, Healthy, Overweight, Obese)
- Store body metrics in database

### 🎯 Exercise Library
Exercises categorized by body parts:
- Chest
- Back
- Legs
- Biceps
- Triceps
- Shoulders
- Core

Each exercise includes:
- Animated GIF demonstration
- Target muscles
- Secondary muscles
- Step-by-step instructions

### 🤖 AI CheckFit (Pose Detection)
- Real-time pose detection using MediaPipe
- AI bodybuilding coach feedback
- Support for multiple poses:
  - Front Double Biceps
  - Back Double Biceps
  - Side Chest
  - Lat Flex
- Audio feedback for correct/incorrect form
- Automatic screenshot when pose is held correctly

---

## 🛠️ Tech Stack

### Backend
- **Python 3.10**
- **Flask 2.3.3** - Web framework
- **Flask-PyMongo** - MongoDB integration
- **Flask-Bcrypt** - Password hashing
- **Flask-CORS** - Cross-origin resource sharing
- **python-dotenv** - Environment variable management

### Database
- **MongoDB** - NoSQL database for user data and workouts

### Frontend
- HTML5
- CSS3
- JavaScript
- Jinja2 Templates
- Bootstrap 4

### AI/ML
- **MediaPipe 0.10.14** - Pose detection
- **OpenCV 4.12.0** - Computer vision
- **NumPy** - Numerical computations
- **Pygame** - Audio feedback

---

## 📋 Prerequisites

- Python 3.10 or higher
- MongoDB account (MongoDB Atlas recommended)
- Webcam (for pose detection feature)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd gymlife-master
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
MONGODB_URI=your_mongodb_connection_string_here
SECRET_KEY=your_secret_key_here
```

### 3. Create Virtual Environment

```powershell
python -m venv gymlife_complete_env
```

### 4. Activate Virtual Environment

**Windows (PowerShell):**
```powershell
.\gymlife_complete_env\Scripts\Activate.ps1
```

> **Note:** If you get an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**Linux/Mac:**
```bash
source gymlife_complete_env/bin/activate
```

### 5. Install Dependencies

```powershell
pip install -r requirements_complete.txt
```

### 6. Run the Application

```powershell
python app.py
```

Or use the startup script:
```powershell
.\start_gymlife.ps1
```

### 7. Access the Application

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 📁 Project Structure

```
gymlife-master/
├── app.py                          # Main Flask application
├── start_gymlife.ps1               # Quick startup script (Windows)
├── requirements_complete.txt       # All dependencies
├── .env                            # Environment variables (create this)
├── .gitignore                      # Git ignore rules
│
├── templates/                      # HTML templates
│   ├── index.html                  # Landing page
│   ├── workout_history.html        # Workout tracking
│   ├── exercises.html              # Exercise library
│   └── ...
│
├── static/                         # Static assets
│   ├── css/                        # Stylesheets
│   ├── js/                         # JavaScript files
│   └── img/                        # Images
│
├── dataset/                        # Exercise data
│   └── exercises.csv               # Exercise database
│
├── pose_detection1/                # AI Pose Detection Module
│   ├── app1.py                     # Pose detection script
│   ├── coach.wav                   # Audio feedback (incorrect)
│   ├── correct.wav                 # Audio feedback (correct)
│   └── snapshots/                  # Saved pose screenshots
│
└── gymlife_complete_env/           # Virtual environment (do not commit)
```

---

## 🎮 Usage Guide

### Creating an Account
1. Navigate to the homepage
2. Click "Sign Up"
3. Enter your email, password, and name
4. Click "Register"

### Adding Workouts
1. Log in to your account
2. Browse the exercise library by body part
3. Select an exercise
4. Enter reps, sets, and weight
5. Click "Add to Workout"

### Using AI CheckFit
1. Log in to your account
2. Click "AI CheckFit" or "CheckFit" button
3. A new window will open with your webcam feed
4. Select a pose using keyboard (1-4):
   - **1** - Front Double Biceps
   - **2** - Back Double Biceps
   - **3** - Side Chest
   - **4** - Lat Flex
5. Perform the pose and hold it
6. Get real-time feedback and scoring
7. Hold a good pose (score ≥80) for 3 seconds to auto-capture
8. Press **Q** to quit

### Calculating BMI
1. Navigate to BMI Calculator
2. Enter your height, weight, age, and sex
3. View your BMI and category

---

## 🔧 Configuration

### MongoDB Setup

1. Create a free MongoDB Atlas account at [mongodb.com](https://www.mongodb.com/cloud/atlas)
2. Create a new cluster
3. Create a database user
4. Get your connection string
5. Add it to your `.env` file:
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/gymlife?retryWrites=true&w=majority
   ```

### Pose Detection Configuration

The pose detection module can be customized in `pose_detection1/app1.py`:
- Adjust scoring thresholds
- Modify pose detection sensitivity
- Change hold time for screenshots
- Customize audio feedback

---

## 🐛 Troubleshooting

### Issue: "Module not found" errors
**Solution:** Make sure you're in the activated virtual environment
```powershell
.\gymlife_complete_env\Scripts\Activate.ps1
```

### Issue: Protobuf errors
**Solution:** Ensure protobuf version 3.20.3 is installed
```powershell
pip uninstall protobuf -y
pip install protobuf==3.20.3
```

### Issue: MongoDB connection error
**Solution:** 
- Verify your `.env` file has the correct `MONGODB_URI`
- Check your MongoDB Atlas IP whitelist settings
- Ensure your database user credentials are correct

### Issue: Camera not opening in pose detection
**Solution:**
- Close any other applications using your webcam
- Grant camera permissions to Python
- Check if your webcam is properly connected

### Issue: Execution policy error (Windows)
**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 🧹 Cleanup & Maintenance

### Remove Old Files
After setup, you can safely delete:
- Old virtual environments (`.venv/`, `pose_detection1/gymlife_env/`)
- Source archives (`Source/` folder)
- Old config files (`python_path.txt`, `readme.txt`)
- Python cache (`__pycache__/`)

### Update Dependencies
```powershell
pip install --upgrade -r requirements_complete.txt
```

---

## 🔒 Security Notes

- Never commit your `.env` file to version control
- Keep your MongoDB credentials secure
- Use strong passwords for user accounts
- The `.gitignore` file is configured to exclude sensitive files

---

## 📝 Development

### Running in Debug Mode
The app runs in debug mode by default (see `app.py` line 532):
```python
app.run(debug=True, host='127.0.0.1', port=8000)
```

For production, set `debug=False`

### Adding New Exercises
1. Add exercise data to `dataset/exercises.csv`
2. Follow the existing CSV format
3. Restart the application

### Modifying Pose Detection
Edit `pose_detection1/app1.py` to:
- Add new poses
- Adjust scoring algorithms
- Customize feedback messages

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

---

## 📄 License

This project is for educational purposes.

---

## 🙏 Acknowledgments

- **MediaPipe** - For pose detection capabilities
- **Flask** - For the web framework
- **MongoDB** - For database services
- Exercise data sourced from public fitness databases

---

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the error messages carefully
3. Ensure all dependencies are correctly installed
4. Verify your `.env` configuration

---

## 🎯 Roadmap

Future enhancements:
- [ ] Mobile app version
- [ ] Social features (share workouts)
- [ ] Nutrition tracking
- [ ] Progress charts and analytics
- [ ] More pose detection exercises
- [ ] Video tutorials
- [ ] Workout plans and programs

---

## ⚡ Quick Commands Reference

| Command | Purpose |
|---------|---------|
| `.\start_gymlife.ps1` | Start the application (Windows) |
| `python app.py` | Start the application (manual) |
| `.\gymlife_complete_env\Scripts\Activate.ps1` | Activate virtual environment |
| `deactivate` | Deactivate virtual environment |
| `pip list` | View installed packages |
| `pip install -r requirements_complete.txt` | Install/update dependencies |

---

**Built with ❤️ for fitness enthusiasts**

*Start your fitness journey with GymLife today! 🏋️‍♂️💪*
