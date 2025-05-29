import os
from datetime import datetime
from uuid import uuid4

import qrcode

from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, flash, abort, send_file
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import genqr

# --- Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:kakabok@localhost:5432/qrdb'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File uploads
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Database ---
db = SQLAlchemy(app)

# --- Login Manager ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Models ---
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    @property
    def password(self):
        raise AttributeError('Password cannot be read')

    @password.setter
    def password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def verify_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

class QRRequest(db.Model):
    __tablename__ = 'qr_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    data = db.Column(db.Text, nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    image_url = db.Column(db.String(300))

# Create tables
with app.app_context():
    db.create_all()

# --- User loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/genqr', methods=['POST'])
@login_required
def api_genqr():
    filename = f"{current_user.username}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    data_url = url_for('public_menu', restaurant_name=current_user.username, _external=True)

    # Save request
    qr_req = QRRequest(
        user_id=current_user.id,
        data=data_url,
        filename=filename
    )
    db.session.add(qr_req)
    db.session.commit()

    # Generate QR synchronously
    img = qrcode.make(data_url)
    img.save(filepath)

    return send_file(
        filepath,
        mimetype='image/png',
        as_attachment=True,
        download_name=filename
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        pwd = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email zaten kullanımda.', 'danger')
            return redirect(url_for('register'))
        user = User(username=username, email=email)
        user.password = pwd
        db.session.add(user)
        db.session.commit()
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pwd = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(pwd):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Email veya şifre hatalı.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    restaurant_name = current_user.username
    items = MenuItem.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', restaurant_name=restaurant_name, menu_items=items)

@app.route('/dashboard/menu', methods=['GET', 'POST'])
@login_required
def dashboard_menu():
    if request.method == 'POST':
        name = request.form['name'].strip()
        price = float(request.form['price'])
        desc = request.form['description'].strip()
        image = request.files.get('image')
        image_url = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            unique_name = f"{uuid4().hex}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            image.save(filepath)
            image_url = url_for('static', filename=f'uploads/{unique_name}')
        item = MenuItem(
            user_id=current_user.id,
            name=name,
            price=price,
            description=desc,
            image_url=image_url
        )
        db.session.add(item)
        db.session.commit()
        flash('Menü öğesi eklendi.', 'success')
        return redirect(url_for('dashboard_menu'))
    menu_items = MenuItem.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard_menu.html', menu_items=menu_items)

@app.route('/dashboard/menu/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    if request.method == 'POST':
        item.name = request.form['name'].strip()
        item.price = float(request.form['price'])
        item.description = request.form['description'].strip()
        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            unique_name = f"{uuid4().hex}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            image.save(filepath)
            item.image_url = url_for('static', filename=f'uploads/{unique_name}')
        db.session.commit()
        flash('Menü öğesi güncellendi.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_menu_item.html', item=item)

@app.route('/dashboard/menu/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    flash('Menü öğesi silindi.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/<string:restaurant_name>')
def public_menu(restaurant_name):
    user = User.query.filter_by(username=restaurant_name).first()
    if not user:
        abort(404)
    items = MenuItem.query.filter_by(user_id=user.id).all()
    return render_template('public_menu.html', user=user, items=items)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
