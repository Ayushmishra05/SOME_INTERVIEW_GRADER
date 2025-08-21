import re
import json
import yaml
import os
import asyncio
import logging
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from groq import APIError
from openai import RateLimitError
from dotenv import load_dotenv
load_dotenv()

api_key = os.environ['OPENAI_API_KEY']



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoResumeEvaluator2:
    def __init__(self, model_name="llama-3.3-70b-versatile", prompt_yaml_path="prompts/qualitative_prompt.yaml", output_json_path="json/quality_analysis.json"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("GROQ_API_KEY environment variable not set")
            raise ValueError("GROQ_API_KEY not set")
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=api_key
        )
        self.output_parser = JsonOutputParser()
        self.output_json_path = output_json_path
        
        try:
            with open(prompt_yaml_path, "r") as f:
                yaml_data = yaml.safe_load(f)
                self.system_prompt = yaml_data["interviewer_prompt_detailed"]["system"]
        except Exception as e:
            logger.error(f"Error reading prompt YAML: {e}")
            raise
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", f"{self.system_prompt}"),
            ("user", """
Transcription: {transcription_input}

You have to Evaluate Candidate's Performance based on two criteria's Qualitative Analysis and Quantitative Analysis
you will be provided with the transcription of the candidate,
Give at least 3 points in the Section of Qualitative Analysis make it clear and concise, in qualitative analysis, you have to talk about the Positives of the candidate
Give your answers in this format (e.g : "You delivered the presentation with a clear voice and tone", "Your articulation was up to the mark", "Overall a very confident presentation.")
You can directly Point out the user, in whichever point you want.
and in case of Quantitative Analysis, Give at least 5 points, make it clear and concise, In Quantitative Analysis, talks about the Areas of Improvement, Talk About where user can improve, and give your output finally in dictionary format something like this.
In a json format
             {{
             "Qualitative Analysis" : (your answer in points), 
             "Quantitative Analysis": (your answer in points)
             }}
             but ensure all the values which you are giving inside list should be in double quotes, Remember this very carefully, that should be in carefully, this is a strict requirement No extras, i only need the JSON Output, Remember this very Carefully, and also You are not allowed to talk about the feature, which you don't know, like you can't talk
about his tone, posture, because you don't know about this, but you have the transcription, so try to give the points only on those basis ,  Refer the user as You, it should be like you are directly talking to him.
            """)
        ])
        
        self.chain = self.prompt_template | self.llm | self.output_parser

    def clean_transcription(self, text: str) -> str:
        cleaned_text = re.sub(r'\[\d+\.\d+s\s*-\s*\d+\.\d+s\]', '', text)
        return ' '.join(cleaned_text.split())
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APIError, asyncio.TimeoutError))
    )



    async def evaluate_transcription(self, transcription_data):
        # if isinstance(transcription_data, dict):
        #     text = transcription_data.get('text', '')
        # else:
        #     text = transcription_data
        # if not text.strip():
        #     logger.error("Transcription text must not be empty")
        #     raise ValueError("Transcription text must not be empty")
        
        # cleaned_text = self.clean_transcription(text)
        with open(transcription_data , 'r') as f:
            transcription = json.dumps(json.load(f))

        # if not text:
        #     logger.error("Transcription text is empty or missing")
        #     raise ValueError("Transcription text is empty or missing")

        # cleaned_text = self.clean_transcription(text)
                
        try:
            output = await self.chain.ainvoke({
                'transcription_input': transcription
            })
            await asyncio.sleep(6)
            # print("Printing Output " , output)
            if not isinstance(output, dict) or "Qualitative Analysis" not in output or "Quantitative Analysis" not in output:
                logger.error("Invalid output format from LLM")
                raise ValueError("LLM output does not match expected JSON format")
            
            # Write output to JSON file in a thread-safe manner
            await asyncio.to_thread(
                json.dump, output, open(self.output_json_path, 'w'),
                indent=4, ensure_ascii=False
            )
            logger.info(f"Saved qualitative analysis to {self.output_json_path}")
            return output
        except APIError as e:
            logger.error(f"Groq API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during evaluation: {e}")
            raise