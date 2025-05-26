from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import os
import yaml
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
model_name = "gpt-4o"

# Load YAML prompt
def load_prompts():
    with open("prompts/Overall_Prompts.yaml", "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

prompts = load_prompts()

def overall_analyser(transcription_input, audio_metrics, presentation_mode="off"):
    print("Entered Overall Analyser")
    llm = ChatOpenAI(model=model_name, api_key=api_key)
    output_parser = StrOutputParser()

    # Select prompt set
    selected_prompt = prompts["presentation"] if presentation_mode == "on" else prompts["non_presentation"]

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", selected_prompt["system"]),
        ("user", selected_prompt["user"])
    ])

    chain = prompt_template | llm | output_parser
    response = chain.invoke({
        "transcription_input": transcription_input,
        "audio_metrics": audio_metrics
    })
    return response
