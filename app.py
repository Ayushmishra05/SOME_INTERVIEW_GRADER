from flask import Flask, render_template, request, redirect, url_for, send_file, flash, send_from_directory
import os
import json
from LLM_Module.newtranscriber import VideoTranscriber
from LLM_Module.Overall_Analyser2 import VideoResumeEvaluator
from video_module.veval import analyze_video_file 
from LLM_Module.Qualitative_Analyser2 import VideoResumeEvaluator2
from report_generation_module.PDF_Generator2 import create_combined_pdf
from video_module.drive_video_download import download_drive_url
from LLM_Module.score_analyser2 import score_analyser
import os
# from video_module.exp_match import analyze_video_smile
from audio_module.audio_analysis import analyze_audio_metrics
os.environ['FLASK_RUN_EXTRA_FILES'] = ''

app = Flask(__name__)
app.secret_key = "your_secret_key_here" 

for folder in ["json", "reports", os.path.join("static", "uploads")]:
    os.makedirs(os.path.join(app.root_path, folder), exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_name = request.form.get("user_name")
        youtube_url = request.form.get("youtube_url")
        video_file = request.files.get("video_file")
        presentation_mode = request.form.get("presentation_mode")
        print("<------------------------------------------------------->")
        print("<------------------------------------------------------->")
        print("Presentation Mode : ", presentation_mode)
        print("<------------------------------------------------------->")
        print("<------------------------------------------------------->")
        with open("json/presentation.json", "w") as file:
            json.dump({"presentation_mode": presentation_mode}, file, indent=4)

        
        if not user_name:
            flash("Name is required before uploading a video.", "warning")
            return redirect(request.url)

        try:
            uploads_dir = os.path.join(app.root_path, "static", "uploads")
            if youtube_url:
                download_drive_url(youtube_url)
                file_path = os.path.join(uploads_dir, "video.mp4")
                video_filename = "video.mp4"
            else:
                if not video_file:
                    flash("Video file is missing!", "warning")
                    return redirect(request.url)
                file_path = os.path.join(uploads_dir, "video.mp4")
                video_file.save(file_path)
                video_filename = "video.mp4"


            with open(file_path, 'rb') as f:
                audio_path = os.path.join(app.root_path, "audiofile.wav")
                transcription_json_path = os.path.join(app.root_path, "json", "transcription_output.json")
                transcriber = VideoTranscriber(f, audio_path, transcription_json_path)
                transcription_output = transcriber.transcribe()

            # with open(file_path, 'rb') as f:
            analysis_output = analyze_video_file(file_path)
            # analysis_output = analyzer.analyze_video()

            # smile = analyze_video_smile(file_path , transcription_json_path)
            # analysis_output.update({"Smile Score" : smile})

            output_json_path = os.path.join(app.root_path, "json", "output.json")
            with open(output_json_path, 'w', encoding='utf-8') as json_file:
                json.dump(analysis_output, json_file, ensure_ascii=False, indent=4)
            

            # with open()


            analysis_audio = analyze_audio_metrics(audio_path , transcription_json_path)
            evaluator = VideoResumeEvaluator()
            quality_evaluator = VideoResumeEvaluator2() 
        
            eval_results = evaluator.evaluate_transcription(transcription_output) 
            print("Audio Analysis --> ", analysis_audio)
            print("AI Results --> " , eval_results)
            output = score_analyser(eval_results)
            with open(os.path.join(app.root_path, "json", "scores.json") , 'w') as fp:
                json.dump(output, fp)
            quality_evaluator.evaluate_transcription(transcription_output)

            with open(output_json_path, 'r') as f:
                data = json.load(f)
            data.update({
                'User Name': user_name,
                'LLM': eval_results
            })
            with open(output_json_path, 'w') as f:
                json.dump(data, f, indent=4)

            reports_dir = os.path.join(app.root_path, "reports")
            pdf_path = os.path.join(reports_dir, "combined_report.pdf")
            logo_path = os.path.join(app.root_path, "logos", "logo.png")
            create_combined_pdf(logo_path, output_json_path)

            flash("Video analysis and PDF report generation completed successfully!", "success")
            return render_template("result.html", 
                            user_name=user_name, 
                            video_filename=video_filename, 
                            pdf_url=url_for("download_pdf"))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(request.url)
    return render_template("index.html")

# Endpoint to serve uploaded video files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    uploads = os.path.join(app.root_path, "static", "uploads")
    return send_from_directory(uploads, filename)

@app.route("/download_pdf")
def download_pdf():
    pdf_path = os.path.join(app.root_path, "reports", "combined_report.pdf")
    return send_file(pdf_path, as_attachment=True, download_name="evaluation_report.pdf")

if __name__ == "__main__":
    app.run(port = '5032',host = '0.0.0.0')