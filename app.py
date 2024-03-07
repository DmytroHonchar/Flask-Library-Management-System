from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, current_app, abort
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import MySQLdb
from dotenv import load_dotenv
from flask_mysqldb import MySQL
from urllib.parse import urlparse
from datetime import datetime
import imghdr 
from functools import wraps
# Initialize Flask application

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY')



# Parse the JawsDB URL from the environment variable
jawsdb_url = urlparse(os.getenv('JAWSDB_URL'))
username = jawsdb_url.username
password = jawsdb_url.password
hostname = jawsdb_url.hostname
database = jawsdb_url.path[1:]  # Exclude the leading forward slash
port = jawsdb_url.port or 3306 

# Configure MySQL database connection
app.config['MYSQL_HOST'] = hostname
app.config['MYSQL_USER'] = username
app.config['MYSQL_PASSWORD'] = password
app.config['MYSQL_DB'] = database
app.config['MYSQL_PORT'] = port 
mysql = MySQL(app)


# Initialize Flask-Login's LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Setup for file uploads
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# User model including role for admin checks
class User(UserMixin):
    def __init__(self, id, role=None, is_banned=False):
        self.id = id
        self.role = role
        self.is_banned = is_banned


    # Function to check if user is admin
    def is_admin(self):
        return self.role == 'admin'

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(id):
    cur = mysql.connection.cursor(cursorclass=DictCursor)
    cur.execute("SELECT * FROM users WHERE id = %s", (id,))
    user_data = cur.fetchone()
    cur.close()
    if user_data:
        return User(id=user_data['id'], role=user_data['role'], is_banned=user_data['is_banned'])
    return None

# Admin required function
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash("Unauthorized access.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Registration route
@app.route("/registration", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed_password = generate_password_hash(password)
        cur = mysql.connection.cursor(cursorclass=DictCursor)

        try:
            cur.execute("INSERT INTO users(username, password, email) VALUES (%s, %s, %s)", 
                        (username, hashed_password, email))
            mysql.connection.commit()

            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            user_data = cur.fetchone()
        except MySQLdb.IntegrityError as e:
            if 'username' in str(e):
                flash('This username is already taken. Please choose another.', 'regi')
            elif 'email' in str(e):
                flash('This email is already registered. Please use another email.', 'regi')
            else:
                flash('An error occurred during registration.', 'regi')
            return redirect(url_for('register'))
        finally:
            cur.close()

        if user_data:
            user_id = user_data['id']
            user = User(user_id)
            login_user(user)
            flash('Registration successful', "regi")
            return redirect(url_for('user'))

    return render_template('registration.html')


# Login route
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form['email']  
        password = request.form['password']
        cur = mysql.connection.cursor(cursorclass=DictCursor)

        # Query the database for the user by email instead of username
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_data = cur.fetchone()
        cur.close()

        # Check if the user exists and the password is correct
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['id'])
            login_user(user)
            return redirect(url_for('user'))  
        else:
            flash('Invalid email or password', "info")
            return redirect(url_for('login')) 

    return render_template("login.html")

#Route for Secure File Serving
@app.route('/uploads/<filename>')
@login_required  # Require the user to be logged in
def uploaded_file(filename):
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path):
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    else:
        abort(404)  # File not found


