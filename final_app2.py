from quart import Quart, Blueprint, render_template, request, redirect, url_for, send_file, flash, send_from_directory, session, abort
import requests
import os
from dotenv import load_dotenv
import certifi
from pymongo import MongoClient
from botocore.exceptions import ClientError
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
import boto3

# Placeholder imports for modules
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Quart app
app = Quart(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")

# Production session configuration (with HTTPS)
# For local development, set SESSION_COOKIE_SECURE=False
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

if IS_PRODUCTION:
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='None',
        PREFERRED_URL_SCHEME="https",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
    )
else:
    # Development configuration
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
    )

# Environment variables
DOMAIN_NAME = os.getenv('DOMAIN_NAME', 'localhost')

# MongoDB Atlas setup - First Database (speak_database)
mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://aitool_db_user:odmBDzFB9DdNYu5H@cluster0.k7po371.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

try:
    mongo_client = MongoClient(
        mongo_uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,
        maxPoolSize=50,
        minPoolSize=10
    )
    # Test connection
    mongo_client.server_info()
    logger.info("MongoDB Atlas connection successful (speak_database)")
except Exception as e:
    logger.error(f"MongoDB Atlas connection failed: {str(e)}")
    raise

db = mongo_client["speak_database"]
users_collection = db["users"]
creds_collection = db["creds"]
reports_collection = db["reports"]

