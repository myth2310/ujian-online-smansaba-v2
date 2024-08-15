from application import app
from flask import Flask, render_template,request, redirect,url_for,flash,session,jsonify, send_file
from flask_mysql_connector import MySQL
import hashlib
import os
from datetime import datetime
from flask_mail import Mail, Message
import pandas as pd
import traceback
from cryptography.fernet import Fernet
import base64
from io import BytesIO

app.secret_key = 'your_secret_key'

# Configure MySQL
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_DATABASE'] = 'e-learning-smaba'
mysql = MySQL(app)

app.config['MAIL_SERVER'] = "smtp.gmail.com"
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = "achmadmiftahudin2310@gmail.com"
app.config['MAIL_PASSWORD'] = "xnpsrjiltljosbaz"
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'achmadmiftahudin2310@gmail.com'  
mail = Mail(app)

key = base64.urlsafe_b64encode(os.urandom(32))
cipher_suite = Fernet(key)

def encrypt_id(id):
    id_str = str(id).encode('utf-8')
    encrypted_id = cipher_suite.encrypt(id_str)
    return encrypted_id.decode('utf-8')

def decrypt_id(encrypted_id):
    encrypted_id = encrypted_id.encode('utf-8')
    decrypted_id = cipher_suite.decrypt(encrypted_id)
    return int(decrypted_id.decode('utf-8'))

@app.context_processor
def utility_processor():
    return dict(encrypt_id=encrypt_id,decrypt_id=decrypt_id)

@app.route("/send_mail")
def send_mail():
    mail_message = Message(
        'Hi! Don’t forget to follow me for more articles!',
        recipients=['19090137.miftahudin@student.poltektegal.ac.id']
    )
    mail_message.body = "This is a test"
    mail.send(mail_message)
    return "Mail has been sent"

@app.route('/')
@app.route('/login')
def login():
    if 'islogin' in session:
         return redirect(url_for('home'))
    else:
        return render_template('login.html')
    
@app.route('/daftar-nilai')
def daftarNilai():
    if 'islogin' in session:
        conn = mysql.connection
        cursor = conn.cursor(dictionary=True)
    
        cursor.execute('''
            SELECT * FROM mapel 
            INNER JOIN users 
            ON mapel.id_mapel = users.id_mapel 
            WHERE users.level = 'Guru';
        ''')
        mapel = cursor.fetchall()
        
        cursor.execute('SELECT * FROM kelas')
        kelas = cursor.fetchall()
        
        return render_template('admin/daftar-nilai.html', mapel=mapel, kelas=kelas)
    else:
        return redirect(url_for('login'))

@app.route('/fetch_results', methods=['POST'])
def fetch_results():
    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    id_user = request.form.get('id_user')
    kelas = request.form.get('kelas')

    query = '''
        SELECT 
            users.nama, 
            kelas.kelas,
            COALESCE(ROUND(AVG(CASE WHEN kategori.kategori = 'Quis' THEN hasil_ujian.hasil ELSE NULL END)), 0) AS quis,
            COALESCE(ROUND(AVG(CASE WHEN kategori.kategori = 'UTS' THEN hasil_ujian.hasil ELSE NULL END)), 0) AS uts,
            COALESCE(ROUND(AVG(CASE WHEN kategori.kategori = 'UAS' THEN hasil_ujian.hasil ELSE NULL END)), 0) AS uas
        FROM users
        JOIN kelas ON users.id_kelas = kelas.id_kelas
        LEFT JOIN hasil_ujian ON hasil_ujian.id_user = users.id_user
        LEFT JOIN kategori ON hasil_ujian.id_kategori = kategori.id_kategori AND kategori.id_user = %s
        WHERE kelas.kelas = %s
        GROUP BY users.id_user, kelas.kelas
    '''
    cursor.execute(query, (id_user, kelas))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(results)

@app.route('/download-rekap')
def downloadRekap():
    if 'islogin' in session:
        id_user = request.args.get('id_user')
        kelas = request.args.get('kelas')

        conn = mysql.connection
        cursor = conn.cursor(dictionary=True)
        
        query = '''
            SELECT 
                users.nama, 
                kelas.kelas,
                COALESCE(ROUND(AVG(CASE WHEN kategori.kategori = 'Quis' THEN hasil_ujian.hasil ELSE NULL END)), 0) AS quis,
                COALESCE(ROUND(AVG(CASE WHEN kategori.kategori = 'UTS' THEN hasil_ujian.hasil ELSE NULL END)), 0) AS uts,
                COALESCE(ROUND(AVG(CASE WHEN kategori.kategori = 'UAS' THEN hasil_ujian.hasil ELSE NULL END)), 0) AS uas
            FROM users
            JOIN kelas ON users.id_kelas = kelas.id_kelas
            LEFT JOIN hasil_ujian ON hasil_ujian.id_user = users.id_user
            LEFT JOIN kategori ON hasil_ujian.id_kategori = kategori.id_kategori
            WHERE kelas.kelas = %s AND kategori.id_user = %s
            GROUP BY users.id_user, kelas.kelas
        '''
        cursor.execute(query, (kelas, id_user))
        nilai_siswa = cursor.fetchall()

        # Convert the data to a pandas DataFrame
        df = pd.DataFrame(nilai_siswa)

        # Create a BytesIO buffer
        output = BytesIO()

        # Write the DataFrame to an Excel file
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Nilai Siswa')

        # Seek to the beginning of the stream
        output.seek(0)

        # Send the file to the user
        return send_file(output, download_name=f"Nilai_Siswa_Kelas_{kelas}.xlsx", as_attachment=True)
    else:
        return redirect(url_for('login'))
    

#Tahun Akademik   
@app.route('/data-tahun-akademik')
def tahunAkademik():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute('SELECT * FROM tahun_akademik')
        data = curl.fetchall()
        return render_template('admin/tahunAkademik.html',data=data)
    else:
        return redirect(url_for('login'))
        
@app.route('/insert-tahun-akademik', methods=['POST'])
def insertTahunAkademik():
    tahun_akademik = request.form['tahun_akademik']
    semester = request.form['semester']
    status = request.form['status']
    conn = mysql.connection
    cur = conn.cursor()

    # Query untuk memeriksa apakah kombinasi tahun akademik dan semester sudah ada
    cur.execute("SELECT COUNT(*) FROM tahun_akademik WHERE tahun_akademik = %s AND semester = %s", (tahun_akademik, semester))
    result = cur.fetchone()

    # Jika kombinasi tahun akademik dan semester sudah ada
    if result[0] > 0:
        flash('Tahun Akademik dan Semester sudah ada, silakan masukkan kombinasi yang berbeda.', 'error')
        return redirect(url_for('tahunAkademik'))

    if status == 'Aktif':
        cur.execute("UPDATE tahun_akademik SET status = 'Tidak Aktif' WHERE status = 'Aktif'")

    cur.execute("INSERT tahun_akademik (tahun_akademik,semester,status) VALUES (%s,%s, %s)", (tahun_akademik,semester,status))
    conn.commit()
    flash('Tahun Akademik Berhasil ditambahkan','success')
    return redirect(url_for('tahunAkademik'))

