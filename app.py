from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import speech_recognition as sr
from flask_login import LoginManager, current_user
from flask_mail import Mail, Message
from config import Config


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db' 
app.config['SECRET_KEY'] = 'NHS76T66^G45#2@H()[-PXX ]XS!!@#$ONC626ssj55a'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
app.config.from_object(Config)
mail = Mail(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer)
    sex = db.Column(db.String(10))
    scores = db.relationship('Score', backref='user', lazy=True)
    reset_token = db.Column(db.String(100))  # Add the reset_token field

    def __repr__(self):
        return '<User %r>' % self.username



# Define the Score model
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_number = db.Column(db.Integer, nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Float, nullable=False)
    test_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return '<Score %r>' % self.score

# Home page
@app.route('/')
def index():
    return render_template('index.html')


# Registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        age = request.form['age']
        sex = request.form['sex']

        hashed_password = generate_password_hash(password)

        user = User(username=username, email=email, password=hashed_password, age=age, sex=sex)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')

        return redirect(url_for('login'))
    return render_template('register.html')


# Login page
# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Set the user as authenticated
            flash('Login successful!', 'success')
            if user.username == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('select_test'))  # Redirect to test selection page
        else:
            flash( 'Invalid username or password', 'info')
            return render_template('login.html')

    return render_template('login.html')

import secrets

# Password reset page
# Password reset page
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']

        user = User.query.filter_by(email=email).first()

        if user:
            # Generate a password reset token
            token = secrets.token_urlsafe(32)  # Generate a secure and random URL-safe token

            # Save the token in the user's database record
            user.reset_token = token
            db.session.commit()

            reset_link = url_for('reset_password_confirm', token=token, _external=True)
            message = f"Click the link below to reset your password:\n{reset_link}"

            msg = Message("Password Reset Request", recipients=[user.email])
            msg.body = message

            mail.send(msg)  # Send the password reset email

            flash('A password reset link has been sent to your email.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid email address.', 'info')
            return redirect(url_for('reset_password'))

    return render_template('reset_password.html')

from werkzeug.security import generate_password_hash


# Password reset confirmation page
@app.route('/reset_password_confirm/<token>', methods=['GET', 'POST'])
def reset_password_confirm(token):
    # Verify the token
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password == confirm_password:
            # Update the user's password in the database
            user.password = generate_password_hash(new_password)
            user.reset_token = None  # Reset the token after password change
            db.session.commit()

            flash('Password has been reset successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match.', 'danger')

    return render_template('reset_password_confirm.html', token=token)

# Test selection page
@app.route('/select_test')
def select_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('select_test.html')



# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# Test selection page
@app.route('/tests/<int:test_number>/<int:round_number>',methods=['GET', 'POST'])
def tests(test_number, round_number):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Load the target words for each test (you may need to define the target words for each test separately)
    target_words = {
        1:['تراکتور','هویج','قناری','موکت','سیر','دوچرخه','یخچال','ببر','اتوبوس','میز','فلفل','گوریل','پرده','پارو','سوسمار','فیلم'],
        2:[ 'لودر','گوجه','شتر','بخاری','ریحان','وانت','فریزر','گربه','مینی بوس','تخته','جعفری','گوسفند','پنجره','ویلچر','کلاغ','نعنا'],
        3:['فرش','قطار','خیار','طوطی','کدو','هواپیما','اجاق','موش','ماشین','صندلی','کاهو','میمون','کمد','موتور','فیل','پیاز'],

        4:['مترو','کامیون','اسفناج','زرافه','کمد','پیاز','موتور','کابینت','گورخر','چراغ','کرفس','گاو','مبل','قایق','سنجاب','کلم']

    }
   
        
    #audio_file = f'test{test_number}.m4a'  #
    
    return render_template('tests.html', target_words=target_words, round_number=round_number,test_number=test_number)


# Test page (record and transcribe)
import os
from pydub import AudioSegment

