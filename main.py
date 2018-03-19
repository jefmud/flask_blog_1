import datetime
from flask import (Flask, flash, g, session, request,
                      redirect, render_template, abort, url_for)

from utils import admin_required, get_object_or_404, login_required, strip_tags

from peewee import *
brand = "FlaskBlog"
about = """
<p>FlaskBlog is an open-source microBlog.
It is our hope it will be useful to community members that have learned or are
discovering the excellence of Python and the Flask web framework.
</p>
<p>
FlaskBlog leverages several Flask plugins and the simple and expressive
PeeWee ORM by Charles Leifer. In addition, we use the Bulma CSS framework under the hood.
We look forward to community involvement to add more to the project.
</p>
"""
app = Flask(__name__)
app.secret_key = '&#*OnNyywiy1$#@'

DB = SqliteDatabase("blog.db")

class BaseModel(Model):
  created_on = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = DB
    
class User(BaseModel):
  username = CharField(unique=True)
  displayname = CharField(default='')
  password = CharField()
  is_admin = BooleanField(default=False)
  
  def __repr__(self):
    return self.username
    
  def authenticate(self, password):
    if password == self.password:
      return True
    return False
    
class Page(BaseModel):
  author = ForeignKeyField(User, related_name='author')
  title = CharField()
  content = TextField()
  is_published = BooleanField(default=True)
  show_title = BooleanField(default=True)
  show_nav = BooleanField(default=True)
  show_sidebar = BooleanField(default=True)
  
  
  def snippet(self):
    snippet_length = len(self.content)
    if snippet_length > 100:
      snippet_length = 100
    return strip_tags(self.content[0:snippet_length])
    
  def __repr__(self):
    return self.title
  
  class Meta:
    order_by = ('-created_on', 'author')
    
class BlogMeta(BaseModel):
  brand = CharField(unique=True)
  about = TextField()
  
def init_database():
  DB.connect()
  print("creating tables")
  DB.create_tables([BlogMeta, User, Page], safe=True)
  try:
    # here is some initial data to get you going.
    BlogMeta.create(brand=brand, about=about)
    User.create(username='admin',password='adminme',is_admin=True)
  except Exception as e:
    pass

  DB.close()
  
@app.before_request
def before_request():
  g.db = DB
  g.db.connect()
  blog = BlogMeta.select()[0]
  g.brand = blog.brand  
  g.user_id = session.get('user_id')
  g.username = session.get('username')
  
@app.after_request
def after_request(response):
  g.db.close()
  return response

@app.route('/login', methods=('GET','POST'))
def login():
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    try:
      user = User.get(User.username==username)
      if user.authenticate(password):
        session['is_admin'] = user.is_admin
        session['is_authenticated'] = True
        session['username'] = username
        session['user_id'] = user.id
        flash("Welcome.  You are logged in now.")
        return redirect(url_for('index'))
    except:
      pass
      
    flash("Username and/or password is incorrect.", category="danger")
    
  return render_template('login.html')

@app.route('/logout')
def logout():
  session.clear()
  flash("You are logged out.", category="warning")
  return redirect(url_for('index'))

@app.route('/')
def index():
  pages = Page.select()
  blog = BlogMeta.select()[0]
  if len(pages) > 5:
    # limit the front page to 5 pages.
    pages = pages[0:5]
  return render_template('index.html', pages=pages, blog=blog)
    
@app.route('/page/<int:page_id>')
def page_view(page_id):
  page = get_object_or_404(Page, page_id)
  if page.is_published:
    return render_template('page_view.html', page=page)
  flash('That page id is not published, check back later.', category="warning")
  return redirect(url_for('index'))

@app.route('/page_create')
@login_required
def page_create():
  return redirect(url_for('page_edit'))

@app.route('/page_edit', methods=('GET','POST'))
@app.route('/page_edit/<int:page_id>', methods=('GET','POST'))
@login_required
def page_edit(page_id=None):
  if page_id==None:
    try:
      page = Page(author=g.user_id)
    except:
      flash("Problems creating a new page", category="danger")
      return redirect(url_for('index'))
  else:
    page = get_object_or_404(Page, page_id)
    
  if request.method == 'POST':
    title = request.form.get('title','')
    author = g.user_id
    content = request.form.get('content','')
    is_published = request.form.get('is_published') == 'on'
    show_sidebar = request.form.get('show_sidebar') == 'on'
    show_title = request.form.get('show_title') == 'on'
    show_nav = request.form.get('show_nav') == 'on'
    if len(title) > 0 and len(content) > 0:
      page.title = title
      page.content = content
      page.is_published = is_published
      page.show_sidebar = show_sidebar
      page.show_nav = show_nav
      page.show_title = show_title
      page.save()
      flash("Page saved.", category="success")
      return redirect(url_for('index'))
    else:
      flash("Please fill in BOTH title and content.", category="danger")
      
    
  return render_template('page_edit.html', page=page)

@app.route('/admin', methods=('GET','POST'), strict_slashes=False)
@admin_required
def admin():
  blog = BlogMeta.select()[0]
  if request.method == 'POST':
    brand = request.form.get('brand','')
    about = request.form.get('about','')
    if len(brand) > 0 and len(about) > 0:
      blog.brand = brand
      blog.about = about
      blog.save()
      return redirect(url_for('admin'))
    else:
      flash("Blog Brand and About CANNOT be BLANK.", category="danger")
      
  return render_template('admin.html', blog=blog)

@app.route('/admin/users', methods=('GET','POST'))
@admin_required
def admin_users():
  users = User.select()
  return render_template('users.html', users=users)

@app.route('/admin/user/add', strict_slashes=False)
@admin_required
def user_add():
  return redirect(url_for('user_edit'))

@app.route('/admin/user', methods=('GET','POST'), strict_slashes=False)
@app.route('/admin/user/<int:user_id>', methods=('GET','POST'))
@admin_required
def user_edit(user_id=None):
  if user_id is None:
    user = User()
  else:
    user = get_object_or_404(User, user_id)
    
  if request.method == 'POST':
    username = request.form.get('username')
    displayname = request.form.get('displayname')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'
    if len(username) > 0 and len(password) > 0:
      user.username = username
      user.displayname = displayname
      user.password = password
      user.is_admin = is_admin
      user.save()
      flash("User information changed", category="success")
      return redirect(url_for('admin_users'))
    else:
      flash('Username and password must be filled in', category="danger")
    
  return render_template('user.html', user=user)

@app.route('/admin/pages', methods=('GET','POST'))
@admin_required
def admin_pages():
  return "todo"

if __name__ == '__main__':
  init_database()
  app.run(host='0.0.0.0', port=5000, debug=False)