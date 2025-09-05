from quart import Quart, render_template, request, redirect, url_for, send_file, flash, send_from_directory
import os
import json
import aiohttp
import asyncio
from concurrent.futures import ProcessPoolExecutor
from LLM_Module.transcription_generator import VideoTranscriber
from LLM_Module.Overall_Analysis_Module import VideoResumeEvaluator
from video_module.Video_Eval import analyze_video_file
from LLM_Module.Qualitative_Analysis_Module import VideoResumeEvaluator2
from report_generation_module.PDF_Generator import create_combined_pdf
from video_module.drive_downloader import download_drive_url
from LLM_Module.Scoring_Module import score_analyser
from audio_module.audio_analysis import analyze_audio_metrics
import logging

from utils.cleaning_script import clean_directories
from utils.get_api_key import get_groq_key , get_api_key

from apscheduler.schedulers.background import BackgroundScheduler
import atexit


print("RUNNING CLEANING PROCESS")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')  # Changed to DEBUG
logger = logging.getLogger(__name__)

app = Quart(__name__)

scheduler = BackgroundScheduler()
scheduler.add_job(func=clean_directories, trigger="interval", minutes=1)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())
# get_groq_key()
# get_api_key()
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_secret_key_here")
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # Increased to 200MB
executor = ProcessPoolExecutor(max_workers=4)  # Increased to handle multiple files

for folder in ["json", "reports", os.path.join("static", "uploads"), "audio"]:
    os.makedirs(os.path.join(app.root_path, folder), exist_ok=True)

async def process_video(user_name: str, video_path: str, presentation_mode: str, session, output_dir: str) -> dict:
    try:
        logger.debug(f"Processing video: {video_path}, user: {user_name}, mode: {presentation_mode}")
        os.makedirs(os.path.join(app.root_path, "audio"), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, "json"), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, "reports"), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, "static", "uploads"), exist_ok=True)
        os.makedirs(os.path.join(app.root_path,  "images"), exist_ok=True)

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


        print("Printing OUTPUT JSON PATH " , output_json_path , " also printing DATA " )
        with open(output_json_path, 'r') as f:
            data = json.load(f)
        data.update({'User Name': user_name, 'LLM': eval_results})
        await asyncio.to_thread(json.dump, data, open(output_json_path, 'w'), indent=4)
        logger.debug(f"Updated output JSON at {output_json_path}")

        logo_path = os.path.join(app.root_path, "logos", "somelogo.png")
        await asyncio.to_thread(create_combined_pdf, logo_path, output_json_path, scores_json_path, quality_json_path, presentation_json_path, pdf_path, graph_path)
        logger.debug(f"Generated PDF at {pdf_path}")

        if os.path.exists(audio_path):
            await asyncio.to_thread(os.remove, audio_path)

        return {"filename": os.path.basename(video_path), "pdf_url": url_for("download_pdf", filename=os.path.basename(pdf_path))}
    except Exception as e:
        logger.error(f"Error processing {video_path}: {str(e)}")
        raise

@app.errorhandler(413)
async def request_entity_too_large(error):
    await flash("File too large. Please upload files smaller than 200MB.", "danger")
    return redirect(url_for('index'))

