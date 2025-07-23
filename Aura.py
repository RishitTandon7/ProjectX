import requests
import speech_recognition as sr
import pyttsx3
import json
import os
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
import geocoder
import datetime
import cv2
import ollama
import webbrowser
import subprocess
import platform
import time
import math
import random
import psutil
import socket
import webbrowser
import feedparser

# Emergency contacts dictionary
contacts_dict = {}

# Notes and To-Do List storage
notes = []
todos = []

# Initialize Text to Speech Engine with Female Voice (Windows)
engine = pyttsx3.init()

# Set the voice to female (index 1 in Windows is usually female)
engine.setProperty('voice', engine.getProperty('voices')[1].id)  # Female voice
engine.setProperty('rate', 190)  # Set the speech rate (optional)

# Function to speak text
def speak(text):
    print(f"Aura says: {text}")  # Debugging: Print what Aura says
    engine.say(text)
    engine.runAndWait()

# Function to listen to user input
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)  # Adjust for ambient noise
        speak("I am listening now.")
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=7)
        except sr.WaitTimeoutError:
            speak("Listening timed out, please try again.")
            return None
    try:
        speak("Recognizing your speech.")
        print("Recognizing...")
        return recognizer.recognize_google(audio).lower()  # Make the input lowercase for comparison
    except sr.UnknownValueError:
        speak("Sorry, I didn't catch that.")
        return None
    except sr.RequestError:
        speak("Sorry, I am having trouble connecting to the service.")
        return None

# Function to greet the user based on the time of the day
def greet_user():
    current_hour = datetime.datetime.now().hour
    greetings = []
    if current_hour < 12:
        greetings = [
            "Good morning! How can I assist you today?",
            "Top of the morning to you! What can I do for you?",
            "Morning! Ready to help you."
        ]
    elif current_hour < 18:
        greetings = [
            "Good afternoon! How can I assist you today?",
            "Hope you're having a great afternoon! How can I help?",
            "Afternoon! What can I do for you?"
        ]
    else:
        greetings = [
            "Good evening! How can I assist you today?",
            "Evening! How may I help you tonight?",
            "Good evening! Ready to assist you."
        ]
    speak(random.choice(greetings))

# Function to fetch weather info
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?appid={WEATHER_API_KEY}&q={city}"
    response = requests.get(url)
    data = response.json()

    if data.get("cod") != 200:
        speak("Sorry, I couldn't retrieve weather information.")
        return None

    main = data["main"]
    weather = data["weather"][0]
    temp = main["temp"] - 273.15  # Convert Kelvin to Celsius
    description = weather["description"]

    return f"The temperature in {city} is {temp:.1f}°C with {description}."

# Function to query Gemini API
def query_gemini_api(query):
    data = {
        "contents": [{
            "parts": [{ "text": query }]
        }]
    }
    response = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}", json=data)
    if response.status_code == 200:
        result = response.json()
        content = result.get("result", {}).get("content", [])
        if content:
            return content[0]["parts"][0]["text"]
        return "Sorry, I couldn't retrieve the information."
    else:
        return "Sorry, there was an error querying the Gemini API."

# Function to detect object in image using Ollama Vision
def detect_object_in_image(image_path):
    response = ollama.chat(
        model="llama3.2-vision",
        messages=[{
            "role": "user",
            "content": "What is in this image?",
            "images": [image_path]
        }]
    )
    return response

# Function to send SOS message using Twilio
def send_sos_message():
    # Get current location (just an example)
    g = geocoder.ip('me')
    location = g.latlng

    if location:
        lat, lng = location
        message = f"Emergency! Please help. My location is: https://maps.google.com/?q={lat},{lng}"
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            to=f"whatsapp:{USER_WHATSAPP_NUMBER}",
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=message
        )
        speak("SOS message sent.")
    else:
        speak("Could not get your location. SOS message not sent.")

# Function to detect face in image using OpenCV
def detect_face_in_image(image_path):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    if len(faces) == 0:
        return "No faces detected."
    else:
        return f"Detected {len(faces)} face(s)."

