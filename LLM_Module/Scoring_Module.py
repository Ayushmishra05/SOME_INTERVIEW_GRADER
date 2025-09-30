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
from utils.MODEL_CONFIG import config
from utils.get_api_key import get_api_key

load_dotenv(override=True)

api_key = os.environ['OPENAI_API_KEY']
# Configure logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type((RateLimitError, APIError, asyncio.TimeoutError))
)

async def score_analyser(
    transcription_output,  # Ignored (eval_results from Overall_Analyser)
    transcription_json_path,
    presentation_json_path,
    output_json_path,
    audio_metrics_json_path,
    prompt_yaml_path="prompts/score_analyser.yaml"
):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY environment variable not set")
        raise ValueError("GROQ_API_KEY not set")
    with open(r'utils/openai_key.json' , 'r') as fp:
        data = json.load(fp)
    print("Model for Score Analyser " , config.MODEL_FOR_SCORE_ANALYSER)
    model = ChatOpenAI(
        model=config.MODEL_FOR_SCORE_ANALYSER,
        api_key=api_key
    )
    output_parser = JsonOutputParser()
    
    try:
        with open(transcription_json_path, 'r', encoding='utf-8') as file:
            transcription_data = json.load(file)
        if not transcription_data or not isinstance(transcription_data, list):
            logger.error("Invalid transcription data: must be a non-empty list")
            raise ValueError("Invalid transcription data")
        logger.info(f"Loaded transcription from {transcription_json_path}, segments: {len(transcription_data)}")
    except Exception as e:
        logger.error(f"Error reading transcription JSON: {e}")
        raise
    
    try:
        with open(presentation_json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        presentation_mode = data.get("presentation_mode", False)
        logger.info(f"Loaded presentation from {presentation_json_path}")
    except Exception as e:
        logger.error(f"Error reading presentation JSON: {e}")
        raise
    
    try:
        with open(output_json_path, 'r', encoding='utf-8') as file:
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
        with open(audio_metrics_json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        volume_std = data.get("volume_std", "neutral")
        speaking_speed = data.get("speaking_speed", "neutral")
        predicted_tone = data.get("predicted_tone", "neutral")
        average_volume = data.get("average_volume", "neutral")
        logger.info(f"Loaded audio metrics from {audio_metrics_json_path}")
    except Exception as e:
        logger.error(f"Error reading audio metrics JSON: {e}")
        raise
    
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
    
    logger.info("----------SCORE-----------------")
    logger.info(audio_metrics)
    logger.info("----------SCORE-----------------")
    logger.info(video_metrics)
    
    if presentation_mode == "on":
        questions = f"""
            "Did the Speaker Speak with Confidence ? (Weightage {config.P_QUESTION_1}%)", 
            "Did the speaker vary their tone, speed, volume while delivering the speech/presentation? (Weightage {config.P_QUESTION_2}%)",
            "Did they use any gestures with their hands or body while speaking? (Weightage {config.P_QUESTION_3}%)" , 
            "Did they have expressions on their faces? (Weightage {config.P_QUESTION_4}%)",
            "Did the speech have a structure of Opening, Body and Conclusion? (Weightage {config.P_QUESTION_5}%)",
            "Did the speaker keep the presentation engaging by adding relevant examples, anecdotes and data to back their content?  (Weightage {config.P_QUESTION_6}%)", 
            "Was the overall “Objective” of the speech delivered clearly? (Weightage {config.P_QUESTION_7}%)", 
            "Was the content of the presentation/speech to the point, or did it include unnecessary details that may have distracted or confused the audience? (Weightage {config.P_QUESTION_8}%)", 
            "Was the content of the presentation/speech relevant to the objective of the presentation? (Weightage {config.P_QUESTION_9}%)",
            "Was the content of the presentation/speech clear and easy to understand? (Weightage {config.P_QUESTION_10}%)", 
            "Did the speaker demonstrate credibility? Will you trust the speaker? (Weightage {config.P_QUESTION_11}%)", 
            "Did the speaker explain how the speech or topic of the presentation would benefit the audience and what they could gain from it? (Weightage {config.P_QUESTION_12}%)", 
            "Did the speaker make an emotional connection with the audience ? (Weightage {config.P_QUESTION_13}%)", 
            "Overall, were you convinced/ persuaded with the speaker’s view on the topic? (Weightage {config.P_QUESTION_14}%)"
        """
    else:
        questions = f"""
            "Did the Speaker Speak with Confidence ? (Weightage {config.V_QUESTION_1}%)", 
            "Did the speaker vary their tone, speed, volume? (Weightage {config.V_QUESTION_2}%)",
            "Did they use any gestures with their hands or body while speaking? (Weightage {config.V_QUESTION_3}%)",
            "Did they have expressions on their faces? (Weightage {config.V_QUESTION_4}%)",
            "Who are you and what are your skills, expertise, personality traits ? (Weightage {config.V_QUESTION_5}%)",
            "Why are you the best person to fit this role? (Weightage {config.V_QUESTION_6}%)",
            "How are you different from others? (Weightage {config.V_QUESTION_7}%)",
            "What value do you bring to the role? (Weightage {config.V_QUESTION_8}%)", 
            "Did the speech have a structure of Opening, Body and Conclusion? (Weightage {config.V_QUESTION_9}%)",
            "How was the quality of research for the topic? Did the student’s speech demonstrate a good depth? Did they cite the sources of research properly? (Weightage {config.V_QUESTION_10}%)", 
            "How creatively did the student present the video? (Weightage {config.V_QUESTION_11}%)", 
            "How convinced were you with the overall speech on the topic? Was it persuasive? Will you give them the job/opportunity? (Weightage {config.V_QUESTION_12}%)"
        """
    
    try:
        with open(prompt_yaml_path, "r") as file:
            yaml_data = yaml.safe_load(file)
        system_prompt = yaml_data["interviewer_scorer_prompt"]["system"]
    except Exception as e:
        logger.error(f"Error reading prompt YAML: {e}")
        raise
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", f"{system_prompt}"),
        ("user", """
    Interviewer's Questions : {questions} , Descriptive_Scoring: {Scores}, Audio Metrics : {audio_metrics}, Video Metrics : {video_metrics}
        """)
    ])
    
    chain = prompt_template | model | output_parser
    
    # Extract transcription text from JSON
    transcription_text = " ".join(segment['text'] for segment in transcription_data)
    
    try:
        output = await chain.ainvoke({
            'Scores': json.dumps(transcription_output),
            'questions': questions,
            'audio_metrics': audio_metrics,
            'video_metrics': video_metrics
        })
        await asyncio.sleep(6)
        logger.info(f"Scoring result: {output}")
        return output
    except APIError as e:
        logger.error(f"Groq API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during scoring: {e}")
        raise
