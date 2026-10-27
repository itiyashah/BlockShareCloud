import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from ipfs import IPFSClient

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'fallback-jwt-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///enterprise.db')
app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
app.config['JWT_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
app.config['JWT_COOKIE_CSRF_PROTECT'] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)
ipfs_client = IPFSClient()

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class FileRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    ipfs_hash = db.Column(db.String(200), nullable=False)
    owner = db.Column(db.String(80), nullable=False)

with app.app_context():
    db.create_all()
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('downloads', exist_ok=True)

# --- ROUTES ---
@app.route('/')
def index():
    files = FileRecord.query.all()
    return render_template('index.html', files=files)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            access_token = create_access_token(identity=username)
            response = redirect(url_for('dashboard'))
            set_access_cookies(response, access_token)
            flash('Logged in successfully!', 'success')
            return response
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
@jwt_required()
def dashboard():
    current_user = get_jwt_identity()
    user_files = FileRecord.query.filter_by(owner=current_user).all()
    return render_template('dashboard.html', user=current_user, files=user_files)

@app.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    current_user = get_jwt_identity()
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('dashboard'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('dashboard'))
        
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        file.save(file_path)
        
        try:
            # Uploads file securely to Pinata Cloud IPFS
            ipfs_hash = ipfs_client.upload_file(file_path)
            
            # Save file record persistently to SQLite/PostgreSQL Database
            new_record = FileRecord(filename=filename, ipfs_hash=ipfs_hash, owner=current_user)
            db.session.add(new_record)
            db.session.commit()
            
            flash(f'File uploaded successfully to Enterprise Cloud! IPFS Hash: {ipfs_hash}', 'success')
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'danger')
            
        if os.path.exists(file_path):
            os.remove(file_path)
            
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    response = redirect(url_for('index'))
    unset_jwt_cookies(response)
    flash('Logged out successfully.', 'info')
    return response

if __name__ == '__main__':
    app.run(debug=True)