# Function to send email
def send_email(recipient, subject, body):
    msg = MIMEText(body)
    msg['From'] = GMAIL_USER
    msg['To'] = recipient
    msg['Subject'] = subject

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, recipient, msg.as_string())
        server.quit()
        speak(f"Email sent to {recipient}")
    except Exception as e:
        speak(f"Failed to send email. Error: {e}")

# Function to store and recall contacts in a dictionary
def store_contact(name, phone_number):
    contacts_dict[name] = phone_number
    speak(f"Contact {name} has been saved.")

def send_message_to_contact(name, message):
    if name in contacts_dict:
        contact_number = contacts_dict[name]
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            to=f"whatsapp:{contact_number}",
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=message
        )
        speak(f"Message sent to {name}.")
    else:
        speak(f"No contact found for {name}.")

# Alarm & Reminders
alarms = []

def set_alarm(time_str):
    try:
        alarm_time = datetime.datetime.strptime(time_str, "%H:%M")
        alarms.append(alarm_time)
        speak(f"Alarm set for {time_str}")
    except ValueError:
        speak("Invalid time format. Please say the time as HH colon MM.")

def check_alarms():
    now = datetime.datetime.now()
    for alarm_time in alarms:
        if now.hour == alarm_time.hour and now.minute == alarm_time.minute:
            speak("Alarm ringing!")
            alarms.remove(alarm_time)

# Notes & To-Do List
def add_note(note):
    notes.append(note)
    speak("Note added.")

def list_notes():
    if notes:
        speak("Here are your notes:")
        for note in notes:
            speak(note)
    else:
        speak("You have no notes.")

def add_todo(todo):
    todos.append(todo)
    speak("To-do item added.")

def list_todos():
    if todos:
        speak("Here are your to-do items:")
        for todo in todos:
            speak(todo)
    else:
        speak("You have no to-do items.")

# File Search & Open
def search_files(filename, search_path='.'):
    matches = []
    for root, dirs, files in os.walk(search_path):
        for file in files:
            if filename.lower() in file.lower():
                matches.append(os.path.join(root, file))
    return matches

def open_file(filepath):
    if platform.system() == "Windows":
        os.startfile(filepath)
    elif platform.system() == "Darwin":
        subprocess.call(["open", filepath])
    else:
        subprocess.call(["xdg-open", filepath])
    speak(f"Opened file {filepath}")

# Send SMS
def send_sms(phone_number, message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            to=phone_number,
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message
        )
        speak(f"SMS sent to {phone_number}")
    except Exception as e:
        speak(f"Failed to send SMS. Error: {e}")

# Calculator
def calculate(expression):
    try:
        # Safe eval: only allow digits, operators, parentheses, decimal points
        allowed_chars = "0123456789+-*/(). "
        if any(c not in allowed_chars for c in expression):
            speak("Invalid characters in expression.")
            return
        result = eval(expression)
        speak(f"The result is {result}")
    except Exception as e:
        speak(f"Error calculating expression: {e}")

# Unit & Currency Converter (simple examples)
def convert_units(value, from_unit, to_unit):
    # Example: length units (meters to feet)
    conversions = {
        ("meters", "feet"): 3.28084,
        ("feet", "meters"): 0.3048,
        ("kilograms", "pounds"): 2.20462,
        ("pounds", "kilograms"): 0.453592,
    }
    key = (from_unit.lower(), to_unit.lower())
    if key in conversions:
        converted = value * conversions[key]
        speak(f"{value} {from_unit} is {converted:.2f} {to_unit}")
    else:
        speak("Conversion not supported.")

def convert_currency(amount, from_currency, to_currency):
    # Use a free API for currency conversion
    url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
    response = requests.get(url)
    if response.status_code != 200:
        speak("Failed to get currency conversion rates.")
        return
    data = response.json()
    rates = data.get("rates", {})
    rate = rates.get(to_currency.upper())
    if rate:
        converted = amount * rate
        speak(f"{amount} {from_currency} is {converted:.2f} {to_currency}")
    else:
        speak("Currency not supported.")

