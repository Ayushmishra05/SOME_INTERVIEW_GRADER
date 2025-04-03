from langchain_groq import ChatGroq 
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.llms import Ollama
from langchain_groq import ChatGroq


def score_analyser(transcription_output) :
    model = ChatGroq(model = 'llama-3.3-70b-versatile')
    output_parser = JsonOutputParser()
    prompt_template = ChatPromptTemplate.from_messages([
                ("system", 
                "You are an expert Scorer, you will be provided with the Interviewers Desctiptive Scoring for the candidates performance, Your task is to SImply Score the result of the candidate based on the Interviewers Descripting Scoring, The Scoring can either Contain in the Priority, Needs Improvement -> Poor -> Satisfactory -> Good -> Excellent , simply give the "
                "score in the JSON Format, like question1 : <score> , question2 : <score> .... and similarly all the questions provided, only json file, no extras , nad no explanation, nothing extra"),
                ("user", 
                """
    Descriptive_Scoring: {Scores}
                """
                )
            ])
    chain = prompt_template | model | output_parser  
    output = chain.invoke({'Scores' : transcription_output})
    return output 




