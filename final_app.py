from quart import Quart, Blueprint, render_template, request, redirect, url_for, send_file, flash, send_from_directory, session
from flask import Flask, request as flask_request, render_template as flask_render_template, flash as flask_flash, redirect as flask_redirect, url_for as flask_url_for, session as flask_session
import requests
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json
import aiohttp
import asyncio
from concurrent.futures import ProcessPoolExecutor
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Placeholder imports for modules from app.py (replace with actual imports based on your setup)
from LLM_Module.transcription_generator import VideoTranscriber
from LLM_Module.Overall_Analysis_Module import VideoResumeEvaluator
from video_module.Video_Eval import analyze_video_file
from LLM_Module.Qualitative_Analysis_Module import VideoResumeEvaluator2
from report_generation_module.PDF_Generator import create_combined_pdf
from video_module.drive_downloader import download_drive_url
from LLM_Module.Scoring_Module import score_analyser
from audio_module.audio_analysis import analyze_audio_metrics
from utils.cleaning_script import clean_directories

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Quart app
app = Quart(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")

# Environment variables
ADMIN_PORT = os.environ['ADMIN_PORT']
# USER_PORT = os.environ['USER_PORT']
# AUTH_PORT = os.environ['AUTH_PORT']
DOMAIN_NAME = os.getenv('DOMAIN_NAME', "http://127.0.0.1:8002")

# MongoDB setup
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
mongo_client = MongoClient(mongo_uri)
db = mongo_client["speak_database"]
users_collection = db["users"]
creds_collection = db["creds"]

# API configuration
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
api_url = "https://speak.some.education/admin/api/v2/users"

# OTP Configuration
OTP_TTL_MIN = 10  # minutes

# Initialize process pool executor
executor = ProcessPoolExecutor(max_workers=2)

# Create directories
for folder in ["json", "reports", os.path.join("static", "uploads"), "audio", "images", "logos"]:
    os.makedirs(os.path.join(app.root_path, folder), exist_ok=True)

# Scheduler for cleaning directories
scheduler = BackgroundScheduler()
scheduler.add_job(func=clean_directories, trigger="interval", minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# Authentication Blueprint
auth_bp = Blueprint("auth", __name__)

def generate_otp(length=6):
    """Generate a random OTP"""
    return "".join(random.choices("0123456789", k=length))

def store_pending_otp(email, otp):
    """Store OTP for verification"""
    creds_collection.update_one(
        {"email": email},
        {"$set": {
            "password": None,
            "otp": otp,
            "otp_expire": datetime.utcnow() + timedelta(minutes=OTP_TTL_MIN)
        }},
        upsert=True
    )

def verify_otp(email, user_otp):
    """Verify the OTP entered by user"""
    rec = creds_collection.find_one({"email": email})
    if not rec:
        return False, "No pending OTP. Start sign-in again."

    if datetime.utcnow() > rec.get("otp_expire", datetime.utcnow()):
        creds_collection.delete_one({"email": email})
        return False, "OTP expired. Please request a new one."

    stored_otp = rec.get("otp")
    print(f"DEBUG - Stored OTP: {stored_otp}, User entered: {user_otp}")

    if str(user_otp).strip() == str(stored_otp).strip():
        return True, "OTP verified."
    return False, f"Incorrect OTP."

def make_db():
    all_users = []
    all_admins = []

    try:
        # Fetch regular users
        for i in range(25):
            querystring = {
                "role": "user",
                "page": i,
                "items_per_page": 200
            }
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
                "Lw-Client": client_id
            }
            response = requests.get(api_url, headers=headers, params=querystring)
            if response.status_code == 200:
                data = response.json()
                users = data.get("data", [])
                all_users.extend(users)
                print(f"Fetched {len(users)} users from page {i}")
                if len(users) == 0:
                    break
            else:
                print(f"Error on page {i}: {response.status_code}, {response.text}")
                continue

        # Fetch admin users
        for i in range(1):
            querystring = {
                "role": "admin",
                "page": i,
                "items_per_page": 200
            }
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
                "Lw-Client": client_id
            }
            response = requests.get(api_url, headers=headers, params=querystring)
            if response.status_code == 200:
                data = response.json()
                admins = data.get("data", [])
                all_admins.extend(admins)
                print(f"Fetched {len(admins)} admins from page {i}")
            else:
                print(f"Error on page {i}: {response.status_code}, {response.text}")
                continue

        if all_users or all_admins:
            users_collection.delete_many({})
            if all_users:
                users_collection.insert_many(all_users)
            if all_admins:
                users_collection.insert_many(all_admins)
            return f"Inserted {len(all_users)} users and {len(all_admins)} admins into MongoDB."
        else:
            return "No users or admins fetched."
    except Exception as e:
        return f"Error rebuilding database: {str(e)}"

