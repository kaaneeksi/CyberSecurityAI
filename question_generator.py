import openai
import json
import os
# OpenAI API anahtarını ayarla
API_KEY = os.getenv("OPENAI_API_KEY")

def generate_questions(topic):
    """
    Belirtilen konu için çoktan seçmeli sorular üretir.
    """
    prompt = (
        f"Generate 3 multiple-choice questions about {topic} with 4 options each. "
        "Include the correct answer for each question in JSON format. "
        "Example: ["
        "{\"question\": \"What is cybersecurity?\", "
        "\"options\": [\"Protecting data\", \"Writing code\", \"Building networks\", \"Installing software\"], "
        "\"answer\": \"Protecting data\"}"
        "]"
    )

    try:
        # ChatGPT API'sine istek gönder
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for generating quiz questions."},
                {"role": "user", "content": prompt}
            ]
        )

        # API'den gelen yanıtı işleme
        questions = response['choices'][0]['message']['content']

        # Soruları JSON formatına dönüştür
        questions = json.loads(questions)
        return questions

    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        return []
    except Exception as e:
        print("An error occurred:", e)
        return []

def generate_advice(success_rate):
    """
    Kullanıcının başarı oranına göre bir tavsiye oluşturur.
    """
    prompt = (
        f"Based on a success rate of {success_rate}%, provide personalized advice for improving cybersecurity skills. "
        "Make it concise, actionable, and encouraging."
    )

    try:
        # ChatGPT API'sine istek gönder
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant providing personalized advice."},
                {"role": "user", "content": prompt}
            ]
        )

        # Tavsiye metnini işleme
        advice = response['choices'][0]['message']['content'].strip()
        return advice

    except Exception as e:
        print("An error occurred:", e)
        return "Unable to generate advice at this time. Please try again later."


def chat_with_gpt(user_message):
    """
    Kullanıcı mesajına yanıt verir.
    """
    try:
        # ChatGPT API'sine sohbet isteği gönder
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a knowledgeable assistant for cybersecurity topics."},
                {"role": "user", "content": user_message}
            ]
        )

        # Yanıt metnini işleme
        reply = response['choices'][0]['message']['content'].strip()
        return reply

    except Exception as e:
        print("An error occurred:", e)
        return "Unable to respond at this time. Please try again later."
