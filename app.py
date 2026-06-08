from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from dotenv import load_dotenv
import os
import csv
import urllib.request
import urllib.error
import uuid
import sys
import subprocess
import json
import re
from bson.objectid import ObjectId
from google import genai

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

CORS(app)

# Secret key for session management
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# MongoDB Configuration (single source of truth)
app.config["MONGO_URI"] = os.getenv("MONGODB_URI")
mongo = PyMongo(app)

# Collections
users = mongo.db.users

# Configure Gemini AI
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    client = genai.Client(api_key=gemini_api_key)
else:
    client = None
    print("Warning: GEMINI_API_KEY not found in environment variables")

# ── BMI Range Helper ────────────────────────────────────────────────────────
MEAL_PLAN_CACHE_DAYS = 60  # Re-generate plan if same BMI range held for this long

def get_bmi_range(bmi: float) -> str:
    """Return a stable string key for the user's BMI category."""
    if bmi < 18.5:
        return "underweight"
    elif bmi <= 24.9:
        return "healthy"
    elif bmi <= 29.9:
        return "overweight"
    else:
        return "obese"


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
        return redirect(url_for('index'))
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
            return redirect(url_for('index'))
    return redirect(url_for('index'))


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

    new_range = get_bmi_range(bmi)

    # Fetch old BMI range to detect boundary crossings
    existing_user = users.find_one({"_id": ObjectId(session['user_id'])}, {"bmi_range": 1})
    old_range = existing_user.get("bmi_range") if existing_user else None

    update_fields = {
        "bmi": bmi,
        "bmi_status": status,
        "bmi_range": new_range,
        "height": height,
        "weight": weight,
        "age": age,
        "sex": sex
    }

    update_op = {"$set": update_fields}

    # If BMI crossed into a new range, wipe all cached meal plans for every old range
    if old_range and old_range != new_range:
        unset_fields = {}
        for goal in ["bulking", "cutting"]:
            for rng in ["underweight", "healthy", "overweight", "obese"]:
                unset_fields[f"meal_plan_{goal}_{rng}"] = ""
                unset_fields[f"meal_plan_{goal}_{rng}_generated_at"] = ""
        update_op["$unset"] = unset_fields

    users.update_one({"_id": ObjectId(session['user_id'])}, update_op)

    # Update session
    session['user_bmi'] = bmi
    session['user_bmi_range'] = new_range

    range_changed = (old_range is not None and old_range != new_range)
    return jsonify({'bmi': bmi, 'status': status, 'range_changed': range_changed})

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
    """Web-based pose detection - runs in browser"""
    if 'user_id' not in session:
        flash('Please login to use AI CheckFit.', 'warning')
        return redirect(url_for('index'))
    return render_template('checkfit_web.html')

@app.route('/checkfit-desktop')
def checkfit_desktop():
    """Legacy desktop-based pose detection (for local use only)"""
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


@app.route('/diet')
def diet():
    """Diet page with bulking/cutting options"""
    if 'user_id' not in session:
        flash('Please login to access diet plans.', 'warning')
        return redirect(url_for('index'))
    
    user = users.find_one({"_id": ObjectId(session['user_id'])})
    return render_template('diet.html', user=user)


