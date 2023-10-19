
import json
from dash import Dash, dcc, html, Input, Output, callback
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
import pexpect
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import defaultdict

ip_map = {
    'falcon': 'falcon.cs.illinois.edu',
    'owl': 'owl.cs.illinois.edu',
    'owl2': 'owl2.cs.illinois.edu',
    'owl3': 'owl3.cs.illinois.edu',
    'osprey1': 'osprey1.csl.illinois.edu',
    'osprey2': 'osprey2.csl.illinois.edu'
}

netid = input('Your netid: ')
password = input('Your netid password: ')

servers = [server.lower() for server in sys.argv[1:]]
if not servers:
    servers = list(ip_map.keys())
    
layout = []
for server in servers:
    child = pexpect.spawn(f'scp {netid}@{ip_map[server]}:/scratch/Forward_gpu/log.json /scratch/Forward_gpu/{server}_log.json')
    choice = child.expect([f"{netid}@{ip_map[server]}'s password:", '.*Are you sure you want to continue connecting.*'])
    if choice == 0:
        child.sendline(password)
    else:
        child.sendline('yes')
        child.expect(f"{netid}@{ip_map[server]}'s password:")
        child.sendline(password)
    time.sleep(3)

    with open(f'{server}_log.json') as f_in:
        gpu_log:dict = json.load(f_in)

    df = pd.concat([pd.DataFrame({
        'usage (%)': gpu_log_['util'] + [mem_used / gpu_log_['mem_all'] * 100 for mem_used in gpu_log_['mem_used']], 
        'resource': (['util'] * len(gpu_log_['util'])) + (['mem_use'] * len(gpu_log_['util'])),
        'time': [datetime(y, m, d, h).isoformat() for y, m, d, h in zip(gpu_log_['y'], gpu_log_['m'], gpu_log_['d'], gpu_log_['h'])] * 2, 
        'gpu_id': gpu_id}) for gpu_id, gpu_log_ in gpu_log.items()])

    fig = px.histogram(df, x="time", y='usage (%)', histfunc='avg', facet_col='gpu_id', facet_row='resource')
    fig.update_layout(bargap=0.2)
    
    layout.append(html.Button(html.H2(server.capitalize()), "%s_button" % server, 0, style={'width': '100%'}))
    sub_dash = []
    sub_dash.append(dcc.Graph(figure=fig))

    for gpu_id, gpu_log_ in gpu_log.items():
        hours = [1, 8, 24, 72]
        labels = []
        values = []
        is_enoughs = []
        p: dict
        for step_num in [60 * h for h in hours]:
            user2mem = defaultdict(int)
            cnt = 0
            for p in gpu_log_['p'][-step_num:]:
                if p == 0:
                    continue
                cnt += 1
                unused = gpu_log_['mem_all']
                for user, mem_use in p.items():
                    user2mem[user] += mem_use
                    unused -= mem_use
                user2mem['Unused'] += unused
            labels_per_plot, values_per_plot = list(zip(*user2mem.items()))
            labels.append(labels_per_plot)
            values.append(values_per_plot)
            is_enoughs.append(cnt == step_num)
            
        fig = make_subplots(rows=1, cols=len(hours), specs=[[{'type':'domain'}] * len(hours)], 
                            subplot_titles=["GPU memory users in last %dh." % h for h in hours])
        for i, (labels_per_plot, values_per_plot, is_enough) in enumerate(zip(labels, values, is_enoughs)):
            if is_enough:
                fig.add_trace(go.Pie(labels=labels_per_plot, values=values_per_plot),
                            1, 1 + i)

        fig.update_traces(hoverinfo="label+percent+name")
        fig.update_layout(title_text = 'GPU %s' % gpu_id)
        sub_dash.append(dcc.Graph(figure=fig))
    layout.append(html.Div(sub_dash, "%s_collapse" % server))

app = Dash(__name__)

app.layout = html.Div(layout)

@callback(
    [Output("%s_collapse" % server, "style") for server in servers],
    [Input("%s_button" % server, "n_clicks") for server in servers]
)
def toggle_collapse(*args):
    return [{'display': 'block' if num_clicks % 2 else 'none'}  for num_clicks in args]
        
    # return {'display': 'block', 'border': '2px black solid'} if num_clicks1 % 2 else {'display': 'none', 'border': '2px black solid'}, {'display': 'block', 'border': '2px black solid'} if num_clicks2 % 2 else {'display': 'none', 'border': '2px black solid'}

app.run_server(port='8049')