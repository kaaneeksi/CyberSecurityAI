from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from question_generator import generate_questions
app = Flask(__name__)
app.secret_key = 'mentor'

# SQL Server bağlantısı
conn = pyodbc.connect('Driver={ODBC Driver 17 for SQL Server};'
                      'Server=KAAN;'
                      'Database=CyberSecurityAI;'
                      'Trusted_Connection=yes;')

cursor = conn.cursor()

topics = [
    "Cyber Security 101",
    "SOC Level 1",
    "DevSecOps",
    "Web Fundamentals",
    "Web_App_Pentesting",
    "Network",
    "Linux"
]

# Ana Sayfa
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start/<topic>', methods=['GET', 'POST'])
def start_test(topic):
    if request.method == 'POST':
        session['current_question'] = 0
        session['score'] = 0
        session['topic'] = topic

        # Soruları oluştur ve session'a ekle
        questions = generate_questions(topic)
        session['questions'] = questions
        return redirect(url_for('test_question'))

    return render_template('start.html', topic=topic)


@app.route('/test/question', methods=['GET', 'POST'])
def test_question():
    questions = session.get('questions', [])
    current_index = session.get('current_question', 0)

    # Tüm sorular tamamlandıysa sonucu göster
    if current_index >= len(questions):
        return redirect(url_for('test_result'))

    # Şu anki soruyu al
    question = questions[current_index]

    if request.method == 'POST':
        user_answer = request.form['answer']
        correct_answer = question['answer']  # Burada sözlük üzerinden erişim sağlanır

        # Cevabı kontrol et
        if user_answer == correct_answer:
            session['score'] += 1
        session['current_question'] += 1

        return render_template(
            'feedback.html',
            question=question,
            user_answer=user_answer,
            correct_answer=correct_answer
        )

    return render_template('question.html', question=question, enumerate=enumerate)


@app.route('/test/result')
def test_result():
    topic = session.get('topic')  # Test konusu
    score = session.get('score')  # Testten alınan puan
    total_questions = len(session.get('questions', []))  # Toplam soru sayısı

    user_id = session.get('user_id')  # Kullanıcının ID'si
    if not user_id:
        flash('Please log in to save your results.', 'error')
        return redirect(url_for('login'))

    try:
        # Kullanıcı mevcutsa güncelle, değilse ekle
        cursor.execute(f"""
            IF EXISTS (SELECT 1 FROM UserResults WHERE user_id = ?)
                UPDATE UserResults
                SET {topic.replace(' ', '_')} = ?,
                    Success_Rate = (
                        (
                            ISNULL(Cyber_Security_101, 0) +
                            ISNULL(SOC_Level_1, 0) +
                            ISNULL(DevSecOps, 0) +
                            ISNULL(Web_Fundamentals, 0) +
                            ISNULL(Web_App_Pentesting, 0) +
                            ISNULL(Network, 0) +
                            ISNULL(Linux, 0)
                        ) / 7.0
                    )
                WHERE user_id = ?
            ELSE
                INSERT INTO UserResults (user_id, {topic.replace(' ', '_')}, Success_Rate)
                VALUES (?, ?, ?);
        """, (user_id, score, user_id, user_id, score, (score / total_questions) * 100))
        conn.commit()

        flash('Test result saved successfully!', 'success')
    except Exception as e:
        print("Database error:", e)
        flash('Error saving test result. Please try again.', 'error')

    # Oturum bilgilerini temizle
    session.pop('current_question', None)
    session.pop('questions', None)
    session.pop('topic', None)
    session.pop('score', None)

    return render_template('result.html', topic=topic, score=score, total_questions=total_questions)


@app.route('/results')
def view_results():
    user_id = session.get('user_id')  # Oturumdaki kullanıcı ID'si

    if not user_id:
        flash('Please log in to view your results.', 'error')
        return redirect(url_for('login'))

    try:
        # Kullanıcının test sonuçlarını getir
        cursor.execute("""
            SELECT Cyber_Security_101, SOC_Level_1, DevSecOps, Web_Fundamentals,
                   Web_App_Pentesting, Network, Linux, Success_Rate
            FROM UserResults
            WHERE user_id = ?;
        """, (user_id,))
        results = cursor.fetchone()
    except Exception as e:
        print("Database error:", e)
        results = []

    return render_template('results.html', results=results)



# Login Sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Kullanıcı adı ve şifre doğrulaması
        cursor.execute("SELECT id, username FROM Users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        if user:
            # Kullanıcı oturumu başlat
            session['user_id'] = user[0]  # Kullanıcı ID'si
            session['username'] = user[1]  # Kullanıcı adı
            flash('Login successful!', 'success')
            return redirect(url_for('home'))  # Home page'e yönlendirme
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')

# Register Sayfası
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Kullanıcı kontrolü (var mı diye kontrol et)
        cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            flash('This username is already taken. Please choose a different one.', 'error')
        else:
            # Yeni kullanıcıyı ekle
            cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            return redirect(url_for('index'))  # Login sayfasına yönlendirme

    return render_template('register.html')


# Ana Sayfa
@app.route('/home')
def home():
    return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True)

