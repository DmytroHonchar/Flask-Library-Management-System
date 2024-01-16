
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
   flask run
   ```