@app.route('/record', methods=['POST'])
def record():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get the user's input from the request
    test_number = int(request.form.get('test_number'))
    round_number = int(request.form.get('round_number'))

    audio = request.files['audio']
    audio_format = audio.filename.split('.')[-1]

    # Construct the file path to save the audio file
    username = current_user.username
    save_directory = os.path.join('voices', username, 'offline')
    os.makedirs(save_directory, exist_ok=True)
    save_path = os.path.join(save_directory, audio.filename)

    # Save the audio file to the specified path
    audio.save(save_path)

    # Convert to PCM WAV if necessary
    if audio_format == 'm4a' or audio_format == 'mp3':
        audio_content = AudioSegment.from_file(save_path, format=audio_format)
        audio_content = audio_content.set_frame_rate(16000).set_channels(1)
        wav_save_path = os.path.splitext(save_path)[0] + '.wav'
        audio_content.export(wav_save_path, format='wav')

        # Update the save_path variable to point to the WAV file
        save_path = wav_save_path

    # Perform speech recognition on the saved audio file
    recognizer = sr.Recognizer()
    audio_data = sr.AudioFile(save_path)
    text = ""
    try:
        with audio_data as source:
            audio_content = recognizer.record(source)
            results = recognizer.recognize_google(audio_content, language="fa-IR", show_all=True)
            if len(results) > 0:
                text = [alt["transcript"] for alt in results["alternative"]]
                text = " ".join(text)
    except sr.UnknownValueError:
        flash('Could not transcribe the audio. Please try again.', 'error')
        return redirect(url_for('tests', round_number=round_number, test_number=test_number))

    # Split the transcribed text into words
    words = text.split()
    words = set(words)

    # Load the target words for the current test
    target_words = {
        1: ['تراکتور', 'هویج', 'قناری', 'موکت', 'سیر', 'دوچرخه', 'یخچال', 'ببر', 'اتوبوس', 'میز', 'فلفل', 'گوریل',
            'پرده', 'پارو', 'سوسمار', 'فیلم'],
        2: ['لودر', 'گوجه', 'شتر', 'بخاری', 'ریحان', 'وانت', 'فریزر', 'گربه', 'مینی بوس', 'تخته', 'جعفری', 'گوسفند',
            'پنجره', 'ویلچر', 'کلاغ', 'نعنا'],
        3: ['فرش', 'قطار', 'خیار', 'طوطی', 'کدو', 'هواپیما', 'اجاق', 'موش', 'ماشین', 'صندلی', 'کاهو', 'میمون', 'کمد', 'موتور',
            'فیل', 'پیاز'],
        4: ['مترو', 'کامیون', 'اسفناج', 'زرافه', 'کمد', 'پیاز', 'موتور', 'کابینت', 'گورخر', 'چراغ', 'کرفس', 'گاو', 'مبل', 'قایق',
            'سنجاب', 'کلم']
    }

    # Compare the transcribed words with the target words and calculate the score
    score = 0
    for word in words:
        if word in target_words[test_number]:
            score += 1

    # Check if a score entry already exists for this user, test, and round
    user_id = session['user_id']
    score_entry = Score.query.filter_by(user_id=user_id, test_number=test_number, round_number=round_number).first()

    if score_entry:
        # Update the existing score entry
        score_entry.score = score
        score_entry.test_time = datetime.now()
        db.session.commit()
    else:
        # Create a new score entry
        score_entry = Score(user_id=user_id, test_number=test_number, round_number=round_number, score=score,
                            test_time=datetime.now())
        db.session.add(score_entry)
        db.session.commit()

    # Prepare the data to be displayed on the next page
    transcribed_words = ', '.join(words)
    total_words = len(words)
    correct_words = score
    incorrect_words = 16 - correct_words

    # Check if all four rounds are completed and redirect to the tests page or profile page
    if round_number == 4:
        flash('You have completed all four rounds!', 'success')
    return render_template('next_round.html', test_number=test_number, round_number=round_number,
                           transcribed_words=transcribed_words, total_words=total_words,
                           correct_words=correct_words, incorrect_words=incorrect_words)

