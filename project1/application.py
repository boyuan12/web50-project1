import os

from flask import Flask, session, render_template, redirect, request, session, jsonify
from flask_session import Session
import json
import logging
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from helper import login_required


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
s = db()

@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):
    response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "j8a2iSFAQeLrHDuaD69Xw", "isbns": isbn})
    if not response:
        return render_template("alert.html", message="404 ERROR, BOOK NOT FOUND", route="/")
    answer = json.loads(response.text)
    result = s.execute("SELECT title, author, year FROM books WHERE isbn = :isbn LIMIT 1", {'isbn': isbn})
    listT = []
    for row in result:
        row_as_dict = dict(row)
        listT.append(row_as_dict)
    review_count = answer['books'][0]['reviews_count']
    average_rating = answer['books'][0]['average_rating']
    
    try:
        title = listT[0]['title']
    except IndexError:
        return render_template("alert.html", message="404 ERROR, BOOK NOT FOUND!", route="")

    # JSON Object
    returnedJson = {
        'title': listT[0]['title'],
        'author': listT[0]['author'],
        'year': listT[0]['year'],
        'isbn': isbn,
        'review count': review_count,
        'average score': average_rating
    }
    return jsonify(returnedJson)

@app.route("/bookpage", methods=["GET"])
def bookpage():
    global isbn
    isbn = request.args.get("isbn")
    logging.warning(isbn)
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "j8a2iSFAQeLrHDuaD69Xw", "isbns": isbn})
    if not res:
        return render_template("alert.html", message="404 ERROR, BOOK NOT FOUND", route="/")
    result = s.execute("SELECT * FROM books WHERE isbn = :isbn LIMIT 1", {'isbn': isbn})
    answer = []
    for row in result:
        row_as_dict = dict(row)
        answer.append(row_as_dict)
    answerJson = json.loads(res.text)
    average_rating = answerJson['books'][0]["average_rating"]
    total_rating = answerJson['books'][0]['work_ratings_count']
    global title
    title = answer[0]["title"]
    comment = s.execute("SELECT * FROM reviews WHERE title = :title", {'title': title})
    reviews = []
    for row2 in comment:
        reviews.append(dict(row2))
    return render_template("bookpage.html", answers=answer, average_rating=average_rating, total_rating=total_rating, reviews=reviews)

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        if not request.form.get("user-input"):
            return render_template("alert.html", message="Make you filled out all required field(s)", route="")
        userInput = request.form.get("user-input")
        query = "SELECT * FROM books WHERE title LIKE '%"+userInput+"%' OR isbn LIKE '%"+userInput+"%' OR author LIKE '%"+userInput+"%'"
        result = s.execute(query)
        answer = []
        for row in result:
            row_as_dict = dict(row)
            answer.append(row_as_dict)
        if not answer:
            return render_template("alert.html", message="No Result Found", route="")
        return render_template("book.html", answers=answer)
    else:
        return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Check user for fill out ALL required fields.
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirmation") or not request.form.get("email"):
            return render_template("alert.html", message="Make sure to fill out required field", route="register")
        
        # Store some variable for the form info.
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Check whether password is equal to confirmation
        if password != confirmation:
            return render_template("alert.html", message="Wrong Password Confirmation", route="register")

        result = s.execute("SELECT username FROM users")
        check = []

        for row in result:
            row_as_dict = dict(row)
            check.append(row_as_dict)
        
        for i in range(len(check)):
            if check[i].get("username") == username:
                return render_template("alert.html", message="Username already registered", route="/register")
        
        # Get email field from form
        email = request.form.get("email")

        # Generate password and execute into the db, commit to the dtabase
        pwHash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        s.execute("INSERT INTO users (username, password, email) VALUES (:username, :password, :email)", {'username': username, 'password': pwHash, 'email': email})                
        s.commit()
        
        # redirect to homepage
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Get required field's info.
        username = request.form.get("username")
        password = request.form.get("password")

        # get the information from user's username info.
        result = s.execute("SELECT * FROM users WHERE username = :username", {'username': username})

        # read proxy object into a dict.
        for row in result:
            row_as_dict = dict(row)
        
        # Check if username exists and password correctness
        if len(row_as_dict) != 4:
            return render_template("alert.html", message="No such username", route="login")

        if check_password_hash(row_as_dict["password"], request.form.get("password")) != True:
            return render_template("alert.html", message="Wrong Password", route="login")
        
        # Store user_id from db as session user_id
        session["user_id"] = row_as_dict["user_id"]

        # redirect to homepage
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    # forget any user id in session
    session.clear()

    # redirect to homepage
    return redirect("/")


@app.route("/review", methods=["GET", "POST"])
@login_required
def review():
    if request.method == "POST":
        if not request.form.get("range") or not request.form.get("review"):
            return render_template("alert.html", message="Make sure you filled out ALL required fields!", route="")
        range = request.form.get("range")
        review = request.form.get("review")
        s.execute("INSERT INTO reviews (title, review, range) VALUES (:title, :review, :range)", {'title': title, 'review': review, 'range': range})
        s.commit()
        return redirect("/")
    else:
        return redirect("/")