def login(email, password):
    """Login a user"""
    user = users_collection.find_one({"email": email})
    if user:
        verify = creds_collection.find_one({"email": email})
        if verify and verify.get("password"):
            if check_password_hash(verify["password"], password):
                role = "admin" if user.get("is_admin", False) else "user"
                return True, f"Login Successful. Role: {role.title()}", role, user
            else:
                return False, "Invalid password.", None, None
        else:
            return False, "Please complete sign-in process first.", None, None
    else:
        return False, f"No user found with email: {email}", None, None

# Authentication routes
@auth_bp.route('/')
async def index():
    return redirect(url_for('auth.login_page'))

@auth_bp.route('/signin', methods=['GET', 'POST'])
async def signin_page():
    if request.method == 'POST':
        form = await request.form
        email = form.get('email', '').strip()

        if not email:
            await flash('Please enter a valid email address.', 'error')
            return await render_template('signin.html')

        user = users_collection.find_one({"email": email})
        if not user:
            await flash('User not found. Reloading database...', 'warning')
            db_result = make_db()
            print(f"Database reload result: {db_result}")

            user = users_collection.find_one({"email": email})
            if not user:
                await flash(f"Database reloaded but user still not found with email: {email}", 'error')
                return await render_template('signin.html')
            else:
                await flash("Database reloaded successfully.", 'success')

        try:
            # Placeholder for send_otp (replace with actual implementation)
            from mail import send_otp
            otp = send_otp(email)
            if otp:
                store_pending_otp(email, otp)
                await flash("OTP sent to your email address.", 'info')
                print(f"DEBUG - OTP sent and stored: {otp}")
                return redirect(url_for('auth.otp_page', email=email))
            else:
                await flash("Failed to send OTP. Please try again.", 'error')
        except Exception as e:
            await flash(f"Error sending OTP: {str(e)}", 'error')
            print(f"Error in sending OTP: {str(e)}")

    return await render_template('signin.html')

@auth_bp.route('/signin/otp', methods=['GET', 'POST'])
async def otp_page():
    email = request.args.get('email') or (await request.form).get('email')

    if not email:
        await flash("Invalid access. Please start sign-in process again.", 'error')
        return redirect(url_for('auth.signin_page'))

    if request.method == 'POST':
        form = await request.form
        user_otp = form.get('otp', '').strip()
        password = form.get('password', '').strip()
        confirm_password = form.get('confirm_password', '').strip()

        if not user_otp or not password or not confirm_password:
            await flash("All fields are required.", 'error')
            return await render_template('otp.html', email=email)

        if password != confirm_password:
            await flash("Passwords do not match.", 'error')
            return await render_template('otp.html', email=email)

        if len(password) < 6:
            await flash("Password must be at least 6 characters long.", 'error')
            return await render_template('otp.html', email=email)

        ok, msg = verify_otp(email, user_otp)
        if not ok:
            await flash(msg, 'error')
            return await render_template('otp.html', email=email)

        hashed_password = generate_password_hash(password)
        creds_collection.update_one(
            {"email": email},
            {"$set": {"password": hashed_password},
             "$unset": {"otp": "", "otp_expire": ""}}
        )

        await flash("Sign-in completed successfully. You can now log in.", 'success')
        return redirect(url_for('auth.login_page'))

    return await render_template('otp.html', email=email)

@auth_bp.route('/resend-otp')
async def resend_otp():
    email = request.args.get('email', '').strip()
    if not email:
        await flash("Invalid request.", 'error')
        return redirect(url_for('auth.signin_page'))

    try:
        # Placeholder for send_otp (replace with actual implementation)
        from mail import send_otp
        otp = send_otp(email)
        if otp:
            store_pending_otp(email, otp)
            await flash("New OTP sent to your email address.", 'success')
            print(f"DEBUG - New OTP sent and stored: {otp}")
        else:
            await flash("Failed to send OTP. Please try again.", 'error')
    except Exception as e:
        await flash(f"Error sending OTP: {str(e)}", 'error')
        print(f"Error in resending OTP: {str(e)}")

    return redirect(url_for('auth.otp_page', email=email))

