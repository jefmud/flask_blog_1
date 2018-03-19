
from functools import wraps
from HTMLParser import HTMLParser
from flask import abort, redirect, request, session, url_for

def get_object_or_404(cls, object_id):
  try:
    return cls.get(cls.id==object_id)
  except:
    abort(404)
    
def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
      if not(session.get('is_authenticated')):
          return redirect(url_for('login', next=request.url))
      return f(*args, **kwargs)
  return decorated_function
  
def admin_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if not(session.get('is_admin')):
      return redirect(url_for('login', next=request.url))
    return f(*args, **kwargs)
  return decorated_function


class MLStripper(HTMLParser):
  def __init__(self):
    self.reset()
    self.fed = []
  def handle_data(self, d):
    self.fed.append(d)
  def get_data(self):
    return ''.join(self.fed)

def strip_tags(html):
  s = MLStripper()
  s.feed(html)
  return s.get_data()  