# User dashboard route
@app.route("/user", methods=['GET', 'POST'])
@login_required
def user():
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    user_id = current_user.get_id()

    # Cheking if user is admin for showing hidden link for admin dashboard
    is_admin = current_user.is_admin()

    if request.method == 'POST':
        if 'delete_account' in request.form:  # Check if delete action was requested
            # Check for user confirmation from the form
            if request.form.get('confirm_delete') == 'yes':
                cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
                cur.execute("SELECT COUNT(*) as book_count FROM user_books WHERE user_id = %s", (user_id,))
                book_count_result = cur.fetchone()

                if book_count_result and book_count_result['book_count'] > 0:
                    flash('You must return all books before deleting your account.')
                    cur.close()
                    return redirect(url_for('user'))

                # If no books to return, delete the user account
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                mysql.connection.commit()
                cur.close()

                logout_user()  # Logout the user after deleting the account
                flash('Your account has been successfully deleted.')
                return redirect(url_for('login'))  
            else:
                return redirect(url_for('user'))


        # Update info section
        update_data = {}
        fields_to_update = ["first_name", "second_name", "dob", "address", "username", "password", "email"]

        for field in fields_to_update:
            if field in request.form and request.form[field]:
                if field == "password":
                    new_password = request.form[field]
                    hashed_new_password = generate_password_hash(new_password)
                    update_data[field] = hashed_new_password
                else:
                    update_data[field] = request.form[field]

   
        
        photo = request.files.get("photo")
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)  
            # Validate image
            image_type = imghdr.what(photo_path)
            if not image_type:
                os.remove(photo_path)  # Remove file if not a valid image
                flash('Invalid image format.')
            else:
                update_data['photo_filename'] = os.path.basename(photo_path)

        if update_data:
            update_stmt = ", ".join(f"{key} = %s" for key in update_data.keys())
            cur.execute(f"""
                UPDATE users
                SET {update_stmt}
                WHERE id = %s
            """, list(update_data.values()) + [user_id])
            mysql.connection.commit()

            flash('User information updated successfully.')

        
        cur.close()
        return redirect(url_for('user'))

    # Handling GET request
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
   

    # Fetch available books from the database, including exchange status
    cur.execute("SELECT id, book_name, author , amount, for_exchange FROM books WHERE amount > 0")
    available_books = cur.fetchall()
    cur.close()

    if user_data:
        return render_template('user_dashboard.html', user=user_data, available_books=available_books, admin=is_admin)
    else:
        flash('User information not found.')
        return redirect(url_for('register'))




@app.route("/edit", methods=['GET', 'POST'])
@login_required
def edit():
    return render_template("edit_profile.html")



@app.route("/addUB", methods=['GET', 'POST'])
@login_required
def addUB():
    return render_template("add_user_book.html")




# Route to delete user's photo
@app.route("/delete_photo", methods=["POST"])
@login_required
def delete_photo():
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    user_id = current_user.get_id()

    # Check if the user has a photo
    cur.execute("SELECT photo_filename FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()

    if user_data and user_data['photo_filename']:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], user_data['photo_filename'])
        if os.path.exists(photo_path):
            os.remove(photo_path)

        cur.execute("UPDATE users SET photo_filename = NULL WHERE id = %s", (user_id,))
        mysql.connection.commit()
        flash('Your photo has been deleted.')
    else:
        flash('No photo to delete.')

    cur.close()
    return redirect(url_for('user'))


# Admin-only route for adding a book
@app.route("/addBook", methods=['GET', 'POST'])
@login_required
@admin_required
def addBook():
    if request.method == 'POST':
        cur = mysql.connection.cursor(cursorclass=DictCursor)

        book_name = request.form['book_name']
        author = request.form['author']

        # Check if a book with the same name and author already exists
        cur.execute("SELECT * FROM books WHERE book_name = %s AND author = %s", (book_name, author))
        if cur.fetchone():
            flash('This book already exists.', 'warning')
        else:
            
            amount = request.form['amount']
            cur.execute("INSERT INTO books(book_name, author, amount) VALUES (%s, %s, %s)", 
                        (book_name, author, amount))
            mysql.connection.commit()
            flash('Your book has been added.')

        
        cur.close()

    # Fetch updated list of books to pass to the template
    cur = mysql.connection.cursor(cursorclass=DictCursor)
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    cur.close()

    return redirect(url_for('addUser', books=books))
       



