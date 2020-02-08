import os

import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Setup Database
engine = create_engine("postgres://badljuvscpblkv:77846dcebffb03ab3ab9785e08fd5c02ab5f376630655de1c84ad65088ce4931@ec2-54-83-61-142.compute-1.amazonaws.com:5432/d5loculdplltmr")
db = scoped_session(sessionmaker(bind=engine))
s = db()


with open('./books.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        isbnNum = row[0]
        title = row[1]
        author = row[2]
        year = row[3]
        s.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)", {'isbn': isbnNum, 'title': title, 'author': author, 'year': year})
        s.commit()
