from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import csv
import urllib.request
import urllib.error
import uuid
import sys
import subprocess
from bson.objectid import ObjectId

app = Flask(__name__)

CORS(app)

# Secret key for session management
app.secret_key = "supersecretkey"

# MongoDB Configuration (single source of truth)
app.config["MONGO_URI"] = "mongodb://localhost:27017/gymlife"
mongo = PyMongo(app)

# Collections
users = mongo.db.users

@app.route('/add_workout', methods=['POST'])
def add_workout():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    exercises = data.get('exercises', [])
    # Fallback: if a single exercise payload is sent
    if not exercises and all(k in data for k in ["exercise_name", "reps", "sets", "weight"]):
        calories = data.get('calories')
        if calories is None:
            # Simple estimation formula
            calories = float(data['reps']) * float(data['sets']) * float(data['weight']) * 0.1
        exercises = [{
            "exercise_name": data['exercise_name'],
            "reps": int(data['reps']),
            "sets": int(data['sets']),
            "weight": float(data['weight']),
            "calories": float(calories)
        }]

    workout = {
        "id": str(uuid.uuid4()),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "name": data.get('name') or (exercises[0]['exercise_name'] if exercises else "Workout"),
        "exercises": exercises,
        "total_calories": sum(float(ex.get('calories', 0)) for ex in exercises)
    }

    users.update_one(
        {"_id": ObjectId(session['user_id'])},
        {"$push": {"workouts": workout}}
    )

    return jsonify({'message': 'Workout added successfully!'})


@app.route('/get_workouts', methods=['GET'])
def get_workouts():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    user = users.find_one({"_id": ObjectId(session['user_id'])})
    if not user:
        return jsonify([])

    workouts = user.get('workouts', [])
    updated = False
    for w in workouts:
        if 'id' not in w:
            w['id'] = str(uuid.uuid4())
            updated = True
    
    if updated:
        users.update_one(
            {"_id": ObjectId(session['user_id'])},
            {"$set": {"workouts": workouts}}
        )
            
    return jsonify(workouts)


@app.route('/update_exercise', methods=['POST'])
def update_exercise():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    workout_date = data['date']
    exercise_name = data['exercise_name']

    users.update_one(
        {
            "_id": ObjectId(session['user_id']),
            "workouts.date": workout_date,
            "workouts.exercises.exercise_name": exercise_name
        },
        {
            "$set": {
                "workouts.$[w].exercises.$[e].reps": int(data['reps']),
                "workouts.$[w].exercises.$[e].weight": float(data['weight']),
                "workouts.$[w].exercises.$[e].calories": float(data['calories'])
            }
        },
        array_filters=[
            {"w.date": workout_date},
            {"e.exercise_name": exercise_name}
        ]
    )

    return jsonify({'message': 'Exercise updated successfully!'})


@app.route('/delete_exercise', methods=['POST'])
def delete_exercise():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    workout_id = data.get('workout_id')
    exercise_name = data.get('exercise_name')

    if not workout_id or not exercise_name:
        return jsonify({'error': 'Missing parameters'}), 400

    # 1. Remove the exercise from the specific workout
    users.update_one(
        {
            "_id": ObjectId(session['user_id']),
            "workouts.id": workout_id
        },
        {
            "$pull": {
                "workouts.$.exercises": {"exercise_name": exercise_name}
            }
        }
    )

    # 2. Clean up: Remove workouts that have no exercises left
    # This might remove other empty workouts too, which is generally good behavior
    users.update_one(
        {"_id": ObjectId(session['user_id'])},
        {"$pull": {"workouts": {"exercises": {"$eq": []}}}}
    )

    return jsonify({'message': 'Exercise deleted successfully!'})

