"""
Routes for core functionality.
"""
from flask import render_template

from monopyly.core import core


@core.route('/')
def index():
    return render_template('index.html')

@core.route('/about')
def about():
    return render_template('about.html')
