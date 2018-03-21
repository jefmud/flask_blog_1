
from functools import wraps
import os, json, re
from HTMLParser import HTMLParser
from flask import abort, redirect, request, session, url_for, jsonify
from playhouse.shortcuts import model_to_dict, dict_to_model

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


def query_to_dict(query):
  """return a python dict from a query"""
  qdict = []
  for item in query:
    qdict.append(model_to_dict(item))
  return qdict
    
def query_to_json(query):
  """return a JSON representation of a query"""
  return jsonify(query_to_dict(query))

def query_to_file(query, filename):
  """save query to file, basic name handling collision (PATH MUST EXIST)"""
  data = query_to_dict(query)
  wfile = filename
  i = 0
  while True:
    if not(os.path.isfile(wfile)):
      break
    i += 1
    wfile = "{}.{}".format(filename, i)
    
  with open(wfile,"w") as fp:
    fp.write(json.dumps(data, indent=4, sort_keys=True, default=str))
    

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

def slugify(s):
  """
  Simplifies ugly strings into something URL-friendly.
  >>> print slugify("[Some] _ Article's Title--")
  some-articles-title
  CREDIT - Dolph Mathews (http://blog.dolphm.com/slugify-a-string-in-python/)
  
  My modification, allow slashes as pseudo directory
  """

  # "[Some] _ Article's Title--"
  # "[some] _ article's title--"
  s = s.lower()

  # "[some] _ article's_title--"
  # "[some]___article's_title__"
  for c in [' ', '-', '.']:
    s = s.replace(c, '_')

  # "[some]___article's_title__"
  # "some___articles_title__"
  #s = re.sub('\W', '', s)
  s = re.sub('[^a-zA-Z0-9_/]','',s)
  
  # multiple slashew replaced with single slash
  s = re.sub('[/]+', '/', s)
  
  # remove leading slash
  s = re.sub('^/','', s)
  
  # remove trailing slash
  s = re.sub('/$','', s)

  # "some___articles_title__"
  # "some   articles title  "
  s = s.replace('_', ' ')

  # "some   articles title  "
  # "some articles title "
  s = re.sub('\s+', ' ', s)

  # "some articles title "
  # "some articles title"
  s = s.strip()

  # "some articles title"
  # "some-articles-title"
  s = s.replace(' ', '-')
  
  # a local addition, protects against someone trying to mess with slugless url
  s = re.sub('^page/','page-',s)

  return s