@app.route('/update-tahun-akademik/<int:akademik_id>', methods=['POST'])
def updateTahunAkademik(akademik_id):
    tahun_akademik = request.form['tahun_akademik']
    semester = request.form['semester']
    status = request.form['status']
    conn = mysql.connection
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tahun_akademik WHERE tahun_akademik = %s AND akademik_id != %s", (tahun_akademik, akademik_id))
    result = cur.fetchone()
    
    if result[0] > 0:
        flash('Tahun Akademik sudah ada, silakan masukkan tahun yang berbeda.', 'error')
        return redirect(url_for('tahunAkademik'))

    if status == 'Aktif':
        cur.execute("UPDATE tahun_akademik SET status = 'Tidak Aktif' WHERE status = 'Aktif'")

    cur.execute("""
        UPDATE tahun_akademik
        SET tahun_akademik = %s, semester = %s, status = %s
        WHERE akademik_id = %s
        """, (tahun_akademik, semester, status, akademik_id))
    conn.commit()
    flash('Tahun Akademik Berhasil diperbarui','success')
    return redirect(url_for('tahunAkademik'))

@app.route('/delete-tahun-akademik/<int:akademik_id>', methods=['GET'])
def deleteTahunAkademik(akademik_id):
    if 'islogin' in session:
        conn = mysql.connection
        cur = conn.cursor()

        cur.execute("DELETE FROM tahun_akademik WHERE akademik_id = %s", (akademik_id,))
        conn.commit()

        flash('Tahun Akademik Berhasil dihapus', 'success')
        return redirect(url_for('tahunAkademik'))
    else:
        return redirect(url_for('login'))
    
#Admin Page
@app.route('/home')
def home():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute('''
            SELECT users.*
            FROM users 
            WHERE users.id_user = %s
        ''',(session['id_user'],))
        data = curl.fetchone()

        curl.execute("SELECT COUNT(*) FROM users WHERE level='Siswa'")
        result_siswa = curl.fetchone()
        count_siswa = result_siswa['COUNT(*)']

        curl.execute("SELECT COUNT(*) FROM users WHERE level='Guru'")
        result_guru = curl.fetchone()
        count_guru = result_guru['COUNT(*)']

        curl.execute("SELECT COUNT(*) FROM kelas")
        result_kelas = curl.fetchone()
        count_kelas = result_kelas['COUNT(*)']

        curl.execute("SELECT COUNT(*) FROM mapel")
        result_mapel = curl.fetchone()
        count_mapel = result_mapel['COUNT(*)']

        curl.execute("SELECT * FROM tahun_akademik WHERE status = 'Aktif'")
        tahun_akademik = curl.fetchone()


        return render_template('admin/index.html',tahun_akademik=tahun_akademik,data=data,count_siswa=count_siswa,count_guru=count_guru,count_kelas=count_kelas,count_mapel=count_mapel)
    else:
        return redirect(url_for('login'))

@app.route('/profil')
def profil():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute('''
            SELECT users.*, kelas.kelas,jurusan.jurusan
            FROM users 
            LEFT JOIN kelas ON kelas.id_kelas = users.id_kelas
            LEFT JOIN jurusan ON users.id_jurusan = jurusan.id_jurusan
            WHERE users.id_user = %s
        ''',(session['id_user'],))
        data = curl.fetchone() 
        return render_template('profil.html',data=data)
    else:
        return redirect(url_for('login'))

@app.route('/form-edit-profil/<int:id_user>', methods=['GET'])
def formEditProfil(id_user):
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute('''
                SELECT users.*, kelas.kelas,jurusan.jurusan
                FROM users 
                LEFT JOIN kelas ON kelas.id_kelas = users.id_kelas
                LEFT JOIN jurusan ON users.id_jurusan = jurusan.id_jurusan
                WHERE users.id_user = %s
        ''',(session['id_user'],))
        data = curl.fetchone() 
        return render_template('formProfil.html',data=data)
    else:
        return redirect(url_for('login'))

@app.route('/edit-profil/<int:id_user>', methods=['GET','POST'])
def updateProfil(id_user):
    nama_ortu = request.form['nama_ortu']
    email_ortu = request.form['email_ortu']
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("UPDATE users SET nama_ortu = %s, email_ortu = %s WHERE id_user = %s", (nama_ortu,email_ortu, id_user))
    conn.commit()
    flash('Data Profil Berhasil diupdate')
    return redirect(url_for('profil'))

@app.route('/data-siswa')
def dataSiswa():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
       

        curl.execute('SELECT * FROM kelas')
        data_kelas = curl.fetchall()
        curl.execute('SELECT * FROM tahun_akademik')
        tahun_akademik = curl.fetchall()

        return render_template('admin/siswa.html',kelas=kelas, data_kelas=data_kelas,tahun_akademik=tahun_akademik )
    else:
        return redirect(url_for('login'))
    

@app.route('/fetch_results_siswa', methods=['POST'])
def fetch_results_siswa():
    conn = mysql.connection
    cursor = conn.cursor(dictionary=True)
    
    id_tahun_akademik = request.form.get('id_tahun_akademik')
    id_kelas = request.form.get('kelas')


    cursor.execute('''
        SELECT users.*, kelas.kelas, jurusan.jurusan
        FROM users 
        LEFT JOIN kelas ON kelas.id_kelas = users.id_kelas
        LEFT JOIN jurusan ON users.id_jurusan = jurusan.id_jurusan
        WHERE users.level = 'Siswa' 
        AND users.id_tahun_akademik = %s
        AND users.id_kelas = %s 
    ''', (id_tahun_akademik, id_kelas))
    
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return jsonify(results)

    
@app.route('/daftar-siswa/<int:id_kelas>', methods=['GET'])
def daftarSiswa(id_kelas):
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        try:
            curl.execute('''
                SELECT users.*, kelas.kelas, jurusan.jurusan
                FROM users 
                LEFT JOIN kelas ON kelas.id_kelas = users.id_kelas
                LEFT JOIN jurusan ON users.id_jurusan = jurusan.id_jurusan
                WHERE users.level = 'Siswa' AND users.id_kelas = %s
            ''', (id_kelas,))
            siswa = curl.fetchall() 

            curl.execute('''
                SELECT kelas.kelas, jurusan.jurusan
                FROM kelas
                LEFT JOIN jurusan ON kelas.id_jurusan = jurusan.id_jurusan
                WHERE kelas.id_kelas = %s
            ''', (id_kelas,))
            kelas_jurusan = curl.fetchone()

        except Exception as e:
            flash(f'Terjadi kesalahan: {e}', 'error')
         
        finally:
            curl.close()
            conn.close()

        return render_template('admin/daftarSiswa.html', siswa=siswa,kelas_jurusan=kelas_jurusan)
    else:
        return redirect(url_for('login'))


