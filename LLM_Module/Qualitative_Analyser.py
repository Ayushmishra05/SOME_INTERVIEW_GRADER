import re
import json
import yaml
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os 

load_dotenv()

def load_prompt_from_yaml(yaml_file: str) -> ChatPromptTemplate:
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    return ChatPromptTemplate.from_messages([
        ("system", data['system']),
        ("user", data['user'])
    ])

def clean_transcription(text: str) -> str:
    cleaned_text = re.sub(r'\[\d+\.\d+s\s*-\s*\d+\.\d+s\]', '', text)
    return ' '.join(cleaned_text.split())

def infer_algorithm_from_trace(transcription_data, audio_metrics, video_metrics):
    model_name = "gpt-4o"
    api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(model=model_name, api_key=api_key)
    output_parser = JsonOutputParser()
    prompt_template = load_prompt_from_yaml("prompts/Qualitative_Prompts.yaml")
    chain = prompt_template | llm | output_parser
    if isinstance(transcription_data, dict):
        text = transcription_data.get('text', '')
    else:
        text = transcription_data
    if not text.strip():
        raise ValueError("Transcription text must not be empty.")
    cleaned_text = clean_transcription(text)
    llm_output = chain.invoke({
        "transcription_input": cleaned_text,
        "audio_metrics": audio_metrics,
        "video_metrics": video_metrics
    })
    with open('json/quality_analysis.json', 'w') as fp:
        json.dump(llm_output, fp, indent=2)
    return llm_output