# Admin-only route for adding a user
@app.route("/addUser", methods=['GET', 'POST'])
@admin_required
def addUser():
    cur = mysql.connection.cursor(cursorclass=DictCursor)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed_password = generate_password_hash(password)
        first_name = request.form.get("first_name", "")
        second_name = request.form.get("second_name", "")
        dob = request.form.get("dob", "")
        address = request.form.get("address", "")
        photo = request.files.get("photo", None)

        # Validate Date of Birth if provided
        valid_dob = None
        if dob:
            try:
                valid_dob = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                flash('Incorrect date format for Date of Birth. Please use YYYY-MM-DD format.', 'warning')
                return redirect(url_for('addUser'))

        # Check if the user with the same email already exists
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        if cur.fetchone():
            flash('This email is already registered. Please use another email.', 'warning')
        else:
            photo_filename = None
            if photo and photo.filename:
                filename = secure_filename(photo.filename)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)

                # Validate image
                image_type = imghdr.what(photo_path)
                if not image_type:
                    os.remove(photo_path)  # Remove file if not a valid image
                    flash('Invalid image format.')
                else:
                    photo_filename = os.path.basename(photo_path)

            cur.execute("INSERT INTO users(username, password, email, first_name, second_name, dob, address, photo_filename) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                        (username, hashed_password, email, first_name, second_name, valid_dob, address, photo_filename))
            mysql.connection.commit()
            flash('User added successfully.')

    # Fetch updated data from the database to display
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()

    cur.close()

    return render_template("admin_dashboard.html", users=users, books=books)

# Admin routes too
@app.route("/list_of_users", methods=['GET', 'POST'])
@admin_required
def LU():
    cur = mysql.connection.cursor(cursorclass=DictCursor)    
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()
    
    return render_template("list_of_users.html", users=users)



@app.route("/Update/<int:user_id>", methods=['GET', 'POST'])
@admin_required
def Update(user_id):
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    # Execute a query to fetch the user data by user_id
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()

    # Check if user data is found
    if user_data:
        return render_template("update_info.html", user=user_data, user_id=user_id)
    else:
        flash("User not found.")
        return redirect(url_for('addUser'))
    


@app.route("/deleting/<int:user_id>", methods=['GET', 'POST'])
@login_required
@admin_required
def deleting(user_id):
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    # Execute a query to fetch the user data by user_id
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()

    return render_template("delete.html", user=user)


# ---------------------- dispaly, update, delete users (Admin)-----------------------------------

# Inside your Flask route for viewing user details
@app.route("/user/<int:user_id>")
@admin_required
def view_user(user_id):
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    # Execute a query to fetch the user data by user_id
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()

    # Check if user data is found
    if user_data:
        # Fetch the user's books
        cur.execute("""
            SELECT b.book_name, b.author, ub.quantity
            FROM user_books ub
            JOIN books b ON ub.book_id = b.id
            WHERE ub.user_id = %s
        """, (user_id,))
        user_books = cur.fetchall()


        return render_template("view_user.html", user=user_data, books=user_books)
    else:
        flash("User not found.")
        return redirect(url_for('addUser'))  


# Admin-only route to update a specific user
@app.route("/update_user/<int:user_id>", methods=["POST"])
@admin_required
def update_user(user_id):
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    update_data = {}
    fields_to_update = ["first_name", "second_name", "dob", "address", "username", "password", "email"]

    for field in fields_to_update:
        if field in request.form and request.form[field]:
            if field == "password":
                new_password = request.form[field]
                hashed_new_password = generate_password_hash(new_password)
                update_data[field] = hashed_new_password
            else:
                update_data[field] = request.form[field]

    photo = request.files.get("photo")
    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)

        # Validate image
        image_type = imghdr.what(photo_path)
        if not image_type:
            os.remove(photo_path)  # Remove file if not a valid image
            flash('Invalid image format.')
        else:
            update_data['photo_filename'] = os.path.basename(photo_path)

    if update_data:
        update_stmt = ", ".join(f"{key} = %s" for key in update_data.keys())
        cur.execute(f"""
            UPDATE users
            SET {update_stmt}
            WHERE id = %s
        """, list(update_data.values()) + [user_id])
        mysql.connection.commit()

        flash('User information updated successfully.')
    

    cur.close()
    return redirect(url_for('view_user', user_id=user_id))


# Admin-only route to delete a user's photo
@app.route("/delete_user_photo/<int:user_id>", methods=["POST"])
@admin_required
def delete_user_photo(user_id):
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    # Check if the user has a photo
    cur.execute("SELECT photo_filename FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()

    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    if user_data and user_data['photo_filename']:
        # Delete the user's photo file from the filesystem
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], user_data['photo_filename'])
        if os.path.exists(photo_path):
            os.remove(photo_path)

        # Update the database to remove the photo filename
        cur.execute("UPDATE users SET photo_filename = NULL WHERE id = %s", (user_id,))
        mysql.connection.commit()
        cur.close()

        flash('Your photo has been deleted.')
    else:
        flash('No photo to delete.')

    return render_template ("view_user.html", user=user, user_id=user_id)

# Admin-only route to delete a user
@app.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    # First, retrieve the user's photo filename before deleting the user record
    cur.execute("SELECT photo_filename FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()

    # Check if there are any books associated with the user
    cur.execute("SELECT COUNT(*) as book_count FROM user_books WHERE user_id = %s", (user_id,))
    book_count_result = cur.fetchone()

    if book_count_result and book_count_result['book_count'] > 0:
        flash('User cannot be deleted until all books are returned.')
        cur.close()
        return redirect(url_for('view_user', user_id=user_id))

    # Delete the user's photo file from the filesystem if it exists
    if user_data and user_data['photo_filename']:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], user_data['photo_filename'])
        if os.path.exists(photo_path):
            os.remove(photo_path)

    # Delete the user from the database
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()
    flash('User account has been deleted.')

    return redirect(url_for('addUser'))


