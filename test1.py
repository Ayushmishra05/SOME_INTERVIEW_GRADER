import openai

api_key = "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"

from langchain_openai import ChatOpenAI 

model = ChatOpenAI(model = 'gpt-3.5-turbo' , api_key = api_key) 

print(model.invoke("Hello Babes"))