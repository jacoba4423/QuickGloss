from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import spacy
import re
import langdetect
from sklearn.metrics.pairwise import cosine_similarity
from faster_whisper import WhisperModel
import tempfile
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
CORS(app)

SPACY_MODELS = {}
AVAILABLE_LANGUAGES = ['en', 'de', 'es', 'fr', 'it', 'pt', 'nl', 'ru', 'zh', 'ja', 'id']

def load_spacy_models():
    """Load available SpaCy models"""
    global SPACY_MODELS
    model_map = {
        'en': 'en_core_web_sm',
        'de': 'de_core_news_sm',
        'es': 'es_core_news_sm',
        'fr': 'fr_core_news_sm',
        'it': 'it_core_news_sm',
        'pt': 'pt_core_news_sm',
        'nl': 'nl_core_news_sm',
        'ru': 'ru_core_news_sm',
        'zh': 'zh_core_web_sm',
        'ja': 'ja_core_news_sm',
        'id': 'id_core_news_sm'
    }
    
    for lang, model_name in model_map.items():
        try:
            SPACY_MODELS[lang] = spacy.load(model_name)
        except OSError:
            # fallback to english
            try:
                SPACY_MODELS[lang] = spacy.load('en_core_web_sm')
            except OSError:
                SPACY_MODELS[lang] = None

print("Loading Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Model loaded!")

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'mp4', 'avi', 'mov', 'mkv', 'flac', 'm4a', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_language(text):
    """Detect language of input text"""
    try:
        detected = langdetect.detect(text)
        return detected if detected in AVAILABLE_LANGUAGES else 'en'
    except:
        return 'en'

def extract_grammatical_features(doc):
    """Extract grammatical features using SpaCy"""
    features = {}
    
    for token in doc:
        token_features = {}
        
        token_features['pos'] = token.pos_
        token_features['tag'] = token.tag_
        token_features['lemma'] = token.lemma_
        
        # extract morphemes if available
        if token.morph:
            for feature in token.morph:
                if '=' in feature:
                    key, value = feature.split('=', 1)
                    token_features[key.lower()] = value.lower()
        
        # dep=dependency
        token_features['dep'] = token.dep_
        
        features[token.text.lower()] = token_features
    
    return features

def generate_abbreviations():
    """Generate standard abbreviations for grammatical features"""
    return {
        'nominative': 'NOM', 'accusative': 'ACC', 'genitive': 'GEN', 
        'dative': 'DAT', 'ablative': 'ABL', 'vocative': 'VOC',
        'instrumental': 'INS', 'locative': 'LOC', 'partitive': 'PART',
        
        'masculine': 'MASC', 'feminine': 'FEM', 'neuter': 'NEUT',
        'masc': 'MASC', 'fem': 'FEM', 'neut': 'NEUT',
        
        'singular': 'SG', 'plural': 'PL', 'dual': 'DU',
        'sing': 'SG', 'plur': 'PL',
        
        'first': '1', 'second': '2', 'third': '3',
        '1': '1', '2': '2', '3': '3',
        
        'present': 'PRES', 'past': 'PAST', 'future': 'FUT',
        'perfect': 'PERF', 'imperfect': 'IMPERF', 'pluperfect': 'PLUP',
        'pres': 'PRES', 'fut': 'FUT',
        
        'progressive': 'PROG', 'perfective': 'PFV', 'imperfective': 'IPFV',
        'prog': 'PROG', 'pfv': 'PFV', 'ipfv': 'IPFV',
        
        'indicative': 'IND', 'subjunctive': 'SUBJ', 'imperative': 'IMP',
        'conditional': 'COND', 'optative': 'OPT',
        'ind': 'IND', 'subj': 'SUBJ', 'imp': 'IMP', 'cond': 'COND',
        
        'active': 'ACT', 'passive': 'PASS', 'middle': 'MID',
        'act': 'ACT', 'pass': 'PASS',
        
        'definite': 'DEF', 'indefinite': 'INDEF',
        'def': 'DEF', 'indef': 'INDEF',
        
        'positive': 'POS', 'comparative': 'COMP', 'superlative': 'SUP',
        'pos': 'POS', 'comp': 'COMP', 'sup': 'SUP',
        
        'animate': 'ANIM', 'inanimate': 'INAN',
        'anim': 'ANIM', 'inan': 'INAN',
        
        'finite': 'FIN', 'infinite': 'INF',
        'fin': 'FIN', 'inf': 'INF',
        
        'positive': 'POS', 'negative': 'NEG',
        'pos': 'POS', 'neg': 'NEG',
        
        'noun': 'N', 'verb': 'V', 'adjective': 'ADJ', 'adverb': 'ADV',
        'preposition': 'PREP', 'conjunction': 'CONJ', 'determiner': 'DET',
        'pronoun': 'PRON', 'particle': 'PART', 'interjection': 'INTERJ'
    }

