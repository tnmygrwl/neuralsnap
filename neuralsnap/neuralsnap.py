
# coding: utf-8

# # NeuralSnap
# 
# Works by generating a caption for the image using a model I trained on the MS COCO data set, with recurrent and convolutional neural networks using NeuralTalk2. That (brief) caption is then expanded into a poem using a recurrent neural network (Karpathy's Char-RNN), which I trained on a ~40 MB corpus of poetry.
# 
# By Ross Goodwin, 2016

# In[1]:

import time
start_time = time.time()


# In[2]:

import os
import sys
import subprocess
import json
import re
from string import Template
from upload_to_s3 import upload

script, output_title, ntalk_model_fp, rnn_model_fp, image_folder_fp = sys.argv

# ## Global Parameters
# 
# Replace these values with parameters that match your installation.

# In[3]:

num_images = '1'
stanza_len = '512'
highlight_color = '#D64541' # Valencia Red
num_steps = 16
tgt_steps = [6,7,8,9]


# ### Static Global Parameters
# 
# Replace these too.

# In[4]:

SCRIPT_PATH = os.getcwd()
NEURALTALK2_PATH = os.path.join(os.getcwd(), '..', 'neuraltalk2')
CHARRNN_PATH = os.path.join(os.getcwd(), '..', 'char-rnn')


# ## NeuralTalk2 Image Captioning

# In[5]:

os.chdir(NEURALTALK2_PATH)

ntalk_cmd_list = [
    'th',
    'eval.lua',
    '-model',
    ntalk_model_fp,
    '-image_folder',
    image_folder_fp,
    '-num_images',
    num_images,
    '-gpuid',
    '-1'
]

print "INIT NEURALTALK2 CAPTIONING"

ntalk_proc = subprocess.Popen(ntalk_cmd_list)
ntalk_proc.communicate()


# In[6]:

with open(NEURALTALK2_PATH+'/vis/vis.json') as caption_json:
    caption_obj_list = json.load(caption_json)
    
caption_obj_list *= num_steps


# ## RNN Caption Expansion

# In[7]:

os.chdir(CHARRNN_PATH)

expansion_obj_list = list()
caption_list = list()

print "INIT CHAR-RNN EXPANSION"

for i in tgt_steps:
    obj = caption_obj_list[i]
    caption = obj['caption']
    prepped_caption = caption[0].upper() + caption[1:]
    
    temp = str((i+1.0)/float(num_steps))
    print "EXPANDING AT TEMPERATURE " + temp
    
    rnn_cmd_list = [
        'th',
        'sample.lua',
        rnn_model_fp,
        '-length',
        stanza_len,
        '-verbose',
        '0',
        '-temperature',
        temp,
        '-primetext',
        prepped_caption,
        '-gpuid',
        '-1'
    ]

    rnn_proc = subprocess.Popen(
        rnn_cmd_list,
        stdout=subprocess.PIPE
    )
    expansion = rnn_proc.stdout.read()
    
    expansion_obj_list.append({
        'id': obj['image_id'],
        'text': expansion
    })
    
    caption_list.append((prepped_caption, '<span style="color:'+highlight_color+';">'+prepped_caption+'</span>'))


# ## Post Processing

# In[25]:

img_fps = map(
    lambda x: os.path.join(NEURALTALK2_PATH, 'vis', 'imgs', 'img%s.jpg'%x['id']),
    expansion_obj_list
)

img_url = img_fps.pop()


# In[26]:

def fix_end_punctuation(exp):
    try:
        first_sentence, remainder = exp.rsplit('.', 1)
        first_sentence = first_sentence.strip()
        if remainder[0] in ["\'", '\"', '”', '’']:
            first_sentence += '.' + remainder[0]
        else:
            first_sentence += '.'
        return first_sentence
    except:
        return exp.rsplit(' ', 1)[0] + '...'

expansions = map(
    lambda x: fix_end_punctuation(x['text']),
    expansion_obj_list
)

exps_tups = zip(expansions, caption_list)


# In[27]:

def add_span(exp, tup):
    original, modified = map(lambda x: x.decode('utf8').encode('ascii', 'xmlcharrefreplace'), tup)
    return exp.replace(original, modified)
    
final_exps = map(lambda (x,y): add_span(x,y), exps_tups)


# In[28]:

def make_html_block(exp):
    exp_ascii = exp.decode('utf8').encode('ascii', 'xmlcharrefreplace')
    exp_ascii = exp_ascii.replace('\n', '</p><p>')
    return '<p>%s</p>' % exp_ascii

img_block = '<p class="text-center"><a href="%s"><img src="%s" width="275px" class="img-thumbnail"></a></p>' % (img_url, img_url)
body_html = img_block + '\n'.join(map(make_html_block, final_exps))


# In[29]:

with open(SCRIPT_PATH+'/template.html', 'r') as tempfile:
    html_temp_str = tempfile.read()
    
html_temp = Template(html_temp_str)
html_result = html_temp.substitute(title=output_title, body=body_html)
html_fp = '%s/pages/%s.html' % (SCRIPT_PATH, re.sub(r'\W+', '_', output_title))

with open(html_fp, 'w') as outfile:
    outfile.write(html_result)
    
# print upload(html_fp)

# Sorry, you'll have to build your own upload
# function if you want to share your results
# on the web... for now.


# In[30]:

end_time = time.time()
print end_time - start_time


# In[31]:

import webbrowser

webbrowser.open_new_tab('file://'+html_fp)