@app.route('/data-guru')
def dataGuru():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute('''
                SELECT users.*, mapel.mapel
                FROM users 
                LEFT JOIN mapel ON mapel.id_mapel = users.id_mapel
                WHERE users.level = 'Guru'
            ''')
        guru = curl.fetchall() 
        return render_template('admin/guru.html',guru=guru)
    else:
        return redirect(url_for('login'))
    
@app.route('/data-admin')
def dataAdmin():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute("SELECT * FROM users WHERE level = 'Admin' ")
        admin = curl.fetchall()
        return render_template('admin/admin.html',admin=admin)
    else:
        return redirect(url_for('login'))
   
@app.route('/form-registrasi')
def formRegistrasi():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute("SELECT * FROM mapel")
        mapel = curl.fetchall()

        curl.execute("SELECT * FROM kelas")
        kelas = curl.fetchall()

        # Correct SQL query and cursor usage
        curl.execute("SELECT * FROM tahun_akademik WHERE status = 'Aktif'")
        akademik = curl.fetchone()


        curl.execute("SELECT * FROM jurusan")
        jurusan = curl.fetchall()
        return render_template('admin/formRegistrasi.html',kelas=kelas,mapel=mapel,jurusan=jurusan,akademik=akademik)
    else:
        return redirect(url_for('login'))
    
@app.route('/kelas')
def kelas():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute('''
                SELECT kelas.*, jurusan.jurusan
                FROM kelas 
                LEFT JOIN jurusan ON kelas.id_jurusan = jurusan.id_jurusan
            ''')
        kelas = curl.fetchall()

        curl.execute("SELECT * FROM jurusan")
        jurusan = curl.fetchall()
        return render_template('admin/kelas.html',kelas=kelas,jurusan=jurusan)
    else:
        return redirect(url_for('login'))
   
@app.route('/mapel')
def mapel():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute('''
                SELECT mapel.*, jurusan.jurusan
                FROM mapel
                LEFT JOIN jurusan ON mapel.id_jurusan = jurusan.id_jurusan
            ''')
        mapel = curl.fetchall()

        curl.execute("SELECT * FROM jurusan")
        jurusan = curl.fetchall()
        return render_template('admin/mapel.html',mapel=mapel,jurusan=jurusan)
    else:
        return redirect(url_for('login'))

@app.route('/jurusan')
def jurusan():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute("SELECT * FROM jurusan")
        jurusan = curl.fetchall()
        return render_template('admin/jurusan.html',jurusan=jurusan)
    else:
        return redirect(url_for('login'))

#Page Guru
# @app.route('/hasil')
# def hasilUjian():
#     if 'islogin' in session:
#         curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         query = "SELECT hasil_ujian.*, users.nama ,kelas.kelas FROM hasil_ujian \
#          JOIN kategori ON hasil_ujian.id_kategori = kategori.id_kategori \
#          JOIN users ON kategori.id_user = users.id_user and hasil_ujian.id_user = users.id_user \
#          JOIN kelas ON users.id_kelas = users.id_kelas \
#          WHERE kategori.id_user = %s"
#         data = (session['id_user'],)
#         curl.execute(query, data)
#         hasil_ujian = curl.fetchall()
#         print(hasil_ujian)
#         return render_template('guru/hasilUjian.html',hasil_ujian=hasil_ujian)
#     else:
#         return redirect(url_for('login'))
    
@app.route('/hasil')
def hasilUjian():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute("""
            SELECT DISTINCT kategori.id_kategori, kategori.kategori, kelas.kelas, mapel.mapel, kategori.tanggal, kategori.time_start, kategori.time_done
            FROM hasil_ujian 
            JOIN users ON hasil_ujian.id_user = users.id_user
            JOIN kelas ON users.id_kelas = users.id_kelas
            JOIN kategori ON hasil_ujian.id_kategori = kategori.id_kategori
            JOIN mapel ON mapel.id_mapel = kategori.id_mapel
            WHERE kategori.id_user = %s
            """,(session['id_user'],))

        kategori = curl.fetchall()
        print(kategori)

        return render_template('guru/hasilUjian.html', kategori=kategori)
    else:
        return redirect(url_for('login'))
    
@app.route('/daftar-nilai-siswa/<id_kategori>/<kelas>')
def daftarNilaiSiswa(id_kategori, kelas):
    if 'islogin' in session:
        kelas = kelas.replace('-', ' ')
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        
        # Perbaiki query SQL
        curl.execute("""
            SELECT 
                users.nama, 
                COALESCE(hasil_ujian.hasil, 'N/A') as hasil, 
                CASE 
                    WHEN hasil_ujian.hasil IS NOT NULL THEN 'Sudah Mengerjakan' 
                    ELSE 'Belum mengerjakan' 
                END as status
            FROM 
                users
            JOIN 
                kelas ON users.id_kelas = kelas.id_kelas
            LEFT JOIN 
                hasil_ujian ON hasil_ujian.id_user = users.id_user AND hasil_ujian.id_kategori = %s
            WHERE 
                kelas.kelas = %s 
                AND (hasil_ujian.id_kategori = %s OR hasil_ujian.id_kategori IS NULL)
            """, (id_kategori, kelas, id_kategori))

        nilai_siswa = curl.fetchall()
        
        return render_template('guru/daftar-nilai-siswa.html', nilai_siswa=nilai_siswa, kelas=kelas)
    else:
        return redirect(url_for('login'))

    
