from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
import os
import speech_recognition as sr
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from faker import Faker
from datetime import datetime, timedelta
import random
import pyttsx3
import os
from gtts import gTTS
from googletrans import Translator

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')

app = Flask(__name__)
app.secret_key = os.urandom(24)
fake = Faker()

# Initialize speech recognizer
recognizer = sr.Recognizer()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id, email):
        self.id = user_id
        self.email = email
        
    def get_id(self):
        return str(self.id)  # Must return string

users = {}  # In-memory user storage

def load_orders():
    try:
        with open('orders.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"orders": []}

def save_orders(orders_data):
    with open('orders.json', 'w') as f:
        json.dump(orders_data, f, indent=2)



def search_orders(query):
    """
    Search orders by order ID, customer name, or product name
    Returns a list of matching orders
    """
    orders = load_orders()
    results = []
    query = query.upper()
    
    for order in orders['orders']:
        # Search by order ID
        if query in order['order_id'].upper():
            results.append(order)
            continue
            
        # Search by customer name
        if query in order['customer_name'].upper():
            results.append(order)
            continue
            
        # Search by product name
        if query in order['product_name'].upper():
            results.append(order)
            continue
    
    return results

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if email in [user.email for user in users.values()]:
            return render_template('signup.html', error="Email already registered")
            
        user_id = str(len(users) + 1)
        users[user_id] = User(user_id, email)
        return redirect(url_for('login'))
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        
        for user in users.values():
            if user.email == email:
                login_user(user)
                return redirect(url_for('chat'))
                
        return render_template('login.html', error="Invalid credentials")
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/api/search-orders', methods=['POST'])
@login_required
def search_orders_api():
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Search query is required'
        }), 400
    
    results = search_orders(query)
    
    return jsonify({
        'success': True,
        'results': results,
        'count': len(results)
    })

@app.route('/api/message', methods=['POST'])
@login_required
def handle_message():
    translator = Translator()
    data = request.json
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({
            'success': False,
            'response': {
                'type': 'text',
                'message': 'कृपया कोई संदेश दें'
            }
        }), 400
    
    # First convert Hindi message to English if needed
    detected_lang = translator.detect(message).lang
    if detected_lang == 'hi':
        message = translator.translate(message, src='hi', dest='en').text
    
    # Process the English message
    words = message.lower().split()
    if any(word in words for word in ['search', 'find', 'order', 'track']):
        search_terms = ' '.join(word for word in words if word not in ['search', 'find', 'order', 'track'])
        results = search_orders(search_terms)
        
        if results:
            if len(results) == 1:
                response_text = f"Here are the details for order {results[0]['order_id']}:"                                         
                # Convert response to Hindi
                hindi_response = translator.translate(response_text, src='en', dest='hi').text
                bolo(hindi_response)
                return jsonify({
                    'success': True,
                    'response': {
                        'type': 'order',
                        'data': results[0],
                        'message': hindi_response
                    }
                })
            else:
                response_text = f"Found {len(results)} matching orders. Please be more specific or provide the exact order ID."
                hindi_response = translator.translate(response_text, src='en', dest='hi').text
                bolo(hindi_response)
                return jsonify({
                    'success': True,
                    'response': {
                        'type': 'text',
                        'message': hindi_response
                    }
                })
        else:
            response_text = "No matching orders found. Please try a different search term or order ID."
            hindi_response = translator.translate(response_text, src='en', dest='hi').text
            bolo(hindi_response)
            return jsonify({
                'success': True,
                'response': {
                    'type': 'text',
                    'message': hindi_response
                }
            })
    
    # Handle other types of messages
    response_text = "How can I help you? You can search for orders by typing 'search' followed by an order ID or customer name."
    hindi_response = translator.translate(response_text, src='en', dest='hi').text
    bolo(hindi_response)
    response = {
        'type': 'text',
        'message': hindi_response
    }
    
    return jsonify({
        'success': True,
        'response': response
    })

@app.route('/api/speech-to-text', methods=['POST'])
@login_required
def speech_to_text():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
        
    audio_file = request.files['audio']
    
    try:
        # Convert the audio file to WAV format
        with sr.AudioFile(audio_file) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source)
            # Record the audio from the source
            audio_data = recognizer.record(source)
            
            try:
                # Try using Google's speech recognition
                text = recognizer.recognize_google(audio_data)
                return jsonify({'text': text})
            except sr.UnknownValueError:
                return jsonify({'error': 'Could not understand audio'}), 400
            except sr.RequestError as e:
                return jsonify({'error': f'Error with speech recognition service: {str(e)}'}), 500
                
    except Exception as e:
        return jsonify({'error': f'Error processing audio: {str(e)}'}), 500

@app.route('/api/start-listening', methods=['POST'])
def start_listening():
    try:
        recognizer = sr.Recognizer()
        
        mics = sr.Microphone.list_microphone_names()
        if not mics:
            return jsonify({
                'success': False,
                'error': 'माइक्रोफ़ोन नहीं मिला'
                
            })

        with sr.Microphone() as source:
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.8
            
            print("Listening...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            
            try:
                print("Recognizing...")
                # Recognize Hindi speech only
                hindi_text = recognizer.recognize_google(audio, language='hi-IN')
                
                return jsonify({
                    'success': True,
                    'text': hindi_text  # Return only the Hindi text
                })
            except sr.UnknownValueError:
                return jsonify({
                    'success': False,
                    'error': 'आवाज़ समझ में नहीं आई। कृपया स्पष्ट रूप से बोलें और पुनः प्रयास करें।'
                    
                })
            except sr.RequestError as e:
                return jsonify({
                    'success': False,
                    'error': f'स्पीच सेवा में त्रुटि: {str(e)}'
                })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'माइक्रोफ़ोन त्रुटि: {str(e)}'
        })

    
def bolo(text):
    tts = gTTS(text=text, lang='hi')
    tts.save("response.mp3")
    os.system("start response.mp3")

if __name__ == '__main__':
    app.run(debug=True)