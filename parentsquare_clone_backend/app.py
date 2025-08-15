from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity, get_jwt
import pymysql.cursors
import os
import string
import random
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables from the .env file
load_dotenv()

# -----------------
# App Configuration
# -----------------
app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('SECRET_KEY')

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# -----------------
# Helper Function for Database Connection
# -----------------
def get_db_connection():
    """Connects to the MySQL database."""
    return pymysql.connect(host=app.config['MYSQL_HOST'],
                           user=app.config['MYSQL_USER'],
                           password=app.config['MYSQL_PASSWORD'],
                           database=app.config['MYSQL_DB'],
                           cursorclass=pymysql.cursors.DictCursor)

# -----------------
# Helper Function to Generate a Random Code
# -----------------
def generate_access_code(length=10):
    """Generates a unique random alphanumeric code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# -----------------
# Role-Based Access Control Helper
# -----------------
def get_user_role(user_id):
    """Returns the role of a user."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT role FROM Users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            user = cursor.fetchone()
            return user['role'] if user else None
    finally:
        connection.close()

# -----------------
# API Endpoints
# -----------------

@app.route('/')
def home():
    return "Welcome to the ParentSquare Clone Backend!"

@app.route('/api/register/school_admin', methods=['POST'])
def register_school_admin():
    data = request.get_json()
    school_name = data.get('school_name')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')

    if not all([school_name, first_name, last_name, email, password]):
        return jsonify({'message': 'Missing required fields'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM Users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'message': 'Email already registered'}), 409

            sql_school = "INSERT INTO Schools (name) VALUES (%s)"
            cursor.execute(sql_school, (school_name,))
            school_id = cursor.lastrowid

            sql_user = "INSERT INTO Users (first_name, last_name, email, password_hash, role, school_id) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql_user, (first_name, last_name, email, hashed_password, 'school_admin', school_id))
            admin_id = cursor.lastrowid

            sql_update_school = "UPDATE Schools SET admin_user_id = %s WHERE id = %s"
            cursor.execute(sql_update_school, (admin_id, school_id))

        connection.commit()
        return jsonify({'message': 'School and admin registered successfully'}), 201

    except Exception as e:
        connection.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, first_name, last_name, email, password_hash, role FROM Users WHERE email = %s"
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if user and bcrypt.check_password_hash(user['password_hash'], password):
                access_token = create_access_token(identity=str(user['id']), additional_claims={"role": user['role']})
                return jsonify({
                    'message': 'Login successful',
                    'access_token': access_token,
                    'user': {
                        'id': user['id'],
                        'first_name': user['first_name'],
                        'last_name': user['last_name'],
                        'email': user['email'],
                        'role': user['role']
                    }
                }), 200
            else:
                return jsonify({'message': 'Invalid email or password'}), 401
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT first_name, role FROM Users WHERE id = %s"
            cursor.execute(sql, (current_user_id,))
            user = cursor.fetchone()
            if user:
                return jsonify({
                    'message': f"Hello {user['first_name']}! You are a {user['role']}. This is protected data."
                }), 200
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/school_admin/add_teacher', methods=['POST'])
@jwt_required()
def add_teacher():
    current_user_id = get_jwt_identity()
    user_role = get_user_role(current_user_id)

    if user_role != 'school_admin':
        return jsonify({'message': 'Access denied: Must be a school admin'}), 403

    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')

    if not all([first_name, last_name, email, password]):
        return jsonify({'message': 'Missing required fields'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM Users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'message': 'Email already registered'}), 409

            cursor.execute("SELECT school_id FROM Users WHERE id = %s", (current_user_id,))
            admin_school_id = cursor.fetchone()['school_id']

            sql = "INSERT INTO Users (first_name, last_name, email, password_hash, role, school_id) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (first_name, last_name, email, hashed_password, 'teacher', admin_school_id))

        connection.commit()
        return jsonify({'message': 'Teacher added successfully'}), 201

    except Exception as e:
        connection.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/school_admin/enroll_student', methods=['POST'])
