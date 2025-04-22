# app/models/user.py
from app.database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'manager'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    incidents_created = db.relationship('Incident', foreign_keys='Incident.creator_id', backref='creator', lazy='dynamic')
    incidents_assigned = db.relationship('Incident', foreign_keys='Incident.assignee_id', backref='assignee', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'