def parse_morpheme_data(morphemes):
    """Parse morpheme data and classify as prefixes, roots, or suffixes"""
    morpheme_data = {
        'prefixes': {},
        'suffixes': {},
        'roots': {},
        'infixes': {}
    }
    
    for line in morphemes.strip().split('\n'):
        if not line.strip() or ':' not in line:
            continue
            
        parts = line.split(':', 1)
        if len(parts) != 2:
            continue
            
        morpheme = parts[0].strip()
        info = parts[1].strip()
        
        features = {}
        if info:
            for part in info.split(','):
                part = part.strip()
                if '=' in part:
                    key, value = part.split('=', 1)
                    features[key.strip().lower()] = value.strip().lower()
                else:
                    features[part.lower()] = 'true'
        
        # sans '-' for storage
        clean_morpheme = morpheme.strip('-')
        
        morpheme_type = features.get('type', '').lower()
        
        if morpheme_type == 'prefix' or morpheme.endswith('-'):
            morpheme_data['prefixes'][clean_morpheme] = features
        elif morpheme_type == 'suffix' or morpheme.startswith('-'):
            morpheme_data['suffixes'][clean_morpheme] = features
        elif morpheme_type == 'infix':
            morpheme_data['infixes'][clean_morpheme] = features
        else:
            morpheme_data['roots'][clean_morpheme] = features
    
    return morpheme_data

def find_morpheme_boundaries(word, morpheme_data):
    """Find morpheme boundaries in a word using longest-match algorithm"""
    word_lower = word.lower()
    segments = []
    
    # find prefixes (longest first)
    remaining = word_lower
    original_remaining = word
    
    while remaining:
        found_prefix = False
        # sort by length (longest first) to prefer longer matches
        for prefix in sorted(morpheme_data['prefixes'].keys(), key=len, reverse=True):
            if remaining.startswith(prefix.lower()) and len(prefix) < len(remaining):
                segments.append({
                    'morpheme': original_remaining[:len(prefix)],
                    'type': 'prefix',
                    'features': morpheme_data['prefixes'][prefix]
                })
                remaining = remaining[len(prefix):]
                original_remaining = original_remaining[len(prefix):]
                found_prefix = True
                break
        
        if not found_prefix:
            break
    
    # find suffixes (longest first)
    suffix_segments = []
    temp_remaining = remaining
    temp_original = original_remaining
    
    while temp_remaining:
        found_suffix = False
        for suffix in sorted(morpheme_data['suffixes'].keys(), key=len, reverse=True):
            if temp_remaining.endswith(suffix.lower()) and len(suffix) < len(temp_remaining):
                suffix_start = len(temp_remaining) - len(suffix)
                suffix_segments.insert(0, {
                    'morpheme': temp_original[suffix_start:],
                    'type': 'suffix',
                    'features': morpheme_data['suffixes'][suffix]
                })
                temp_remaining = temp_remaining[:suffix_start]
                temp_original = temp_original[:suffix_start]
                found_suffix = True
                break
        
        if not found_suffix:
            break
    
    # now only root is left
    if temp_remaining:
        root_features = morpheme_data['roots'].get(temp_remaining, {})
        segments.append({
            'morpheme': temp_original,
            'type': 'root',
            'features': root_features
        })
    
    segments.extend(suffix_segments)
    
    return segments

