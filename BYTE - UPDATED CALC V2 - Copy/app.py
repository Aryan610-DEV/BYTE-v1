from flask import Flask, request, jsonify, render_template
from PIL import Image
import io
import os
import logging
import sqlite3
import requests 
from datetime import datetime
import easyocr
import numpy
import uuid

app = Flask(__name__)

TOGETHER_AI_API_KEY = '382b4bebddd75e5d7d3eca4e25ec9f106794bba76ad773614f480d29a2bc4dac'  # Replace with your actual API key
TOGETHER_AI_URL = "https://api.together.xyz/v1/completions"

logging.basicConfig(filename='user_queries.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

conn = sqlite3.connect('chat_history.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS history 
             (id INTEGER PRIMARY KEY, query TEXT, response TEXT)''')
conn.commit()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/byte')
def index():
    return render_template('index.html')

@app.route('/calculator')
def calculator():
    return render_template('calculator.html')

@app.route('/todo')
def todo():
    return render_template('todo.html')


@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['query']
    bot_response = basic_chatbot_responses(user_input)
    if bot_response:
        return jsonify({'response': format_response_as_html(bot_response)})
    response = ask_together_ai(user_input)
    return jsonify({'response': format_response_as_html(response)})

@app.route('/recognize_handwriting', methods=['POST'])
def recognize_handwriting():
    try:
        file = request.files['image']
        if file:
            image = Image.open(file.stream)
            reader = easyocr.Reader(['en'])
            results = reader.readtext(numpy.array(image))

            if not results:
                logging.warning("No text found in the image.")
                return jsonify({'response': "No text recognized from the image."}), 400

            recognized_text = " ".join([result[1] for result in results])
            logging.info(f"Recognized text from image: {recognized_text.strip()}")
            response = ask_together_ai(recognized_text.strip())
            return jsonify({'response': format_response_as_html(response)})
        
        else:
            logging.error("No file uploaded.")
            return jsonify({'response': "No file uploaded."}), 400

    except Exception as e:
        logging.error(f"Error recognizing handwriting: {e}")
        return jsonify({'response': "Error processing the image."}), 500

def ask_together_ai(query):
    try:
        prompt = (
            f"Provide a detailed, professional answer to the following question in a structured format with clear headings, bullet points, or numbered steps:\n"
            f"{query}\n"
            f"Make sure the answer is well-organized, concise, and easy to follow."
        )
        headers = {
            'Authorization': f'Bearer {TOGETHER_AI_API_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            "model": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
            "prompt": prompt,
            "max_tokens": 800,
            "temperature": 0.1,
        }
        response = requests.post(TOGETHER_AI_URL, headers=headers, json=data)
        logging.info(f"Full API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['text'].strip()
        else:
            logging.error(f"AI API error: {response.status_code} - {response.text}")
            return "Error processing your query. Please try again."
    except Exception as e:
        logging.error(f"Error processing the query '{query}': {e}")
        return "Error processing your query. Please try again."

def format_response_as_html(response_text):
    lines = response_text.split('\n')
    formatted_response = "<div style='font-family:Arial, sans-serif; line-height:1.7; font-size:16px;'>"

    for line in lines:
        line = line.strip()
        if line:
            if line.endswith(':'):
                formatted_response += f"<p style='font-weight:bold; font-size:18px; margin-top:15px; margin-bottom:5px;'>{line}</p>"
            elif line and line[0].isdigit() and line[1] == '.':
                formatted_response += f"<p style='margin-left:20px; font-size:16px; margin-bottom:8px;'><strong>{line}</strong></p>"
            else:
                formatted_response += f"<p style='margin-left:20px; font-size:16px; margin-bottom:8px;'><strong>• {line}</strong></p>"

    formatted_response += "</div>"
    return formatted_response

def basic_chatbot_responses(user_input):
    user_input = user_input.lower()
    
    responses = {
        "how are you": ["I'm fine, thank you!", "Doing well, how about you?"],
        "what is your name": ["I am Byte, your AI assistant."],
        "tell me a joke": ["Why did the chicken cross the road? To get to the other side!"],
        "what time is it": [get_current_time()],
        "what is the date": [get_current_date()],
        "bye": ["Goodbye! Have a great day!"],
    }

    for key, variations in responses.items():
        if user_input in variations:
            return variations[0]
    
    return ""

def get_current_time():
    now = datetime.now()
    return f"The current time is {now.strftime('%H:%M')}."

def get_current_date():
    today = datetime.now()
    return f"Today's date is {today.strftime('%B %d, %Y')}."

if __name__ == "__main__":
    try:
        print("Server running at: http://127.0.0.1:8080/")
        app.run(debug=True, port=8080)
    finally:
        conn.close()
