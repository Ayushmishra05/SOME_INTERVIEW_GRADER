
import json
import os

CONFIG_FILE = r'utils/tuned.json'

def load_config():
    with open(CONFIG_FILE, 'r') as fp:
        return json.load(fp)

def get_value(key, default=None):
    data = load_config()
    return data.get(key, default)


"""
From file import the json format for the model configuration 
"""

# These are now *dynamic lookups* — whenever you use them, they reload from JSON
class Config:
    @property
    def MODEL_FOR_OVERALL_ANALYSER(self):
        return get_value('overall', 'gpt-4')

    @property
    def MODEL_FOR_QUALITATIVE_ANALYSER(self):
        return get_value('qualitative', 'gpt-4')

    @property
    def MODEL_FOR_SCORE_ANALYSER(self):
        return get_value('score', 'gpt-4')

    @property
    def P_QUESTION_1(self): return get_value("p_question_1", '100')
    @property
    def P_QUESTION_2(self): return get_value("p_question_2", '100')
    @property
    def P_QUESTION_3(self): return get_value("p_question_3", '100')
    @property
    def P_QUESTION_4(self): return get_value("p_question_4", '100')
    @property
    def P_QUESTION_5(self): return get_value("p_question_5", '100')
    @property
    def P_QUESTION_6(self): return get_value("p_question_6", '100')
    @property
    def P_QUESTION_7(self): return get_value("p_question_7", '100')
    @property
    def P_QUESTION_8(self): return get_value("p_question_8", '100')
    @property
    def P_QUESTION_9(self): return get_value("p_question_9", '100')
    @property
    def P_QUESTION_10(self): return get_value("p_question_10", '100')
    @property
    def P_QUESTION_11(self): return get_value("p_question_11", '100')
    @property
    def P_QUESTION_12(self): return get_value("p_question_12", '100')
    @property
    def P_QUESTION_13(self): return get_value("p_question_13", '100')
    @property
    def P_QUESTION_14(self): return get_value("p_question_14", '100')

    @property
    def V_QUESTION_1(self): return get_value("v_question_1", '100')
    @property
    def V_QUESTION_2(self): return get_value("v_question_2", '100')
    @property
    def V_QUESTION_3(self): return get_value("v_question_3", '100')
    @property
    def V_QUESTION_4(self): return get_value("v_question_4", '100')
    @property
    def V_QUESTION_5(self): return get_value("v_question_5", '100')
    @property
    def V_QUESTION_6(self): return get_value("v_question_6", '100')
    @property
    def V_QUESTION_7(self): return get_value("v_question_7", '100')
    @property
    def V_QUESTION_8(self): return get_value("v_question_8", '100')
    @property
    def V_QUESTION_9(self): return get_value("v_question_9", '100')
    @property
    def V_QUESTION_10(self): return get_value("v_question_10", '100')
    @property
    def V_QUESTION_11(self): return get_value("v_question_11", '100')
    @property
    def V_QUESTION_12(self): return get_value("v_question_12", '100')


# Create a single instance
config = Config()

# Now you can use variables like before:
print(config.MODEL_FOR_OVERALL_ANALYSER)
print(config.P_QUESTION_1)
print(config.V_QUESTION_10)

