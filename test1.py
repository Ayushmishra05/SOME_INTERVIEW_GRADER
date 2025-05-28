import whisper 

model = whisper.load_model("base") 
results = model.transcribe(r"D:\SOME_UPDATED\SOME_\static\uploads\video.mp4")
print(results)