@app.route('/generate_meal_plan', methods=['POST'])
def generate_meal_plan():
    """Generate personalized meal plan using Gemini AI"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    if not client:
        return jsonify({'error': 'Gemini API not configured'}), 500
    
    data = request.get_json()
    goal = data.get('goal', 'bulking').lower()  # 'bulking' or 'cutting'
    
    if goal not in ['bulking', 'cutting']:
        return jsonify({'error': 'Invalid goal. Must be bulking or cutting'}), 400

    # ── Health Guard: block medically unsafe goal/BMI combinations ───────────
    pre_check_user = users.find_one({"_id": ObjectId(session['user_id'])}, {"bmi": 1, "bmi_range": 1})
    pre_bmi        = pre_check_user.get('bmi', 22) if pre_check_user else 22
    pre_bmi_range  = pre_check_user.get('bmi_range') or get_bmi_range(pre_bmi)

    if pre_bmi_range == 'underweight' and goal == 'cutting':
        return jsonify({'error': 'Cutting is not recommended for underweight individuals. Please choose Bulking to reach a healthy weight first.'}), 400
    if pre_bmi_range == 'obese' and goal == 'bulking':
        return jsonify({'error': 'Bulking is not recommended for obese individuals. Please choose Cutting to reach a healthier weight first.'}), 400
    
    user = users.find_one({"_id": ObjectId(session['user_id'])})

    # ── User stats ────────────────────────────────────────────────────────────
    bmi    = user.get('bmi', 22)
    weight = user.get('weight', 70)
    height = user.get('height', 170)
    age    = user.get('age', 25)
    sex    = user.get('sex', 'male')
    bmi_range = user.get('bmi_range') or get_bmi_range(bmi)

    # ── Cache key is goal + BMI range (e.g. "meal_plan_cutting_overweight") ──
    cache_key      = f"meal_plan_{goal}_{bmi_range}"
    cache_date_key = f"{cache_key}_generated_at"

    cached_plan      = user.get(cache_key)
    cached_generated = user.get(cache_date_key)   # stored as "YYYY-MM-DD" string

    # Determine if the cached plan is still fresh (within MEAL_PLAN_CACHE_DAYS)
    cache_is_fresh = False
    days_in_range  = 0
    if cached_plan and cached_generated:
        try:
            gen_date      = datetime.strptime(cached_generated, "%Y-%m-%d").date()
            days_in_range = (date.today() - gen_date).days
            cache_is_fresh = days_in_range < MEAL_PLAN_CACHE_DAYS
        except ValueError:
            pass

    if cache_is_fresh:
        return jsonify(cached_plan)

    # ── Progressive mode: same range held for 60+ days ───────────────────────
    progressive = (cached_plan is not None and days_in_range >= MEAL_PLAN_CACHE_DAYS)

    # ── Build Gemini prompt ───────────────────────────────────────────────────
    bmi_label_map = {
        "underweight": "Underweight (BMI < 18.5)",
        "healthy":     "Healthy (BMI 18.5–24.9)",
        "overweight":  "Overweight (BMI 25.0–29.9)",
        "obese":       "Obese (BMI ≥ 30.0)",
    }
    bmi_label = bmi_label_map.get(bmi_range, f"BMI {bmi}")

    if progressive:
        intensity_note = (
            f"IMPORTANT: The user has been following a {goal} diet for {days_in_range} days "
            f"but their BMI category ({bmi_label}) has NOT changed yet. "
            f"This is a PROGRESSIVE refresh — increase the dietary intensity to accelerate "
            f"progress toward their {goal} goal. "
            + ("Increase the calorie surplus by 10-15%, boost protein and complex carbs "
               "to drive more muscle gain." if goal == "bulking" else
               "Tighten the calorie deficit by 10-15%, increase protein further to protect "
               "muscle, reduce refined carbs and fats more aggressively.")
        )
    else:
        intensity_note = (
            f"The user is in the {bmi_label} category. "
            f"Tailor the plan specifically for someone starting their {goal} journey at this BMI."
        )

    # ── BMI-range-specific calorie & protein targets ──────────────────────────
    if bmi_range == "underweight":
        # Bulk only (cutting blocked upstream)
        protein_lo, protein_hi = 130, 160
        calorie_note = "Maintenance + 300–500 kcal surplus (hard bulk to build mass)"
        carb_note    = "High complex carbs (rice, oats, banana, roti, sweet potato) for calorie surplus"
        fat_note     = "Healthy fats (peanut butter, ghee, nuts) — 25-35% of calories"
        goal_label   = "Bulking"

    elif bmi_range == "healthy":
        if goal == "bulking":
            protein_lo, protein_hi = 130, 180
            calorie_note = "Maintenance + 250–400 kcal surplus (moderate lean bulk)"
            carb_note    = "Moderate-to-high complex carbs for energy and muscle growth"
            fat_note     = "Healthy fats — 20-30% of calories"
            goal_label   = "Bulking"
        else:
            protein_lo, protein_hi = 120, 160
            calorie_note = "Maintenance − 300–500 kcal deficit (steady fat loss)"
            carb_note    = "Moderate complex carbs (oats, brown rice, roti) — no refined sugar"
            fat_note     = "Lower fats but keep essential fats from nuts and seeds"
            goal_label   = "Cutting"

    elif bmi_range == "overweight":
        if goal == "bulking":
            protein_lo, protein_hi = 120, 150
            calorie_note = "Maintenance + 100–200 kcal only (lean bulk — minimal fat gain)"
            carb_note    = "Lower carbs than standard bulk — complex carbs only (oats, brown rice)"
            fat_note     = "Minimal added fats; rely on natural sources (nuts, curd)"
            goal_label   = "Lean Bulk"
        else:
            protein_lo, protein_hi = 140, 190
            calorie_note = "Maintenance − 400–600 kcal deficit (aggressive fat loss)"
            carb_note    = "Moderate complex carbs only — strictly avoid refined carbs and sugar"
            fat_note     = "Low fats; include only essential fats from nuts and seeds"
            goal_label   = "Cutting"

    else:  # obese — cut only (bulk blocked upstream)
        protein_lo, protein_hi = 150, 220
        calorie_note = "Maintenance − 500–800 kcal deficit (aggressive cut to reduce health risk)"
        carb_note    = "Low carbs — only high-fibre complex carbs (vegetables, oats, 1 small roti)"
        fat_note     = "Very low added fats; only essential omega-3 fats"
        goal_label   = "Cutting"

    protein_g   = (protein_lo + protein_hi) // 2   # midpoint for prompt enforcement
    veg_protein_min = protein_lo                    # veg plan must hit at least lower bound

    goal_guidelines = (
        f"- Daily protein target: {protein_lo}–{protein_hi} g (fixed range for {bmi_label} + {goal_label})\n"
        f"- Calorie adjustment: {calorie_note}\n"
        f"- Carbs: {carb_note}\n"
        f"- Fats: {fat_note}\n"
        "- CRITICAL: Use real Indian household portions — NOT bodybuilder quantities"
    )

    prompt = f"""Create a REALISTIC {goal_label} meal plan for a {sex} with:
- BMI: {bmi} ({bmi_label})
- Weight: {weight} kg | Height: {height} cm | Age: {age} years
- Daily protein target: {protein_lo}–{protein_hi} g (MUST stay within this range)

{intensity_note}

STRICT RULES:
- Total protein across all 5 meals MUST be between {protein_lo} g and {protein_hi} g — no exceptions
- Total calorie adjustment: {calorie_note}
- Use real Indian home-cooked portions (e.g. "2 medium rotis", "1 cup dal", "100g paneer")
- Preferred foods: dal, rajma, chana, paneer, eggs, chicken breast, curd, oats, poha, idli, brown rice, roti, sprouts, banana, peanut butter
- NO protein powder or supplements in the main plan

Provide exactly 5 meals:
1. Pre-workout (light, 150–300 kcal)
2. Post-workout (protein-focused, 300–450 kcal)
3. Breakfast (balanced, 350–500 kcal)
4. Lunch (main meal, 450–650 kcal)
5. Dinner (lighter, 300–450 kcal)

For each meal provide:
- name: Short meal name
- calories: number only
- protein: grams, number only
- carbs: grams, number only
- fats: grams, number only
- description: 1-2 sentences with realistic portions and key ingredients

ALSO provide a PURE VEGETARIAN ALTERNATIVE plan (strictly no meat, no eggs, no fish).
Use: paneer, tofu, curd, dal, rajma, chana, soya chunks, sprouts, nuts, seeds, milk.
The veg plan must achieve similar total calories and at least {veg_protein_min} g total protein.

Respond with valid JSON using EXACTLY this structure:
{{
    "pre_workout":  {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
    "post_workout": {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
    "breakfast":    {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
    "lunch":        {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
    "dinner":       {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
    "veg_plan": {{
        "pre_workout":  {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
        "post_workout": {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
        "breakfast":    {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
        "lunch":        {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}},
        "dinner":       {{"name": "", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "description": ""}}
    }}
}}

Guidelines for {goal_label}:

{goal_guidelines}
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        if hasattr(response, 'text'):
            meal_plan_text = response.text
        elif hasattr(response, 'candidates') and len(response.candidates) > 0:
            meal_plan_text = response.candidates[0].content.parts[0].text
        else:
            return jsonify({'error': 'Unexpected API response format'}), 500

        json_match = re.search(r'\{.*\}', meal_plan_text, re.DOTALL)
        if json_match:
            meal_plan = json.loads(json_match.group())

            # Persist under the range-keyed cache fields
            users.update_one(
                {"_id": ObjectId(session['user_id'])},
                {"$set": {
                    cache_key:      meal_plan,
                    cache_date_key: date.today().strftime("%Y-%m-%d"),
                    "bmi_range":    bmi_range,
                }}
            )
            return jsonify(meal_plan)
        else:
            return jsonify({'error': 'Could not parse meal plan from AI response'}), 500

    except Exception as e:
        print(f"Error generating meal plan: {str(e)}")
        return jsonify({'error': f'Failed to generate meal plan: {str(e)}'}), 500


if __name__ == '__main__':
    # Get port from environment variable (for deployment) or use 8000 for local
    port = int(os.getenv('PORT', 8000))
    # Use debug mode only in development
    debug_mode = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