# Dictionary & Translation
def translate_text(text, target_language):
    # Use Google Translate API or similar
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target_language,
        "dt": "t",
        "q": text,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        try:
            translation = response.json()[0][0][0]
            speak(f"Translation: {translation}")
        except Exception:
            speak("Failed to parse translation response.")
    else:
        speak("Translation service failed.")

# Open Applications
def open_application(app_name):
    app_name = app_name.lower()
    try:
        if "chrome" in app_name:
            webbrowser.open("https://www.google.com/chrome/")
            speak("Opening Google Chrome.")
        elif "youtube" in app_name:
            webbrowser.open("https://www.youtube.com")
            speak("Opening YouTube.")
        elif "notepad" in app_name:
            if platform.system() == "Windows":
                subprocess.Popen(["notepad.exe"])
                speak("Opening Notepad.")
            else:
                speak("Notepad is not supported on this OS.")
        else:
            speak(f"Application {app_name} is not supported.")
    except Exception as e:
        speak(f"Failed to open application. Error: {e}")

# Control Volume, Brightness
def control_volume(action):
    try:
        if platform.system() == "Windows":
            import ctypes
            devices = ctypes.windll.winmm.waveOutGetNumDevs()
            # For simplicity, just speak the action
            speak(f"Volume control action: {action}")
        else:
            speak("Volume control not supported on this OS.")
    except Exception as e:
        speak(f"Failed to control volume. Error: {e}")

def control_brightness(action):
    try:
        if platform.system() == "Windows":
            # Windows brightness control requires additional packages or WMI calls
            speak(f"Brightness control action: {action}")
        else:
            speak("Brightness control not supported on this OS.")
    except Exception as e:
        speak(f"Failed to control brightness. Error: {e}")

# System Shutdown, Restart, Lock
def system_shutdown():
    try:
        if platform.system() == "Windows":
            os.system("shutdown /s /t 1")
        elif platform.system() == "Linux" or platform.system() == "Darwin":
            os.system("shutdown now")
        speak("System is shutting down.")
    except Exception as e:
        speak(f"Failed to shutdown system. Error: {e}")

def system_restart():
    try:
        if platform.system() == "Windows":
            os.system("shutdown /r /t 1")
        elif platform.system() == "Linux" or platform.system() == "Darwin":
            os.system("reboot")
        speak("System is restarting.")
    except Exception as e:
        speak(f"Failed to restart system. Error: {e}")

def system_lock():
    try:
        if platform.system() == "Windows":
            ctypes.windll.user32.LockWorkStation()
        else:
            speak("System lock not supported on this OS.")
    except Exception as e:
        speak(f"Failed to lock system. Error: {e}")

# Read Notifications (placeholder)
def read_notifications():
    # Platform dependent, complex to implement here
    speak("Reading notifications is not supported yet.")

# Play Music (Local or YouTube)
def play_music(source):
    if source == "local":
        music_folder = os.path.expanduser("~/Music")
        if os.path.exists(music_folder):
            files = [f for f in os.listdir(music_folder) if f.endswith(('.mp3', '.wav'))]
            if files:
                file_to_play = os.path.join(music_folder, random.choice(files))
                if platform.system() == "Windows":
                    os.startfile(file_to_play)
                else:
                    subprocess.call(["open", file_to_play])
                speak(f"Playing {file_to_play}")
            else:
                speak("No music files found in your Music folder.")
        else:
            speak("Music folder not found.")
    elif source == "youtube":
        speak("Opening YouTube Music.")
        webbrowser.open("https://music.youtube.com")
    else:
        speak("Unknown music source.")

# Tell Jokes or Stories
jokes = [
    "Why don't scientists trust atoms? Because they make up everything.",
    "Why did the scarecrow win an award? Because he was outstanding in his field.",
    "I told my computer I needed a break, and it said no problem — it needed one too."
]

stories = [
    "Once upon a time, in a land far away, there was a brave knight who fought dragons.",
    "There was a little girl who loved to explore the forest near her home.",
    "In a small village, a mysterious stranger arrived with a secret."
]

def tell_joke():
    joke = random.choice(jokes)
    speak(joke)

