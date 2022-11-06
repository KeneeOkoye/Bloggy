from flask import Flask, flash, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_user, logout_user, login_required, LoginManager, UserMixin
from datetime import datetime
import os

base_dir = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///' + \
    os.path.join(base_dir, 'bloggy.db')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = '026b0eb800ec2934fb5cf2e7'

login_manager = LoginManager(app)

db = SQLAlchemy(app)
db.init_app(app)

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    blogs_by = db.relationship(
        "Blog", back_populates="created_by", lazy="dynamic")

    def __repr__(self):
        return f"User: <{self.username}>"

class Blog(db.Model):
    __tablename__ = "blogs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String, nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey(
        "users.id"), unique=False, nullable=False)
    author = db.Column(db.String, nullable=False)
    created_by = db.relationship("User", back_populates="blogs_by")

    def __repr__(self):
        return f"Blog: <{self.title}>"

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(80), nullable=False)
    message = db.Column(db.String, nullable=False)
    priority = db.Column(db.String(20))

    def __repr__(self):
        return f"Message: <{self.title}>"

@app.before_first_request
def create_tables():
    db.create_all()

@login_manager.user_loader
def user_loader(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    blogs = Blog.query.all()
    context = {
        "blogs": blogs
    }
    return render_template('index.html', **context)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        sender = request.form.get('name')
        email = request.form.get('email')
        title = request.form.get('title')
        message = request.form.get('message')
        priority = request.form.get('priority')

        new_message = Message(sender=sender, email=email,
                              title=title, message=message, priority=priority)
        db.session.add(new_message)
        db.session.commit()

        flash("Message received!")
        return redirect(url_for('index'))

    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        username_exists = User.query.filter_by(username=username).first()
        if username_exists:
            flash("Username already exists.")
            return redirect(url_for('register'))

        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash("Email is already registered.")
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)

        new_user = User(username=username, first_name=first_name,
                        last_name=last_name, email=email, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration was Successful.")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        flash("You are now logged in.")
        return redirect(url_for('index'))
    if (user and check_password_hash(user.password_hash, password)) == False:
        flash("Enter valid credentials.")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    flash("You are now logged out.")
    return redirect(url_for('index'))

@app.route('/blog/<int:id>/')
def blog(id):
    blog = Blog.query.get_or_404(id)

    context = {
        "blog": blog
    }

    return render_template('blog.html', **context)

@app.route('/contribute', methods=['GET', 'POST'])
@login_required
def contribute():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        user_id = current_user.id
        author = current_user.username

        title_exists = Blog.query.filter_by(title=title).first()
        if title_exists:
            flash("This Blog Post already exists. Pick a new title.")
            return redirect(url_for('contribute'))

        new_blog = Blog(title=title, content=content,
                              user_id=user_id, author=author)
        db.session.add(new_blog)
        db.session.commit()

        flash("Thanks for your amazing thoughts.")
        return redirect(url_for('index'))

    return render_template('contribute.html')

@app.route('/edit/<int:id>/', methods=['GET', 'POST'])
@login_required
def edit(id):
    blog_to_edit = Blog.query.get_or_404(id)

    if current_user.username == blog_to_edit.author:
        if request.method == 'POST':
            blog_to_edit.title = request.form.get('title')
            blog_to_edit.content = request.form.get('content')

            db.session.commit()

            flash("New changes have been saved.")
            return redirect(url_for('blog', id=blog_to_edit.id))

        context = {
            'blog': blog_to_edit
        }

        return render_template('edit.html', **context)

    flash("Another user's Blog Post cannot be edited.")
    return redirect(url_for('index'))

@app.route('/delete/<int:id>/', methods=['GET'])
@login_required
def delete(id):
    blog_to_delete = Blog.query.get_or_404(id)

    if current_user.username == blog_to_delete.author:
        db.session.delete(blog_to_delete)
        db.session.commit()
        flash("Blog Post deleted!")
        return redirect(url_for('index'))

    flash("Another user's Blog Post cannot be deleted.")
    return redirect(url_for('index'))
