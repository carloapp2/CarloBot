from flask import Flask, Response, render_template, request, redirect, url_for, session
import uuid
import os
import secrets;
from dotenv import load_dotenv
from utils.processor import Processor
from threading import Thread
import time
import pandas as pd
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
BOTNAME = os.getenv("BOTNAME")
FULLNAME = os.getenv("FULLNAME")

logs_file = "assistant_logs.csv"

with open("default_questions.txt", "r") as f:
    default_questions = f.read().split("\n")

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def generate_answer(question, summary, log=False):
    rephrased_ques, answer, docs = processor.respond_to_query(question, summary=summary, stream=True, log=log)
    return rephrased_ques, answer

def save_history(session_id, question, summary, qa_id):
    history = chat_histories[session_id]
    history["wait"] = True
    rephrased_ques, response_data = generate_answer(question, summary)
    response_text = ''
    for chunk in response_data:
        response_text += chunk
    response_data.close()
    answer = response_text.strip()
    summary = processor.generate_chat_summary(question, answer, history["summary"])
    history["summary"] = summary
    history["wait"] = False
    save_chats(session_id, qa_id, question, rephrased_ques, answer, summary)
    print("Chat Histories -", chat_histories)

def save_chats(session_id, qa_id, question, rephrased_ques, answer, summary):
    if os.path.exists(logs_file):
        df = pd.read_csv(logs_file)
    else:
        df = pd.DataFrame()
    row = pd.DataFrame({'session_id': [session_id], 'qa_id': qa_id, 'question': [question], 'rephrased_question': [rephrased_ques], 
                        'answer': [answer], 'summary': [summary], 'feedback': ['']})
    df = pd.concat([df,row])
    df.to_csv(logs_file, index=False)

def save_feedback(qa_id, feedback):
    df = pd.read_csv(logs_file)
    df = df.fillna("")
    df.loc[df['qa_id']==qa_id, 'feedback'] = feedback
    df.to_csv(logs_file, index=False)

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
    return render_template('chat_app.html', session_id=session_id, botname=BOTNAME, fullname=FULLNAME, default_questions=default_questions)

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
    qa_id = str(uuid.uuid4())
    processing_thread = Thread(target=save_history, args=(session_id, question, summary, qa_id))
    processing_thread.start()
    _, answer = generate_answer(question, summary, log=True)
    return Response(answer, content_type='text/event-stream'), qa_id

@app.route('/feedback', methods = ["POST"])
def get_feedback():
    data = request.get_json(force=True)
    print(data)
    session_id = data["session_id"]
    qa_id = data["qa_id"]
    feedback = data["feedback"]

    history = chat_histories[session_id]
    history["time"] = time.time()
    while history["wait"]:
        print("Waiting for summary to complete....")
        time.sleep(1)

    save_feedback(qa_id, feedback)
    return '', 204

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
