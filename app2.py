from quart import Quart, render_template, request, redirect, url_for, send_file, flash, send_from_directory
import os
import json
import aiohttp
import asyncio
from concurrent.futures import ProcessPoolExecutor
from LLM_Module.newtranscriber2 import VideoTranscriber
from LLM_Module.Overall_Analyser3 import VideoResumeEvaluator
from video_module.veval2 import analyze_video_file
from LLM_Module.Qualitative_Analyser3 import VideoResumeEvaluator2
from report_generation_module.PDF_Generator3 import create_combined_pdf
from video_module.drive_video_download2 import download_drive_url
from LLM_Module.score_analyser3 import score_analyser
from audio_module.audio_analysis2 import analyze_audio_metrics
import logging
from cleaning_script import clean_directories 


print("RUNNING CLEANING PROCESS")

clean_directories()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Quart(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_secret_key_here")
executor = ProcessPoolExecutor(max_workers=2)  # Adjust based on CPU cores

for folder in ["json", "reports", os.path.join("static", "uploads"), "audio"]:
    os.makedirs(os.path.join(app.root_path, folder), exist_ok=True)

async def process_video(user_name: str, video_path: str, presentation_mode: str, session, output_dir: str) -> str:
    try:
        # Ensure directories exist
        os.makedirs(os.path.join(app.root_path, "audio"), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, "json"), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, "reports"), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, "static", "uploads"), exist_ok=True)

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
        print("Presentation Mode : " , presentation_mode)
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
        # print(" JSON PATH " , transcription_json_path)
        # print(" content " , djs)
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
        data.update({'User Name': user_name, 'LLM': eval_results})
        await asyncio.to_thread(json.dump, data, open(output_json_path, 'w'), indent=4)
        logger.info(f"Updated output JSON at {output_json_path}")

        logo_path = os.path.join(app.root_path, "logos", "somelogo.jpg")
        await asyncio.to_thread(create_combined_pdf, logo_path, output_json_path, scores_json_path, quality_json_path, presentation_json_path, pdf_path , graph_path)
        logger.info(f"Generated PDF at {pdf_path}")

        if os.path.exists(audio_path):
            await asyncio.to_thread(os.remove, audio_path)
        return pdf_path
    except Exception as e:
        logger.error(f"Error processing {video_path}: {e}")
        raise

    
@app.route("/", methods=["GET", "POST"])
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

            async with aiohttp.ClientSession() as session:
                pdf_path = await process_video(user_name, video_path, presentation_mode, session, uploads_dir)
                await flash("Video analysis and PDF report generation completed successfully!", "success")
                return await render_template(
                    "multi-result.html",
                    user_name=user_name,
                    video_filename=video_filename,
                    pdf_url=url_for("download_pdf", filename=os.path.basename(pdf_path))
                )
        except Exception as e:
            logger.error(f"Error in request: {e}")
            await flash(f"An error occurred: {str(e)}", "danger")
            return redirect(request.url)
    return await render_template("multi-index.html")

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
    app.run(host='0.0.0.0', port=8000)