@app.route('/workout_history')
def workout_history():
    if 'user_id' not in session:
        flash('Please login to view your workout history.', 'warning')
        return redirect(url_for('index1'))
    user = users.find_one({"_id": ObjectId(session['user_id'])})
    return render_template('workout_history.html', user=user or {})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user'] = email
            session['user_id'] = str(user['_id'])
            session['user_name'] = user.get('name')
            session['user_bmi'] = user.get('bmi')
            flash('Login successful!', 'success')
            return redirect(url_for('workout_history'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('index1'))
    return redirect(url_for('index1'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form.get('name', '')

        if users.find_one({'email': email}):
            flash('Email already registered.', 'warning')
            return redirect(url_for('index'))

        hashed_password = generate_password_hash(password)
        users.insert_one({'email': email, 'password': hashed_password, 'name': name, 'workouts': []})
        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('index'))

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_bmi', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))


@app.route('/calculate_bmi', methods=['POST'])
def calculate_bmi():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    try:
        height = float(data.get('height'))
        weight = float(data.get('weight'))
        age = int(data.get('age'))
        sex = data.get('sex')
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid input'}), 400

    height_m = height / 100
    bmi = round(weight / (height_m * height_m), 1)
    
    status = ""
    if bmi < 18.5:
        status = "Underweight"
    elif 18.5 <= bmi <= 24.9:
        status = "Healthy"
    elif 25.0 <= bmi <= 29.9:
        status = "Overweight"
    else:
        status = "Obese"

    # Update user in DB
    users.update_one(
        {"_id": ObjectId(session['user_id'])},
        {"$set": {"bmi": bmi, "bmi_status": status, "height": height, "weight": weight, "age": age, "sex": sex}}
    )
    
    # Update session
    session['user_bmi'] = bmi
    
    return jsonify({'bmi': bmi, 'status': status})

SECTIONS = ["Legs", "Back", "Chest", "Biceps", "Triceps", "Shoulders", "Core"]

_DATASET_ROWS = []

def _load_exercises_dataset() -> None:
    global _DATASET_ROWS
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dataset_path = os.path.join(base_dir, 'dataset', 'exercises.csv')
        with open(dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            _DATASET_ROWS = [row for row in reader]
    except Exception:
        _DATASET_ROWS = []


def _filter_exercises_by_category(category: str) -> list[str]:
    cat = category.lower()
    items: dict[str, dict] = {}

    for row in _DATASET_ROWS:
        body_part = (row.get('bodyPart') or '').lower()
        target = (row.get('target') or '').lower()
        name = row.get('name') or ''
        ex_id = row.get('id') or ''
        gif = row.get('gifUrl') or ''

        if not name or not ex_id:
            continue

        match = (
            (cat == 'legs' and (body_part in ['upper legs', 'lower legs', 'hips'])) or
            (cat == 'back' and body_part == 'back') or
            (cat == 'chest' and body_part == 'chest') or
            (cat == 'biceps' and target == 'biceps') or
            (cat == 'triceps' and target == 'triceps') or
            (cat == 'shoulders' and body_part == 'shoulders') or
            (cat == 'core' and (target in ['abs', 'obliques'] or body_part == 'waist'))
        )

        if match and ex_id not in items:
            items[ex_id] = {"id": ex_id, "name": name, "gifUrl": gif}

    return sorted(items.values(), key=lambda x: x['name'])


def _get_exercise_by_id(exercise_id: str) -> dict | None:
    for row in _DATASET_ROWS:
        if (row.get('id') or '') == exercise_id:
            # Normalize dynamic fields
            secs = []
            for i in range(0, 6):
                val = row.get(f'secondaryMuscles/{i}')
                if val:
                    secs.append(val)
            instr = []
            for i in range(0, 11):
                val = row.get(f'instructions/{i}')
                if val:
                    instr.append(val)
            return {
                "id": row.get('id'),
                "name": row.get('name'),
                "bodyPart": row.get('bodyPart'),
                "equipment": row.get('equipment'),
                "gifUrl": row.get('gifUrl'),
                "target": row.get('target'),
                "secondaryMuscles": secs,
                "instructions": instr,
            }
    return None


@app.route('/exercise/img/<exercise_id>')
def exercise_image(exercise_id: str):
    exercise = _get_exercise_by_id(exercise_id)
    if not exercise or not exercise.get('gifUrl'):
        return ('', 404)
    url = exercise['gifUrl']
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': ''
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            content_type = resp.headers.get('Content-Type') or 'image/gif'
            return app.response_class(data, mimetype=content_type)
    except urllib.error.URLError:
        return ('', 502)


# Load dataset at startup
_load_exercises_dataset()


@app.route('/exercises')
def exercises():
    # Show only sections; user clicks into a section to view exercises
    return render_template('exercises.html', sections=SECTIONS)


@app.route('/exercise/id/<exercise_id>', methods=['GET'])
def exercise_detail(exercise_id):
    if 'user_id' not in session:
        flash('Please login to add workouts.', 'warning')
        return redirect(url_for('index'))
    exercise = _get_exercise_by_id(exercise_id)
    if not exercise:
        flash('Exercise not found.', 'danger')
        return redirect(url_for('exercises'))
    return render_template('exercise_detail.html', exercise=exercise)


@app.route('/exercise/id/<exercise_id>', methods=['POST'])
def add_single_exercise_workout(exercise_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    exercise = _get_exercise_by_id(exercise_id)
    if not exercise:
        flash('Exercise not found.', 'danger')
        return redirect(url_for('exercises'))
    reps = int(request.form.get('reps', 0))
    sets = int(request.form.get('sets', 0))
    weight = float(request.form.get('weight', 0))
    calories = request.form.get('calories')
    if calories is None or calories == '':
        calories = reps * sets * weight * 0.1
    else:
        calories = float(calories)

    payload = {
        "name": exercise['name'],
        "exercises": [{
            "exercise_name": exercise['name'],
            "reps": reps,
            "sets": sets,
            "weight": weight,
            "calories": float(calories),
            "image_url": exercise.get('gifUrl')
        }]
    }

    users.update_one(
        {"_id": ObjectId(session['user_id'])},
        {"$push": {"workouts": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "name": payload['name'],
            "exercises": payload['exercises'],
            "total_calories": sum(ex['calories'] for ex in payload['exercises'])
        }}}
    )

    flash('Workout added to your history!', 'success')
    return redirect(url_for('exercises'))


@app.route('/exercises/<category>')
def exercises_by_category(category):
    # Case-insensitive match for category
    matched_key = None
    for key in SECTIONS:
        if key.lower() == category.lower():
            matched_key = key
            break
    if not matched_key:
        flash('Category not found.', 'danger')
        return redirect(url_for('exercises'))
    ex_list = _filter_exercises_by_category(matched_key)
    return render_template('exercises_category.html', category=matched_key, exercises=ex_list)




@app.route('/about-us')
def about_us():
    return render_template('about-us.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/class-timetable')
def class_timetable():
    return render_template('class-timetable.html')

@app.route('/bmi-calculator')
def bmi_calculator():
    return render_template('bmi-calculator.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/blog-details')
def blog_details():
    return render_template('blog-details.html')

@app.route('/class-details')
def class_details():
    return render_template('class-details.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/404')
def error_404():
    return render_template('404.html')

@app.route("/chest")
def chest():
    return render_template("chest.html")

@app.route("/back")
def back():
    return render_template("back.html")

@app.route("/biceps")
def biceps():
    return render_template("biceps.html")

@app.route('/main')
def main():
    return render_template('main.html')

@app.route('/legs')
def legs():
    return render_template('legs.html')

@app.route('/shoulders')
def shoulders():
    return render_template('shoulders.html')

@app.route('/triceps')
def triceps():
    return render_template('triceps.html')

@app.route('/checkfit')
def checkfit():
    try:
        # Path to the pose detection script
        script_path = os.path.join(app.root_path, 'pose_detection1', 'app1.py')
        working_dir = os.path.join(app.root_path, 'pose_detection1')
        
        # Use the specialized environment python if it exists, otherwise system python
        env_python = r"C:\Users\Admin\anaconda3\envs\gymlife_checkfit\python.exe"
        python_exe = env_python if os.path.exists(env_python) else sys.executable

        # Launch the script as a separate process
        subprocess.Popen([python_exe, script_path], cwd=working_dir)
        
        flash('Checkfit started! Look for the "AI Bodybuilding Coach" window.', 'success')
    except Exception as e:
        flash(f'Error starting Checkfit: {str(e)}', 'danger')
    
    # Redirect to the 'next' param (current page), or referrer, or fallback to workout_history
    next_page = request.args.get('next')
    return redirect(next_page or request.referrer or url_for('workout_history'))


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8000)