# MongoDB Atlas setup - Second Database (somereports)
mongo_uri1 = os.getenv("MONGO_URI_REPORTS", "mongodb+srv://aitool_db_user:odmBDzFB9DdNYu5H@cluster0.k7po371.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

try:
    mongo_client1 = MongoClient(
        mongo_uri1,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,
        maxPoolSize=50,
        minPoolSize=10
    )
    # Test connection
    mongo_client1.server_info()
    logger.info("MongoDB Atlas connection successful (somereports)")
except Exception as e:
    logger.error(f"MongoDB Atlas connection failed: {str(e)}")
    raise

db1 = mongo_client1.somereports
collection1 = db1.uploads

# S3 Configuration
bucket_name = os.getenv('S3_BUCKET_NAME', 'some-report-bucket')
region = os.getenv('AWS_REGION', 'eu-north-1')
s3_folder = 'reports/'

try:
    s3 = boto3.client('s3', region_name=region)
    logger.info("S3 client initialized successfully")
except Exception as e:
    logger.error(f"S3 client initialization failed: {str(e)}")
    raise

# API configuration
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
api_url = "https://speak.some.education/admin/api/v2/users"

# OTP Configuration
OTP_TTL_MIN = 15  # minutes

def upload_to_s3(file_path, email):
    """Upload PDF report to S3 with error handling"""
    try:
        original_filename = os.path.basename(file_path)
        s3_key = f"{s3_folder}{original_filename}"
        
        s3.upload_file(
            file_path,
            bucket_name,
            s3_key,
            ExtraArgs={'ContentType': 'application/pdf'}
        )
        
        response = s3.head_object(Bucket=bucket_name, Key=s3_key)
        etag = response['ETag'].strip('"')
        
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        arn = f"arn:aws:s3:::{bucket_name}/{s3_key}"
        object_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        
        # Store info with email in MongoDB
        doc = {
            'email': email,
            'file_name': original_filename,
            's3_uri': s3_uri,
            'arn': arn,
            'etag': etag,
            'object_url': object_url,
            'uploaded_at': datetime.utcnow()
        }
        collection1.insert_one(doc)
        
        logger.info(f"Uploaded {original_filename} for {email}")
        return True
        
    except ClientError as e:
        logger.error(f"S3 upload error for {email}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {str(e)}")
        return False

def download_and_delete_by_email(email, download_path):
    """Download report from S3 and delete with error handling"""
    try:
        doc = collection1.find_one({'email': email})
        if not doc:
            logger.warning(f"No upload found for email: {email}")
            return False
            
        s3_key = f"{s3_folder}{doc['file_name']}"
        
        # Download from S3
        s3.download_file(bucket_name, s3_key, download_path)
        logger.info(f"Downloaded file to {download_path}")
        
        # Delete from S3
        s3.delete_object(Bucket=bucket_name, Key=s3_key)
        logger.info(f"Deleted file from S3: {s3_key}")
        
        # Delete from MongoDB
        collection1.delete_one({'email': email})
        logger.info(f"Removed MongoDB record for {email}")
        return True
        
    except ClientError as e:
        logger.error(f"S3 operation failed for {email}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in download_and_delete: {str(e)}")
        return False

# Initialize process pool executor
executor = ProcessPoolExecutor(max_workers=4)

# Create directories
for folder in ["json", "reports", os.path.join("static", "Uploads"), "audio", "images", "logos"]:
    os.makedirs(os.path.join(app.root_path, folder), exist_ok=True)

# Scheduler for cleaning directories
scheduler = BackgroundScheduler()
scheduler.add_job(func=clean_directories, trigger="interval", minutes=30)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# Blueprints
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Authentication functions
def generate_otp(length=6):
    """Generate a random OTP"""
    return "".join(random.choices("0123456789", k=length))

def store_pending_otp(email, otp):
    """Store OTP for verification"""
    try:
        creds_collection.update_one(
            {"email": email},
            {"$set": {
                "password": None,
                "otp": otp,
                "otp_expire": datetime.utcnow() + timedelta(minutes=OTP_TTL_MIN)
            }},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error storing OTP: {str(e)}")
        return False

def verify_otp(email, user_otp):
    """Verify the OTP entered by user"""
    try:
        rec = creds_collection.find_one({"email": email})
        if not rec:
            return False, "No pending OTP. Start sign-in again."

        if datetime.utcnow() > rec.get("otp_expire", datetime.utcnow()):
            creds_collection.delete_one({"email": email})
            return False, "OTP expired. Please request a new one."

        stored_otp = rec.get("otp")
        logger.debug(f"Verifying OTP for {email}")
        if str(user_otp).strip() == str(stored_otp).strip():
            return True, "OTP verified."
        return False, "Incorrect OTP."
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        return False, "Error verifying OTP."

def make_db():
    """Fetch users and admins from API and store in MongoDB"""
    all_users = []
    all_admins = []

    try:
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
                logger.info(f"Fetched {len(users)} users from page {i}")
                if len(users) == 0:
                    break
            else:
                logger.error(f"Error on page {i}: {response.status_code}, {response.text}")
                continue

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
                logger.info(f"Fetched {len(admins)} admins from page {i}")
            else:
                logger.error(f"Error on page {i}: {response.status_code}, {response.text}")
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
        logger.error(f"Error rebuilding database: {str(e)}")
        return f"Error rebuilding database: {str(e)}"

import re

def get_drive_filename(url):
    """Extract filename from Google Drive URL"""
    try:
        file_id = url.split("/d/")[1].split("/")[0]
        direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        response = requests.get(direct_url, stream=True)
        
        cd = response.headers.get("Content-Disposition", "")
        match = re.findall("filename=\"(.+)\"", cd)
        if match:
            return match[0]
        else:
            return None
    except Exception as e:
        logger.error(f"Error extracting Drive filename: {str(e)}")
        return None
    
def get_all_filenames(link: str):
    """Get filename without extension from Drive link"""
    filename = get_drive_filename(link)
    logger.debug(f"Extracted filename: {filename}")
    return filename.split(".")[0] if filename is not None else None

def login(email, password):
    """Login a user"""
    try:
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
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return False, "Login error occurred.", None, None

# Authentication decorators
def login_required(f):
    @wraps(f)
    async def check_login(*args, **kwargs):
        if 'user_id' not in session:
            await flash("Please log in to access this page.", 'warning')
            return redirect(url_for('auth.login_page'))
        return await f(*args, **kwargs)
    return check_login

def admin_required(f):
    @wraps(f)
    async def check_admin(*args, **kwargs):
        if 'user_id' not in session:
            await flash("Please log in to access this page.", 'warning')
            return redirect(url_for('auth.login_page'))
        if session.get('role') != 'admin':
            await flash("Admin access required.", 'error')
            return redirect(url_for('index'))
        return await f(*args, **kwargs)
    return check_admin

# Video processing function
async def process_video(user_name: str, video_path: str, presentation_mode: str, http_session, output_dir: str, download_pdf_path: str) -> dict:
    try:
        logger.info(f"Processing video: {video_path}, user: {user_name}, mode: {presentation_mode}")
        video_name = os.path.basename(video_path).split('.')[0]
        audio_path = os.path.join(app.root_path, "audio", f"audio_{video_name}.wav")
        transcription_json_path = os.path.join(app.root_path, "json", f"transcription_{video_name}.json")
        output_json_path = os.path.join(app.root_path, "json", f"output_{video_name}.json")
        scores_json_path = os.path.join(app.root_path, "json", f"scores_{video_name}.json")
        quality_json_path = os.path.join(app.root_path, "json", f"quality_{video_name}.json")
        audio_metrics_json_path = os.path.join(app.root_path, "json", f"audio_metrics_{video_name}.json")
        presentation_json_path = os.path.join(app.root_path, "json", f"presentation_{video_name}.json")
        pdf_path = os.path.join(app.root_path, "reports", f"{download_pdf_path if download_pdf_path is not None else video_name}.pdf")
        graph_path = os.path.join(app.root_path, "json", f"graph_{video_name}.json")

        await asyncio.to_thread(json.dump, {"presentation_mode": presentation_mode}, open(presentation_json_path, "w"), indent=4)
        logger.debug(f"Saved presentation JSON to {presentation_json_path}")

        with open(video_path, 'rb') as f:
            transcriber = VideoTranscriber(f, audio_path, transcription_json_path)
            transcription_output = await transcriber.transcribe()

        cv_task = asyncio.get_event_loop().run_in_executor(None, analyze_video_file, video_path)
        audio_task = asyncio.to_thread(analyze_audio_metrics, audio_path, transcription_json_path, audio_metrics_json_path)
        analysis_output, audio_analysis = await asyncio.gather(cv_task, audio_task, return_exceptions=True)

        if isinstance(analysis_output, Exception) or isinstance(audio_analysis, Exception):
            raise Exception(f"Error in CV or audio analysis: {analysis_output}, {audio_analysis}")

        await asyncio.to_thread(json.dump, analysis_output, open(output_json_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
        logger.debug(f"Saved CV analysis to {output_json_path}")

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
        logger.debug(f"Saved scores to {scores_json_path}")

        with open(output_json_path, 'r') as f:
            data = json.load(f)
        data.update({'User Name': user_name, 'LLM': eval_results})
        await asyncio.to_thread(json.dump, data, open(output_json_path, 'w'), indent=4)
        logger.debug(f"Updated output JSON at {output_json_path}")

        logo_path = os.path.join(app.root_path, "logos", "somelogo.png")
        await asyncio.to_thread(create_combined_pdf, logo_path, output_json_path, scores_json_path, quality_json_path, presentation_json_path, pdf_path, graph_path)
        logger.info(f"Generated PDF at {pdf_path}")

        # Upload report to S3 after PDF generation
        user_email = session.get('email')
        if user_email:
            try:
                upload_to_s3(pdf_path, user_email)
            except Exception as e:
                logger.error(f"Failed to upload report to S3 for {user_email}: {str(e)}")

        if os.path.exists(audio_path):
            await asyncio.to_thread(os.remove, audio_path)

        return {"filename": os.path.basename(video_path), "pdf_filename": os.path.basename(pdf_path)}
    except Exception as e:
        logger.error(f"Error processing {video_path}: {str(e)}")
        raise

# Authentication routes
@auth_bp.route('/')
async def auth_index():
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
            logger.info(f"Database reload result: {db_result}")

            user = users_collection.find_one({"email": email})
            if not user:
                await flash(f"Database reloaded but user still not found with email: {email}", 'error')
                return await render_template('signin.html')
            else:
                await flash("Database reloaded successfully.", 'success')

        try:
            from mail import send_otp
            otp = send_otp(email)
            if otp:
                store_pending_otp(email, otp)
                await flash("OTP sent to your email address.", 'info')
                logger.info(f"OTP sent to {email}")
                return redirect(url_for('auth.otp_page', email=email))
            else:
                await flash("Failed to send OTP. Please try again.", 'error')
        except Exception as e:
            await flash(f"Error sending OTP: {str(e)}", 'error')
            logger.error(f"Error in sending OTP: {str(e)}")

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
        from mail import send_otp
        otp = send_otp(email)
        if otp:
            store_pending_otp(email, otp)
            await flash("New OTP sent to your email address.", 'success')
            logger.info(f"New OTP sent to {email}")
        else:
            await flash("Failed to send OTP. Please try again.", 'error')
    except Exception as e:
        await flash(f"Error sending OTP: {str(e)}", 'error')
        logger.error(f"Error in resending OTP: {str(e)}")

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
            # Make session permanent
            session.permanent = True
            
            session['user_id'] = str(user['_id'])
            session['email'] = user['email']
            session['role'] = role
            session['name'] = user.get('name', 'User')
            
            await flash(message, 'success')
            logger.info(f"User logged in: {email}, role: {role}")
            
            if role == 'admin':
                return redirect(url_for('admin.index'))
            else:
                return redirect(url_for('index'))
        else:
            await flash(message, 'error')

    return await render_template('login.html')

@auth_bp.route('/logout')
async def logout():
    user_email = session.get('email', 'Unknown')
    session.clear()
    await flash("You have been logged out successfully.", 'info')
    logger.info(f"User logged out: {user_email}")
    return redirect(url_for('auth.login_page'))

# Main app routes (user functionality)
@app.route("/", methods=["GET", "POST"])
@login_required
async def index():
    if request.method == "POST":
        form = await request.form
        files = await request.files
        user_name = form.get("user_name")
        youtube_url = form.get("youtube_url")
        video_file = files.get("video_file")
        presentation_mode = form.get("presentation_mode", "off")
        logger.info(f"Received request: user={user_name}, youtube_url={youtube_url}, presentation_mode={presentation_mode}")
        pdf_name = None
        
        if not user_name:
            await flash("Name is required before uploading a video.", "warning")
            return redirect(request.url)

        try:
            uploads_dir = os.path.join(app.root_path, "static", "Uploads")
            video_filename = f"video_{user_name}_{os.urandom(4).hex()}.mp4"
            video_path = os.path.join(uploads_dir, video_filename)

            if youtube_url:
                pdf_name = get_all_filenames(youtube_url)
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
                video_data = await process_video(user_name, video_path, presentation_mode, http_session, uploads_dir, pdf_name if pdf_name is not None else None)
                # Save report metadata
                reports_collection.insert_one({
                    "user_id": session['user_id'],
                    "user_name": user_name,
                    "pdf_filename": video_data["pdf_filename"],
                    "created_at": datetime.utcnow()
                })
                await flash("Video analysis and PDF report generation completed successfully!", "success")
                return await render_template(
                    "result.html",
                    user_name=user_name,
                    video_filename=video_data["filename"],
                    pdf_url=url_for("download_pdf", filename=video_data["pdf_filename"])
                )
        except Exception as e:
            logger.error(f"Error in request: {e}", exc_info=True)
            await flash(f"An error occurred: {str(e)}", "danger")
            return redirect(request.url)

    submissions = list(reports_collection.find({"user_id": session['user_id']}))
    return await render_template(
        "index.html",
        user_name=session.get('name', 'User'),
        email=session.get('email'),
        role=session.get('role'),
        submissions=submissions
    )

@app.route('/profile')
@login_required
async def user_profile():
    return await render_template('user_profile.html')

@app.route('/settings')
@login_required
async def user_settings():
    return await render_template('user_settings.html')

@app.route('/uploads/<filename>')
@login_required
async def uploaded_file(filename):
    uploads = os.path.join(app.root_path, "static", "Uploads")
    return await send_from_directory(uploads, filename)

@login_required
@app.route("/download_pdf/<path:filename>")
async def download_pdf(filename):
    reports_dir = os.path.join(app.root_path, "reports")
    pdf_path = os.path.join(reports_dir, filename)

    # Normalize & prevent directory traversal
    pdf_path = os.path.normpath(pdf_path)
    if not pdf_path.startswith(reports_dir):
        logger.warning(f"Directory traversal attempt: {filename}")
        abort(403)

    if not os.path.exists(pdf_path):
        logger.warning(f"PDF not found: {pdf_path}")
        abort(404)

    safe_name = os.path.basename(filename)
    return await send_file(
        pdf_path,
        as_attachment=True,
        attachment_filename=f"evaluation_report_{safe_name}"
    )

# Admin routes
@admin_bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
async def index():
    try:
        with open('utils/tuned.json', 'r') as f:
            data = json.load(f)
        model_config = {
            'qualitative': data.get('qualitative', 'gpt-4'),
            'overall': data.get('overall', 'gpt-4'),
            'score': data.get('score', 'gpt-4'),
            'p_question_1': data.get('p_question_1', "100"),
            'p_question_2': data.get('p_question_2', "100"),
            'p_question_3': data.get('p_question_3', "100"),
            'p_question_4': data.get('p_question_4', "100"),
            'p_question_5': data.get('p_question_5', "100"),
            'p_question_6': data.get('p_question_6', "100"),
            'p_question_7': data.get('p_question_7', "100"),
            'p_question_8': data.get('p_question_8', "100"),
            'p_question_9': data.get('p_question_9', "100"),
            'p_question_10': data.get('p_question_10', "100"),
            'p_question_11': data.get('p_question_11', "100"),
            'p_question_12': data.get('p_question_12', "100"),
            'p_question_13': data.get('p_question_13', "100"),
            'p_question_14': data.get('p_question_14', "100"),
            'v_question_1': data.get('v_question_1', "100"),
            'v_question_2': data.get('v_question_2', "100"),
            'v_question_3': data.get('v_question_3', "100"),
            'v_question_4': data.get('v_question_4', "100"),
            'v_question_5': data.get('v_question_5', "100"),
            'v_question_6': data.get('v_question_6', "100"),
            'v_question_7': data.get('v_question_7', "100"),
            'v_question_8': data.get('v_question_8', "100"),
            'v_question_9': data.get('v_question_9', "100"),
            'v_question_10': data.get('v_question_10', "100"),
            'v_question_11': data.get('v_question_11', "100"),
            'v_question_12': data.get('v_question_12', "100")
        }
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading tuned.json: {str(e)}")
        model_config = {}

    if request.method == "POST":
        try:
            form = await request.form
            files = await request.files
            user_name = form.get("user_name", "").strip()
            video_urls = form.get("videoUrls", "").split('\n')
            video_files = files.getlist("video_files[]") if "video_files[]" in files else []
            presentation_mode = form.get("presentation_mode", "off")
            logger.info(f"Admin bulk processing: user={user_name}, urls={len([u for u in video_urls if u.strip()])}, files={len([f for f in video_files if f.filename])}")

            if not user_name:
                await flash("Please provide a valid name.", "danger")
                return redirect(request.url)

            if not any(url.strip() for url in video_urls) and not any(f.filename for f in video_files):
                await flash("Please provide at least one video URL or file.", "danger")
                return redirect(request.url)

            uploads_dir = os.path.join(app.root_path, "static", "Uploads")
            videos = []

            async with aiohttp.ClientSession() as http_session:
                for url in video_urls:
                    if url.strip():
                        try:
                            video_filename = f"video_{user_name}_{os.urandom(4).hex()}.mp4"
                            video_path = os.path.join(uploads_dir, video_filename)
                            pdf_name = get_all_filenames(url)
                            await download_drive_url(url, video_path)
                            if not os.path.exists(video_path):
                                await flash(f"Failed to download video from URL: {url}", "warning")
                                continue
                            video_data = await process_video(user_name, video_path, presentation_mode, http_session, uploads_dir, pdf_name)
                            reports_collection.insert_one({
                                "user_id": session['user_id'],
                                "user_name": user_name,
                                "pdf_filename": video_data["pdf_filename"],
                                "created_at": datetime.utcnow()
                            })
                            videos.append(video_data)
                        except Exception as e:
                            logger.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
                            await flash(f"Error processing URL {url}: {str(e)}", "warning")

                for video_file in video_files:
                    if video_file and video_file.filename:
                        try:
                            original_filename = video_file.filename
                            video_filename = f"file_{user_name}_{os.urandom(4).hex()}.mp4"
                            video_path = os.path.join(uploads_dir, video_filename)
                            await video_file.save(video_path)
                            logger.info(f"Saved file {original_filename} as {video_filename}, size: {os.path.getsize(video_path)} bytes")
                            video_data = await process_video(user_name, video_path, presentation_mode, http_session, uploads_dir, None)
                            reports_collection.insert_one({
                                "user_id": session['user_id'],
                                "user_name": user_name,
                                "pdf_filename": video_data["pdf_filename"],
                                "created_at": datetime.utcnow()
                            })
                            videos.append(video_data)
                        except Exception as e:
                            logger.error(f"Error processing file {original_filename}: {str(e)}", exc_info=True)
                            await flash(f"Error processing file {original_filename}: {str(e)}", "warning")

            if not videos:
                await flash("No valid videos were processed.", "danger")
                return redirect(request.url)

            await flash(f"Successfully processed {len(videos)} video(s)!", "success")
            return await render_template(
                "multi-result2.html",
                user_name=user_name,
                videos=videos
            )
        except Exception as e:
            logger.error(f"Error in admin index route: {str(e)}", exc_info=True)
            await flash(f"Server error: {str(e)}", "danger")
            return redirect(request.url)

    return await render_template(
        "multi-index2.html",
        model_config=model_config,
        user_name=session.get('name', 'Admin'),
        email=session.get('email')
    )

@admin_bp.route('/save_tuning', methods=['POST'])
@login_required
@admin_required
async def save_tuning():
    try:
        data = await request.get_json()
        logger.info(f"Saving tuning configuration")
        transformed_data = {
            "overall": data.get('overall_analysis_model', 'gpt-4'),
            "qualitative": data.get('qualitative_analysis_model', 'gpt-4'),
            "score": data.get('score_model', 'gpt-4')
        }
        if 'questions' in data:
            transformed_data.update(data['questions'])

        with open('utils/tuned.json', 'w') as f:
            json.dump(transformed_data, f, indent=2)

        logger.info("Tuning configuration saved successfully")
        return {'status': 'success'}, 200
    except Exception as e:
        logger.error(f"Error in save_tuning: {str(e)}", exc_info=True)
        return {'status': 'error', 'message': str(e)}, 500

@app.errorhandler(413)
async def request_entity_too_large(error):
    await flash("File too large. Please upload files smaller than 2GB.", "danger")
    return redirect(url_for('index'))

@app.errorhandler(500)
async def internal_server_error(error):
    logger.error(f"Internal server error: {str(error)}", exc_info=True)
    await flash("An internal server error occurred. Please try again later.", "danger")
    return redirect(url_for('index'))

@app.before_serving
async def startup():
    logger.info("=" * 60)
    logger.info("Starting SOME Grading Automation Application")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Session Secure Cookies: {app.config.get('SESSION_COOKIE_SECURE')}")
    logger.info("=" * 60)

@app.after_serving
async def shutdown():
    executor.shutdown(wait=True)
    scheduler.shutdown()
    mongo_client.close()
    mongo_client1.close()
    logger.info("Application shutdown complete")

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    import hypercorn.asyncio
    import hypercorn.config
    
    # Get port from environment or default to 8093
    port = int(os.getenv("PORT", 8093))
    
    config = hypercorn.config.Config()
    config.bind = [f"0.0.0.0:{port}"]
    config.use_reloader = not IS_PRODUCTION
    config.accesslog = "-"
    config.errorlog = "-"
    
    print("\n" + "=" * 60)
    print("🚀 SOME Grading Automation Server")
    print("=" * 60)
    print(f"📍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"📍 Server URL: http://0.0.0.0:{port}")
    print(f"📍 Auth URL: http://localhost:{port}/auth/login")
    print(f"📍 Admin URL: http://localhost:{port}/admin")
    print("=" * 60)
    print("✅ MongoDB Atlas: Connected")
    print("✅ S3 Bucket: Connected")
    print("=" * 60)
    print("Press CTRL+C to stop the server\n")
    
    asyncio.run(hypercorn.asyncio.serve(app, config))