def get_relevant_features(word_features, morpheme_features, pos_tag):
    """Get only relevant grammatical features based on POS and context"""
    relevant_features = []
    abbreviations = generate_abbreviations()
    
    all_features = {}
    all_features.update(morpheme_features)
    all_features.update(word_features)
    
    pos_feature_map = {
        'NOUN': ['case', 'number', 'gender', 'animacy', 'definiteness'],
        'PRON': ['case', 'number', 'gender', 'person'],
        'ADJ': ['case', 'number', 'gender', 'degree'],
        'VERB': ['tense', 'aspect', 'mood', 'voice', 'person', 'number', 'finiteness'],
        'AUX': ['tense', 'aspect', 'mood', 'person', 'number'],
        'DET': ['case', 'number', 'gender', 'definiteness'],
        'ADP': ['case'],
        'ADV': ['degree'],
        'PART': ['polarity']
    }
    
    relevant_feature_types = pos_feature_map.get(pos_tag, [])
    
    for feature_type in relevant_feature_types:
        if feature_type in all_features:
            value = all_features[feature_type]
            if value and value.lower() not in ['true', 'false', '']:
                abbrev = abbreviations.get(value.lower())
                if abbrev:
                    relevant_features.append(abbrev)
    
    for key, value in morpheme_features.items():
        if key not in ['type'] and value.lower() not in ['true', 'false', '']:
            abbrev = abbreviations.get(value.lower())
            if abbrev and abbrev not in relevant_features:
                relevant_features.append(abbrev)
    
    return relevant_features

