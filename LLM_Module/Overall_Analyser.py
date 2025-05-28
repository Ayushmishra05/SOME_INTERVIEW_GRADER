from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
from langchain_groq import ChatGroq
import json
from langchain_openai import ChatOpenAI
from audio_module.audio_analysis import analyze_audio_metrics
from config import audio_path, transcription_path
from dotenv import load_dotenv
import os
load_dotenv()

class VideoResumeEvaluator:
    def __init__(self, model_name="o1"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model=model_name, api_key=self.api_key)
        self.output_parser = StrOutputParser()
        with open("json/presentation.json", "r") as file:  # Correct path
            data = json.load(file)
        presentation_mode = data.get("presentation_mode", False)
         
        with open('json/output.json', 'r') as file:
            data = json.load(file)
        
        posture = data.get("posture", "neutral")
        eye_contact = data.get("Eye Contact", "neutral")
        energetic = data.get("Energetic Start", "neutral")
        smile = data.get("Smile Score", "neutral")
            
        with open('json/audio_metrics.json', 'r') as file:
            data = json.load(file)
            
        volume_std = data.get("volume_std", "neutral")
        speaking_speed = data.get("speaking_speed", "neutral")
        predicted_tone = data.get("predicted_tone", "neutral")
        average_volume = data.get("average_volume", "neutral")
        
        self.video_metrics = f"""
        Posture : {posture},
        eye_contact : {eye_contact},
        energetic start : {energetic},
        smile : {smile}
        """
        
        self.audio_metrics = f"""
        Variance of voice volume : {volume_std},
        Speaking Speed : {speaking_speed},
        Predicted Tone : {predicted_tone},
        Average Volume : {average_volume}
        """
        if presentation_mode == "on":
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", 
                "You are an expert interviewer evaluating a video resume based on a transcription and provided audio metrics and video metrics. Keep the answers a little concise and straight to the point, do not let them know that you are using transcripts, you are an interviewer, and evaluate like an actual interviewer does, do not reveal that you are using transcripts anywhere"),
                ("user", 
                """
    Transcription: {transcription_input}
    Audio Metrics : {audio_metrics}
    Video Metrics : {video_metrics}

    Questions:
    1. Did the Speaker Speak with Confidence? (One line answer)
    2. Did the speaker vary their tone, speed, and volume while delivering the speech/presentation? Here are the details provided about the tone, speed, pace, and volume, {audio_metrics}, I want you 
    to give the answer in a sentence format, (For ex : The Tone and Volume was appropriate. you could have maintained a steady Speed in Delivery. A few Words were pronounced very fast), I want you to give the answer in a proper sentence like the example, and doesn't provide the numerical metrics to user, it should be in sentence, but dont tell like, dont tell your that your tone was neutrl/sad/happy, say that your maintained a good tone, this is an example

    3. Did they use any gestures with their hands or body while speaking? (Give 2-3 line Explanation, no straight answers or marks should be provided, i want descriptive answers, this is mandatory , judge on the basis of the gestures of the candidate in the transcript)
    4. Did they have expressions on their faces? Refer Video metrics for this video metrics {video_metrics} (Give 2-3 line Explanation, no straight answers or marks should be provided, i want descriptive answers, this is mandatory)
    5. Did the speech have a structure of Opening, Body and Conclusion? (Give 2-3 line Explanation, no straight answers or marks should be provided, i want descriptive answers, this is mandatory)
    6. Did the speaker keep the presentation engaging by adding relevant examples, anecdotes and data to back their content?   (Give 2-3 line Explanation, no straight answers or marks should be provided, i want descriptive answers, this is mandatory)
    7. Was the overall “Objective” of the speech delivered clearly?  (3-4 lines Descriptive Answer)
    8. Was the content of the presentation/speech to the point, or did it include unnecessary details that may have distracted or confused the audience?  (2-3 lines explanation about hwo good or bad it was)
    9. Was the content of the presentation/speech relevant to the objective of the presentation? (2-3 lines descriptive answer)
    10. Was the content of the presentation/speech clear and easy to understand?  (2-3 lines descriptive answer)
    11. Did the speaker demonstrate credibility? Will you trust the speaker?   (2-3 lines descriptive answer)
    12. Did the speaker explain how the speech or topic of the presentation would benefit the audience and what they could gain from it? (2-3 lines descriptive answer)
    13. Did the speaker make an emotional connection with the audience ? (2-3 lines Descriptive answer)
    14. Overall, were you convinced/ persuaded with the speaker’s view on the topic? (2-3 lines Descriptive answer)
    Only provide the answers to these questions—do not include any extra commentary. 
    Start your response with "These are the Answers:" and then list each answer on a new line. Refer the user as You, it should be like you are directly talking to him
                """
                )
            ])
        else:
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", 
                "You are an expert interviewer evaluating a video resume based on a transcription and provided audio metrics and video metrics. Keep the answers a little concise and straight to the point."),
                ("user", 
                """
    Transcription: {transcription_input}
    Audio Metrics : {audio_metrics}
    Video Metrics : {video_metrics}

    Questions:
    1. Did the Speaker Speak with Confidence? (One line answer)
    2. Did the speaker vary their tone, speed, volume?  Here are the details provided about the tone, speed, pace, and volume, {audio_metrics}, I want you 
    to give the answer in a sentence format, (For ex : The Tone and Volume was appropriate. you could have maintained a steady Speed in Delivery. A few Words were pronounced very fast), I want you to give the answer in a proper sentence like the example, and doesn't provide the numerical metrics to user, it should be in sentence, but dont tell like, dont tell your that your tone was neutrl/sad/happy, say that your maintained a good tone, this is an example)
    3. Did they use any gestures with their hands or body while speaking?  Refer to the video metrics here {video_metrics} (Give one to two line descriptive answer)
    4. Did they have expressions on their faces?  (Give a one line answer, give the judgement based on video metrics {video_metrics})
    5. Did the Person was able to introduce about them, their skills, and their personality traits ? (Give a one line answer, including the point)
    6. Why are you the best person to fit this role? (Give a one line answer, including the point, where he/she performed well/bad)
    7. How are you different from others? (One line descriptive answer)
    8. What value do you bring to the role? (Descriptive answer)
    9. Did the speech have a structure of Opening, Body and Conclusion?  (Descriptive answer)
    10. How was the quality of research for the topic? Did the student’s speech demonstrate a good depth? Did they cite the sources of research properly? (Descriptive answer)
    11. How creatively did the student present the video? (Descriptive answer)
    12. How convinced were you with the overall speech on the topic? Was it persuasive? Will you give them the job/opportunity? (Descriptive answer)
    Only provide the answers to these questions—do not include any extra commentary. 
    Start your response with "These are the Answers:" and then list each answer on a new line. Refer the user as You, it should be like you are directly talking to him
                """
                )
            ])
        
        self.chain = self.prompt_template | self.llm | self.output_parser

    def evaluate_transcription(self, transcription):
        transcription_input = transcription
        output = self.chain.invoke({
            'transcription_input': transcription_input, 
            'audio_metrics' : self.audio_metrics, 
            'video_metrics' : self.video_metrics
        })
        return output 