# User profile page
@app.route('/profile')
def profile():
    user_id = session['user_id']
    user = User.query.filter_by(id=user_id).first()
    scores = Score.query.filter_by(user_id=user_id).all()

    # Check if the user has completed all four rounds in a row for each test
    test_numbers = set(score.test_number for score in scores)
    approved_tests = set()
    for test_number in test_numbers:
        test_scores = [score for score in scores if score.test_number == test_number]
        rounds = [score.round_number for score in test_scores]
        if set(range(1, 5)) == set(rounds):
            # Check if the test time in each subsequent round is smaller than the previous round
            time_check = all(test_scores[i].test_time < test_scores[i+1].test_time for i in range(3))
            if time_check:
                approved_tests.add(test_number)

    # Calculate total score for each approved test
    total_scores = {}
    for test_number in approved_tests:
        total_score = sum(score.score for score in scores if score.test_number == test_number)
        total_scores[test_number] = total_score

    return render_template('profile.html', user=user, scores=scores, approved_tests=approved_tests, total_scores=total_scores)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.username != 'admin':
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('index'))

    # Handle filters
    filter_username = request.args.get('username')
    filter_test_number = request.args.get('test_number')

    # Get user options for dropdown
    user_options = [(u.username, u.username) for u in User.query.all()]

    # Query scores based on filters
    scores_query = Score.query
    if filter_username:
        user = User.query.filter_by(username=filter_username).first()
        if not user:
            flash(f'User {filter_username} not found.', 'error')
            return redirect(url_for('admin'))
        scores_query = scores_query.filter_by(user_id=user.id)
    if filter_test_number:
        scores_query = scores_query.filter(Score.test_number == int(filter_test_number))
    scores = scores_query.all()

    # Calculate approved tests and total scores for each test
    approved_tests = set()
    total_scores = {}
    for score in scores:
        test_number = score.test_number
        if test_number in approved_tests:
            continue
        test_scores = Score.query.filter_by(user_id=score.user_id, test_number=test_number).all()
        rounds = [s.round_number for s in test_scores]
        if set(range(1, 5)) == set(rounds):
            time_check = all(test_scores[i].test_time < test_scores[i+1].test_time for i in range(3))
            if time_check:
                approved_tests.add(test_number)
                if len(test_scores) == 4 and test_scores[0].test_time < test_scores[1].test_time < test_scores[2].test_time < test_scores[3].test_time:
                    total_scores[test_number] = sum(s.score for s in test_scores)

    return render_template('admin.html', scores=scores, user=user, user_options=user_options, approved_tests=approved_tests, total_scores=total_scores)

from flask import jsonify
@app.route('/admin/user/<int:user_id>')
def get_user_email(user_id):
    user = User.query.get(user_id)
    if user:
        return jsonify({'email': user.email})
    else:
        return jsonify({'error': 'User not found'})
# ----------------------live recorder ------------------------

import pyaudio
import wave,os,glob
from uuid import uuid4
from flask_login import current_user


UPLOAD_FOLDER = 'voices'
def record_audio(seconds=63):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = seconds
    
    # create the subfolders if they don't exist
    user_folder = os.path.join(UPLOAD_FOLDER, current_user.username)
    liverecord_folder = os.path.join(user_folder, 'liverecord')
    os.makedirs(liverecord_folder, exist_ok=True)

    # generate a random filename
    filename = str(uuid4()) + '.wav'
    WAVE_OUTPUT_FILENAME = os.path.join(liverecord_folder, filename)

    audio = pyaudio.PyAudio()

    # start recording
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    # stop recording
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # save the audio to a file in the liverecord subfolder
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
@app.route('/live_record_api', methods=['POST'])
def live_record_api():
    test_number = int(request.form.get('test_number'))
    round_number = int(request.form.get('round_number'))
    #seconds = int(request.form['seconds'])
    #record_audio(seconds)
    record_audio()
    flash('Recording saved. Click the "Submit" button below to see the result.', 'success')
    return redirect(url_for('tests',round_number=round_number , test_number=test_number))


