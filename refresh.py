from flask import Flask
from flask_mysqldb import MySQL
import os

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'e-learning-smaba'
mysql = MySQL(app)

with app.app_context():
    cur = mysql.connection.cursor()
        
    # Migrasi Data
    cur = mysql.connection.cursor()

    #Users
    cur.execute("DELETE FROM users")
    cur.execute("ALTER TABLE users DROP id_user")
    cur.execute("ALTER TABLE users ADD  id_user INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")

    #Kelas
    cur.execute("DELETE FROM kelas")
    cur.execute("ALTER TABLE kelas DROP id_kelas")
    cur.execute("ALTER TABLE kelas ADD id_kelas INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")

    #Mapel
    cur.execute("DELETE FROM mapel")
    cur.execute("ALTER TABLE mapel DROP id_mapel")
    cur.execute("ALTER TABLE mapel ADD id_mapel INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")

    #Aktifitas
    cur.execute("DELETE FROM kategori")
    cur.execute("ALTER TABLE kategori DROP id_kategori")
    cur.execute("ALTER TABLE kategori ADD id_kategori INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")

    #Materi
    cur.execute("DELETE FROM soal")
    cur.execute("ALTER TABLE soal DROP id_soal")
    cur.execute("ALTER TABLE soal ADD id_soal INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")

    #Materi
    cur.execute("DELETE FROM jurusan")
    cur.execute("ALTER TABLE jurusan DROP id_jurusan")
    cur.execute("ALTER TABLE jurusan ADD id_jurusan INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")

    cur.execute("DELETE FROM hasil_ujian")
    cur.execute("ALTER TABLE hasil_ujian DROP id_ujian")
    cur.execute("ALTER TABLE hasil_ujian ADD  id_ujian INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")

    cur.execute("DELETE FROM tahun_akademik")
    cur.execute("ALTER TABLE tahun_akademik DROP id_akademik")
    cur.execute("ALTER TABLE tahun_akademik ADD  id_akademik INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST")
    
    mysql.connection.commit()