@app.route('/download-excel/<kelas>')
def downloadExcel(kelas):
    if 'islogin' in session:
        kelas = kelas.replace('-', ' ')
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute("""
            SELECT users.nama, 
                   COALESCE(hasil_ujian.hasil, 'N/A') as hasil, 
                   CASE 
                       WHEN hasil_ujian.hasil IS NOT NULL THEN 'Selesai' 
                       ELSE 'Tidak mengerjakan' 
                   END as status
            FROM users
            JOIN kelas ON users.id_kelas = kelas.id_kelas
            LEFT JOIN hasil_ujian ON hasil_ujian.id_user = users.id_user
            LEFT JOIN kategori ON hasil_ujian.id_kategori = kategori.id_kategori
            WHERE users.id_kelas = (SELECT id_kelas FROM kelas WHERE kelas.kelas = %s) AND (kategori.id_user = %s OR kategori.id_user IS NULL)
            """, (kelas, session['id_user']))
        
        nilai_siswa = curl.fetchall()

        # Convert the data to a pandas DataFrame
        df = pd.DataFrame(nilai_siswa)

        # Create a BytesIO buffer
        output = BytesIO()

        # Write the DataFrame to an Excel file
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Nilai Siswa')

        # Seek to the beginning of the stream
        output.seek(0)

        # Send the file to the user
        return send_file(output, download_name=f"Nilai_Siswa_Kelas_{kelas}.xlsx", as_attachment=True)
    else:
        return redirect(url_for('login'))

    
@app.route('/tema-soal')
def temaSoal():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute("SELECT * FROM kategori WHERE id_user = %s",(session['id_user'],))
        kategori = curl.fetchall()
      
        curl.execute('''
            SELECT users.*, mapel.mapel
            FROM users
            LEFT JOIN mapel ON mapel.id_mapel = users.id_mapel
            WHERE users.id_user = %s
        ''',(session['id_user'],))
        users = curl.fetchone()

        curl.execute("SELECT * FROM tahun_akademik WHERE status = 'Aktif'")
        tahun_akademik = curl.fetchone()

        return render_template('guru/tema.html',kategori=kategori,users=users,tahun_akademik=tahun_akademik)
    else:
        return redirect(url_for('login'))

@app.route('/soal')
def soal():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        
        curl.execute('''
            SELECT soal.*,kategori.kategori,kategori.tanggal
            FROM soal
            LEFT JOIN kategori ON kategori.id_kategori = soal.id_kategori
            LEFT JOIN users ON users.id_user = kategori.id_user
            WHERE users.id_user = %s
        ''', (session['id_user'],))
        soal = curl.fetchall()

        return render_template('guru/soal.html',soal=soal)
    else:
        return redirect(url_for('login'))

@app.route('/view-ujian/<int:id_kategori>', methods=['GET'])
def viewUjian(id_kategori):
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        query = '''
                SELECT kategori.*
                FROM kategori 
                LEFT JOIN soal ON soal.id_kategori = kategori.id_kategori
                WHERE kategori.id_kategori = %s
            '''
        curl.execute(query, (id_kategori,))
        detail = curl.fetchone()

        return render_template('guru/tinjau.html', soal=soal,detail=detail)
    else:
        return redirect(url_for('login'))


@app.route('/form-soal')
def formSoal():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        curl.execute("SELECT * FROM kategori WHERE id_user = %s",(session['id_user'],))
        kategori = curl.fetchall()

        curl.execute("SELECT * FROM mapel")
        mapel = curl.fetchall()
        return render_template('guru/formSoal.html',kategori=kategori,mapel=mapel)
    else:
        return redirect(url_for('login'))
        
#Page Siswa
@app.route('/hasil-ujian')
def hasil():
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        query = '''
                SELECT * FROM mapel
            '''
        curl.execute(query)
        data = curl.fetchall()
        return render_template('siswa/hasil.html',data=data)
    else:
        return redirect(url_for('login'))
    
@app.route('/daftar-ujian/<id_mapel>')
def daftarUjian(id_mapel):
    if 'islogin' in session:
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)
        
        query = '''
            SELECT hasil_ujian.*, kategori.kategori, mapel.mapel
            FROM hasil_ujian 
            LEFT JOIN users ON hasil_ujian.id_user = users.id_user
            LEFT JOIN kategori ON hasil_ujian.id_kategori = kategori.id_kategori
            LEFT JOIN mapel ON mapel.id_mapel = kategori.id_mapel
            WHERE hasil_ujian.id_user = %s AND kategori.id_mapel = %s
        '''
        
        curl.execute(query, (session['id_user'], id_mapel))
        data = curl.fetchall()  # Fetch all rows once

        curl.close()  # Close the cursor
        conn.close()  # Close the connection
        
        return render_template('siswa/daftar-nilai-siswa.html', data=data)
    else:
        return redirect(url_for('login'))
    
# @app.route('/hasil-ujian')
# def hasil2():
#     if 'islogin' in session:
#         conn = mysql.connection
#         curl = conn.cursor(dictionary=True)
#         query = '''
#                 SELECT hasil_ujian.*,kategori.kategori,mapel.mapel
#                 FROM hasil_ujian 
#                 LEFT JOIN users ON hasil_ujian.id_user = users.id_user
#                 LEFT JOIN kategori ON hasil_ujian.id_kategori = kategori.id_kategori
#                 LEFT JOIN mapel ON mapel.id_mapel = kategori.id_mapel
#                 WHERE hasil_ujian.id_user = %s
#             '''
#         curl.execute(query,(session['id_user'],))
#         data = curl.fetchall()
#         return render_template('siswa/hasil.html',data=data)
#     else:
#         return redirect(url_for('login'))

# @app.route('/ujian/<encrypted_id_kategori>', methods=['GET', 'POST'])
# def ujian(encrypted_id_kategori):
#     if 'islogin' in session:
#         try:
#             id_kategori = decrypt_id(encrypted_id_kategori)
#         except Exception as e:
#             return jsonify({"error": "Invalid ID"}), 400

#         conn = mysql.connection

#         if request.method == 'GET':
#             cursor = conn.cursor()
#             insert_query = "INSERT INTO hasil_ujian (id_user, id_kategori) VALUES (%s, %s)"
#             cursor.execute(insert_query, (session['id_user'], id_kategori))
#             conn.commit()
#             cursor.close()  

#         curl = conn.cursor(dictionary=True)

#         query = '''
#             SELECT kategori.*, mapel.mapel
#             FROM kategori 
#             LEFT JOIN soal ON soal.id_kategori = kategori.id_kategori
#             LEFT JOIN mapel ON mapel.id_mapel = kategori.id_mapel
#             WHERE kategori.id_kategori = %s
#         '''
#         curl.execute(query, (id_kategori,))
#         detail = curl.fetchone()  # Fetch the result of the first query
#         curl.fetchall()  # Ensure all results are read
#         curl.close()  # Close the cursor after use

#         curl = conn.cursor(dictionary=True)

#         # Second query
#         users_query = '''
#             SELECT users.*, kelas.kelas
#             FROM users 
#             LEFT JOIN kelas ON kelas.id_kelas = users.id_kelas
#             WHERE users.id_user = %s
#         '''
#         curl.execute(users_query, (session['id_user'],))
#         data = curl.fetchone()  # Fetch the result of the second query
#         curl.fetchall()  # Ensure all results are read
#         curl.close()  # Close the cursor after use