# Test page (record and transcribe)
@app.route('/live_record', methods=['POST'])
def live_record():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get the user's input from the request
    test_number = int(request.form.get('test_number'))
    round_number = int(request.form.get('round_number'))
    user_folder = os.path.join(UPLOAD_FOLDER, current_user.username)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    liverecord_folder = os.path.join(user_folder, 'liverecord')
    wav_files = glob.glob(os.path.join(liverecord_folder, '*.wav'))

    if not wav_files:
        flash('No recorded audio found.', 'error')
        return redirect(url_for('tests', round_number=round_number, test_number=test_number))

    last_file = max(wav_files, key=os.path.getctime)

    # Perform speech recognition on the recorded audio
    recognizer = sr.Recognizer()
    audio_data = sr.AudioFile(last_file)
    text = ""
    try:
        with audio_data as source:
            audio_content = recognizer.record(source)
            results = recognizer.recognize_google(audio_content, language="fa-IR", show_all=True)
            if len(results) > 0:
                text = [alt["transcript"] for alt in results["alternative"]]
                text = " ".join(text)
    except sr.UnknownValueError:
        flash('Could not transcribe the audio. Please try again.', 'error')
        return redirect(url_for('tests', round_number=round_number, test_number=test_number))

    # Split the transcribed text into words
    test=text
    print(test)
    words = text.split()
    words = set(words)

    # Load the target words for the current test
    target_words = {
        1: ['تراکتور', 'هویج', 'قناری', 'موکت', 'سیر', 'دوچرخه', 'یخچال', 'ببر', 'اتوبوس', 'میز', 'فلفل', 'گوریل',
            'پرده', 'پارو', 'سوسمار', 'فیلم'],
        2: ['لودر', 'گوجه', 'شتر', 'بخاری', 'ریحان', 'وانت', 'فریزر', 'گربه', 'مینی بوس', 'تخته', 'جعفری', 'گوسفند',
            'پنجره', 'ویلچر', 'کلاغ', 'نعنا'],
        3: ['فرش', 'قطار', 'خیار', 'طوطی', 'کدو', 'هواپیما', 'اجاق', 'موش', 'ماشین', 'صندلی', 'کاهو', 'میمون', 'کمد', 'موتور',
            'فیل', 'پیاز'],

        4: ['مترو', 'کامیون', 'اسفناج', 'زرافه', 'کمد', 'پیاز', 'موتور', 'کابینت', 'گورخر', 'چراغ', 'کرفس', 'گاو', 'مبل', 'قایق',
            'سنجاب', 'کلم']
    }

    # Compare the transcribed words with the target words and calculate the score
    score = 0
    for word in words:
        if word in target_words[test_number]:
            score += 1

    # Check if the score entry already exists in the database
    user_id = session['user_id']
    score_entry = Score.query.filter_by(user_id=user_id, test_number=test_number, round_number=round_number).first()

    if score_entry:
        # Update the existing score entry in the database
        score_entry.score = score
        score_entry.test_time = datetime.now()
        db.session.commit()
    else:
        # Create a new score entry in the database
        score_entry = Score(user_id=user_id, test_number=test_number, round_number=round_number, score=score,
                            test_time=datetime.now())
        db.session.add(score_entry)
        db.session.commit()

    # Prepare the data to be displayed on the next page
    transcribed_words = ', '.join(words)
    total_words = len(words)
    correct_words = score
    incorrect_words = 16 - correct_words

    # Check if all four rounds are completed and redirect to the tests page or profile page
    if round_number == 4:
        flash('You have completed all four rounds!', 'success')
    return render_template('next_round.html', test_number=test_number, round_number=round_number,
                           transcribed_words=transcribed_words, total_words=total_words,
                           correct_words=correct_words, incorrect_words=incorrect_words)

@app.route('/how_to')
def how_to():
    return render_template("how_to.html")

# Error handler for 500 Internal Server Error
@app.errorhandler(500)
def internal_server_error(error):
    # Custom error handling logic
    return render_template('error.html'), 500

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)

