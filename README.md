# QuickGloss
Welcome to QuickGloss! This is a tool for documentary linguists to be able to preserve under-resourced languages more efficiently.

QuickGloss aims to the process of glossing, and, more broadly, linguistic preservation. We have three main features: speech to text, manual glossing, and, our centerpiece, automated glossing. Our speech to text takes an audio file of native speaker materials, and automatically transcribes it. It then prompts the user to gloss that transcribed text. The user then uploads a necessary corpus of morphemes, including as many or as little properties as they would like, in a custom list format. The algorithm then matches the morphemes with the ones in the provided sentences, and marks it down using standard Leipzig notation. Finally, for the morphemes not found in the corpus, it uses predictive ML techniques to extrapolate likely glosses based on morphological patterns in the language.

You can find the frontend of our code in the "templates" and "static" folders, while the backend is within quickGloss.py. The requirements to run this code are listed below:

flask>=3.1.1  
flask-cors>=4.0.0  
spacy>=3.7.2  
scikit-learn>=1.3.2  
langdetect>=1.0.9  
faster-whisper>=0.9.0  
werkzeug>=2.3.7  

A few external commands to install spaCy models may be needed:  
python -m spacy download en_core_web_sm  
python -m spacy download de_core_news_sm  
python -m spacy download es_core_news_sm  
python -m spacy download ru_core_news_sm  
