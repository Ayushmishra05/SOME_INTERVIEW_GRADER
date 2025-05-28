import matplotlib.pyplot as plt 
import json   # Assume a 5-point scale
import matplotlib.pyplot as plt
import numpy as np
from LLM_Module.graph_LLM import graph_analyser





def generate_radar_chart(output_path='radar_chart.png'):
    graph_analyser()
    values = []
    labels = []
    with open(r'json/graph.json' , 'r') as fp:
        data = json.load(fp)
    print("Printing Graph Data" , data)
    items = list(data.items()) 
    for i in range(len(items)):
        values.append(items[i][1])
        labels.append(items[i][0])
    
    plt.plot(labels, values, marker="s")
    plt.grid(axis='x', which='both', linestyle='-', linewidth=1.5, color='gray', alpha=0.6)
    plt.tight_layout()
    plt.xlabel("Parameters")
    plt.ylabel("Percentage") 
    plt.title("Scores", fontsize=16, fontweight='bold' )
    ax = plt.gca()  
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.savefig(output_path, bbox_inches='tight', pad_inches=0.2)
    plt.close()



generate_radar_chart("output.png")