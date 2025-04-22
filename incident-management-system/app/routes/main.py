# app/routes/main.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('incidents.dashboard'))
    return render_template('index.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')