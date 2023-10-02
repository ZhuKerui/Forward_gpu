import subprocess
from collections import defaultdict
import time
from statistics import mean
from datetime import datetime
import json
import os

def get_gpu_sum(s:str):
    s = s.strip().split('|===============================+======================+======================|')[1]
    overall_usage, pids = s.split('+-----------------------------------------------------------------------------+\n')

    datas = overall_usage.strip().split('+-------------------------------+----------------------+----------------------+')
    datas = [l.strip() for l in datas if l]
    pids = pids.split('|=============================================================================|\n')[1].split('\n')[:-1]

    gpu_sum = defaultdict(lambda: {'p': [], 'mem_used': 0, 'mem_all': 0, 'util': 0})
    for data in datas:
        data_lines = data.split('\n')
        gpu_id = data_lines[0].strip('| ').split('|')[0].split()[0]
        _, mem_data, util = data_lines[1].strip('| ').split('|')
        mem_used, mem_all = mem_data.strip().split(' / ')
        mem_used = int(mem_used.split('MiB')[0])
        mem_all = int(mem_all.split('MiB')[0])
        util = int(util.split()[0][:-1])
        gpu_sum[gpu_id]['mem_used'] = mem_used
        gpu_sum[gpu_id]['mem_all'] = mem_all
        gpu_sum[gpu_id]['util'] = util
        
    for pid in pids:
        if 'No running processes found' in pid:
            break
        pid_data = pid.strip('| ').split()
        gpu_id = pid_data[0]
        pid_id = pid_data[3]
        memory = int(pid_data[-1].split('MiB')[0])
        try:
            user = subprocess.run(['ps', 'u', pid_id], stdout=subprocess.PIPE).stdout.decode('utf-8').split('\n')[1].split()[0]
            gpu_sum[gpu_id]['p'].append((user, memory))
        except:
            print('Process has been killed.')
    return gpu_sum


gpu_utils = defaultdict(list)
gpu_mem_useds = defaultdict(list)
gpu_mem_alls = defaultdict(int)
gpu_users = defaultdict(lambda: defaultdict(int))

type_map = {
    'util': list,
    'mem_used': list,
    'y': list, 
    'm': list, 
    'd': list, 
    'h': list, 
    'mem_all': int, 
    'p': list
}
if os.path.exists('log.json'):
    with open('log.json') as f_in:
        gpu_log:dict = json.load(f_in)
        gpu_data:dict
        for gpu_id, gpu_data in gpu_log.items():
            for k, t in type_map.items():
                if k not in gpu_data:
                    previous_length = 0
                    for exist_k, exist_data in gpu_data.items():
                        if isinstance(exist_data, list):
                            previous_length = len(exist_data)
                            break
                    if t == list and previous_length:
                        gpu_data[k] = [0] * previous_length
                    else:
                        gpu_data[k] = t()
else:
    gpu_log = defaultdict(lambda: {'util': [], 'mem_used': [], 'y': [], 'm': [], 'd': [], 'h': [], 'mem_all': 0, 'p': []})

while True:
    result = subprocess.run('nvidia-smi', stdout=subprocess.PIPE)
    s = result.stdout.decode('utf-8')
    gpu_sum = get_gpu_sum(s)
    for gpu_id, gpu_data in gpu_sum.items():
        gpu_utils[gpu_id].append(gpu_data['util'])
        gpu_mem_useds[gpu_id].append(gpu_data['mem_used'])
        gpu_mem_alls[gpu_id] = gpu_data['mem_all']
        for user, user_mem in gpu_data['p']:
            gpu_users[gpu_id][user] += user_mem

    if len(gpu_utils['0']) == 6:
        dt = datetime.fromtimestamp(int(time.time()))
        for gpu_id in gpu_utils.keys():
            gpu_log[gpu_id]['util'].append(mean(gpu_utils[gpu_id]))
            gpu_log[gpu_id]['mem_used'].append(mean(gpu_mem_useds[gpu_id]))
            gpu_log[gpu_id]['mem_all'] = gpu_mem_alls[gpu_id]
            gpu_log[gpu_id]['y'].append(dt.year)
            gpu_log[gpu_id]['m'].append(dt.month)
            gpu_log[gpu_id]['d'].append(dt.day)
            gpu_log[gpu_id]['h'].append(dt.hour)
            gpu_log[gpu_id]['p'].append({user : user_mem_sum // 6 for user, user_mem_sum in gpu_users[gpu_id].items()})
            
        if len(gpu_log['0']['h']) >= 60*24*7 and dt.hour != gpu_log['0']['h'][-2]:
            for idx in range(len(gpu_log['0']['h'])):
                if gpu_log['0']['h'][idx] != gpu_log['0']['h'][idx + 1]:
                    for gpu_id in gpu_log.keys():
                        for k, v in gpu_log[gpu_id].items():
                            if k != 'mem_all':
                                gpu_log[gpu_id][k] = v[idx + 1:]
                    break
            
        gpu_utils = defaultdict(list)
        gpu_mem_useds = defaultdict(list)
        gpu_users = defaultdict(lambda: defaultdict(int))

        with open('log.json', 'w') as f_out:
            json.dump(gpu_log, f_out)
        
    time.sleep(10)