
import json
from dash import Dash, dcc, html, Input, Output
import pandas as pd
import plotly.express as px
from datetime import datetime

with open('log.json') as f_in:
    gpu_log:dict = json.load(f_in)

df = pd.concat([pd.DataFrame({
    'usage (%)': gpu_log_['util'] + [mem_used / gpu_log_['mem_all'] * 100 for mem_used in gpu_log_['mem_used']], 
    'resource': (['util'] * len(gpu_log_['util'])) + (['mem_use'] * len(gpu_log_['util'])),
    'time': [datetime(y, m, d, h).isoformat() for y, m, d, h in zip(gpu_log_['y'], gpu_log_['m'], gpu_log_['d'], gpu_log_['h'])] * 2, 
    'gpu_id': k}) for k, gpu_log_ in gpu_log.items()])

fig = px.histogram(df, x="time", y='usage (%)', histfunc='avg', facet_col='gpu_id', facet_row='resource')
fig.update_layout(bargap=0.2)


app = Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id="graph", figure=fig),
])


app.run_server(debug=True)