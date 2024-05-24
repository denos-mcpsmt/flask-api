from flask import Flask, jsonify, request, render_template, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

app = Flask(__name__)

# Configure MongoDB connection
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
db = client['school']
classes_collection = db['classes']
students_collection = db['students']
teachers_collection = db['teachers']
schedules_collection = db['schedules']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/students')
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
        if cls.get('teacher_id'):
            teacher = teachers_collection.find_one({"_id": ObjectId(cls['teacher_id'])})
            cls['teacher_name'] = teacher['name'] if teacher else "Unknown"
        else:
            cls['teacher_name'] = "Not Assigned"
    return render_template('classes.html', classes=classes)

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
    for teacher in teachers:
        teacher['_id'] = str(teacher['_id'])
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
    for student in students:
        student['_id'] = str(student['_id'])

    classes = list(classes_collection.find())
    for cls in classes:
        cls['_id'] = str(cls['_id'])

    return render_template('enroll.html', students=students, classes=classes)

@app.route('/teachers')
def teachers():
    teachers = list(teachers_collection.find())
    for teacher in teachers:
        teacher['_id'] = str(teacher['_id'])
        classes = list(classes_collection.find({"teacher_id": teacher['_id']}))
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
    for cls in classes:
        cls['_id'] = str(cls['_id'])
    for teacher in teachers:
        teacher['_id'] = str(teacher['_id'])
    return render_template('add_schedule.html', classes=classes, teachers=teachers)

@app.route('/select_teacher')
def select_teacher():
    teachers = list(teachers_collection.find())
    for teacher in teachers:
        teacher['_id'] = str(teacher['_id'])
    return render_template('select_teacher.html', teachers=teachers)

@app.route('/teacher_schedules')
def teacher_schedules():
    teacher_id = request.args.get('teacher_id')
    if not teacher_id:
        return "Please select a teacher."
    schedules = list(schedules_collection.find({"teacher_id": teacher_id}))
    for schedule in schedules:
        schedule['_id'] = str(schedule['_id'])
        schedule['class_name'] = classes_collection.find_one({"_id": ObjectId(schedule['class_id'])})['name']
    teacher_name = teachers_collection.find_one({"_id": ObjectId(teacher_id)})['name']
    return render_template('teacher_schedules.html', schedules=schedules, teacher_name=teacher_name)

@app.route('/select_class')
def select_class():
    classes = list(classes_collection.find())
    for cls in classes:
        cls['_id'] = str(cls['_id'])
    return render_template('select_class.html', classes=classes)

@app.route('/class_schedules')
def class_schedules():
    class_id = request.args.get('class_id')
    if not class_id:
        return "Please select a class."
    schedules = list(schedules_collection.find({"class_id": class_id}))
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