# ------------for books----------------------------------

@app.route("/listbooks", methods=['GET', 'POST'])
@login_required
def listbooks():

    user_id = current_user.get_id()
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()

    
     # Fetch available books from the database, including exchange status
    cur.execute("SELECT id, book_name, author , amount, for_exchange FROM books WHERE amount > 0")
    available_books = cur.fetchall()
    cur.close()


    return render_template("list_book_users.html",user=user_data, available_books=available_books )

@app.route("/list_of_books", methods=['GET', 'POST'])
@admin_required
def LB():
    cur = mysql.connection.cursor(cursorclass=DictCursor)    
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    cur.close()
    
    return render_template("list_of_books.html", books=books)


@app.route("/taken_books/<int:user_id>", methods=['GET', 'POST'])
@login_required
@admin_required
def taken_books(user_id):
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    # Execute a query to fetch the user data by user_id
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    # Execute a query to fetch the books associated with the user
    cur.execute("""
        SELECT b.book_name, b.author, ub.quantity
        FROM user_books ub
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = %s
    """, (user_id,))
    
    books = cur.fetchall()
    cur.close()

    return render_template("taken_books.html", user=user, books=books)

@app.route("/edit_book/<int:book_id>", methods=["GET"])
@login_required
@admin_required
def edit_book(book_id):    
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM books WHERE id = %s", [book_id])
    book = cur.fetchone()
    cur.close()

    if book:
        return render_template('update_book.html', book=book)
    else:
        flash("Book not found.", "error")
        return redirect(url_for('addUser'))  


@app.route("/book/<int:book_id>")
@admin_required
def view_book(book_id):
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
 
    # Fetch users who have this book and their quantities
    cur.execute("""
        SELECT u.username, ub.quantity
        FROM user_books ub
        JOIN users u ON ub.user_id = u.id
        WHERE ub.book_id = %s
    """, (book_id,))
    user_books = cur.fetchall()

    # Execute a query to fetch the user data by user_id
    cur.execute("SELECT * FROM books WHERE id = %s", (book_id,))
    book_data = cur.fetchone()
    cur.close()

    # Check if user data is found
    if book_data:
        return render_template("view_book.html", book=book_data, user_books=user_books)
    else:
        flash("Book not found.")
        return redirect(url_for('addUser'))  # Redirect to the admin dashboard


@app.route("/update_book/<int:book_id>", methods=["POST"])
@login_required
@admin_required
def update_book(book_id):    
    cur = mysql.connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    update_data = {}
    fields_to_update = ["book_name", "author", "amount"]

    for field in fields_to_update:
        if field in request.form and request.form[field]:
            update_data[field] = request.form[field]
        
    # For the 'for_exchange' checkbox, check if it's present in the form (meaning it's checked)
    update_data['for_exchange'] = 'for_exchange' in request.form

    if update_data:
        update_stmt = ", ".join(f"{key} = %s" for key in update_data.keys())
        cur.execute(f"""
            UPDATE books
            SET {update_stmt}
            WHERE id = %s
        """, list(update_data.values()) + [book_id])
        mysql.connection.commit()

        flash('Book information updated successfully.')

    cur.close()
    return redirect(url_for('view_book', book_id=book_id))


@app.route("/delete_book/<int:book_id>", methods=['POST'])
@login_required
def delete_book(book_id):
    user_id = current_user.get_id()
    
    # Check if the book is in a user's collection
    cur = mysql.connection.cursor(cursorclass=DictCursor)
    cur.execute("SELECT * FROM user_books WHERE book_id = %s", (book_id,))
    user_books = cur.fetchall()
    cur.close()

    if user_books:
        # If the book is in a user's collection, show a message indicating it cannot be deleted
        flash('This book is currently in a user\'s collection and cannot be deleted.', 'error')
        # make this show which user has a book???????

    else:
        # If the book is not in any user's collection, an admin can delete it
        if current_user.is_admin():
            cur = mysql.connection.cursor()
            cur.execute("DELETE FROM books WHERE id = %s", (book_id,))
            mysql.connection.commit()
            cur.close()
            flash('Book deleted successfully.', 'success')
        else:
            flash('You do not have permission to delete this book.', 'error')

    return redirect(url_for('view_book', book_id=book_id))  



# -------------------------Adding books to profile-----------


