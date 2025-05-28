from langchain_groq import ChatGroq 
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.llms import Ollama
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json 
import os

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
        
    prompt_template = ChatPromptTemplate.from_messages([
                ("system", 
                """You are an expert Scorer, you will be provided with the Interviewers Questions and their evaluations based on the candidates transcript , 
                audio and video metrics, Your task is to  Score the result of the candidate based on the Interviewers Questions mapped with descripting scoring upon transcript , 
                audio and video metrics, The Scoring can either Contain in the Priority, 1 -> 2 -> 3 -> 4 -> 5.Do not give random results.  you need to only return numerical outputs for each questions from 1-5, based on the evaluation criteria
                map results exactly with descriptive evaluations. You are not allowed give out of the box evaluations. 
                Criteria for evaluation : 
                1 (Worst)
                When to use: The candidate's answer demonstrates a complete lack of understanding, is incorrect, irrelevant, or inappropriate.
                Indicators:
                Shows no grasp of the topic. Fails to answer the question in any meaningful way. Serious misunderstandings or inappropriate responses. Might raise red flags about suitability for the role.
                2 (Poor): When to use: The candidate tries to answer but gives a weak or mostly incorrect response.
                Indicators: Partial understanding but largely inaccurate. Struggles with basic concepts or makes major errors. Poor communication or logic. Needs significant guidance to reach correct conclusions.
                3 (Satisfactory) : When to use: The candidate gives a mostly correct but basic or unrefined response.
                Indicators : Understands the question and answers it reasonably well. Minor errors or lack of depth.
                Response is acceptable but not particularly strong. Might need some support or training.
                4 (Good): 
                When to use : The candidate gives a clear, correct, and confident answer.
                Indicators : Solid understanding and application of knowledge. Well-structured and logical reasoning. Demonstrates readiness for the role. Can explain concepts clearly and concisely.
                5 (Excellent) : 
                When to use: The candidate answers thoroughly, shows deep insight, or goes beyond expectations.
                Indicators : Mastery of the subject, innovative or strategic thinking. Anticipates related questions or edge cases. Communicates with clarity, precision, and professionalism. Stands out clearly above the typical expectation.
                score in the JSON Format, like question1 : <score> , question2 : <score> .... and similarly all the questions provided, only json file, no extras , nad no explanation, nothing extra"""),
                ("user", 
                """
    Interviewer's Questions : {questions} , Descriptive_Scoring: {Scores}, Audio Metrics : {audio_metrics}, Video Metrics : {video_metrics}
                """
                )
            ])
    chain = prompt_template | model | output_parser  
    output = chain.invoke({'Scores' : transcription_output, 'questions' : questions, 'audio_metrics' : audio_metrics, 'video_metrics' : video_metrics})
    return output 




