
import json
import dash
import pandas as pd
import plotly.express as px

with open('test.json') as f_in:
    gpu_log = json.load(f_in)
    
gpu_log_0 = gpu_log['0']

df = pd.DataFrame({'util': gpu_log_0['util'], 'mem_used': [mem_used / gpu_log_0['mem_all'] * 100 for mem_used in gpu_log_0['mem_used']], 'time': gpu_log_0['h']})

fig = px.histogram(df, x="time", y="util", histfunc='avg', nbins=len(set(gpu_log_0['h'])))

fig.show()