#         curl = conn.cursor(dictionary=True)

#         # Third query
#         curl.execute("SELECT * FROM soal WHERE id_kategori = %s ORDER BY RAND()", (id_kategori,))
#         soal = curl.fetchall()  # Fetch the result of the third query
#         curl.close()  # Close the cursor after use

#         return render_template('ujian.html', soal=soal, detail=detail, data=data, id_kategori=encrypted_id_kategori)
#     else:
#         return redirect(url_for('login'))

@app.route('/ujian/<int:id_kategori>', methods=['GET', 'POST'])
def ujian(id_kategori):
    if 'islogin' in session:
        conn = mysql.connection

        if request.method == 'GET':
            cursor = conn.cursor()
            insert_query = "INSERT INTO hasil_ujian (id_user, id_kategori) VALUES (%s, %s)"
            cursor.execute(insert_query, (session['id_user'], id_kategori))
            conn.commit()
            cursor.close()  # Close the cursor after use

        curl = conn.cursor(dictionary=True)

        # First query
        query = '''
            SELECT kategori.*, mapel.mapel
            FROM kategori 
            LEFT JOIN soal ON soal.id_kategori = kategori.id_kategori
            LEFT JOIN mapel ON mapel.id_mapel = kategori.id_mapel
            WHERE kategori.id_kategori = %s
        '''
        curl.execute(query, (id_kategori,))
        detail = curl.fetchone()  # Fetch the result of the first query
        curl.fetchall()  # Ensure all results are read
        curl.close()  # Close the cursor after use

        curl = conn.cursor(dictionary=True)

        # Second query
        users_query = '''
            SELECT users.*, kelas.kelas
            FROM users 
            LEFT JOIN kelas ON kelas.id_kelas = users.id_kelas
            WHERE users.id_user = %s
        '''
        curl.execute(users_query, (session['id_user'],))
        data = curl.fetchone()  # Fetch the result of the second query
        curl.fetchall()  # Ensure all results are read
        curl.close()  # Close the cursor after use

        curl = conn.cursor(dictionary=True)

        # Third query
        curl.execute("SELECT * FROM soal WHERE id_kategori = %s ORDER BY RAND()", (id_kategori,))
        soal = curl.fetchall()  # Fetch the result of the third query
        curl.close()  # Close the cursor after use

        return render_template('ujian.html', soal=soal, detail=detail, data=data, id_kategori=id_kategori)
    else:
        return redirect(url_for('login'))

@app.route('/daftar-ujian')
def listUjian():
    conn = mysql.connection
    curl = conn.cursor(dictionary=True)
    curl.execute('''
        SELECT kategori.*, mapel.mapel
        FROM kategori
        LEFT JOIN mapel ON mapel.id_mapel = kategori.id_mapel
        WHERE kategori.id_kategori IN (
            SELECT DISTINCT id_kategori
            FROM soal
        )
    ''')
    ujian = curl.fetchall()


    curl.execute('''
        SELECT users.*
        FROM users 
        WHERE users.id_user = %s
    ''',(session['id_user'],))
    data = curl.fetchone()

    if data['email_ortu'] is None:
        return redirect(url_for('profil'))

    curl.execute('''
                SELECT kategori.id_kategori
                FROM kategori
                JOIN hasil_ujian ON kategori.id_kategori = hasil_ujian.id_kategori 
                WHERE hasil_ujian.id_user = %s
            ''', (session['id_user'],))

    ujianSelesai = [item['id_kategori'] for item in curl.fetchall()]

    current_time = get_current_time()
    formatted_datetime = current_time.strftime("%H:%M")
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d")

    return render_template('siswa/listUjian.html',ujian=ujian,ujianSelesai=ujianSelesai,formatted_date= formatted_date,formatted_datetime=formatted_datetime)

def get_current_time():
    return datetime.now()

#Action Guru
@app.route('/insert-jenis-ujian', methods=['POST'])
def insertKategori():
    id_user = session.get('id_user')
    id_mapel = request.form['id_mapel']
    kategori = request.form['kategori']
    tanggal = request.form['tanggal']
    time_start = request.form['time_start']
    time_done = request.form['time_done']
    # Convert strings to datetime objects
    format_str = '%H:%M'  # The format
    time_start_obj = datetime.strptime(time_start, format_str)
    time_done_obj = datetime.strptime(time_done, format_str)

    # Calculate the duration in minutes
    duration = (time_done_obj - time_start_obj).seconds // 60
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("INSERT INTO kategori (id_user,id_mapel,kategori,tanggal,time_start,time_done,duration) VALUES (%s,%s,%s,%s,%s,%s,%s)",(id_user,id_mapel,kategori,tanggal,time_start,time_done,duration))
    conn.commit()
    return redirect(url_for('temaSoal'))

@app.route('/insert-soal', methods=['POST'])
def insertSoal():
    id_kategori = request.form['id_kategori']
    pertanyaan = request.form['pertanyaan']
    jawaban_a = request.form['jawaban_a']
    jawaban_b = request.form['jawaban_b']
    jawaban_c = request.form['jawaban_c']
    jawaban_d = request.form['jawaban_d']
    correct = request.form['correct']
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("INSERT INTO soal (id_kategori, pertanyaan, jawaban_a, jawaban_b, jawaban_c, jawaban_d, correct) VALUES (%s, %s, %s, %s, %s, %s, %s)", (id_kategori, pertanyaan, jawaban_a, jawaban_b, jawaban_c, jawaban_d, correct))
    conn.commit()
    flash('Soal Berhasil ditambahkan')
    return redirect(url_for('soal'))

@app.route('/update-soal/<int:id_soal>', methods=['POST'])
def updateSoal(id_soal):
    id_kategori = request.form['id_kategori']
    pertanyaan = request.form['pertanyaan']
    jawaban_a = request.form['jawaban_a']
    jawaban_b = request.form['jawaban_b']
    jawaban_c = request.form['jawaban_c']
    jawaban_d = request.form['jawaban_d']
    correct = request.form['correct']
    
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("UPDATE soal SET id_kategori=%s, pertanyaan=%s, jawaban_a=%s, jawaban_b=%s, jawaban_c=%s, jawaban_d=%s, correct=%s WHERE id_soal=%s", (id_kategori, pertanyaan, jawaban_a, jawaban_b, jawaban_c, jawaban_d, correct, id_soal))
    conn.commit()
    flash('Soal Berhasil diperbarui')
    return redirect(url_for('soal'))