@app.route("/add_book_to_profile", methods=['POST'])
@login_required
def add_book_to_profile():
    if current_user.is_banned:
        flash('You are banned from borrowing books.')
        return redirect(url_for('user_books')) 
    
    user_id = current_user.get_id()
    book_id = request.form.get('book_id')
    quantity_field_name = f'quantity_{book_id}'
    quantity = int(request.form.get(quantity_field_name, 1))

    cur = mysql.connection.cursor(cursorclass=DictCursor)

    # First check if the book is available for exchange
    cur.execute("SELECT amount, for_exchange FROM books WHERE id = %s", (book_id,))
    book = cur.fetchone()

    if not book:
        flash('Book not found.')
        return redirect(url_for('user_books'))

    # If the book is not available for exchange, prevent adding to profile
    if not book['for_exchange']:
        flash('This book is not available for exchange.')
        return redirect(url_for('user_books'))

    if book['amount'] >= quantity:
        # Begin a transaction
        cur.execute("BEGIN;")

        try:
            # Add books to user's profile
            cur.execute("""
                INSERT INTO user_books (user_id, book_id, quantity) 
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity = quantity + %s;
                """, (user_id, book_id, quantity, quantity))

            # Reduce the amount in the books table
            cur.execute("""
                UPDATE books SET amount = amount - %s
                WHERE id = %s AND amount >= %s;
                """, (quantity, book_id, quantity))

            # Commit the transaction
            mysql.connection.commit()
            flash('Book added to your profile.')
        except MySQLdb.IntegrityError as e:
            # Rollback the transaction
            mysql.connection.rollback()
            flash('Failed to add book to profile.')
    else:
        flash('Not enough copies of the book available.')

    cur.close()
    return redirect(url_for('user_books'))



@app.route("/user_books")
@login_required
def user_books():
    user_id = current_user.get_id()

    cur = mysql.connection.cursor(cursorclass=DictCursor)
    cur.execute("""
        SELECT b.id, b.book_name, b.author, ub.quantity
        FROM user_books ub
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = %s
    """, (user_id,))
    books = cur.fetchall()
    cur.close()

    return render_template('user_books.html', books=books)


@app.route("/delete_book_from_profile", methods=['POST'])
@login_required
def delete_book_from_profile():
    user_id = current_user.get_id()
    book_id = request.form.get('book_id')
    quantity_to_remove = int(request.form.get('quantity_to_remove', 1))  # Get the quantity to remove


    cur = mysql.connection.cursor(cursorclass=DictCursor)

    # Begin a transaction
    cur.execute("BEGIN;")

    try:
        # Check current quantity of the book in the user's profile
        cur.execute("SELECT quantity FROM user_books WHERE user_id = %s AND book_id = %s", (user_id, book_id))
        result = cur.fetchone()
        if not result or result['quantity'] < quantity_to_remove:
            raise ValueError('Not enough quantity to remove.')

        # Update the user_books table
        cur.execute("UPDATE user_books SET quantity = quantity - %s WHERE user_id = %s AND book_id = %s", (quantity_to_remove, user_id, book_id))
        
        # Increase the stock in the books table
        cur.execute("UPDATE books SET amount = amount + %s WHERE id = %s", (quantity_to_remove, book_id))

        # Remove the entry if the quantity is zero
        cur.execute("DELETE FROM user_books WHERE user_id = %s AND book_id = %s AND quantity = 0", (user_id, book_id))

        # Commit the transaction
        mysql.connection.commit()
        flash('Book removed from your profile.')
    except (MySQLdb.IntegrityError, ValueError) as e:
        # Rollback the transaction in case of error
        mysql.connection.rollback()
        flash('Failed to remove book from profile.' if isinstance(e, MySQLdb.IntegrityError) else str(e))

    cur.close()
    return redirect(url_for('user_books'))

# --------------------- Ban section--------------------------------

@app.route("/ban_user/<int:user_id>", methods=['POST'])
@login_required
@admin_required
def ban_user(user_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE users SET is_banned = TRUE WHERE id = %s", (user_id,))
        mysql.connection.commit()
        flash('User has been banned.')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error banning user: {e}')
    finally:
        cur.close()

    return redirect(url_for('view_user', user_id=user_id))

@app.route("/unban_user/<int:user_id>", methods=['POST'])
@login_required
@admin_required
def unban_user(user_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE users SET is_banned = FALSE WHERE id = %s", (user_id,))
        mysql.connection.commit()
        flash('User has been unbanned.')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error unbanning user: {e}')
    finally:
        cur.close()

    return redirect(url_for('view_user', user_id=user_id))


# ------------------------end of adding books to profile-----------
   
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()