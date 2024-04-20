from flask import Flask, Response, render_template, request, redirect, url_for, session
import uuid
import os
import secrets;
from dotenv import load_dotenv
from utils.processor import Processor
from threading import Thread
import time
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex()
app.permanent_session_lifetime = timedelta(minutes=60)
login_manager = LoginManager()
login_manager.init_app(app)

processor = Processor()
processor.create_vector_embedding()

chat_histories = {}

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def generate_data(question, summary, log=False):
    answer, docs = processor.respond_to_query(question, summary=summary, stream=True, log=log)
    return answer

def save_history(session_id, question, summary):
    history = chat_histories[session_id]
    history["wait"] = True
    response_data = generate_data(question, summary)
    response_text = ''
    for chunk in response_data:
        response_text += chunk
    response_data.close()
    answer = response_text.strip()
    summary = processor.generate_chat_summary(question, answer, history["summary"])
    history["summary"] = summary
    history["wait"] = False
    print("Chat Histories -", chat_histories)


def clear_chat_history(timeout=3600):
    session_ids = list(chat_histories.keys())
    # print("Session IDs -", session_ids)
    current_time = time.time()
    for session_id in session_ids:
        last_message_time = chat_histories[session_id]["time"]
        if current_time-last_message_time > timeout:
            del chat_histories[session_id]

scheduler = BackgroundScheduler()
scheduler.add_job(func=clear_chat_history, trigger="interval", seconds=60)
scheduler.start()

@app.route('/')
def index():
    # Generate a unique session ID for this session
    session_id = str(uuid.uuid4())

    # Create a new chat history for this session
    chat_histories[session_id] = {"summary": "", "wait": False, "time": time.time()}
    return render_template('chat_app.html', session_id=session_id)

@app.route('/stream_data', methods = ["POST"])
def stream_data():
    data = request.get_json(force=True)
    question = data["question"]
    session_id = data["session_id"]

    if session_id not in chat_histories:
        chat_histories[session_id] = {"summary": "", "wait": False, "time": time.time()}

    history = chat_histories[session_id]
    history["time"] = time.time()
    while history["wait"]:
        print("Waiting for summary to complete....")
        time.sleep(1)
    
    summary = history["summary"]

    processing_thread = Thread(target=save_history, args=(session_id, question, summary))
    processing_thread.start()
    return Response(generate_data(question, summary, log=True), content_type='text/event-stream')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        username = data["email"].lower()
        password = data["pass"]
        if username==USERNAME and password==PASSWORD:
            user = User(username)
            login_user(user)
            session.permanent = True
            return redirect(url_for('add_to_kb'))
        else:
            return render_template("login.html", info_text="Wrong Email/Password Entered. Please try again with correct credentials.")
    return render_template("login.html", info_text="")
    
@app.route('/add_to_kb', methods=["GET", "POST"])
@login_required
def add_to_kb():
    if request.method == "GET":
        return render_template("add_to_kb.html", info_text="")
    try:
        data = request.form
        question = data["question"]
        answer = data["answer"]
        processor.add_new_qa(question, answer)
        return render_template("add_to_kb.html", info_text="Question-Answer added to knowledge base.")
    except Exception as e:
        return render_template("add_to_kb.html", info_text="Error encountered while trying to add to knowledge base - " + e)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(port=5001)
