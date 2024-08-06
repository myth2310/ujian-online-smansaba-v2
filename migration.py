from flask import Flask
from flask_mysqldb import MySQL
import hashlib

app = Flask(__name__)

# Konfigurasi MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'e-learning-smaba'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' 

mysql = MySQL(app)

with app.app_context():
    cur = mysql.connection.cursor()
    password = '#adminsmansaba'
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    # Migrasi Data
    cur.execute('''
        INSERT INTO users (nama, email, status, level, password) VALUES
        (%s,%s,'Aktif','Admin',%s)
    ''', ('Adminsmansabajaya','adminsmansaba@gmail.com',hashed_password))

    mysql.connection.commit()
    cur.close()