@jwt_required()
def enroll_student():
    current_user_id = get_jwt_identity()
    user_role = get_user_role(current_user_id)

    if user_role != 'school_admin':
        return jsonify({'message': 'Access denied: Must be a school admin'}), 403

    data = request.get_json()
    student_first_name = data.get('student_first_name')
    student_last_name = data.get('student_last_name')
    parent_email = data.get('parent_email')
    class_id = data.get('class_id')

    if not all([student_first_name, student_last_name, parent_email, class_id]):
        return jsonify({'message': 'Missing required fields'}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT school_id FROM Users WHERE id = %s", (current_user_id,))
            admin_school_id = cursor.fetchone()['school_id']

            sql_student = "INSERT INTO Students (first_name, last_name, school_id) VALUES (%s, %s, %s)"
            cursor.execute(sql_student, (student_first_name, student_last_name, admin_school_id))
            student_id = cursor.lastrowid

            sql_enroll = "INSERT INTO StudentEnrollments (student_id, class_id) VALUES (%s, %s)"
            cursor.execute(sql_enroll, (student_id, class_id))

            access_code = generate_access_code()
            sql_code = "INSERT INTO AccessCodes (code, student_id, parent_email) VALUES (%s, %s, %s)"
            cursor.execute(sql_code, (access_code, student_id, parent_email))

        connection.commit()
        return jsonify({
            'message': 'Student enrolled and access code generated successfully',
            'student_id': student_id,
            'access_code': access_code
        }), 201

    except Exception as e:
        connection.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/teacher/add_class', methods=['POST'])
@jwt_required()
def add_class():
    current_user_id = get_jwt_identity()
    user_role = get_user_role(current_user_id)

    if user_role != 'teacher':
        return jsonify({'message': 'Access denied: Must be a teacher'}), 403

    data = request.get_json()
    class_name = data.get('class_name')

    if not class_name:
        return jsonify({'message': 'Missing required field: class_name'}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT school_id FROM Users WHERE id = %s", (current_user_id,))
            teacher_school_id = cursor.fetchone()['school_id']

            sql = "INSERT INTO Classes (class_name, teacher_id, school_id) VALUES (%s, %s, %s)"
            cursor.execute(sql, (class_name, current_user_id, teacher_school_id))

        connection.commit()
        return jsonify({'message': 'Class added successfully'}), 201

    except Exception as e:
        connection.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/parent/register', methods=['POST'])
def register_parent():
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')
    access_code = data.get('access_code')

    if not all([first_name, last_name, email, password, access_code]):
        return jsonify({'message': 'Missing required fields'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql_code_check = "SELECT student_id, parent_email FROM AccessCodes WHERE code = %s AND is_used = FALSE"
            cursor.execute(sql_code_check, (access_code,))
            code_info = cursor.fetchone()

            if not code_info:
                return jsonify({'message': 'Invalid or used access code'}), 400

            cursor.execute("SELECT id FROM Users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'message': 'Email already registered'}), 409

            student_id = code_info['student_id']

            cursor.execute("SELECT school_id FROM Students WHERE id = %s", (student_id,))
            school_id = cursor.fetchone()['school_id']

            sql_user = "INSERT INTO Users (first_name, last_name, email, password_hash, role, school_id) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql_user, (first_name, last_name, email, hashed_password, 'parent', school_id))
            parent_user_id = cursor.lastrowid

            sql_link = "INSERT INTO ParentStudentLinks (parent_user_id, student_id) VALUES (%s, %s)"
            cursor.execute(sql_link, (parent_user_id, student_id))

            sql_invalidate = "UPDATE AccessCodes SET is_used = TRUE WHERE code = %s"
            cursor.execute(sql_invalidate, (access_code,))

        connection.commit()
        return jsonify({'message': 'Parent registered and linked successfully'}), 201

    except Exception as e:
        connection.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/student/dashboard', methods=['GET'])
@jwt_required()
def student_dashboard():
    current_user_id = get_jwt_identity()
    user_role = get_user_role(current_user_id)

    if user_role != 'student':
        return jsonify({'message': 'Access denied: Must be a student'}), 403

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, first_name, last_name FROM Students WHERE user_id = %s", (current_user_id,))
            student_info = cursor.fetchone()
            if not student_info:
                return jsonify({'message': 'Student record not found'}), 404

            student_id = student_info['id']

            sql = """
                SELECT c.class_name, u.first_name AS teacher_first_name, u.last_name AS teacher_last_name
                FROM StudentEnrollments se
                JOIN Classes c ON se.class_id = c.id
                JOIN Users u ON c.teacher_id = u.id
                WHERE se.student_id = %s
            """
            cursor.execute(sql, (student_id,))
            classes = cursor.fetchall()

        return jsonify({
            'student_name': f"{student_info['first_name']} {student_info['last_name']}",
            'enrolled_classes': classes
        }), 200

    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/teacher/create_post', methods=['POST'])
@jwt_required()
def create_post():
    current_user_id = get_jwt_identity()
    user_role = get_user_role(current_user_id)

    if user_role != 'teacher':
        return jsonify({'message': 'Access denied: Must be a teacher'}), 403

    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    class_id = data.get('class_id')

    if not all([title, content, class_id]):
        return jsonify({'message': 'Missing required fields'}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT school_id FROM Classes WHERE id = %s", (class_id,))
            class_info = cursor.fetchone()
            if not class_info:
                return jsonify({'message': 'Class not found'}), 404

            cursor.execute("SELECT school_id FROM Users WHERE id = %s", (current_user_id,))
            teacher_info = cursor.fetchone()
            if teacher_info['school_id'] != class_info['school_id']:
                return jsonify({'message': 'Teacher is not authorized for this class'}), 403

            sql = "INSERT INTO Posts (title, content, user_id, class_id) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (title, content, current_user_id, class_id))

        connection.commit()
        return jsonify({'message': 'Post created successfully'}), 201

    except Exception as e:
        connection.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/student/posts', methods=['GET'])
@jwt_required()
def student_posts():
    current_user_id = get_jwt_identity()
    user_role = get_user_role(current_user_id)

    if user_role != 'student':
        return jsonify({'message': 'Access denied: Must be a student'}), 403

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT p.title, p.content, p.created_at, u.first_name AS author_first_name, u.last_name AS author_last_name, c.class_name
                FROM Posts p
                JOIN Users u ON p.user_id = u.id
                JOIN Classes c ON p.class_id = c.id
                JOIN StudentEnrollments se ON c.id = se.class_id
                JOIN Students s ON se.student_id = s.id
                WHERE s.user_id = %s
                ORDER BY p.created_at DESC
            """
            cursor.execute(sql, (current_user_id,))
            posts = cursor.fetchall()

        return jsonify(posts), 200

    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        connection.close()

@app.route('/api/admin/posts', methods=['GET'])
@jwt_required()
def admin_posts():
    user_claims = get_jwt()
    if user_claims.get('role') != 'school_admin':
        return jsonify({"message": "Unauthorized access."}), 403
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
            SELECT p.id, p.title, p.content, p.created_at, c.class_name, u.first_name AS author_first_name, u.last_name AS author_last_name
            FROM Posts p
            JOIN Classes c ON p.class_id = c.id
            JOIN Users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
            """
            cursor.execute(query)
            posts = cursor.fetchall()
            return jsonify(posts), 200
    except Exception as e:
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/delete_post/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    user_claims = get_jwt()
    if user_claims.get('role') != 'school_admin':
        return jsonify({"message": "Unauthorized access. Only school admins can delete posts."}), 403
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM Posts WHERE id = %s", (post_id,))
            rows_affected = cursor.rowcount
            connection.commit()
            
            if rows_affected > 0:
                return jsonify({"message": f"Post {post_id} deleted successfully."}), 200
            else:
                return jsonify({"message": f"Post {post_id} not found."}), 404
    except Exception as e:
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/parent/posts', methods=['GET'])
@jwt_required()
def parent_posts():
    user_claims = get_jwt()
    current_user_id = get_jwt_identity()
    if user_claims.get('role') != 'parent':
        return jsonify({"message": "Unauthorized access."}), 403
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT student_id FROM ParentStudentLinks WHERE parent_user_id = %s", (current_user_id,))
            child = cursor.fetchone()
            
            if not child:
                return jsonify({"message": "No child found for this parent."}), 404
            
            child_id = child['student_id']

            query = """
            SELECT p.title, p.content, p.created_at, c.class_name, u.first_name AS author_first_name, u.last_name AS author_last_name
            FROM Posts p
            JOIN Classes c ON p.class_id = c.id
            JOIN Users u ON p.user_id = u.id
            JOIN StudentEnrollments se ON c.id = se.class_id
            WHERE se.student_id = %s
            ORDER BY p.created_at DESC
            """
            cursor.execute(query, (child_id,))
            posts = cursor.fetchall()
            return jsonify(posts), 200
    except Exception as e:
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if connection:
            connection.close()
            
if __name__ == '__main__':
    app.run(debug=True)