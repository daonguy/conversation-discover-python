# Copyright 2017 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from configparser import ConfigParser
from flask import Flask, jsonify, render_template, request, session, make_response

from watson_developer_cloud import DiscoveryV1
from watson_developer_cloud import ConversationV1
from watson_developer_cloud import NaturalLanguageUnderstandingV1
from watson_developer_cloud import ToneAnalyzerV3
import watson_developer_cloud.natural_language_understanding.features.v1 as features

# For discovery summerise
from gensim.summarization import summarize

# Set up configuation connection.
c = ConfigParser(allow_no_value=False)
c.readfp(open('config.ini'))

app = Flask(__name__)

# Set up conversation objects.
conversation = ConversationV1(
	version=c.get('conversation','version'),
	username=c.get('conversation','username'),
	password=c.get('conversation','password')
)
context = {}

# Set up NLU
nlu = NaturalLanguageUnderstandingV1( 
	version=c.get('nlu','version'),
	username=c.get('nlu','username'),
	password=c.get('nlu','password')
)

# Set up Tone Analzyer
tone_analyzer = ToneAnalyzerV3(
    username=c.get('tone_analyzer','username'),
    password=c.get('tone_analyzer','password'),
    version=c.get('tone_analyzer','version')
 )

# Set up Discovery
discovery = DiscoveryV1(
	version=c.get('discovery','version'),
	username=c.get('discovery','username'),
	password=c.get('discovery','password')
)

# Flask settings
app.secret_key = c.get('flask','session_secret_key')

# Main entrypoints.

@app.route('/')
def Welcome():	
	session.clear()
	response = make_response(render_template('index.html', name='chatapp'))

	return response

@app.route('/api/message', methods=['POST'])
def message():
	r = send_message(request.json)
	return(jsonify(r))

def send_message(msg):
	'''
	Sends a message to conversation. Also checks if NLU or Discovery should run. 
	:param msg The string of user input to send to conversation. 
	'''
	if 'context' not in session:
		session['context'] = {}

	if 'input' in msg:
		text = msg['input']
	else:
		text = { 'text': '' }

	r = conversation.message(
		workspace_id=c.get('conversation','workspace_id'), 
		message_input=text, 
		alternate_intents=c.getboolean('conversation','alternate_intents'),
		context=session['context']
		)

	print('I am here 1---------', r)
	# NLU check
	if c.getboolean('nlu','enabled'):
		r['context']['nlu_enabled'] = True
		r['context']['nlu_results'] = callNLU(r['input']['text'])
	else:
		r['context']['nlu_enabled'] = False
		r['context']['nlu_results'] = {}
	# Discovery check.
	if c.getboolean('conversation','call_discovery_if_irrelevant') and r['intents'] == []:
		r['context']['discovery'] = callDiscovery(r['input']['text'])
		r['output']['text'] = alchemyapiText(r, r['output']['text'])

	elif  'output' in r and 'action' in r['output'] and 'call_discovery' in r['output']['action']:
		print('I am here ---------2')
		r['context']['discovery'] = callDiscovery(r['input']['text'])
		r['output']['text'] = alchemyapiText(r, r['output']['text'])

	elif c.getboolean('conversation','call_discovery_if_low_confidence') and r['intents'][0]['confidence'] < 0.2:
		print('I am here ---------3')
		r['context']['discovery'] = callDiscovery(r['input']['text'])
		r['output']['text'] = alchemyapiText(r, r['output']['text'])

	elif c.get('conversation','call_discovery_context_variable') in r['context']:
		if r['context'][c.get('conversation','call_discovery_context_variable')] == True:
			r['context']['discovery'] = callDiscovery(r['input']['text'])
			r['output']['text'] = alchemyapiText(r, r['output']['text'])
	else:
		r['context']['discovery'] = {}

	# Tone Analyzer check. 
	if c.getboolean('tone_analyzer','enabled'):
		r['context']['tone_analyzer'] = callToneAnalyzer(r['input']['text'])

	session['context'] = r['context']

	return r

def callToneAnalyzer(text):
	'''
	Calls Tone Analzer. 
	:param text The text to analyse.
	'''
	if text == None or text.strip() == '': 
		return {}

	return tone_analyzer.tone(text=text)

def alchemyapiText(j,fallback):
	'''
	Pulls the text from the alchemyapi_text field, and summerizes if needed. 
	If it can't, then it uses the fallback. 
	:param j The discovery JSON object.
	:param fallback Text to use if you can't get alchemy text.
	'''
	if 'results' not in j['context']['discovery']:
		return fallback

	if len(j['context']['discovery']['results']) == 0:
		return fallback

	txt = j['context']['discovery']['results'][0]['contentHtml']
	title = j['context']['discovery']['results'][0]['title']

	resp_text = '{}:<br><b>{}</b><p>{}'


	if c.has_option('gensim','summarize') and c.getboolean('gensim','summarize'): 
		header = 'Here is a summary of what I found'
		try:
			sumtext = summarize(txt,word_count=c.getint('gensim','summarize_word_count'))
		except:
			sumtext = txt
			header = 'Here is what I found'

		txt = resp_text.format(header, title, sumtext)
	else:
		txt = resp_text.format('Here is what I found',title,txt)

	return txt



def callDiscovery(text):
	'''
	Does a lookup in Discovery for the response
	:param text the string to use as your query. 
	'''
	if text == None or text.strip() == '': 
		return {}

	query = {'query': text }
	print("---- discovery query",query)

	if c.has_option('discovery_feature','count'): query['count'] = c.get('discovery_feature','count')
	if c.has_option('discovery_feature','offset'): query['offset'] = c.get('discovery_feature','offset')
	if c.has_option('discovery_feature','aggregation'): query['aggregation'] = c.get('discovery_feature','aggregation')
	if c.has_option('discovery_feature','filter'): query['filter'] = c.get('discovery_feature','filter')
	if c.has_option('discovery_feature','return'): query['return'] = c.get('discovery_feature','return')

	print("---- discovery env",c.get('discovery','environment_id'))
	print("---- discovery coll",c.get('discovery','collection_id'))
	d = discovery.query(
		environment_id=c.get('discovery','environment_id'),
		collection_id=c.get('discovery','collection_id'),
		query_options=query
	)
	print("this is return from discovery",d)

	return d


# Sends the user input to NLU. 
def callNLU(text):
	'''
	Checks what features are enabled, then makes a call to NLU and returns JSON. 
	:param text The string containing the information you want to analyse. 
	'''
	if text == None or text.strip() == '': 
		return {}

	f = []
	if c.getboolean('nlu_feature','concepts'): f.append(features.Concepts())
	if c.getboolean('nlu_feature','entities'): f.append(features.Entities())
	if c.getboolean('nlu_feature','keywords'): f.append(features.Keywords())
	if c.getboolean('nlu_feature','categories'): f.append(features.Categories())
	if c.getboolean('nlu_feature','emotion'): f.append(features.Emotion())
	if c.getboolean('nlu_feature','semanticroles'): f.append(features.SemanticRoles())
	if c.getboolean('nlu_feature','relations'): f.append(features.Relations())
	if c.getboolean('nlu_feature','sentiment'): f.append(features.Sentiment())

	r = nlu.analyze(text=text, features=f)

	return r

port = os.getenv('PORT', '5000')
if __name__ == "__main__":
	app.run(host='0.0.0.0', port=int(port))
