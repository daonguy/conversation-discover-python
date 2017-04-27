# Watson Conversation Flask project.

This is the Watson [conversation-simple](https://github.com/watson-developer-cloud/conversation-simple) project converted from node.js to Flask. 

It also has added integration of Discovery service, Tone Analyzer and NLU. These can be configured to be enabled/disabled and scale the amount of information you want to get back from the services. 

It also has the gensim summariser to reduce the response from Discovery service (again can be toggled). 

## How to install. 

Edit `config.ini` and put in your related settings where you see something surrounded with `<>`. For example `<CONVERSATION_USER_NAME>` should be changed to the username of your conversation service. 

The config.ini file has the following settings. 

#### `[flask]`
Contains the session secret key. You should generate a new key (can be anything). 

#### `[conversation]`
Conversation settings. There are the discovery related options. 

`call_discovery_if_low_confidence` - unused - ignore this setting - the APP will connect to discovery when the response JSON from Conversation contain this element {output: {action: call_discovery: ""}}, this app is modified to use conversation and discovery sample data from car demo
https://github.com/watson-developer-cloud/conversation-with-discovery

`call_discovery_if_irrelevant` if `True` will call to Discovery if the offtopic (Irrelevant) option was hit. 

`call_discovery_context_variable` should be set to the name of a boolean context variable. If this context variable exists and is set to `True` then Discovery will be used to find the answer. 

#### `[discovery]`
The Discovery service settings - DO NOT remove title and contenthtml element

#### `[discovery_feature]`
These are the feature settings for a discovery call. The `return` option **must have** at least `alchemyapi_text,title` as value. If you want to return other fields, then just add them to the end (comma delimited). 

#### `[tone_analyzer]`
Settings for tone analyzer. 

#### `[gensim]`
Summeriser settings. If enabled, it will attempt to summarise the discovery content returned. 

#### `[nlu]`
NLU settings. 

#### `[nlu_feature]`
The features to enable/disable when calling the NLU. 
