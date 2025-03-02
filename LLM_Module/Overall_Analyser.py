from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import Ollama
from langchain_groq import ChatGroq
from audio_module.audio_analysis import analyze_audio_metrics
from config import audio_path, transcription_path 

class VideoResumeEvaluator:
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        self.llm = ChatGroq(model=model_name)
        self.output_parser = StrOutputParser()
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert interviewer evaluating a video resume based on a transcription and provided audio metrics. For questions 3–6, provide only a rating (no explanation)."),
            ("user", 
             """
Transcription: {transcription_input}

Questions:
1. Did the Speaker Speak with Confidence? (One line answer)
2. Was the content interesting and as per the guidelines provided? (One line answer)
3. Who are you and what are your skills, expertise, and personality traits? (Provide only a rating: Needs Improvement, Poor, Satisfactory, or Excellent)
4. Why are you the best person to fit this role? (Provide only a rating: Excellent, Good, or Poor)
5. How are you different from others? (Provide only a rating: Excellent, Good, or Poor)
6. What value do you bring to the role? (Provide only a rating: Excellent, Good, or Poor)
7. Did the speech have a structure of Opening, Body, and Conclusion? (One line descriptive answer)
8. Did the speaker vary their tone, speed, and volume while delivering the speech/presentation? Here are the details provided about the tone, speed, pace, and volume, {audio_metrics}, I want you 
to give the answer in a sentence format, (For ex : The Tone and Volume was appropriate. you could have maintained a steady Speed in Delivery. A few Words were pronounced very fast), I want you to give the answer in a proper sentence like the example, and doesn't provide the numerical metrics to user, it should be in sentence, but dont tell like, dont tell your that your tone was neutrl/sad/happy, say that your maintained a good tone, this is an example
9. How was the quality of research for the topic? Did the speech demonstrate good depth and proper citations? (2-3 lines descriptive answer)
10. How convinced were you with the overall speech on the topic? Was it persuasive? Will you consider them for the job/opportunity? (Descriptive answer)
Only provide the answers to these questions—do not include any extra commentary. 
Start your response with "These are the Answers:" and then list each answer on a new line.
             """
            )
        ])
        
        self.chain = self.prompt_template | self.llm | self.output_parser

    def evaluate_transcription(self, transcription, audio_metrics=""):
        transcription_input = transcription
        # if audio_metrics:
        #     transcription_input += "\nAudio Analysis Metrics: " + str(audio_metrics)
        output = self.chain.invoke({
            'transcription_input': transcription_input, 
            'audio_metrics' : analyze_audio_metrics(audio_path , transcription_path)
        })
        return output