def is_article_or_function_word(word, language): #we unfortunately had to hard code this part,
                                                # as it seemed to be the only words that our program
                                                # consistently mislabeled
    """Check if a word is an article or function word that shouldn't be segmented"""
    articles_by_language = {
        'es': ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas'],
        'fr': ['le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'des'],
        'it': ['il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'una', 'uno', 'del', 'della', 'dei', 'delle'],
        'de': ['der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einen', 'einem', 'einer'],
        'pt': ['o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'do', 'da', 'dos', 'das'],
        'nl': ['de', 'het', 'een'],
        'ru': [],
        'en': ['the', 'a', 'an'],
        'zh': [],
        'ja': [],
        'id': []
    }
    
    return word.lower() in articles_by_language.get(language, [])

def generate_pseudo_translation(segments, pos_tag):
    """Generate pseudo-translation using morpheme meanings and grammatical features"""
    translation_parts = []
    root_meaning = None
    all_features = []
    
    for segment in segments:
        features = segment['features']
        morpheme_type = segment['type']
        
        if morpheme_type == 'root':
            root_meaning = features.get('meaning', segment['morpheme'].lower())
        else:
            # collect features from affixes
            for key, value in features.items():
                if key not in ['type', 'meaning'] and value.lower() not in ['true', 'false', '']:
                    all_features.append(value.lower())
    
    if not root_meaning:
        root_meaning = segments[0]['morpheme'].lower() if segments else 'UNKNOWN'
    
    abbreviations = generate_abbreviations()
    feature_abbrevs = []
    
    for feature in all_features:
        abbrev = abbreviations.get(feature.lower())
        if abbrev:
            feature_abbrevs.append(abbrev)
    
    pos_features = get_relevant_features({}, {}, pos_tag)
    for pos_feature in pos_features:
        if pos_feature not in feature_abbrevs:
            feature_abbrevs.append(pos_feature)
    
    if feature_abbrevs:
        return f"{root_meaning}.{'.'.join(feature_abbrevs)}"
    else:
        return root_meaning

def segment_morphemes(text, morphemes, nlp, features_dict, include_translation=False):
    doc = nlp(text)
    segmented_words = []
    translated_words = []
    
    morpheme_data = parse_morpheme_data(morphemes)
    
    for token in doc:
        word = token.text
        word_lower = word.lower()
        
        if token.is_punct:
            segmented_words.append(word)
            if include_translation:
                translated_words.append(word)
            continue
        
        detected_language = detect_language(text)
        if is_article_or_function_word(word_lower, detected_language):
            found_meaning = None
            morpheme_data = parse_morpheme_data(morphemes)
            
            for category in ['roots', 'prefixes', 'suffixes']:
                if word_lower in morpheme_data[category]:
                    found_meaning = morpheme_data[category][word_lower].get('meaning', word_lower)
                    break
            
            if not found_meaning:
                found_meaning = word_lower
            
            segmented_words.append(word)
            if include_translation:
                translated_words.append(found_meaning)
            continue
        
        segments = find_morpheme_boundaries(word, morpheme_data)
        
        if not segments:
            # If no morphemes found, treat as single morpheme
            word_features = features_dict.get(word_lower, {})
            relevant_features = get_relevant_features(word_features, {}, token.pos_)
            
            if relevant_features:
                segmented_word = f"{word}.{'.'.join(relevant_features)}"
            else:
                segmented_word = word
            
            segmented_words.append(segmented_word)
            
            if include_translation:
                # for translation, just use the word if no morpheme data
                if relevant_features:
                    translated_words.append(f"{word_lower}.{'.'.join(relevant_features)}")
                else:
                    translated_words.append(word_lower)
            continue
        
        morpheme_parts = []
        all_morpheme_features = {}
        
        for segment in segments:
            morpheme_text = segment['morpheme']
            morpheme_type = segment['type']
            features = segment['features']
            
            # add morpheme w markers
            if morpheme_type == 'prefix':
                morpheme_parts.append(f"{morpheme_text}-")
            elif morpheme_type == 'suffix':
                morpheme_parts.append(f"-{morpheme_text}")
            else:
                morpheme_parts.append(morpheme_text)
            
            # clllect all morpheme features
            all_morpheme_features.update(features)
        
        if len(morpheme_parts) > 1:
            segmented_word = ''.join(morpheme_parts)
            # clean up multiple hyphens
            segmented_word = re.sub(r'-{2,}', '-', segmented_word)
        else:
            segmented_word = morpheme_parts[0] if morpheme_parts else word
        
        word_features = features_dict.get(word_lower, {})
        
        relevant_features = get_relevant_features(word_features, all_morpheme_features, token.pos_)
        
        if relevant_features:
            segmented_word += '.' + '.'.join(relevant_features)
        
        segmented_words.append(segmented_word)
        
        if include_translation:
            pseudo_translation = generate_pseudo_translation(segments, token.pos_)
            translated_words.append(pseudo_translation)
    
    if include_translation:
        return ' '.join(segmented_words), ' '.join(translated_words)
    else:
        return ' '.join(segmented_words)

    

@app.route('/')
def index():
    return render_template("linghackshtml.html")

@app.route('/segment', methods=['POST'])
def segment():
    try:
        data = request.json
        text = data.get('text', '').strip()
        morphemes = data.get('morphemes', '').strip()
        include_translation = data.get('include_translation', False)
        
        if not text or not morphemes:
            return jsonify({'error': 'Both text and morphemes are required'})
        
        language = detect_language(text)
        

        nlp = SPACY_MODELS.get(language)
        if not nlp:
            nlp = SPACY_MODELS.get('en')  # fallback to English
            if not nlp:
                return jsonify({'error': 'No SpaCy models available'})
            
        doc = nlp(text)
        
        features_dict = extract_grammatical_features(doc)
        
        if include_translation:
            segmented_text, pseudo_translation = segment_morphemes(text, morphemes, nlp, features_dict, include_translation=True)
        else:
            segmented_text = segment_morphemes(text, morphemes, nlp, features_dict, include_translation=False)
            pseudo_translation = None
        
        analysis = {
            'features': features_dict,
            'morpheme_count': len([line for line in morphemes.split('\n') if ':' in line]),
            'word_count': len([token for token in doc if not token.is_punct and not token.is_space]),
            'tokens': [{'text': token.text, 'pos': token.pos_, 'lemma': token.lemma_} for token in doc if not token.is_punct and not token.is_space]
        }
        
        response_data = {
            'original': text,
            'segmented': segmented_text,
            'language': language,
            'analysis': analysis
        }
        
        if pseudo_translation:
            response_data['pseudo_translation'] = pseudo_translation
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)})
        