def tell_story():
    story = random.choice(stories)
    speak(story)

# Movie/Book Recommendations
def recommend_movie():
    movies = ["Inception", "The Matrix", "Interstellar", "The Shawshank Redemption"]
    movie = random.choice(movies)
    speak(f"I recommend watching {movie}.")

def recommend_book():
    books = ["1984 by George Orwell", "To Kill a Mockingbird by Harper Lee", "The Great Gatsby by F. Scott Fitzgerald"]
    book = random.choice(books)
    speak(f"I recommend reading {book}.")

# Health Tips
health_tips = [
    "Drink plenty of water every day.",
    "Exercise regularly to stay healthy.",
    "Get at least 7 to 8 hours of sleep every night.",
    "Eat a balanced diet with fruits and vegetables."
]

def give_health_tip():
    tip = random.choice(health_tips)
    speak(tip)

# Llama-based Conversations (using ollama)
def llama_conversation(prompt):
    response = ollama.chat(
        model="llama3.2-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return response

# Main function to interact with user


import json

# Conversation memory to store recent interactions
conversation_memory = []

CONVERSATION_HISTORY_FILE = "conversation_history.json"

def load_conversation_history():
    global conversation_memory
    try:
        with open(CONVERSATION_HISTORY_FILE, "r", encoding="utf-8") as f:
            conversation_memory = json.load(f)
    except FileNotFoundError:
        conversation_memory = []
    except Exception as e:
        print(f"Error loading conversation history: {e}")
        conversation_memory = []

def save_conversation_history():
    try:
        with open(CONVERSATION_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(conversation_memory, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving conversation history: {e}")

def add_to_memory(user_input, assistant_response):
    conversation_memory.append({"user": user_input, "assistant": assistant_response})
    # Keep memory size limited
    if len(conversation_memory) > 50:
        conversation_memory.pop(0)
    save_conversation_history()

def voice_web_search(query):
    # Simple web search using default search engine
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(search_url)
    speak(f"Here are the search results for {query}")

# Load conversation history at startup
load_conversation_history()

def open_website(url):
    if not url.startswith("http"):
        url = "http://" + url
    webbrowser.open(url)
    speak(f"Opening {url}")

def get_news_headlines():
    # Example RSS feed for news
    feed_url = "http://feeds.bbci.co.uk/news/rss.xml"
    feed = feedparser.parse(feed_url)
    headlines = []
    for entry in feed.entries[:5]:
        headlines.append(entry.title)
    return headlines

def read_news():
    headlines = get_news_headlines()
    if headlines:
        speak("Here are the latest news headlines:")
        for headline in headlines:
            speak(headline)
    else:
        speak("Sorry, I couldn't fetch the news right now.")

def main():
    greet_user()
    
    while True:
        check_alarms()
        print("Listening for your command...")
        query = listen()

        if query and 'aura' in query:  # Only trigger if 'aura' is in the command
            print(f"You asked: {query}")

            # Add to conversation memory
            add_to_memory(query, "")

            if 'weather' in query:
                city = query.split('in')[-1].strip()
                weather_info = get_weather(city)
                speak(weather_info)
                add_to_memory(query, weather_info)

            elif 'sos' in query:
                speak("Sending emergency message.")
                send_sos_message()
                add_to_memory(query, "SOS message sent.")

            elif 'object detection' in query or 'image search' in query:
                speak("Please show me the image.")
                image_path = 'captured_image.jpg'  # Placeholder, this should be an image capture code
                speak("What do you want to know about this image?")
                additional_query = listen()
                if additional_query:
                    response = detect_object_in_image(image_path)
                    speak(f"Here is the analysis: {response}")
                    add_to_memory(query, response)
                else:
                    speak("No query received for image.")
                    add_to_memory(query, "No query received for image.")

            elif 'face detection' in query:
                speak("Please show me the image for face detection.")
                image_path = 'captured_image.jpg'  # Placeholder, this should be an image capture code
                response = detect_face_in_image(image_path)
                speak(response)
                add_to_memory(query, response)

            elif 'search' in query:
                speak("What would you like to search for?")
                search_query = listen()
                if search_query:
                    response = query_gemini_api(search_query)
                    speak(f"Here is what I found: {response}")
                    add_to_memory(search_query, response)
                else:
                    speak("No search query received.")
                    add_to_memory(search_query, "No search query received.")

            elif 'voice search' in query or 'web search' in query:
                speak("What do you want to search for on the web?")
                search_term = listen()
                if search_term:
                    voice_web_search(search_term)
                    add_to_memory(search_term, "Performed web search.")
                else:
                    speak("No search term received.")
                    add_to_memory(search_term, "No search term received.")

            elif 'open website' in query:
                speak("Please tell me the website URL.")
                url = listen()
                if url:
                    open_website(url)
                    add_to_memory(url, f"Opened website {url}")
                else:
                    speak("No URL received.")
                    add_to_memory(url, "No URL received.")

            elif 'news' in query or 'headlines' in query:
                read_news()
                add_to_memory(query, "Read news headlines.")

            elif 'save contact' in query:
                speak("Please tell me the name and phone number of the contact.")
                contact_info = listen()
                if contact_info:
                    try:
                        name, phone_number = contact_info.split(' ')  # Simple split, you may need more complex parsing
                        store_contact(name, phone_number)
                        add_to_memory(contact_info, f"Saved contact {name}")
                    except Exception:
                        speak("Failed to save contact. Please say name and phone number separated by space.")
                        add_to_memory(contact_info, "Failed to save contact.")

            elif 'send message to' in query:
                speak("Please tell me the name of the contact and the message.")
                message_info = listen()
                if message_info:
                    try:
                        name, message = message_info.split(' ', 1)
                        send_message_to_contact(name, message)
                        add_to_memory(message_info, f"Sent message to {name}")
                    except Exception:
                        speak("Failed to send message. Please say the contact name followed by the message.")
                        add_to_memory(message_info, "Failed to send message.")

            elif 'set alarm' in query:
                speak("Please tell me the time for the alarm in HH colon MM format.")
                time_str = listen()
                if time_str:
                    set_alarm(time_str)
                    add_to_memory(time_str, f"Set alarm for {time_str}")

            elif 'add note' in query:
                speak("Please tell me the note.")
                note = listen()
                if note:
                    add_note(note)
                    add_to_memory(note, "Added note.")

            elif 'list notes' in query:
                list_notes()
                add_to_memory(query, "Listed notes.")

            elif 'add to-do' in query or 'add todo' in query:
                speak("Please tell me the to-do item.")
                todo = listen()
                if todo:
                    add_todo(todo)
                    add_to_memory(todo, "Added to-do item.")

            elif 'list to-do' in query or 'list todo' in query:
                list_todos()
                add_to_memory(query, "Listed to-do items.")

            elif 'search file' in query:
                speak("Please tell me the filename to search for.")
                filename = listen()
                if filename:
                    matches = search_files(filename)
                    if matches:
                        speak(f"Found {len(matches)} files. Opening the first one.")
                        open_file(matches[0])
                        add_to_memory(filename, f"Opened file {matches[0]}")
                    else:
                        speak("No files found matching that name.")
                        add_to_memory(filename, "No files found.")

            elif 'send sms' in query:
                speak("Please tell me the phone number and message.")
                sms_info = listen()
                if sms_info:
                    try:
                        phone_number, message = sms_info.split(' ', 1)
                        send_sms(phone_number, message)
                        add_to_memory(sms_info, f"Sent SMS to {phone_number}")
                    except Exception:
                        speak("Failed to send SMS. Please say the phone number followed by the message.")
                        add_to_memory(sms_info, "Failed to send SMS.")

            elif 'calculate' in query:
                speak("Please tell me the expression to calculate.")
                expression = listen()
                if expression:
                    calculate(expression)
                    add_to_memory(expression, "Calculated expression.")

            elif 'convert unit' in query:
                speak("Please tell me the value, from unit, and to unit separated by spaces.")
                conversion_info = listen()
                if conversion_info:
                    try:
                        value_str, from_unit, to_unit = conversion_info.split(' ')
                        value = float(value_str)
                        convert_units(value, from_unit, to_unit)
                        add_to_memory(conversion_info, "Converted units.")
                    except Exception:
                        speak("Failed to convert units. Please say value, from unit, and to unit separated by spaces.")
                        add_to_memory(conversion_info, "Failed to convert units.")

            elif 'convert currency' in query:
                speak("Please tell me the amount, from currency, and to currency separated by spaces.")
                conversion_info = listen()
                if conversion_info:
                    try:
                        amount_str, from_currency, to_currency = conversion_info.split(' ')
                        amount = float(amount_str)
                        convert_currency(amount, from_currency, to_currency)
                        add_to_memory(conversion_info, "Converted currency.")
                    except Exception:
                        speak("Failed to convert currency. Please say amount, from currency, and to currency separated by spaces.")
                        add_to_memory(conversion_info, "Failed to convert currency.")

            elif 'translate' in query:
                speak("Please tell me the text to translate.")
                text = listen()
                if text:
                    speak("Please tell me the target language code (e.g., en, es, fr).")
                    target_language = listen()
                    if target_language:
                        translate_text(text, target_language)
                        add_to_memory(text, f"Translated text to {target_language}")

            elif 'open application' in query:
                speak("Please tell me the application name.")
                app_name = listen()
                if app_name:
                    open_application(app_name)
                    add_to_memory(app_name, f"Opened application {app_name}")

            elif 'volume up' in query:
                control_volume("up")
                add_to_memory(query, "Volume up")

            elif 'volume down' in query:
                control_volume("down")
                add_to_memory(query, "Volume down")

            elif 'brightness up' in query:
                control_brightness("up")
                add_to_memory(query, "Brightness up")

            elif 'brightness down' in query:
                control_brightness("down")
                add_to_memory(query, "Brightness down")

            elif 'shutdown' in query:
                system_shutdown()
                add_to_memory(query, "System shutdown")

            elif 'restart' in query:
                system_restart()
                add_to_memory(query, "System restart")

            elif 'lock' in query:
                system_lock()
                add_to_memory(query, "System lock")

            elif 'read notifications' in query:
                read_notifications()
                add_to_memory(query, "Read notifications")

            elif 'play music' in query:
                if 'local' in query:
                    play_music("local")
                    add_to_memory(query, "Play local music")
                elif 'youtube' in query:
                    play_music("youtube")
                    add_to_memory(query, "Play YouTube music")
                else:
                    speak("Please specify local or YouTube music.")
                    add_to_memory(query, "Music source not specified")

            elif 'tell joke' in query:
                tell_joke()
                add_to_memory(query, "Told joke")

            elif 'tell story' in query:
                tell_story()
                add_to_memory(query, "Told story")

            elif 'recommend movie' in query:
                recommend_movie()
                add_to_memory(query, "Recommended movie")

            elif 'recommend book' in query:
                recommend_book()
                add_to_memory(query, "Recommended book")

            elif 'health tip' in query:
                give_health_tip()
                add_to_memory(query, "Gave health tip")

            elif 'llama' in query or 'chat' in query:
                speak("What would you like to talk about?")
                prompt = listen()
                if prompt:
                    response = llama_conversation(prompt)
                    speak(response)
                    add_to_memory(prompt, response)

            elif 'exit' in query:
                speak("Goodbye!")
                break

GEMINI_API_KEY = "AIzaSyCH4e3uW1SuQXUY7DaNAzrURAo88XMutzo"
WEATHER_API_KEY =  "caee82e8e463de3e8f49dd36df54db44"
TWILIO_ACCOUNT_SID = "AC5d73acabe916a4e4ebce286317dccb09"
TWILIO_AUTH_TOKEN = "525a40d253983dcad7df16fa3a15efbd"
TWILIO_WHATSAPP_NUMBER = "+1415523888"
USER_WHATSAPP_NUMBER = "525a40d253983dcad7df16fa3a15efbd"
GMAIL_USER = "rt5136@srmist.edu.in"
GMAIL_PASSWORD = "Prokingxtopia.7"

if __name__ == "__main__":
    main()