@auth_bp.route('/login', methods=['GET', 'POST'])
async def login_page():
    if request.method == 'POST':
        form = await request.form
        email = form.get('email', '').strip()
        password = form.get('password', '').strip()

        if not email or not password:
            await flash("Please enter both email and password.", 'error')
            return await render_template('login.html')

        success, message, role, user = login(email, password)
        if success:
            # Set session variables
            session['user_id'] = str(user['_id'])
            session['email'] = user['email']
            session['role'] = role
            session['name'] = user.get('name', 'User')

            await flash(message, 'success')

            # Redirect based on role
            if role == 'admin':
                return redirect(f'{DOMAIN_NAME}:{ADMIN_PORT}')
            else:
                return redirect(f'{DOMAIN_NAME}')
        else:
            await flash(message, 'error')

    return await render_template('login.html')

@auth_bp.route('/logout')
async def logout():
    session.clear()
    await flash("You have been logged out successfully.", 'info')
    return redirect(url_for('auth.login_page'))

# Authentication decorator
def login_required(f):
    @wraps(f)
    async def check_login(*args, **kwargs):
        if 'user_id' not in session:
            await flash("Please log in to access this page.", 'warning')
            return redirect(f"{DOMAIN_NAME}/auth/login")
        return await f(*args, **kwargs)
    return check_login