def generate_slug(text):
    text = text.lower()
    text = ''.join(e for e in text if (e.isalnum() or e == ' '))
    text = text.replace(' ', '-')
    return text

#Action Admin
@app.route('/insert-user', methods=['POST'])
def insertUser():
    nama = request.form['nama']
    email = request.form['email']
    status = request.form['status']
    level = request.form['level']
    id_mapel = request.form['id_mapel']
    id_jurusan = request.form['id_jurusan']
    id_tahun_akademik = request.form['id_tahun_akademik']
    id_kelas = request.form['id_kelas']
    password = request.form['password'] 
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("INSERT INTO users (nama,email,status,level,id_mapel,id_jurusan,id_tahun_akademik,id_kelas,password) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",(nama,email,status,level,id_mapel,id_jurusan,id_tahun_akademik,id_kelas,hashed_password))
    conn.commit()
    return redirect(url_for('home'))

@app.route('/insert-siswa-from-excel', methods=['POST'])
def insert_siswa_from_excel():
    try:
        excel_file = request.files['file']
        if excel_file:
            df = pd.read_excel(excel_file)

            required_columns = ['nama', 'email', 'status', 'level', 'id_mapel', 'id_jurusan', 'id_kelas', 'password']
            for column in required_columns:
                if column not in df.columns:
                    return f"Error: Column '{column}' not found in the Excel file."
            for index, row in df.iterrows():
                nama = row['nama']
                email = row['email']
                status = row['status']
                level = row['level']
                id_mapel = row['id_mapel']
                id_jurusan = row['id_jurusan']
                id_kelas = row['id_kelas']
                password = row['password']
                hashed_password = hashlib.sha256(password.encode()).hexdigest()

                conn = mysql.connection
                cur = conn.cursor()
                cur.execute("INSERT INTO users (nama, email, status, level, id_mapel, id_jurusan, id_kelas, password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (nama, email, status, level, id_mapel, id_jurusan, id_kelas, hashed_password))
                conn.commit()
                flash('Data Siswa Berhasil diexport')

            return redirect(url_for('dataSiswa'))
        else:
            return "No file provided."
    except Exception as e:
        return f"Error: {str(e)}"
    
@app.route('/insert-guru-from-excel', methods=['POST'])
def insert_guru_from_excel():
    try:
        excel_file = request.files['file']
        if excel_file:
            df = pd.read_excel(excel_file)

            required_columns = ['nama', 'email', 'status', 'level', 'id_mapel', 'id_jurusan', 'id_kelas', 'password']
            for column in required_columns:
                if column not in df.columns:
                    return f"Error: Column '{column}' not found in the Excel file."
            for index, row in df.iterrows():
                nama = row['nama']
                email = row['email']
                status = row['status']
                level = row['level']
                id_mapel = row['id_mapel']
                id_jurusan = row['id_jurusan']
                id_kelas = row['id_kelas']
                password = row['password']
                hashed_password = hashlib.sha256(password.encode()).hexdigest()

                conn = mysql.connection
                cur = conn.cursor()
                cur.execute("INSERT INTO users (nama, email, status, level, id_mapel, id_jurusan, id_kelas, password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (nama, email, status, level, id_mapel, id_jurusan, id_kelas, hashed_password))
                conn.commit()
                flash('Data Guru Berhasil diexport')

            return redirect(url_for('dataGuru'))
        else:
            return "No file provided."
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/update-user/<int:id_user>', methods=['POST'])
def updateUser(id_user):
    nama = request.form['nama']
    email = request.form['email']
    status = request.form['status']
    level = request.form['level']
    id_mapel = request.form['id_mapel']
    id_jurusan = request.form['id_jurusan']
    id_kelas = request.form['id_kelas']
    password = request.form['password']
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    conn = mysql.connection
    cur = conn.cursor()
    cur.execute('''
        UPDATE users 
        SET nama = %s, email = %s, status = %s, level = %s, id_mapel = %s, id_jurusan = %s, id_kelas = %s, password = %s 
        WHERE id_user = %s
    ''', (nama, email, status, level, id_mapel, id_jurusan, id_kelas, hashed_password, id_user))
    
    conn.commit()
    return redirect(url_for('home'))


@app.route('/insert-kelas',methods=['POST'])
def insertKelas():
    id_jurusan = request.form['id_jurusan']
    kelas = request.form['kelas']
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("INSERT INTO kelas (id_jurusan,kelas) VALUES (%s,%s)" ,(id_jurusan,kelas))  
    conn.commit()
    return redirect(url_for('kelas'))

@app.route('/insert-mapel',methods=['POST','GET'])
def insertMapel():
    mapel= request.form['mapel']
    id_jurusan = request.form['id_jurusan']
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("INSERT INTO mapel (mapel,id_jurusan) VALUES (%s,%s)", (mapel, id_jurusan))
    conn.commit()
    return redirect(url_for('mapel'))

@app.route('/insert-jurusan',methods=['POST','GET'])
def insertJurusan():
    jurusan= request.form['jurusan']
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("INSERT INTO jurusan (jurusan) VALUES (%s)", (jurusan,))
    conn.commit()
    return redirect(url_for('jurusan'))

@app.route('/view-users/<int:id_user>', methods=['GET'])
def viewUsers(id_user):
    conn = mysql.connection
    curl = conn.cursor()
    query = '''
        SELECT users.*,mapel.mapel,jurusan.jurusan,kelas.kelas
        FROM users 
        LEFT JOIN mapel ON users.id_mapel = mapel.id_mapel
        LEFT JOIN jurusan ON users.id_jurusan = jurusan.id_jurusan
        LEFT JOIN kelas ON users.id_kelas = kelas.id_kelas
        WHERE users.id_user = %s
    '''
    curl.execute(query, (id_user,))
    data = curl.fetchone()

    curl.execute("SELECT * FROM mapel")
    mapel = curl.fetchall()

    curl.execute("SELECT * FROM jurusan")
    jurusan = curl.fetchall()

    curl.execute("SELECT * FROM kelas")
    kelas = curl.fetchall()

    return render_template('admin/formEdit.html', data=data,mapel=mapel,kelas=kelas,jurusan=jurusan)

@app.route('/delete-users/<int:id_user>', methods=['GET'])
def deleteUsers(id_user):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id_user = %s", (id_user,))
    conn.commit()
    flash('Data Berhasil dihapus')
    return redirect(url_for('home'))

@app.route('/update-jurusan/<int:id_jurusan>', methods=['POST', 'GET'])
def updateJurusan(id_jurusan):
    jurusan = request.form['jurusan']
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("UPDATE jurusan SET jurusan = %s WHERE id_jurusan = %s", (jurusan, id_jurusan))
    conn.commit()
    flash('Data Jurusan Berhasil diupdate')
    return redirect(url_for('jurusan'))

@app.route('/delete-jurusan/<int:id_jurusan>', methods=['GET'])
def deleteJurusan(id_jurusan):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("DELETE FROM jurusan WHERE id_jurusan = %s", (id_jurusan,))
    cur.execute("DELETE FROM kelas WHERE id_jurusan = %s", (id_jurusan,))
    cur.execute("DELETE FROM mapel WHERE id_jurusan = %s", (id_jurusan,))
    cur.execute("DELETE FROM users WHERE id_jurusan = %s", (id_jurusan,))
    conn.commit()
    flash('Data Jurusan Berhasil dihapus')
    return redirect(url_for('jurusan'))

@app.route('/update-kelas/<int:id_kelas>', methods=['POST', 'GET'])
def updateKelas(id_kelas):
    id_jurusan = request.form['id_jurusan']
    kelas = request.form['kelas']
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("UPDATE kelas SET id_jurusan = %s ,kelas = %s WHERE id_kelas = %s", (id_jurusan,kelas, id_kelas))
    conn.commit()
    flash('Data Kelas Berhasil diupdate')
    return redirect(url_for('kelas'))

@app.route('/delete-kelas/<int:id_kelas>', methods=['GET'])
def deleteKelas(id_kelas):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("DELETE FROM kelas WHERE id_kelas = %s", (id_kelas,))
    cur.execute("DELETE FROM users WHERE id_kelas = %s", (id_kelas,))
    conn.commit()
    flash('Data  Kelas Berhasil dihapus')
    return redirect(url_for('kelas'))

@app.route('/update-mapel/<int:id_mapel>', methods=['POST', 'GET'])
def updateMapel(id_mapel):
    id_jurusan = request.form['id_jurusan']
    mapel = request.form['mapel']
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("UPDATE mapel SET id_jurusan = %s ,mapel = %s WHERE id_mapel = %s", (id_jurusan,mapel, id_mapel))
    conn.commit()
    flash('Data Mapel Berhasil diupdate')
    return redirect(url_for('mapel'))

@app.route('/delete-mapel/<int:id_mapel>', methods=['GET'])
def deleteMapel(id_mapel):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("DELETE FROM mapel WHERE id_mapel = %s", (id_mapel,))
    cur.execute("DELETE FROM users WHERE id_mapel = %s", (id_mapel,))
    conn.commit()
    flash('Data Mapel Berhasil dihapus')
    return redirect(url_for('mapel'))

@app.route('/delete-soal/<int:id_soal>', methods=['GET'])
def deleteSoal(id_soal):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("DELETE FROM soal WHERE id_soal = %s", (id_soal,))
    conn.commit()
    flash('Data Soal Berhasil dihapus')
    return redirect(url_for('soal'))

@app.route('/delete-kategori/<int:id_kategori>', methods=['GET'])
def deleteKategori(id_kategori):
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("DELETE FROM kategori WHERE id_kategori = %s", (id_kategori,))
    cur.execute("DELETE FROM soal WHERE id_kategori = %s", (id_kategori,))
    cur.execute("DELETE FROM hasil_ujian WHERE id_kategori = %s", (id_kategori,))
    conn.commit()
    flash('Data Kategori Berhasil dihapus')
    return redirect(url_for('temaSoal'))

@app.route('/update-kategori/<int:id_kategori>', methods=['POST'])
def updateKategori(id_kategori):
    id_user = session.get('id_user')
    id_mapel = request.form['id_mapel']
    kategori = request.form['kategori']
    tanggal = request.form['tanggal']
    time_start = request.form['time_start']
    time_done = request.form['time_done']
    # Convert strings to datetime objects
    format_str = '%H:%M'  # The format
    time_start_obj = datetime.strptime(time_start, format_str)
    time_done_obj = datetime.strptime(time_done, format_str)

    # Calculate the duration in minutes
    duration = (time_done_obj - time_start_obj).seconds // 60
    conn = mysql.connection
    cur = conn.cursor()
    cur.execute("UPDATE kategori SET id_user=%s, id_mapel=%s, kategori=%s, tanggal=%s, time_start=%s, time_done=%s, duration=%s WHERE id_kategori=%s", (id_user, id_mapel, kategori, tanggal, time_start, time_done, duration, id_kategori))
    conn.commit()
    return redirect(url_for('temaSoal'))

@app.route('/view-soal/<int:id_soal>', methods=['GET'])
def viewSoal(id_soal):
    conn = mysql.connection
    curl = conn.cursor()
    query = '''
                SELECT soal.*, kategori.kategori, kategori.tanggal
                FROM soal 
                LEFT JOIN kategori ON soal.id_kategori = kategori.id_kategori
                WHERE soal.id_soal = %s
            '''
    curl.execute(query, (id_soal,))
    data = curl.fetchone()

    curl.execute("SELECT * FROM kategori WHERE id_user = %s",(session['id_user'],))
    kategori = curl.fetchall()
    return render_template('guru/editSoal.html', data=data,kategori=kategori)

#Auth/Login
@app.route('/action-login', methods=['GET', 'POST'])
def actionLogin():
    if 'islogin' in session:
        return redirect(url_for('home'))
    if request.method == 'POST' and 'nama' in request.form and 'password' in request.form:
        nama = request.form['nama']
        password = request.form['password'] 
        conn = mysql.connection
        curl = conn.cursor(dictionary=True)

        curl.execute('SELECT * FROM users WHERE nama = %s', (nama,))
        account = curl.fetchone()
        if account and check_password(password, account['password']):
            session['islogin'] = True
            session['id_user'] = account['id_user']
            session['nama'] = account['nama']
            session['level'] = account['level']
           
            if account['level'] == 'Admin':
                return redirect(url_for('home'))
            elif account['level'] == 'Guru':
                return redirect(url_for('home'))
            elif account['level'] == 'Siswa':
                return redirect(url_for('home'))
        else:
            flash("User Tidak Ditemukan atau Password Salah")
            return redirect(url_for('login'))
    else:
        return render_template('login.html')

def check_password(input_password, stored_password):
    hashed_input_password = hashlib.sha256(input_password.encode()).hexdigest()
    return hashed_input_password == stored_password

def get_correct_answers(id_kategori):
    correct_answers = {}
    conn = mysql.connection
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id_soal, correct FROM soal WHERE id_kategori = %s", (id_kategori,))
    rows = cur.fetchall()
    cur.close()
    print(rows)
    for row in rows:
        question_id = row['id_soal'] 
        correct_option = row['correct'] 
        print("Nilai id_soal:", question_id)
        print("Nilai correct:", correct_option)
        correct_answers[question_id] = correct_option 
    return correct_answers

def calculate_score(user_answers, correct_answers):
    correct_count = 0
    wrong_count = 0
    for question_id, user_choice in user_answers.items():
        if question_id.startswith('question_'):
            question_id = question_id[9:]
            correct_option = correct_answers.get(int(question_id), '')
            if correct_option and user_choice == correct_option:
                correct_count += 1
            else:
                wrong_count += 1
    return correct_count, wrong_count

        
# @app.route('/submit-quiz/<encrypted_id_kategori>', methods=['POST'])
# def submit_quiz(encrypted_id_kategori):
#     try:
#         id_kategori = encrypt_id(encrypted_id_kategori)
#     except Exception as e:
#         return jsonify({"error": "Invalid ID"}), 400
    
#     if request.method == 'POST':
#         try:
#             conn = mysql.connection
#             cursor = conn.cursor(dictionary=True)
#             cursor.execute('''
#                 SELECT users.*
#                 FROM users 
#                 WHERE users.id_user = %s
#             ''', (session['id_user'],))
#             data = cursor.fetchone()

#             if data:
#                 email_ortu = data['email_ortu']
#                 nama_ortu = data['nama_ortu']
#                 nama = data['nama']

#                 user_answers = request.form
#                 correct_answers = get_correct_answers(id_kategori)
#                 print("Jawaban Pengguna:", user_answers)
#                 print("Jawaban yang Benar:", correct_answers)
#                 correct_count, wrong_count = calculate_score(user_answers, correct_answers)

#                 total_questions = len(correct_answers)
#                 score = correct_count / total_questions * 100

#                 update_query = '''
#                     UPDATE hasil_ujian 
#                     SET hasil=%s, total_soal=%s, jumlah_betul=%s, jumlah_salah=%s 
#                     WHERE id_user=%s AND id_kategori=%s
#                 '''
#                 cursor.execute(update_query, (score, total_questions, correct_count, wrong_count, session['id_user'], id_kategori))
#                 conn.commit()

#                 # Kirim pesan email
#                 mail_message = Message(
#                     f"Hasil Ujian {nama} | SMAN Balapulang 1",
#                     recipients=[email_ortu]
#                 )
#                 mail_message.body = (
#                     f"Assalamualaikum Wr. Wb Selamat Siang Ibu/Bapak {nama_ortu} \n\n"
#                     f"Selaku orang tua/wali {nama}, kami sampaikan bahwa {nama} telah menyelesaikan ujian dan mendapatkan hasil ujian: \n"
#                     f"Score {score} dari {total_questions} soal. \n"
#                     f"Jumlah jawaban benar: {correct_count}. \n"
#                     f"Jumlah jawaban salah: {wrong_count}.\n\n"
#                     f"Terima kasih kami sampaikan, Wassalamualaikum Wr. Wb \n\n"
#                     f"Ttd, Akademik SMAN Balapulang 1"
#                 )
#                 mail.send(mail_message)

#                 return render_template('score.html', score=score, total=total_questions, wrong_count=wrong_count, correct_count=correct_count)
#             else:
#                 return "Data pengguna tidak ditemukan.", 404
#         except mysql.connector.Error as err:
#             return f"Terjadi kesalahan pada database: {err}", 500
#         except Exception as e:
#             return f"Terjadi kesalahan: {e}", 500

@app.route('/submit-quiz/<int:id_kategori>', methods=['POST'])
def submit_quiz(id_kategori):
    if request.method == 'POST':
        try:
            conn = mysql.connection
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT users.*
                FROM users 
                WHERE users.id_user = %s
            ''', (session['id_user'],))
            data = cursor.fetchone()

            if data:
                email_ortu = data['email_ortu']
                nama_ortu = data['nama_ortu']
                nama = data['nama']

                user_answers = request.form
                correct_answers = get_correct_answers(id_kategori)
                print("Jawaban Pengguna:", user_answers)
                print("Jawaban yang Benar:", correct_answers)
                correct_count, wrong_count = calculate_score(user_answers, correct_answers)

                total_questions = len(correct_answers)
                score = correct_count / total_questions * 100

                update_query = '''
                    UPDATE hasil_ujian 
                    SET hasil=%s, total_soal=%s, jumlah_betul=%s, jumlah_salah=%s 
                    WHERE id_user=%s AND id_kategori=%s
                '''
                cursor.execute(update_query, (score, total_questions, correct_count, wrong_count, session['id_user'], id_kategori))
                conn.commit()

                # Kirim pesan email
                mail_message = Message(
                    f"Hasil Ujian {nama} | SMAN Balapulang 1",
                    recipients=[email_ortu]
                )
                mail_message.body = (
                    f"Assalamualaikum Wr. Wb Selamat Siang Ibu/Bapak {nama_ortu} \n\n"
                    f"Selaku orang tua/wali {nama}, kami sampaikan bahwa {nama} telah menyelesaikan ujian dan mendapatkan hasil ujian: \n"
                    f"Score {score} dari {total_questions} soal. \n"
                    f"Jumlah jawaban benar: {correct_count}. \n"
                    f"Jumlah jawaban salah: {wrong_count}.\n\n"
                    f"Terima kasih kami sampaikan, Wassalamualaikum Wr. Wb \n\n"
                    f"Ttd, Akademik SMAN Balapulang 1"
                )
                mail.send(mail_message)

                return render_template('score.html', score=score, total=total_questions, wrong_count=wrong_count, correct_count=correct_count)
            else:
                return "Data pengguna tidak ditemukan.", 404
        except mysql.connector.Error as err:
            return f"Terjadi kesalahan pada database: {err}", 500
        except Exception as e:
            return f"Terjadi kesalahan: {e}", 500
        
@app.route('/add_violation_data', methods=['POST'])
def add_violation_data():
    if request.method == 'POST':
        data = request.get_json()
        id_user = data.get('id_user')
        id_kategori = data.get('id_kategori')
        conn = mysql.connection
        cur = conn.cursor()
        cur.execute("UPDATE hasil_ujian SET pelanggaran = COALESCE(pelanggaran, 0) + 1 WHERE id_user = %s AND id_kategori = %s", (id_user, id_kategori))
        conn.commit()

        pelanggaran_query = 'SELECT pelanggaran FROM hasil_ujian WHERE id_user = %s AND id_kategori = %s'
        cur.execute(pelanggaran_query, (id_user, id_kategori))
        pelanggaran_result = cur.fetchone()
        pelanggaran = pelanggaran_result['pelanggaran'] if pelanggaran_result else 0

        return str(pelanggaran)  

@app.route('/score')
def score():
    return render_template('score.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



