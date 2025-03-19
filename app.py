from flask import Flask, render_template, jsonify, request
import cv2
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
from deepface import DeepFace

app = Flask(__name__)

UPLOAD_FOLDER = 'known_faces'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def initialize_db():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            time TEXT
        )
    """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS faculty (
                userid INTEGER PRIMARY KEY AUTOINCREMENT,
                password TEXT
                
            )
        """)
    cursor.execute("""
                CREATE TABLE IF NOT EXISTS working (
                    date TEXT,
                    marked INTEGER

                )
            """)
    conn.commit()
    conn.close()


def mark_absent(names):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d ")
    for i in range(1,8):
        for name,year in names:
            cursor.execute("SELECT * FROM attendance WHERE name=? AND year=? AND status='Ab'AND period=? and date=?", (name, year,i,date))
            existing_record = cursor.fetchone()

            if not existing_record:
                cursor.execute("INSERT INTO attendance (name, year, status,period,date) VALUES (?, ?, 'Ab',?,?)", (name, year,i,date))


    conn.commit()
    conn.close()

def get_image_names():
    image_names = []

    for file in os.listdir(UPLOAD_FOLDER):
        if file.endswith(('.png', '.jpg', '.jpeg')):  # Filter only image files
            file_name = os.path.splitext(file)[0]  # Remove file extension
            allnames= file_name.split("_")
            name=allnames[0]
            year= allnames[1]
            image_names.append((name,year))

    return image_names


def find_name_exits(student_name):
    count=0
    for file in os.listdir(UPLOAD_FOLDER):
        file_name = os.path.splitext(file)[0]
        allnames = file_name.split("_")
        name = allnames[0]
        if student_name==name:
            count+=1
    return count+1


student_data = get_image_names()  # Extract names and years
mark_absent(student_data)





def mark_attendance(name):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d ")
    time=datetime.now().strftime("%H:%M:%S")
    per=datetime.now().strftime("%H")
    per=int(per)
    if per<9 or per>=16 or (per>=12 and per<13):
        period=0
    else:
        period=per-8
    print(period)
    print(per>int(17))
    print(type(per),per)
    name=name.split("_")
    year=name[1]
    print(name)
    name=name[0]
    if period==0:
        cursor.execute("INSERT INTO attendance (name, date,period,year,time,status) VALUES (?, ?,?,?,?,'P' )", (name, date,period,year,time))
    else:
        cursor.execute("UPDATE attendance SET status = 'P' ,time=? WHERE name = ? AND date = ? AND period = ? AND year=?",(time,name, date, period,year))

    conn.commit()
    conn.close()
    return time,period


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/train", methods=["POST"])
def train():
    return render_template("train_student.html")


@app.route("/recognize", methods=["POST"])
def recognize():
    cap = cv2.VideoCapture(0)  # Open the default camera
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    while True:
        ret, img = cap.read()

        if not ret:
            cap.release()
            return jsonify({"error": "Camera error"}), 500
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        name = "Unknown"

        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)  # Green border


            face_roi = img[y:y + h, x:x + w]
            if cv2.waitKey(1) & 0xFF == ord('q'):
                face_path = "temp_face.jpg"
                cv2.imwrite(face_path, face_roi)

                try:
                    result = DeepFace.find(img_path=face_path, db_path=UPLOAD_FOLDER, model_name="Facenet")
                    if len(result) > 0 and not result[0].empty:
                        name = os.path.splitext(os.path.basename(result[0]['identity'][0]))[0]
                        time,period=mark_attendance(name)
                        print("this is name from recognizer and result",name,result)
                        print(time)
                        cap.release()
                        cv2.destroyAllWindows()
                        return jsonify({"name": name,"time":time,"period":period})
                except Exception as e:
                    print("DeepFace error:", e)



                break
        cv2.imshow("Face Recognition", img)

    cap.release()
    cv2.destroyAllWindows()
    return jsonify({"name": name}), 400





@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No file part"}), 400

    image = request.files['image']
    student_name = request.form.get('studentName')
    year=request.form.get('year')
    print(year)


    if not student_name:
        return jsonify({"error": "No student name provided"}), 400

    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        exists=find_name_exits(student_name)
        new_filename = f"{student_name}_{year}_{exists}.jpg"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        image.save(file_path)
        return jsonify({"message": f"File uploaded successfully as {new_filename}.", "path": file_path}), 200
    else:
        return jsonify({"error": "Invalid file format"}), 400

@app.route('/capture', methods=['POST'])
def capture():
    cap = cv2.VideoCapture(0)
    while True:
        ret, img = cap.read()
        if not ret:
            cap.release()
            return jsonify({"error": "Camera error"}), 500
        cv2.imshow("Camera Feed", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            student_name = request.form.get('studentName')
            if not student_name:
                print( "Student name is required")
            print(student_name)
            year=request.form.get("year")
            exists = find_name_exits(student_name)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                      student_name + "_" + str(year) + "_" + str(exists) + ".jpg")
            cv2.imwrite(image_path, img)  # Save the image
            cap.release()
            cv2.destroyAllWindows()
            break

    return render_template('index.html')



@app.route("/login",methods=["POST"])
def login():
    return render_template("login.html")

@app.route("/verify",methods=["POST"])
def verify():
    userid=request.form.get("userid")
    password= request.form.get("pass")
    conn=sqlite3.connect("attendance.db")
    cursor=conn.cursor()
    a=cursor.execute("select * from faculty where userid=? and password=?",(userid,password))

    if len(list(a))>=1:
        print(list(a))
        conn.commit()
        conn.close()
        conn = sqlite3.connect("attendance.db")
        students = []
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT name FROM attendance")
        student_names =[]
        folder_names=get_image_names()
        #student_names = [row[0] for row in cursor.fetchall()]
        for i in range(len(folder_names)):

            student_names.append(folder_names[i][0])
        d=set(student_names)
        student_names=list(d)



        conn.close()
        return render_template("home.html", students=students, student_names=student_names)


def fetch_students(year, date_filter, name,period,status):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    query = ("SELECT id, name, year,  date, period,time,status"
             " FROM attendance WHERE 1=1")
    params = []

    # Filter by Year
    if year:
        query += " AND year = ?"
        params.append(year)

    # Filter by Date
    today_date = datetime.today().strftime('%Y-%m-%d')
    this_month = datetime.today().strftime('%Y-%m')

    if date_filter == "today":
        query += " AND date LIKE ?"
        params.append(today_date)
    elif date_filter == "this_month":
        query += " AND date LIKE ?"
        params.append(this_month + "%")

    # Filter by Name
    if name and name != "all":
        query += " AND name = ?"
        params.append(name)
    if period!="all":
        query+=" AND period = ?"
        params.append(period)
    if status!="":
        query+=" AND status= ?"
        params.append(status)

    cursor.execute(query, params)
    students = cursor.fetchall()
    conn.close()

    return students




@app.route("/fetch",methods=["POST"])
def fetch():
    year = request.form.get("year")
    date_filter = request.form.get("date")
    name = request.form.get("name")
    period=request.form.get("period")
    status=request.form.get("status")

    students = fetch_students(year, date_filter, name,period,status)

    # Fetch all student names for dropdown again
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT name FROM attendance")
    student_names = []
    folder_names = get_image_names()
    #student_names = [row[0] for row in cursor.fetchall()]
    for i in range(len(folder_names)):
        student_names.append(folder_names[i][0])
    d = set(student_names)
    student_names = list(d)
    conn.close()

    return render_template("home.html", students=students, student_names=student_names)


if __name__ == "__main__":
    initialize_db()
    app.run(debug=True)
