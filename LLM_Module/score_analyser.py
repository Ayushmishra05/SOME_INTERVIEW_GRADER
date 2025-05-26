import yaml
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
import os 
import json 
from langchain_openai import ChatOpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o"

def load_prompts():
    with open("prompts/Score_Prompts.yaml", "r") as file:
        return yaml.safe_load(file)

PROMPTS = load_prompts()

with open('json/transcription_output.json', 'r') as file:
    transcription_output = json.load(file)

    
with open('json/output.json', 'r') as file:
    audio_metrics = json.load(file)

with open("json/output.json", "r") as f:
    data = json.load(f)

answer = data["LLM"]

def phaser():
    llm = ChatOpenAI(model=MODEL, api_key=api_key)
    with open('json/presentation.json', 'r') as file:
        data = json.load(file)
    presentation_mode = data.get("presentation_mode", False)

    questions = []  
    questions_pm = [] 

    questions_text = "\n".join(questions_pm if presentation_mode == "on" else questions)
    
    prompt_set = PROMPTS["presentation_mode_on"] if presentation_mode == "on" else PROMPTS["presentation_mode_off"]
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", prompt_set["system"]),
        ("user", prompt_set["user"])
    ])
    
    output_parser = JsonOutputParser()
    chain = prompt_template | llm | output_parser
    evaluation = chain.invoke({
        "question": questions_text,
        "answer": str(answer)
    })
    
    with open("json/evaluation.json", "w") as file:
        json.dump(evaluation, file, indent=4)
    return evaluation

evaluation = phaser()

with open('json/evaluation.json', 'r') as file:
    evaluation = json.load(file)

def score_analyser(transcription, audio_metrics, video_metrics, evaluation):
    model = ChatOpenAI(model=MODEL, api_key=api_key)
    output_parser = JsonOutputParser()

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", PROMPTS["scoring"]["system"]),
        ("user", PROMPTS["scoring"]["user"])
    ])

    chain = prompt_template | model | output_parser
    output = chain.invoke({
        'transcript': str(transcription),
        'audio_metrics': str(audio_metrics),
        'video_metrics': str(video_metrics),
        'evaluation': str(evaluation)
    })
    return output