@app.route('/save_tuning', methods=['POST'])
async def save_tuning():
    try:
        data = await request.get_json()  # This is correct for Quart
        print("Printing data from Save Tuning:", data)
        
        # Transform the received data to match your expected format
        transformed_data = {
            "overall": data.get('overall_analysis_model', 'gpt-4'),
            "qualitative": data.get('qualitative_analysis_model', 'gpt-4'),
            "score": data.get('score_model', 'gpt-4')
        }
        
        # Add all questions directly to root level (not nested under 'questions')
        if 'questions' in data:
            transformed_data.update(data['questions'])
        
        print("Transformed data:", transformed_data)
        
        with open('utils/tuned.json', 'w') as f:
            json.dump(transformed_data, f, indent=2)
            
        return {'status': 'success'}, 200
    except Exception as e:
        print(f"Error in save_tuning: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500


@app.route("/", methods=["GET", "POST"])
async def index():
    # model_config = {
    #     'qualitative': 'gpt-4',
    #     'overall': 'gpt-4',
    #     'score': 'gpt-4',
    #     "p_question_1": "95",
    #     "p_question_2": "88",
    #     "p_question_3": "76",
    #     "p_question_4": "92",
    #     "p_question_5": "85",
    #     "p_question_6": "90",
    #     "p_question_7": "78",
    #     "p_question_8": "84",
    #     "p_question_9": "91",
    #     "p_question_10": "87",
    #     "p_question_11": "93",
    #     "p_question_12": "89",
    #     "p_question_13": "80",
    #     "p_question_14": "86",

    #     "v_question_1": "88",
    #     "v_question_2": "82",
    #     "v_question_3": "91",
    #     "v_question_4": "85",
    #     "v_question_5": "79",
    #     "v_question_6": "94",
    #     "v_question_7": "90",
    #     "v_question_8": "87",
    #     "v_question_9": "83",
    #     "v_question_10": "89",
    #     "v_question_11": "92",
    #     "v_question_12": "86"
    # }

    try:
        with open('utils/tuned.json', 'r') as f:
            data = json.load(f)
        model_config = {
            'qualitative': data.get('qualitative', 'gpt-4'),
            'overall': data.get('overall', 'gpt-4'),
            'score': data.get('score', 'gpt-4'),
            'p_question_1': data.get('p_question_1' , "100"),
            'p_question_2': data.get('p_question_2' , "100"),
            'p_question_3': data.get('p_question_3' , "100"),
            'p_question_4': data.get('p_question_4' , "100"),
            'p_question_5': data.get('p_question_5' , "100"),
            'p_question_6': data.get('p_question_6' , "100"),
            'p_question_7': data.get('p_question_7' , "100"),
            'p_question_8': data.get('p_question_8' , "100"),
            'p_question_9': data.get('p_question_9' , "100"),
            'p_question_10': data.get('p_question_10' , "100"),
            'p_question_11': data.get('p_question_11' , "100"),
            'p_question_12': data.get('p_question_12' , "100"),
            'p_question_13': data.get('p_question_13' , "100"),
            'p_question_14': data.get('p_question_14' , "100"),
            'v_question_1': data.get('v_question_1' , "100"),
            'v_question_2': data.get('v_question_2' , "100"),
            'v_question_3': data.get('v_question_3' , "100"),
            'v_question_4': data.get('v_question_4' , "100"),
            'v_question_5': data.get('v_question_5' , "100"),
            'v_question_6': data.get('v_question_6' , "100"),
            'v_question_7': data.get('v_question_7' , "100"),
            'v_question_8': data.get('v_question_8' , "100"),
            'v_question_9': data.get('v_question_9' , "100"),
            'v_question_10': data.get('v_question_10' , "100"),
            'v_question_11': data.get('v_question_11' , "100"),
            'v_question_12': data.get('v_question_12' , "100")
        }
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading tuned.json: {str(e)}")

    if request.method == "POST":
        try:
            form = await request.form
            files = await request.files
            user_name = form.get("user_name", "").strip()
            video_urls = form.get("videoUrls", "").split('\n')
            video_files = files.getlist("video_files[]") if "video_files[]" in files else []
            presentation_mode = form.get("presentation_mode", "on")
            logger.debug(f"Received request: user={user_name}, video_urls={video_urls}, video_files={[f.filename for f in video_files if f.filename]}, presentation_mode={presentation_mode}")

            if not user_name:
                await flash("Please provide a valid name.", "danger")
                return redirect(request.url)

            if not any(url.strip() for url in video_urls) and not any(f.filename for f in video_files):
                await flash("Please provide at least one video URL or file.", "danger")
                return redirect(request.url)

            uploads_dir = os.path.join(app.root_path, "static", "uploads")
            videos = []

            
            async with aiohttp.ClientSession() as session:
                # Process URLs
                for url in video_urls:
                    if url.strip():
                        try:
                            video_filename = f"video_{user_name}_{os.urandom(4).hex()}.mp4"
                            video_path = os.path.join(uploads_dir, video_filename)
                            await download_drive_url(url, video_path)
                            if not os.path.exists(video_path):
                                await flash(f"Failed to download video from URL: {url}", "warning")
                                continue
                            video_data = await process_video(user_name, video_path, presentation_mode, session, uploads_dir)
                            videos.append(video_data)
                        except Exception as e:
                            logger.error(f"Error processing URL {url}: {str(e)}")
                            await flash(f"Error processing URL {url}: {str(e)}", "warning")

                # Process files
                for video_file in video_files:
                    if video_file and video_file.filename:
                        try:
                            original_filename = video_file.filename
                            video_filename = f"file_{user_name}_{os.urandom(4).hex()}.mp4"
                            video_path = os.path.join(uploads_dir, video_filename)
                            await video_file.save(video_path)
                            logger.debug(f"Saved file {original_filename} as {video_filename}, size: {os.path.getsize(video_path)} bytes")
                            video_data = await process_video(user_name, video_path, presentation_mode, session, uploads_dir)
                            videos.append(video_data)
                        except Exception as e:
                            logger.error(f"Error processing file {original_filename}: {str(e)}")
                            await flash(f"Error processing file {original_filename}: {str(e)}", "warning")

            if not videos:
                await flash("No valid videos were processed.", "danger")
                return redirect(request.url)

            await flash("Video analysis and PDF report generation completed successfully!", "success")
            return await render_template(
                "multi-result.html",
                user_name=user_name,
                videos=videos
            )
        except Exception as e:
            logger.error(f"Error in index route: {str(e)}")
            await flash(f"Server error: {str(e)}", "danger")
            return redirect(request.url)

    return await render_template("multi-index.html" , model_config=model_config)

@app.route('/uploads/<filename>')
async def uploaded_file(filename):
    uploads = os.path.join(app.root_path, "static", "uploads")
    return await send_from_directory(uploads, filename)

@app.route("/download_pdf/<filename>")
async def download_pdf(filename):
    pdf_path = os.path.join(app.root_path, "reports", filename)
    return await send_file(pdf_path, as_attachment=True, attachment_filename=f"evaluation_report_{filename}")

@app.before_serving
async def startup():
    logger.info("Starting application and process pool")

@app.after_serving
async def shutdown():
    executor.shutdown()
    logger.info("Shutting down application and process pool")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8051)