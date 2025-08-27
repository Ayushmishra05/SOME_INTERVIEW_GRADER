import json 

with open(r'utils/tuned.json' , 'r') as fp:
    data = json.load(fp)


"""
From file import the json format for the model configuration 
"""


MODEL_FOR_OVERALL_ANALYSER = data.get('overall' , 'gpt-4')
MODEL_FOR_QUALITATIVE_ANALYSER = data.get('qualitative' , 'gpt-4') 
MODEL_FOR_SCORE_ANALYSER = data.get('score' , 'gpt-4')

P_QUESTION_1 = data.get("p_question_1" , '100')
P_QUESTION_2 = data.get("p_question_2" , '100')
P_QUESTION_3 = data.get("p_question_3" , '100')
P_QUESTION_4 = data.get("p_question_4" , '100')
P_QUESTION_5 = data.get("p_question_5" , '100')
P_QUESTION_6 = data.get("p_question_6" , '100')
P_QUESTION_7 = data.get("p_question_7" , '100')
P_QUESTION_8 = data.get("p_question_8" , '100')
P_QUESTION_9 = data.get("p_question_9" , '100')
P_QUESTION_10 = data.get("p_question_10" , '100')
P_QUESTION_11 = data.get("p_question_11" , '100')
P_QUESTION_12 = data.get("p_question_12" , '100')
P_QUESTION_13 = data.get("p_question_13", '100')
P_QUESTION_14 = data.get("p_question_14" , '100')

V_QUESTION_1 = data.get("v_question_1" , '100')
V_QUESTION_2 = data.get("v_question_2" , '100')
V_QUESTION_3 = data.get("v_question_3" , '100')
V_QUESTION_4 = data.get("v_question_4" , '100')
V_QUESTION_5 = data.get("v_question_5" , '100')
V_QUESTION_6 = data.get("v_question_6" , '100')
V_QUESTION_7 = data.get("v_question_7" , '100')
V_QUESTION_8 = data.get("v_question_8" , '100')
V_QUESTION_9 = data.get("v_question_9" , '100')
V_QUESTION_10 = data.get("v_question_10" , '100')
V_QUESTION_11 = data.get("v_question_11" , '100')
V_QUESTION_12 = data.get("v_question_12" , '100')

print(MODEL_FOR_OVERALL_ANALYSER)
print(MODEL_FOR_QUALITATIVE_ANALYSER)
print(MODEL_FOR_SCORE_ANALYSER)
print(P_QUESTION_1)
print(P_QUESTION_2)
print(P_QUESTION_3)
print(P_QUESTION_4)
print(P_QUESTION_5)
print(P_QUESTION_6)
print(P_QUESTION_9)
print(P_QUESTION_8)
print(P_QUESTION_10)
print(P_QUESTION_11)
print(P_QUESTION_12)
print(P_QUESTION_13)
print(P_QUESTION_14)


print(V_QUESTION_1)
print(V_QUESTION_2)
print(V_QUESTION_3)
print(V_QUESTION_4)
print(V_QUESTION_5)
print(V_QUESTION_6)
print(V_QUESTION_7)
print(V_QUESTION_8)
print(V_QUESTION_9)
print(V_QUESTION_10)
print(V_QUESTION_11)
print(V_QUESTION_12)