from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import os

app = Flask(__name__)

# Secret key for session management
app.secret_key = os.urandom(24)

# Configure MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/school"

# Initialize PyMongo
mongo = PyMongo(app)

# Get references to collections
users_collection = mongo.db.users
classes_collection = mongo.db.classes
students_collection = mongo.db.students
teachers_collection = mongo.db.teachers
schedules_collection = mongo.db.schedules

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, username, password_hash):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        return User(str(user['_id']), user['username'], user['password_hash'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        users_collection.insert_one({"username": username, "password_hash": password_hash})
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user['password_hash'], password):
            login_user(User(str(user['_id']), user['username'], user['password_hash']))
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/students')
@login_required
def students():
    students = list(students_collection.find())
    for student in students:
        student['_id'] = str(student['_id'])
        class_names = []
        for class_id in student.get('class_ids', []):
            cls = classes_collection.find_one({"_id": ObjectId(class_id)})
            if cls:
                class_names.append(cls['name'])
        student['class_names'] = class_names
    return render_template('students.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        new_student = {
            "name": request.form['name'],
            "class_ids": []
        }
        students_collection.insert_one(new_student)
        return redirect(url_for('students'))
    return render_template('add_student.html')

@app.route('/classes')
def classes():
    classes = list(classes_collection.find())
    for cls in classes:
        cls['_id'] = str(cls['_id'])
        cls['name'] = cls['name']
        cls['schedule'] = schedules_collection.find_one({"_id": ObjectId(cls['_id'])})
        cls['teacher_name'] = teachers_collection.find_one({"_id": ObjectId(cls['teacher_id'])})['name']
    return render_template('classes.html', classes=cls)

@app.route('/classes/edit/<class_id>', methods=['GET'])
def edit_class(class_id):
    class_data = classes_collection.find_one({"_id": ObjectId(class_id)})
    teachers = list(teachers_collection.find())
    return render_template('edit_class.html', class_data=class_data, teachers=teachers)

@app.route('/classes/edit/<class_id>', methods=['POST'])
def update_class(class_id):
    name = request.form.get('name')
    teacher_id = request.form.get('teacher')
    schedule = request.form.get('schedule')

    classes_collection.update_one(
        {"_id": ObjectId(class_id)},
        {"$set": {"name": name, "teacher_id": ObjectId(teacher_id), "schedule": schedule}}
    )
    flash('Class updated successfully!', 'success')
    return redirect(url_for('classes'))

@app.route('/add_class', methods=['GET', 'POST'])
def add_class():
    if request.method == 'POST':
        new_class = {
            "name": request.form['name'],
            "teacher_id": request.form['teacher_id']
        }
        classes_collection.insert_one(new_class)
        return redirect(url_for('classes'))
    teachers = list(teachers_collection.find())
    return render_template('add_class.html', teachers=teachers)

@app.route('/enroll', methods=['GET', 'POST'])
def enroll():
    if request.method == 'POST':
        student_id = request.form['student_id']
        class_id = request.form['class_id']
        students_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$addToSet": {"class_ids": class_id}}
        )
        return redirect(url_for('students'))

    students = list(students_collection.find())
    classes = list(classes_collection.find())
    return render_template('enroll.html', students=students, classes=classes)

@app.route('/teachers')
def teachers():
    teachers = list(teachers_collection.find())
    for teacher in teachers:
        teacher['_id'] = str(teacher['_id'])
        classes = list(classes_collection.find({"teacher_id": ObjectId(teacher['_id'])}))
        for cls in classes:
            cls['_id'] = str(cls['_id'])
        teacher['classes'] = classes
    return render_template('teachers.html', teachers=teachers)

@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if request.method == 'POST':
        new_teacher = {
            "name": request.form['name']
        }
        teachers_collection.insert_one(new_teacher)
        return redirect(url_for('teachers'))
    return render_template('add_teacher.html')

