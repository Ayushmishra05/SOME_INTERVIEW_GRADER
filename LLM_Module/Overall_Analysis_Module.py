import json
import yaml
import os
import asyncio
import logging
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from groq import APIError
from openai import RateLimitError
from dotenv import load_dotenv
from utils.MODEL_CONFIG import MODEL_FOR_OVERALL_ANALYSER
# import boto3 
from utils.get_api_key import get_api_key
load_dotenv()

# api_key = os.environ['OPENAI_API_KEY']




# print("API_KEY ==> " , api_key)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class VideoResumeEvaluator:
    def __init__(self, model_name="llama-3.3-70b-versatile", presentation_json_path="json/presentation.json",
                 output_json_path="json/output.json", audio_metrics_json_path="json/audio_metrics.json",
                 prompt_yaml_path="prompts/overall_prompt.yaml"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        with open(r'utils/openai_key.json' , 'r') as fp:
            data = json.load(fp)
        print("Model for Overall Analyser " , MODEL_FOR_OVERALL_ANALYSER)
        self.llm = ChatOpenAI(
            model=MODEL_FOR_OVERALL_ANALYSER,
            api_key=data['api_key']
        )
        self.output_parser = StrOutputParser()
        self.presentation_json_path = presentation_json_path
        self.output_json_path = output_json_path
        self.audio_metrics_json_path = audio_metrics_json_path
        
        # Read all files during initialization
        try:
            with open(presentation_json_path, "r") as file:
                data = json.load(file)
            self.presentation_mode = data.get("presentation_mode", False)
            logger.info(f"Loaded presentation from {presentation_json_path}")
        except Exception as e:
            logger.error(f"Error reading presentation JSON: {e}")
            raise
        
        try:
            with open(output_json_path, 'r') as file:
                data = json.load(file)
            posture = data.get("posture", "neutral")
            eye_contact = data.get("Eye Contact", "neutral")
            energetic = data.get("Energetic Start", "neutral")
            smile = data.get("Smile Score", "neutral")
            logger.info(f"Loaded output from {output_json_path}")
        except Exception as e:
            logger.error(f"Error reading output JSON: {e}")
            raise
        
        try:
            with open(audio_metrics_json_path, 'r') as file:
                data = json.load(file)
            volume_std = data.get("volume_std", "neutral")
            speaking_speed = data.get("speaking_speed", "neutral")
            predicted_tone = data.get("predicted_tone", "neutral")
            average_volume = data.get("average_volume", "neutral")
            logger.info(f"Loaded audio metrics from {audio_metrics_json_path}")
        except Exception as e:
            logger.error(f"Error reading audio metrics JSON: {e}")
            raise
        
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
        
        try:
            with open(prompt_yaml_path, "r") as file:
                yaml_data = yaml.safe_load(file)
            system_prompt = yaml_data["interview_prompt"]["system"]
        except Exception as e:
            logger.error(f"Error reading prompt YAML: {e}")
            raise
        
        if self.presentation_mode == "on":
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", f"{system_prompt}"),
                ("user", """
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
                """)
            ])
        else:
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", "You are an expert interviewer evaluating a video resume based on a transcription and provided audio metrics and video metrics. Keep the answers a little concise and straight to the point."),
                ("user", """
    Transcription: {transcription_input}
    Audio Metrics : {audio_metrics}
    Video Metrics : {video_metrics}

    Questions:
    1. Did the Speaker Speak with Confidence? (One line answer)
    2. Did the speaker vary their tone, speed, volume? Here are the details provided about the tone, speed, pace, and volume, {audio_metrics}, I want you 
    to give the answer in a sentence format, (For ex : The Tone and Volume was appropriate. you could have maintained a steady Speed in Delivery. A few Words were pronounced very fast), I want you to give the answer in a proper sentence like the example, and doesn't provide the numerical metrics to user, it should be in sentence, but dont tell like, dont tell your that your tone was neutrl/sad/happy, say that your maintained a good tone, this is an example)
    3. Did they use any gestures with their hands or body while speaking? Refer to the video metrics here {video_metrics} (Give one to two line descriptive answer)
    4. Did they have expressions on their faces? (Give a one line answer, give the judgement based on video metrics {video_metrics})
    5. Did the Person was able to introduce about them, their skills, and their personality traits? (Give a one line answer, including the point)
    6. Why are you the best person to fit this role? (Give a one line answer, including the point, where he/she performed well/bad)
    7. How are you different from others? (One line descriptive answer)
    8. What value do you bring to the role? (Descriptive answer)
    9. Did the speech have a structure of Opening, Body and Conclusion? (Descriptive answer)
    10. How was the quality of research for the topic? Did the student’s speech demonstrate a good depth? Did they cite the sources of research properly? (Descriptive answer)
    11. How creatively did the student present the video? (Descriptive answer)
    12. How convinced were you with the overall speech on the topic? Was it persuasive? Will you give them the job/opportunity? (Descriptive answer)
    Only provide the answers to these questions—do not include any extra commentary. 
    Start your response with "These are the Answers:" and then list each answer on a new line. Refer the user as You, it should be like you are directly talking to him
                """)
            ])
        
        self.chain = self.prompt_template | self.llm | self.output_parser

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APIError, asyncio.TimeoutError))
    )

    async def evaluate_transcription(self, transcription_output_path): 
        with open(transcription_output_path , 'r') as f:
            transcription = json.dumps((json.load(f)))
        try:
            output = await self.chain.ainvoke({
                'transcription_input': transcription,
                'audio_metrics': self.audio_metrics,
                'video_metrics': self.video_metrics
            })
            await asyncio.sleep(6)
            logger.info(f"Evaluation result from {self.output_json_path}: {output[:100]}...")
            return output
        except APIError as e:
            logger.error(f"Groq API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during evaluation: {e}")
            raise