# Main app routes
async def process_video(user_name: str, video_path: str, presentation_mode: str, http_session, output_dir: str) -> str:
    try:
        video_name = os.path.basename(video_path).split('.')[0]
        audio_path = os.path.join(app.root_path, "audio", f"audio_{video_name}.wav")
        transcription_json_path = os.path.join(app.root_path, "json", f"transcription_{video_name}.json")
        output_json_path = os.path.join(app.root_path, "json", f"output_{video_name}.json")
        scores_json_path = os.path.join(app.root_path, "json", f"scores_{video_name}.json")
        quality_json_path = os.path.join(app.root_path, "json", f"quality_{video_name}.json")
        audio_metrics_json_path = os.path.join(app.root_path, "json", f"audio_metrics_{video_name}.json")
        presentation_json_path = os.path.join(app.root_path, "json", f"presentation_{video_name}.json")
        pdf_path = os.path.join(app.root_path, "reports", f"report_{video_name}.pdf")
        graph_path = os.path.join(app.root_path, "json", f"graph_{video_name}.json")

        await asyncio.to_thread(json.dump, {"presentation_mode": presentation_mode}, open(presentation_json_path, "w"), indent=4)
        logger.info(f"Saved presentation JSON to {presentation_json_path}")
        print("Presentation Mode : ", presentation_mode)
        with open(video_path, 'rb') as f:
            transcriber = VideoTranscriber(f, audio_path, transcription_json_path)
            transcription_output = await transcriber.transcribe()

        cv_task = asyncio.get_event_loop().run_in_executor(None, analyze_video_file, video_path)
        audio_task = asyncio.to_thread(analyze_audio_metrics, audio_path, transcription_json_path, audio_metrics_json_path)
        analysis_output, audio_analysis = await asyncio.gather(cv_task, audio_task, return_exceptions=True)

        if isinstance(analysis_output, Exception) or isinstance(audio_analysis, Exception):
            raise Exception(f"Error in CV or audio analysis: {analysis_output}, {audio_analysis}")

        await asyncio.to_thread(json.dump, analysis_output, open(output_json_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
        logger.info(f"Saved CV analysis to {output_json_path}")

        evaluator = VideoResumeEvaluator(
            model_name="llama-3.3-70b-versatile",
            presentation_json_path=presentation_json_path,
            output_json_path=output_json_path,
            audio_metrics_json_path=audio_metrics_json_path
        )
        quality_evaluator = VideoResumeEvaluator2(
            model_name="llama-3.3-70b-versatile",
            output_json_path=quality_json_path
        )
        eval_results = await evaluator.evaluate_transcription(transcription_json_path)
        output = await score_analyser(
            eval_results,
            transcription_json_path=transcription_json_path,
            presentation_json_path=presentation_json_path,
            output_json_path=output_json_path,
            audio_metrics_json_path=audio_metrics_json_path
        )
        await quality_evaluator.evaluate_transcription(transcription_json_path)

        await asyncio.to_thread(json.dump, output, open(scores_json_path, 'w'), indent=4)
        logger.info(f"Saved scores to {scores_json_path}")

        with open(output_json_path, 'r') as f:
            data = json.load(f)

        print(data)
        data.update({'User Name': user_name, 'LLM': eval_results})
        await asyncio.to_thread(json.dump, data, open(output_json_path, 'w'), indent=4)
        logger.info(f"Updated output JSON at {output_json_path}")

        logo_path = os.path.join(app.root_path, "logos", "somelogo.jpg")
        await asyncio.to_thread(create_combined_pdf, logo_path, output_json_path, scores_json_path, quality_json_path, presentation_json_path, pdf_path, graph_path)
        logger.info(f"Generated PDF at {pdf_path}")

        if os.path.exists(audio_path):
            await asyncio.to_thread(os.remove, audio_path)
        return pdf_path
    except Exception as e:
        logger.error(f"Error processing {video_path}: {e}")
        raise

@app.route("/", methods=["GET", "POST"])
@login_required
async def index():
    if request.method == "POST":
        form = await request.form
        files = await request.files
        user_name = form.get("user_name")
        youtube_url = form.get("youtube_url")
        video_file = files.get("video_file")
        presentation_mode = form.get("presentation_mode")
        logger.info(f"Received request: user={user_name}, youtube_url={youtube_url}, presentation_mode={presentation_mode}")

        if not user_name:
            await flash("Name is required before uploading a video.", "warning")
            return redirect(request.url)

        try:
            uploads_dir = os.path.join(app.root_path, "static", "uploads")
            video_filename = f"video_{user_name}_{os.urandom(4).hex()}.mp4"
            video_path = os.path.join(uploads_dir, video_filename)

            if youtube_url:
                await download_drive_url(youtube_url, video_path)
                if not os.path.exists(video_path):
                    await flash("Failed to download video from URL.", "warning")
                    return redirect(request.url)
            else:
                if not video_file:
                    await flash("Video file is missing!", "warning")
                    return redirect(request.url)
                await video_file.save(video_path)

            async with aiohttp.ClientSession() as http_session:
                pdf_path = await process_video(user_name, video_path, presentation_mode, http_session, uploads_dir)
                await flash("Video analysis and PDF report generation completed successfully!", "success")
                return await render_template(
                    "result.html",
                    user_name=user_name,
                    video_filename=video_filename,
                    pdf_url=url_for("download_pdf", filename=os.path.basename(pdf_path))
                )
        except Exception as e:
            logger.error(f"Error in request: {e}")
            await flash(f"An error occurred: {str(e)}", "danger")
            return redirect(request.url)

    return await render_template("index.html",
                               user_name=session.get('name', 'User'),
                               email=session.get('email'),
                               role=session.get('role'))

@app.route('/profile')
@login_required
async def user_profile():
    return await render_template('user_profile.html')

@app.route('/settings')
@login_required
async def user_settings():
    return await render_template('user_settings.html')

@auth_bp.route('/uploads/<filename>')
@login_required
async def uploaded_file(filename):
    uploads = os.path.join(app.root_path, "static", "uploads")
    return await send_from_directory(uploads, filename)

@app.route("/download_pdf/<filename>")
@login_required
async def download_pdf(filename):
    pdf_path = os.path.join(app.root_path, "reports", filename)
    return await send_file(pdf_path, as_attachment=True, attachment_filename=f"evaluation_report_{filename}")

@auth_bp.route('/user_logout')
async def user_logout():
    session.clear()
    await flash("You have been logged out successfully.", 'info')
    return redirect(f"{DOMAIN_NAME}/auth/login")

@app.before_serving
async def startup():
    logger.info("Starting application and process pool")

@app.after_serving
async def shutdown():
    executor.shutdown()
    logger.info("Shutting down application and process pool")

# Register the auth blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")

#if __name__ == "__main__":
#    app.run(host='0.0.0.0', port=8002)

