
# Flask Library Management System

A web-based library management system built with Flask, providing functionalities for user authentication, book management, and administrative controls.

## Features

- User Authentication: Register, log in, and log out.
- Admin Dashboard: Manage users and books.
- User Dashboard: Personal account management and book browsing.
- Book Management: Admins can add, update, delete, view books and users.
- File Uploads: Users can upload files securely.
- MySQL Database Integration: Stores user and book data.

## Getting Started

### Prerequisites

- Python 3
- MySQL

### Installation

1. Clone the repository:
   ```
   https://github.com/DmytroHonchar/Flask-Library-Management-System.git
   ```
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on the `.env.example` and fill in your MySQL database details and secret key.

---

## Database Setup

Before running the application, set up the necessary tables in your MySQL database. Here are the SQL commands to create the required tables:

### 1. Table: `books`

This table stores information about the books.

```sql
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    book_name VARCHAR(255),
    author VARCHAR(255),
    amount INT,
    for_exchange TINYINT(1)
);
```

### 2. Table: `user_books`

This table links users and books, indicating which user has which books and in what quantity.

```sql
CREATE TABLE user_books (
    user_id INT,
    book_id INT,
    quantity INT,
    PRIMARY KEY (user_id, book_id)
);
```

### 3. Table: `users`

This table stores user information.

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(255),
    email VARCHAR(100),
    first_name VARCHAR(255),
    second_name VARCHAR(255),
    dob DATE,
    address VARCHAR(255),
    photo_filename VARCHAR(255),
    role VARCHAR(20),
    is_banned TINYINT(1)
);
```

After creating these tables, your database will be set up to store and manage the data for the Flask Library Management System.

---
Heroku Deployment
The Flask Library Management System can be deployed to Heroku. If you are deploying it to Heroku, make sure to set up the Heroku Postgres add-on and set the DATABASE_URL environment variable.

Additionally, you can parse the JAWSDB_URL environment variable to access the database details provided by Heroku. In your app.py, you can include the following code to parse the JawsDB URL:

# Parse the JawsDB URL from the environment variable
jawsdb_url = urlparse(os.getenv('JAWSDB_URL'))
username = jawsdb_url.username
password = jawsdb_url.password
hostname = jawsdb_url.hostname
database = jawsdb_url.path[1:]  # Exclude the leading forward slash
port = jawsdb_url.port or 3306

This will allow your Flask application to use the JawsDB database details provided by Heroku when running in a Heroku environment.

 Import Tables From Your Local Database
If you already have an existing MySQL database with the required tables, you can export the schema and data from your local database and import it into the database you plan to use for this application. You can use tools like mysqldump or export data using a database management tool like phpMyAdmin.

Ensure that your local database schema matches the tables and fields described above. Importing the tables from your local database will help preserve your existing data when running the Flask Library Management System.

Once you have created or imported the tables into your MySQL database, your database will be set up to store and manage the data for the Flask Library Management System.

Heroku Deployment
When deploying the application to Heroku, make sure to set up the Heroku Postgres add-on and set the DATABASE_URL environment variable as mentioned earlier. Additionally, if you are migrating from a local MySQL database to Heroku's PostgreSQL, you may need to adjust the database schema accordingly.

## User Roles

The `users` table includes a `role` field to define user roles within the application. To assign an admin role to a user, you need to manually update the `role` field in the `users` table through MySQL outside of the application.

```sql
UPDATE users SET role = 'admin' WHERE id = [user_id];
```

Replace `[user_id]` with the actual ID of the user you want to grant admin privileges.

---
### Running the Application

1. Initialize your MySQL database with the necessary tables.
2. Run the Flask application:
   ```
   flask runRunning the Application
Before you can run the Flask Library Management System, ensure that you have initialized your MySQL database with the necessary tables. You can either create these tables using the provided SQL commands or import them from your local database, as described in the "Database Setup" section above.

Once your database is set up, follow these steps to run the application:

Open a terminal or command prompt.

Navigate to the project directory where your Flask application code is located.

Create and activate a virtual environment (if not already done):

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
Install the required packages by running the following command:

pip install -r requirements.txt
Create a .env file based on the .env.example provided in the project directory, and fill in your MySQL database details and secret key.

Once your virtual environment is activated and the packages are installed, you can start the Flask application:

flask run
The application will start, and you will see output indicating the local development server's address (usually http://127.0.0.1:5000/).

Open a web browser and navigate to the provided address to access the Flask Library Management System.
   ```
