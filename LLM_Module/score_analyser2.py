from langchain_groq import ChatGroq 
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.llms import Ollama
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json 
import os
import yaml

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

def score_analyser(transcription_output) :
    model = ChatOpenAI(model = 'o1', api_key = api_key)
    output_parser = JsonOutputParser()
    with open('json/transcription_output.json', 'r') as file:
        transcription_output = json.load(file)
    with open('json/presentation.json', 'r') as file:
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
    
    video_metrics = f"""
    Posture : {posture},
    eye_contact : {eye_contact},
    energetic start : {energetic},
    smile : {smile}
    """
    
    audio_metrics = f"""
    Variance of voice volume : {volume_std},
    Speaking Speed : {speaking_speed},
    Predicted Tone : {predicted_tone},
    Average Volume : {average_volume}
    """
    
    
    print("----------SCORE-----------------")
    print(audio_metrics)
    print("----------SCORE-----------------")
    print(video_metrics)
    
    
    if presentation_mode == "on":
        questions = """
            "Did the Speaker Speak with Confidence ?", 
            "Did the speaker vary their tone, speed, volume while delivering the speech/presentation? ",
            "Did they use any gestures with their hands or body while speaking?" , 
            "Did they have expressions on their faces?",
            "Did the speech have a structure of Opening, Body and Conclusion? ",
            "Did the speaker keep the presentation engaging by adding relevant examples, anecdotes and data to back their content?  ", 
            "Was the overall “Objective” of the speech delivered clearly?", 
            "Was the content of the presentation/speech to the point, or did it include unnecessary details that may have distracted or confused the audience?", 
            "Was the content of the presentation/speech relevant to the objective of the presentation?",
            "Was the content of the presentation/speech clear and easy to understand?", 
            "Did the speaker demonstrate credibility? Will you trust the speaker? ", 
            "Did the speaker explain how the speech or topic of the presentation would benefit the audience and what they could gain from it?", 
            "Did the speaker make an emotional connection with the audience ? " , 
            "Overall, were you convinced/ persuaded with the speaker’s view on the topic?"
        """
    else : 
        questions = """
            "Did the Speaker Speak with Confidence ?", 
            "Did the speaker vary their tone, speed, volume?",
            "Did they use any gestures with their hands or body while speaking? ",
            "Did they have expressions on their faces?",
            "Who are you and what are your skills, expertise, personality traits ?",
            "Why are you the best person to fit this role?",
            "How are you different from others? ",
            "What value do you bring to the role?", 
            "Did the speech have a structure of Opening, Body and Conclusion?",
            "How was the quality of research for the topic? Did the student’s speech demonstrate a good depth? Did they cite the sources of research properly?", 
            "How creatively did the student present the video?", 
            "How convinced were you with the overall speech on the topic? Was it persuasive? Will you give them the job/opportunity? "        """
            
    with open("prompts/score_analyser.yaml", "r") as file:
        yaml_data = yaml.safe_load(file)

    system_prompt = yaml_data["interviewer_scorer_prompt"]["system"]
    
    prompt_template = ChatPromptTemplate.from_messages([
                ("system", 
                f"{system_prompt}"),
                ("user", 
                """
    Interviewer's Questions : {questions} , Descriptive_Scoring: {Scores}, Audio Metrics : {audio_metrics}, Video Metrics : {video_metrics}
                """
                )
            ])
    chain = prompt_template | model | output_parser  
    output = chain.invoke({'Scores' : transcription_output, 'questions' : questions, 'audio_metrics' : audio_metrics, 'video_metrics' : video_metrics})
    return output 