@app.route('/schedules')
def schedules():
    schedules = list(schedules_collection.find())
    for schedule in schedules:
        schedule['_id'] = str(schedule['_id'])
        schedule['class_name'] = classes_collection.find_one({"_id": ObjectId(schedule['class_id'])})['name']
        schedule['teacher_name'] = teachers_collection.find_one({"_id": ObjectId(schedule['teacher_id'])})['name']
    return render_template('schedules.html', schedules=schedules)

@app.route('/add_schedule', methods=['GET', 'POST'])
def add_schedule():
    if request.method == 'POST':
        new_schedule = {
            "class_id": request.form['class_id'],
            "teacher_id": request.form['teacher_id'],
            "day_of_week": request.form['day_of_week'],
            "start_time": request.form['start_time'],
            "end_time": request.form['end_time']
        }
        schedules_collection.insert_one(new_schedule)
        return redirect(url_for('schedules'))

    classes = list(classes_collection.find())
    teachers = list(teachers_collection.find())
    return render_template('add_schedule.html', classes=classes, teachers=teachers)

@app.route('/select_teacher')
def select_teacher():
    teachers = list(teachers_collection.find())
    return render_template('select_teacher.html', teachers=teachers)

@app.route('/teacher_schedules')
def teacher_schedules():
    teacher_id = request.args.get('teacher_id')
    if not teacher_id:
        return "Please select a teacher."
    schedules = list(schedules_collection.find({"teacher_id": ObjectId(teacher_id)}))
    for schedule in schedules:
        schedule['_id'] = str(schedule['_id'])
        schedule['class_name'] = classes_collection.find_one({"_id": ObjectId(schedule['class_id'])})['name']
    teacher_name = teachers_collection.find_one({"_id": ObjectId(teacher_id)})['name']
    return render_template('teacher_schedules.html', schedules=schedules, teacher_name=teacher_name)

@app.route('/select_class')
def select_class():
    classes = list(classes_collection.find())
    return render_template('select_class.html', classes=classes)

@app.route('/class_schedules')
def class_schedules():
    class_id = request.args.get('class_id')
    if not class_id:
        return "Please select a class."
    schedules = list(schedules_collection.find({"class_id": ObjectId(class_id)}))
    for schedule in schedules:
        schedule['_id'] = str(schedule['_id'])
        schedule['teacher_name'] = teachers_collection.find_one({"_id": ObjectId(schedule['teacher_id'])})['name']
    class_name = classes_collection.find_one({"_id": ObjectId(class_id)})['name']
    return render_template('class_schedules.html', schedules=schedules, class_name=class_name)

@app.route('/api/classes', methods=['GET'])
def get_classes():
    classes = list(classes_collection.find())
    for cls in classes:
        cls['_id'] = str(cls['_id'])
    return jsonify(classes)

@app.route('/api/classes', methods=['POST'])
def create_class():
    new_class = request.get_json()
    result = classes_collection.insert_one(new_class)
    new_class['_id'] = str(result.inserted_id)
    return jsonify(new_class), 201

@app.route('/api/students', methods=['GET'])
def get_students():
    students = list(students_collection.find())
    for student in students:
        student['_id'] = str(student['_id'])
    return jsonify(students)

@app.route('/api/students', methods=['POST'])
def create_student():
    new_student = request.get_json()
    result = students_collection.insert_one(new_student)
    new_student['_id'] = str(result.inserted_id)
    return jsonify(new_student), 201

@app.route('/api/teachers', methods=['GET'])
def get_teachers():
    teachers = list(teachers_collection.find())
    for teacher in teachers:
        teacher['_id'] = str(teacher['_id'])
    return jsonify(teachers)

@app.route('/api/teachers', methods=['POST'])
def create_teacher():
    new_teacher = request.get_json()
    result = teachers_collection.insert_one(new_teacher)
    new_teacher['_id'] = str(result.inserted_id)
    return jsonify(new_teacher), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
