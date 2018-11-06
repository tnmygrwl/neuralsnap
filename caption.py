import requests
import nltk
import random
import sys

path = sys.argv[1]
r = requests.post(
    "https://api.deepai.org/api/neuraltalk",
    files={
        'image': open(path, 'rb'),
    },
    headers={'api-key': ''}
)
TEXT = r.json()
TEXT = TEXT['output']
print(TEXT)
# TEXT = nltk.corpus.gutenberg.words('austen-emma.txt')
bigrams = nltk.bigrams(TEXT)
cfd = nltk.ConditionalFreqDist(bigrams)

# pick a random word from the corpus to start with
word = random.choice(TEXT)
# generate 15 more words
for i in range(15):
    print(word, end="")
    if word in cfd:
        word = random.choice(list(cfd[word]))
    else:
        break
