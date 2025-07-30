import json
with open(r'D:\SOME CLOUD\SOME-Grading-Automation\json\transcription_video_Ayush _17062b4d.json' , 'r') as f:
    transcription_dict = json.load(f)

text = transcription_dict[0].get("text", "").strip()

print(text)