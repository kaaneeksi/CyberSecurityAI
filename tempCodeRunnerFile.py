from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from question_generator import generate_questions, generate_advice, chat_with_gpt
import openai
import os
app = Flask(__name__)
app.secret_key = 'mentor'

API_KEY = os.getenv("OPENAI_API_KEY")
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

@app.route('/evaluation', methods=['GET', 'POST'])
def evaluation():
    user_id = session.get('user_id')

    if not user_id:
        flash("Please log in to view your evaluation.", "error")
        return redirect(url_for('login'))

    # Kullanıcının test sonuçlarını al
    cursor.execute("""
        SELECT Cyber_Security_101, SOC_Level_1, DevSecOps, Web_Fundamentals,
               Web_App_Pentesting, Network, Linux, Success_Rate
        FROM UserResults
        WHERE user_id = ?;
    """, (user_id,))
    results = cursor.fetchone()

    # Test sonuçları yoksa kullanıcıyı bilgilendir
    if not results:
        flash("No test results found. Please complete some tests first.", "info")
        return redirect(url_for('home'))

    # Başarı oranına göre tavsiye oluştur
    success_rate = results[-1] if results[-1] else 0
    advice = generate_advice(success_rate)

    # Kullanıcıdan gelen mesajları GPT ile sohbet için işleme
    chatbot_response = None
    if request.method == "POST":
        user_message = request.form.get('user_message')
        chatbot_response = chat_with_gpt(user_message)

    return render_template('evaluation.html', results=results, advice=advice, chatbot_response=chatbot_response)

@app.route('/learn/<topic>', methods=['GET', 'POST'])
def learn_topic(topic):
    # Eğitim içeriği örnekleri
    content = {
        "Cyber Security 101": {
            "title": "Cyber Security 101",
            "description": "Learn the basics of cybersecurity, including concepts, threats, and best practices.",
            "modules": [
                {"title": "What is Cybersecurity?", "content": "Cybersecurity involves protecting systems and networks from digital attacks."},
                {"title": "Common Threats", "content": "Phishing, Malware, Ransomware, and more."},
                {"title": "Best Practices", "content": "Use strong passwords, enable MFA, and stay aware of threats."}
            ],
            "image": "static/introtocybersecurity.svg"
        },
        "SOC Level 1": {
            "title": "SOC Level 1",
            "description": "Learn the skills needed to work as a Security Operations Center Analyst.",
            "modules": [
                {"title": "Introduction to SOC", "content": "What is SOC and its role in cybersecurity?"},
                {"title": "Incident Response", "content": "Learn how to respond to security incidents."}
            ],
            "image": "static/SOCL1.svg"
        },
        "Offensive Pentesting": {
            "title": "Offensive Pentesting",
            "description": "Learn about penetration testing and how to identify vulnerabilities.",
            "modules": [
                {"title": "Penetration Testing Basics", "content": "What is pentesting and its methodology?"},
                {"title": "Tools and Techniques", "content": "Learn about Nmap, Metasploit, and more."}
            ],
            "image": "static/redteaming.svg"
        }
    }

    # Eğitim içeriğini kontrol et
    current_content = content.get(topic, {"title": topic, "description": "Content not available", "modules": []})

    if request.method == 'POST':
        # Testi başlat
        return redirect(url_for('start_test', topic=topic))

    return render_template('learn.html', content=current_content)


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

