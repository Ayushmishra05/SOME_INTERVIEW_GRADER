from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import json 
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

def graph_analyser():
    # model = ChatOpenAI(model='o1', api_key=api_key)
    # output_parser = JsonOutputParser()
    # with open('json/transcription_output.json', 'r') as file:
    #     transcription_output = json.load(file)
 
    # with open('json/output.json', 'r') as file:
    #     data = json.load(file)
        
        
    # posture = data.get("posture", "neutral")
    # eye_contact = data.get("Eye Contact", "neutral")
    # energetic = data.get("Energetic Start", "neutral")
    # smile = data.get("Smile Score", "neutral")
    
    # video_metrics = f"""
    # Posture : {posture},
    # eye_contact : {eye_contact},
    # energetic start : {energetic},
    # smile : {smile}
    # """
    
    # with open('json/audio_metrics.json', 'r') as file:
    #     data = json.load(file)
        
    # volume_std = data.get("volume_std", "neutral")
    # speaking_speed = data.get("speaking_speed", "neutral")
    # predicted_tone = data.get("predicted_tone", "neutral")
    # average_volume = data.get("average_volume", "neutral")
    
    # audio_metrics = f"""
    # Variance of voice volume : {volume_std},
    # Speaking Speed : {speaking_speed},
    # Predicted Tone : {predicted_tone},
    # Average Volume : {average_volume}
    # """
    

    # prompt_template = ChatPromptTemplate.from_messages([
    #     ("system", """You are an AI evaluation agent assigned to score a candidate across four communication factors:
    # 1. **Confidence**
    # 2. **Presence**
    # 3. **Structure and Articulation**
    # 4. **Impact**
    # You will be provided with:
    # - The candidate's **transcript**: {transcript}
    # - The audio metrics : {audio_metrics}
    # - The video metrics : {video_metrics}
    # Scoring Guidelines:
    # Rate each of the following on a scale of **1 to 5**, based solely on the transcript and audio metrics and video metrics :
    # - **Confidence**: Vocal fluency, steadiness, assertiveness.
    # - **Presence**: Posture, eye contact, engagement.
    # - **Structure and Articulation**: Clarity and logical flow of ideas.
    # - **Impact**: Overall persuasiveness and memorability.
    # Output Format:
    # Respond only with a **clean JSON object** containing numeric scores:
    
    # "Confidence": <1-5>,
    # "Presence": <1-5>,
    # "Structure_and_Articulation": <1-5>,
    # "Impact": <1-5>
    
    # """), 
    #     ("user", "transcript : {transcript}, audio_metrics : {audio_metrics}, video_metrics : {video_metrics}")
    # ])
    
    # chain = prompt_template | model | output_parser 
    # output = chain.invoke({'transcript' : transcription_output,'audio_metrics' : audio_metrics, 'video_metrics' : video_metrics})
    # with open("json/graph.json" , "w") as fp:
    #     json.dump(output , fp=fp)
    with open("json/presentation.json" , 'r') as fp:
        data = json.load(fp) 
    mode = data.get("presentation_mode") 

    with open("json/scores.json" , 'r') as fp:
        scores = json.load(fp) 
    

    if mode == "on":
        confidence = round((scores.get("question1") + scores.get("question14"))/2)
        presence = round((scores.get("question1") + scores.get("question2") + scores.get("question3") + scores.get("question4"))/4)
        structure_and_articulation = round((scores.get("question5") + scores.get("question7") + scores.get("question8") + scores.get("question9") + scores.get("question10")) / 5) 
        impact = round((scores.get("question6") + scores.get("question11") + scores.get("question12") + scores.get("question13"))/4)
    else:
        confidence = round((scores.get("question1") + scores.get("question12"))/2) 
        presence = round((scores.get("question1") + scores.get("question2") + scores.get("question3") + scores.get("question4"))/4)
        structure_and_articulation = round((scores.get("question9") + scores.get("question10") + scores.get("question11"))/3) 
        impact = scores.get("question5")
    output= {"confidence" : confidence , "presence" : presence , "structure_and_articulation" : structure_and_articulation , "impact" : impact}
    with open("json/graph.json" , "w") as fp:
        json.dump(output , fp=fp)
    return output