@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not supported'})
        
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            print(f"Transcribing file: {filename}")
            segments, info = model.transcribe(temp_path, beam_size=5)
            transcription = " ".join([segment.text for segment in segments]).strip()
            
            return jsonify({
                'success': True,
                'transcription': transcription,
                'filename': filename
            })
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return jsonify({'success': False, 'error': f'Transcription failed: {str(e)}'})
    
@app.route('/manual_gloss', methods=['POST'])
def manual_gloss():
    try:
        data = request.json
        text = data.get('text', '').strip()
        word_breakdown = data.get('word_breakdown', '').strip()
        gloss_abbreviations = data.get('gloss_abbreviations', '').strip()
        
        if not text or not word_breakdown:
            return jsonify({'error': 'Both text and word breakdown are required'})
        
        custom_abbrevs = {}
        if gloss_abbreviations:
            for line in gloss_abbreviations.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    custom_abbrevs[key.strip().lower()] = value.strip().upper()
        
        abbreviations = generate_abbreviations()
        abbreviations.update(custom_abbrevs)
        
        result = process_manual_glossing(text, word_breakdown, abbreviations)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)})

def process_manual_glossing(text, word_breakdown, abbreviations):
    """Process manual glossing without SpaCy dependency"""
    words = text.split()
    word_data = {}
    
    for line in word_breakdown.strip().split('\n'):
        if ':' not in line:
            continue
        
        word, breakdown = line.split(':', 1)
        word = word.strip().lower()
        
        features = {}
        for part in breakdown.split(','):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                features[key.strip().lower()] = value.strip().lower()
        
        word_data[word] = features
    
    morpheme_breakdown = []
    glossed_words = []
    
    
    for word in words:
        word_lower = word.lower()
        
        if word_lower in word_data:
            features = word_data[word_lower]
            
            morpheme_parts = []
            gloss_parts = []
            
            root_part = features.get('root', word_lower)
            prefixes = []
            suffixes = []
            grammatical_features = []

            for key, value in features.items():
                if key == 'root':
                    continue  # already handled
                elif key in ['prefix', 'prefix1', 'prefix2']:
                    prefixes.append(value)
                elif key in ['suffix', 'suffix1', 'suffix2']:
                    suffixes.append(value)
                else:
                    abbrev = abbreviations.get(value.lower())
                    if abbrev:
                        grammatical_features.append(abbrev)
                    else:
                        grammatical_features.append(value.upper())

            morpheme_parts = []
            if prefixes:
                morpheme_parts.extend([f"{prefix}-" for prefix in prefixes])
            morpheme_parts.append(root_part)
            if suffixes:
                morpheme_parts.extend([f"-{suffix}" for suffix in suffixes])

            gloss_parts = []
            if prefixes:
                gloss_parts.extend([prefix.upper() for prefix in prefixes])
                
            root_gloss = root_part.upper()
            if grammatical_features:
                root_gloss += '.' + '.'.join(grammatical_features)
            gloss_parts.append(root_gloss)

            if suffixes:
                gloss_parts.extend([suffix.upper() for suffix in suffixes])

            morpheme_breakdown.append(''.join(morpheme_parts))
            glossed_words.append('-'.join(gloss_parts))
            
            #morpheme_breakdown.append(''.join(morpheme_parts))
            #glossed_words.append('.'.join(gloss_parts))
        else:
            morpheme_breakdown.append(word)
            glossed_words.append(word.upper())
    
    return {
        'original': text,
        'morpheme_breakdown': ' '.join(morpheme_breakdown),
        'glossed': ' '.join(glossed_words)
    }

if __name__ == '__main__':
    load_spacy_models()
    app.run(debug=True, host='0.0.0.0', port=5000)