import time, datetime, sys, getpass, io, os
from flask import (Flask, flash, g, session, request, send_from_directory,
                      redirect, render_template, abort, url_for)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from utils import (login_required, admin_required, get_object_or_404, 
                   strip_tags, query_to_file, slugify, generate_csrf_token)

from peewee import *

############### BLOG META DEFAULTS #############
# once running, you can override these defaults
default_brand = "FlaskBlog"
default_about = """
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
###############
app = Flask(__name__)
app.secret_key = '&#*OnNyywiy1$#@'
app.jinja_env.globals['csrf_token'] = generate_csrf_token 
HOST = '0.0.0.0'
PORT = 5000
DEBUG = False

### FILE UPLOADS PARAMETERS
# UPLOAD FOLDER will have to change based on your own needs/deployment scenario
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, './uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

# DBPATH will have to change based on your needs/deployment scenario
DBPATH = os.path.join(BASE_DIR, 'blog.db')
DB = SqliteDatabase(DBPATH)

############# OUR MODELS ############
class BaseModel(Model):
  """BaseModel is common parent, so all models have the SAME database and created_on field"""
  created_on = DateTimeField(default=datetime.datetime.now)
  class Meta:
    database = DB
    
class BlogMeta(BaseModel):
  """meta information about our blog"""
  brand = CharField(unique=True)
  about = TextField()
    
class User(BaseModel):
  """Basic user model"""
  username = CharField(unique=True)
  displayname = CharField(default='')
  email = CharField(default='')
  password = CharField()
  is_admin = BooleanField(default=False)
  is_active = BooleanField(default=True)
  ## User model frills, often unused
  avatar_url = CharField(default="")
  bio = TextField(default="")
  
  def display_name(self):
    if self.displayname:
      return self.displayname
    return self.username
  
  def authenticate(self, password):
    """provides basic authentication against a password"""
    # enforce hashing (werkzeug) to make it sort of secure
    if check_password_hash(self.password, password):
      return True
    
    return False  
  
  def password_hash(self):
    # manual hash operation.
    self.password = generate_password_hash(self.password)  
  
  @classmethod
  def create_user(cls, username, password, email="", displayname="", is_admin=False, is_active=True, avatar_url="", bio=""):
    hashed_pw = generate_password_hash(password) # enforce password hashing (werkzueg)
    try:
      with DB.transaction():    
        cls.create(username=username, password=hashed_pw, email=email, displayname=displayname,
                   is_admin=is_admin, is_active=is_active, avatar_url=avatar_url, bio=bio)
    except IntegrityError:
      raise ValueError('username already exists')      
    
  def __repr__(self):
    return self.username
    
    
class Page(BaseModel):
  """The Page model (each blog entry is a page)"""
  # required fields: author, title, content
  author = ForeignKeyField(User, related_name='author')
  title = CharField()
  content = TextField()
  # fields with defaults: slug, is_published, show_title, show_nav, show_sidebar
  slug = TextField(default="") # in case user wants a better url (as a feature page, etc.)
  # boolean type fields for page visibility and presentation options
  is_published = BooleanField(default=True)
  show_title = BooleanField(default=True)
  show_nav = BooleanField(default=True)
  # not implemented yet
  show_sidebar = BooleanField(default=True)
  
  def url(self):
    """return page slug or url for generic page view"""
    if self.slug:
      return self.slug
    return url_for('page_view',page_id=self.id)
  
  def snippet(self, length=100):
    """returns a snippet of a particular length (default=100) without tags"""
    snippet_length = len(self.content)
    if snippet_length > length:
      snippet_length = length
    plain_text = strip_tags(self.content)
    return strip_tags(plain_text[0:snippet_length])
  
  def date(self, fmt='%B %d, %Y'):
    """returns a nicely formatted date, can override format if you want"""
    return self.created_on.strftime(fmt)
    
  def __repr__(self):
    """returns a string representation"""
    return self.title
  
  class Meta:
    order_by = ('-created_on', 'author')
    

class File(BaseModel):
  """meta information about files that are uploaded by users"""
  title = CharField()
  filepath = CharField(unique=True)
  owner = ForeignKeyField(User, related_name="owner")
  
  def __repr__(self):
    return self.title
  
  def url(self):
    return url_for('file_uploads', path=self.filepath)
  
  class Meta:
    order_by = ('-created_on','title')
  
################### END MODELS #########################
  
def initialize(args=[]):
  """initialize the database and CLI (command line args)
  --drop <table> (valid table aliases are "users", "pages", or "files")
  --createadmin (creation of an administrator account for initial login)
  --init (safe creation of tables in case we're starting out.)
  Some deployment methodologies will make initialize unreachable except from CLI
  """
  
  print("INITIALIZATION BEGINS")
  
  DB.connect()
  
  if '--init' in args or '--initialize' in args:
    # SAFE CREATION OF TABLES, And exit
    DB.create_tables([BlogMeta, User, Page, File], safe=True)
    print("tables created (safe), exiting.")
    sys.exit(0)
  
  if '--drop' in args:
    if 'users' in args:
      resp = raw_input("DELETE all USERS? (type DELETE) to confirm: ")
      if resp == "DELETE":
        DB.drop_tables([User])
        print("USERS dropped, exiting.")
      else:
        print("Cancelled")
      sys.exit(0)    
    
    if 'pages' in args:
      resp = raw_input("DELETE all PAGES? (type DELETE) to confirm: ")
      if resp == "DELETE":
        DB.drop_tables([Page])
        print("PAGES dropped, exiting.")
      else:
        print("Cancelled")
      sys.exit(0)
    
    if 'files' in args:
      resp = raw_input("DELETE all UPLOADED FILES? (type DELETE) to confirm: ")
      if resp == "DELETE":
        DB.drop_tables([File])
        print("FILES dropped, exiting.")
      else:
        print("Cancelled")
    sys.exit(0) # exit CLI
  
  if '--createadmin' in args:
    username = raw_input("Enter admin username: ")
    password = getpass.getpass()
    User.create_user(username=username, password=password, is_admin=True)
    print("admin user created, exiting.")
    sys.exit(0) # EXIT CLI
    
  

  DB.close()
  print("INIT COMPLETE")



def get_blog_meta():
  """grabs the blog meta data for branding, etc."""
  blog = BlogMeta.select()
  if len(blog):
    blog = blog[0]
  else:
    blog = BlogMeta.create(brand=default_brand, about=default_about)
  return blog

@app.before_request
def before_request():
  """tasks before request is executed"""
  g.db = DB
  g.db.connect()
  blog = get_blog_meta()
  g.brand = blog.brand  
  g.user_id = session.get('user_id')
  g.username = session.get('username')
  
  # recommended csrf protection
  if request.method == "POST":
    if session.get('no_csrf'):
      # handle temporary csrf override
      session.pop('no_csrf')
    else:
      token = session.pop('_csrf_token', None)
      if not token or token != request.form.get('_csrf_token'):
          abort(400)  
  
@app.after_request
def after_request(response):
  """tasks after request is executed"""
  g.db.close()
  return response

@app.route('/login', methods=('GET','POST'))
def login():
  """handle basic login"""
  error = None
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    try:
      user = User.get(User.username==username)
      if user.authenticate(password) and user.is_active:
        session['is_admin'] = user.is_admin
        session['is_authenticated'] = True
        session['username'] = username
        session['user_id'] = user.id
        flash("Welcome.  You are logged in now.")
        return redirect(url_for('index'))
      if not(user.is_active):
        error = "Username is deactivated, please contact an admin to be reinstated"
    except:
      pass
    
    if error:
      flash(error, category="danger")
    else:
      flash("Username and/or password is incorrect.", category="danger")
    
  return render_template('login.html')

def allowed_file(filename):
  """return True if filename is allowed for upload, False if not allowed"""
  return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<path:path>')
def file_uploads(path):
  """serve up a file in our uploads"""
  print("access path={}".format(path))
  return send_from_directory(app.config['UPLOAD_FOLDER'], path)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def file_upload():
  """File upload handling"""
  if request.method == 'POST':
    # check if the post request has the file part
    if 'file' not in request.files:
      flash('No file part')
      return redirect(request.url)
    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
      flash('No selected file')
      return redirect(request.url)
    if file and allowed_file(file.filename):
      filename = secure_filename(file.filename)
      subfolder = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m/")
      pathname = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
      
      # handle name collision if needed
      # filename will add integers at beginning of filename in dotted fashion
      # hello.jpg => 1.hello.jpg => 2.hello.jpg => ...
      # until it finds an unused name
      i=1
      while os.path.isfile(pathname):
        parts = filename.split('.')
        parts.insert(0,str(i))
        filename = '.'.join(parts)
        i += 1
        if i > 100:
          # probably under attack, so just fail
          raise ValueError("too many filename collisions, administrator should check this out")
        
        pathname = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
        
      try:
        # ensure directory where we are storing exists, and create it
        directory = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        if not os.path.exists(directory):
          os.makedirs(directory)
        # finally, save the file AND create its resource object in database
        file.save(pathname)
        local_filepath = os.path.join(subfolder, filename)
        file_object = File.create(title=filename, filepath=local_filepath, owner=session['user_id'])
        return redirect(url_for('file_edit', file_id=file_object.id))
      except Exception as e:
        print(e)
        flash("Something went wrong here-- please let administrator know", category="danger")
        raise ValueError("Something went wrong with file upload.")
      
  # TODO, replace with fancier upload drag+drop
  session['no_csrf'] = True
  return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''


@app.route('/logout')
def logout():
  """basic logout operations"""
  session.clear()
  flash("You are logged out.", category="warning")
  return redirect(url_for('index'))

@app.route('/index')
def index():
  """serve up the home page, and 5 cards of the most recent articles.
  http://localhost (root of the site is redirected here)
  You can customize this in the code if you need to.
  """
  s = request.args.get('s')
  if s:
    return redirect( url_for('search', s=s) )  
  if len(User.select()) == 0:
    return redirect(url_for('admin_first_use'))  
  pages = Page.select()
  blog = BlogMeta.select()[0]
  if len(pages) > 5:
    # limit the front page to 5 pages.
    pages = pages[0:5]
  return render_template('index.html', pages=pages, blog=blog)

def fix_page_ownership():
  pages = Page.select()
  for page in pages:
    print page.author
    
@app.route('/user_delete/<int:user_id>')
@app.route('/user_delete/<int:user_id>/<hard_delete>')
@admin_required
def user_delete(user_id, hard_delete=False):
  """delete a user. A soft delete only sets the is_active to false
  a hard_delete signal deletes the user and reassigns all the pages and files to the current ADMIN
  """
  edit_url = url_for('user_edit', user_id=user_id)
  user = get_object_or_404(User, user_id)
  if user.id != session.get('user_id'):
    if hard_delete:
      # reassign all pages to admin who is deleting
      pages = Page.select().where(Page.author==user.id)
      for page in pages:
        page.author = session.get('user_id')
        page.save()
      user.delete_instance()
      flash("User fully deleted", category="primary")
    else:
      user.is_active = False
      user.save()
      flash("User deactivated, but still present in database", category="primary")
  else:
    flash("CANNOT DELETE/DEACTIVATE an actively logged in account.", category="danger")
  
  # redirect to caller or index page if we deleted on an edit view
  if request.referrer == None or edit_url in request.referrer:
    return redirect(url_for('index'))
  else:
    return redirect(request.referrer)  
  
  
@app.route('/page/<int:page_id>')
def page_view(page_id):
  """page view by page.id"""
  s = request.args.get('s')
  if s:
    return redirect( url_for('search', s=s) )  
  page = get_object_or_404(Page, page_id)
  if page.is_published:
    return render_template('page_view.html', page=page)
  flash('That page id is not published, check back later.', category="warning")
  return redirect(url_for('index'))

@app.route('/page_create')
@login_required
def page_create():
  """view creates a page, simply redirects to page_edit view with NO id"""
  return redirect(url_for('page_edit'))

@app.route('/page_delete/<int:page_id>')
@login_required
def page_delete(page_id):
  """view deletes a page and redirects back to referrer or index"""
  edit_url = url_for('page_edit', page_id=page_id)
  page = get_object_or_404(Page, page_id)
  if page.author.id == session['user_id']  or session['is_admin']:
    page.delete_instance()
    flash('Page deleted', category="success")
  else:
    flash('You are not authorized to remove this page', category='danger')
  # handle redirect to referer
  if request.referrer == None or edit_url in request.referrer:
    return redirect(url_for('index'))
  else:
    return redirect(request.referrer)
  

@app.route('/page_edit', methods=('GET','POST'))
@app.route('/page_edit/<int:page_id>', methods=('GET','POST'))
@login_required
def page_edit(page_id=None):
  """view edits/creates a page (if called with no page.id)"""
  if page_id==None:
    try:
      page = Page(author=g.user_id, content="")
    except:
      flash("Problems creating a new page", category="danger")
      return redirect(url_for('index'))
  else:
    page = get_object_or_404(Page, page_id)
    
  if request.method == 'POST':
    title = request.form.get('title','')
    slug = request.form.get('slug','')
    author = g.user_id
    content = request.form.get('content','')
    is_published = request.form.get('is_published') == 'on'
    show_sidebar = request.form.get('show_sidebar') == 'on'
    show_title = request.form.get('show_title') == 'on'
    show_nav = request.form.get('show_nav') == 'on'
    if len(title) > 0 and len(content) > 0:
      page.title = title
      page.slug = slugify(slug)
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
  """view for basic admin tasks"""
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
      flash("Blog Brand field and About field need a value.", category="danger")
      
  return render_template('admin.html', blog=blog)


@app.route('/admin/export/<model>/<filename>')
@admin_required
def export_model(model, filename):
  """view exports a named model to a JSON file on the physical file system
  this view should be used with caution since it doesn't put a limitation on filename/location
  theoretically could overwrite a critical file.  I haven't tried this yet.
  TODO - the file should be served up (downloaded to user client)
  """
  if model == 'user':
    query = User.select()
  else:
    query = Page.select()
  query_to_file(query, filename)
  return "Done"
    
  
@app.route('/admin/users', methods=('GET','POST'))
@admin_required
def admin_users():
  """view for administering users"""
  users = User.select()
  return render_template('users.html', users=users)

@app.route('/admin/user/add', strict_slashes=False)
@admin_required
def user_add():
  """ADMIN-ONLY view to add a user"""
  return redirect(url_for('user_edit'))

@app.route('/admin/user', methods=('GET','POST'), strict_slashes=False)
@app.route('/admin/user/<int:user_id>', methods=('GET','POST'))
@admin_required
def user_edit(user_id=None):
  """ADMIN-ONLY view to edit a user or create a user if no user_id supplied"""
  if user_id is None:
    user = User()
  else:
    user = get_object_or_404(User, user_id)
    
  if request.method == 'POST':
    username = request.form.get('username')
    displayname = request.form.get('displayname')
    email = request.form.get('email')
    password = request.form.get('password')
    is_active = request.form.get('is_active') == 'on'
    is_admin = request.form.get('is_admin') == 'on'
    if len(username) > 0 and len(password) > 0:
      user.username = username
      user.displayname = displayname
      if user.password != password:
        user.password = password
        user.password_hash()
      user.is_active = is_active
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
  """ADMIN-ONLY view to look at all pages.
  TODO: change view to support non-admin users
  """
  pages = Page.select()
  return render_template('admin_pages.html', pages=pages)


@app.route('/file_delete/<int:file_id>')
@login_required
def file_delete(file_id):
  """view to delete an existing file object and physical file (owned by user)"""
  f = get_object_or_404(File, file_id)
  pathname = os.path.join(app.config['UPLOAD_FOLDER'], f.filepath)
  if f.owner.id == session['user_id'] or session['is_admin']:
    f.delete_instance()
    try:
      os.remove(pathname)
      flash('File Successfully Deleted', category="success")
    except:
      flash("Error: problems removing physical file. Check log for details.", category="warning")
  else:
    flash('You are not authorized to remove this file.', category="danger")
    
  # handle redirect to referer
  if request.referrer == None:
    return redirect(url_for('index'))
  else:
    return redirect(request.referrer)  

@app.route('/file_edit/<int:file_id>', methods=['GET','POST'])
@admin_required
def file_edit(file_id):
  """view to allow edit/delete of a File resource"""
  file = get_object_or_404(File, file_id)
  if request.method == 'POST':
    if file.owner.id == session['user_id'] or session['is_admin']:
      title = request.form.get('title')
      if title:
        file.title = title
        file.save()
        flash("File information changed", category="success")
        return redirect(url_for('admin_files'))
      else:
        flash('Title must not be blank.', category="danger")
    else:
      flash("You are not authorized to edit/delete this object.", category="danger")
      
  return render_template('file_edit.html',file=file)
    
  
@app.route('/admin/files')
@admin_required
def admin_files():
  """ADMIN-ONLY view for all File resources
  TODO: change this view to support non-admin users
  """
  files = File.select()
  return render_template('admin_files.html', files=files)

@app.route('/admin/firstuse', methods=('GET', 'POST'))
def admin_first_use():
  """view for first-use.  This view is triggered by EMPTY User table"""
  # this route should only work on empty user table
  if len(User.select()) > 0:
    abort(403) # forbidden
  
  errors = False
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    confirm = request.form.get('confirm')
    if len(username) == 0:
      errors = True
      flash("Username must be NON-NULL", category="danger")
    if len(password) == 0:
      errors = True
      flash("Password must be NON-NULL", category="danger")
    if password != confirm:
      errors = True
      flash("Password and Confirm must match", category="danger")
    if not(errors):
      User.create_user(username=username, password=password, is_admin=True)
      return redirect(url_for('login'))
    
  return render_template('first_use.html')


@app.route("/search")
def search():
  """a general search view
  TODO: improve search results to be Page cards like index
  """
  search_term = request.args.get('s')
  pages = Page.select().where(Page.content.contains(search_term) | Page.title.contains(search_term) | Page.slug.contains(search_term))
  return render_template('search.html', pages=pages, search_term=search_term)

# this is the general route "catchment"
@app.route("/")
@app.route("/<path:path>")
def site(path=None):
  """view for pages referenced via their slug
  If you want to modify what happens when an empty path comes in
  See below, it is redirected to "index" view.  This can be changed via code below.
  """
  s = request.args.get('s')
  if s:
    return redirect( url_for('search', s=s) )

  if path is None:
    """modify here to change behavior of the home-index"""
    return redirect(url_for("index"))
  
  page = Page.select().where(Page.slug==path)
  if len(page) > 0:
    page = page[0]
  else:
    abort(404)
    
  return render_template('page_view.html', page=page)   

if __name__ == '__main__':
  """launched from the command line, you pass args to initialize, then run the app"""
  initialize(sys.argv)
  app.run(host=HOST, port=PORT, debug=DEBUG)