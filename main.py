#!/usr/bin/env python3
from string import Template
import argparse
import configparser
import os
import subprocess
import tempfile

from flask import Flask, Response, request
import requests as py3reqs

parser = argparse.ArgumentParser(
    description='Slack bot for rendering LaTeX formulas')
parser.add_argument('--host', type=str, dest='host', required=True)
parser.add_argument('--port', type=int, dest='port', required=True)
parser.add_argument('--config-file', type=str, dest='config_file',
                    required=True,
                    help='Path of an INI file containing Slack tokens')
parser.add_argument('--template-file', type=str, dest='template_file',
                    required=True,
                    help='Path of the .tex file used for rendering')

args = parser.parse_args()

config = configparser.ConfigParser()
config.read(args.config_file)
SLASH_COMMAND_TOKEN = config.get('Slack', 'slash_command_verification_token')
API_TOKEN = config.get('Slack', 'bot_user_api_token')
app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def render_latex():
    if request.form['token'] != SLASH_COMMAND_TOKEN:
        return Response("NOT AUTHORIZED" + str(request.values), 403)
    with tempfile.TemporaryDirectory() as work_dir:
        try:
            str2png(request.form['text'], work_dir)
        except Exception as e:
            print(e)
            return "Invalid LaTeX?"
        out_url = "https://slack.com/api/files.upload"
        payload = {}
        files = {'file':open(os.path.join(work_dir, 'out.png'), 'rb')}
        payload['token'] = API_TOKEN
        payload['filename'] = 'LaTeX.png'
        payload['initial_comment'] = '@' + request.form['user_name'] + ' ' + request.form['text']
        payload['channels'] = [request.form['channel_id']]
        r = py3reqs.post(out_url, params=payload, files=files)
        r.raise_for_status()
    return ""


def str2png(input_string, work_dir):
    with open(args.template_file,'r') as f:
        s = Template(f.read())
    out_txt = s.substitute(my_text=input_string)

    with open(os.path.join(work_dir, 'out.tex'),'w') as f:
        f.write(out_txt)
    subprocess.check_call(['pdflatex', '-halt-on-error', 'out.tex'], cwd=work_dir, stdout=None, stderr=None)
    subprocess.check_call(['convert', '-density', '300', 'out.pdf', '-quality', '100', '-sharpen', '0x1.0', 'out.png'], cwd=work_dir, stdout=None, stderr=None)

if __name__=="__main__":
    app.run(args.host, port=args.port)
