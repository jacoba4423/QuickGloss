        //sample data to be used for the buttons
        const sampleData = {
            english: {
                text: "The children are playing happily in the garden.",
                morphemes: `the: type=root, meaning=the
child: type=root, meaning=child
ren: type=suffix, number=plural
are: type=root, meaning=be
play: type=root, meaning=play
ing: type=suffix, aspect=progressive
happy: type=root, meaning=happy
ly: type=suffix, type=adverb
in: type=root, meaning=in
garden: type=root, meaning=garden`
            },
            spanish: {
                text: "Los niños están jugando felizmente en el jardín.",
                morphemes: `los: type=root, meaning=the, gender=masculine, number=plural
niñ: type=root, meaning=child
os: type=suffix, gender=masculine, number=plural
están: type=root, meaning=be, tense=present, number=plural
jug: type=root, meaning=play
ando: type=suffix, aspect=progressive
feliz: type=root, meaning=happy
mente: type=suffix, type=adverb
en: type=root, meaning=in
el: type=root, meaning=the, gender=masculine, number=singular
jardín: type=root, meaning=garden`
            },
            russian: {
                text: "Дети играют весело в саду.",
                morphemes: `дет: type=root, meaning=child
и: type=suffix, number=plural, case=nominative
игра: type=root, meaning=play
ют: type=suffix, tense=present, number=plural, person=third
весел: type=root, meaning=happy
о: type=suffix, type=adverb
в: type=root, meaning=in
сад: type=root, meaning=garden
у: type=suffix, case=locative`
            },
            german: {
                text: "Die Kinder spielen gerne mit ihren Freunden.",
                morphemes: "kind: meaning=child, type=root\ner: meaning=plural, type=suffix, number=plural\nspiel: meaning=play, type=root\nen: meaning=infinitive, type=suffix\ngern: meaning=gladly, type=root\ne: meaning=adverb, type=suffix\nmit: meaning=with, type=root\nihr: meaning=their, type=root, person=3\nen: meaning=dative_plural, type=suffix, case=dative, number=plural\nfreund: meaning=friend, type=root\ndie: meaning=the_feminine, type=root, gender=feminine\ndas: meaning=the_neuter, type=root, gender=neuter\nder: meaning=the_masculine, type=root, gender=masculine"
            }
        };
        
        function loadSample(language) {
            const sample = sampleData[language];
            if (sample) {
                document.getElementById('textInput').value = sample.text;
                document.getElementById('morphemeInput').value = sample.morphemes;
                
                // add a visual feedback
                const textInput = document.getElementById('textInput');
                const morphemeInput = document.getElementById('morphemeInput');
                
                textInput.style.backgroundColor = '#e8f5e8';
                morphemeInput.style.backgroundColor = '#e8f5e8';
                
                setTimeout(() => {
                    textInput.style.backgroundColor = '';
                    morphemeInput.style.backgroundColor = '';
                }, 1000);
            }
        }
        
        function verifyFile(file) {
            if (!file) {
                return false;
            }
            
            const allowedTypes = ['audio/', 'video/'];
            return allowedTypes.some(type => file.type.startsWith(type));
        }

        async function processManualGlossing() {
            const text = document.getElementById('manualTextInput').value.trim();
            const wordBreakdown = document.getElementById('wordBreakdownInput').value.trim();
            const glossAbbrev = document.getElementById('glossAbbrevInput').value.trim();
            
            if (!text || !wordBreakdown) {
                showManualError('Please provide both text and word breakdown.');
                return;
            }
            
            showManualLoading();
            
            try {
                const response = await fetch('/manual_gloss', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        word_breakdown: wordBreakdown,
                        gloss_abbreviations: glossAbbrev
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showManualError(data.error);
                } else {
                    showManualResults(data);
                }
            } catch (error) {
                showManualError('An error occurred while processing: ' + error.message);
            }
        }

        function showManualError(message) {
            document.getElementById('manualResults').innerHTML = `
                <div class="error">
                    <strong>Error:</strong> ${message}
                </div>
            `;
        }

        function showManualResults(data) {
            const resultsHTML = `
                <div class="results">
                    <h3>Manual Glossing Results</h3>
                    <h4>Original Text:</h4>
                    <pre>${data.original}</pre>
                    <h4>Morpheme Breakdown:</h4>
                    <pre>${data.morpheme_breakdown}</pre>
                    <h4>Glossed Text:</h4>
                    <pre>${data.glossed}</pre>
                </div>
            `;
            
            document.getElementById('manualResults').innerHTML = resultsHTML;
        }

        function showManualLoading() {
            document.getElementById('manualResults').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Processing manual gloss...</p>
                </div>
            `;
        }
        
        // transcription function
        async function transcribeText(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/transcribe', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    return data.transcription;
                } else {
                    throw new Error(data.error || 'Transcription failed');
                }
            } catch (error) {
                throw new Error('Network error: ' + error.message);
            }
        }
        
        // glossing functions
        async function processSegmentation() {
            const text = document.getElementById('textInput').value.trim();
            const morphemes = document.getElementById('morphemeInput').value.trim();
            const includeTranslation = document.getElementById('includeTranslation').checked;
            
            if (!text || !morphemes) {
                showError('Please provide both text and morphemes.');
                return;
            }
            
            showLoading();
            
            try {
                const response = await fetch('/segment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        morphemes: morphemes,
                        include_translation: includeTranslation
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showError(data.error);
                } else {
                    showResults(data);
                }
            } catch (error) {
                showError('An error occurred while processing: ' + error.message);
            }
        }
        
        function showError(message) {
            document.getElementById('results').innerHTML = `
                <div class="error">
                    <strong>Error:</strong> ${message}
                </div>
            `;
        }
        
        function showResults(data) {
            let resultsHTML = `
                <div class="results">
                    <h3>Segmentation Results</h3>
                    <p><strong>Detected Language:</strong> ${data.language}</p>
                    <h4>Original Text:</h4>
                    <pre>${data.original}</pre>
                    <h4>Segmented Text:</h4>
                    <pre>${data.segmented}</pre>
            `;
            
            if (data.pseudo_translation) {
                resultsHTML += `
                    <h4>Pseudo-Translation:</h4>
                    <pre>${data.pseudo_translation}</pre>
                `;
            }
            
            resultsHTML += `
                    <h4>Analysis:</h4>
                    <pre>${JSON.stringify(data.analysis, null, 2)}</pre>
                </div>
            `;
            
            document.getElementById('results').innerHTML = resultsHTML;
        }
        function showLoading() {
            document.getElementById('results').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Processing segmentation...</p>
                </div>
            `;
        }

        function portToGlossing() {
            const transcribedText = document.getElementById("transcribed_text").textContent;
            const textInput = document.getElementById("textInput");
            
            textInput.value = transcribedText;
            
            const speechText = document.getElementById("speech_text");
            const glossingText = document.getElementById("glossing_text");
            const speechWrapper = document.getElementById("speech_wrapper");
            const glossingWrapper = document.getElementById("glossing_wrapper");
            
            speechText.classList.remove("active");
            glossingText.classList.add("active");
            speechWrapper.style.display = "none";
            glossingWrapper.style.display = "flex";
            
            // focus on the text input to show it has been populated
            textInput.focus();
        }
        
        document.addEventListener("DOMContentLoaded", function() {
            const speechText = document.getElementById("speech_text");
            const glossingText = document.getElementById("glossing_text");
            const speechWrapper = document.getElementById("speech_wrapper");
            const glossingWrapper = document.getElementById("glossing_wrapper");
            const transcribedText = document.getElementById("transcribed_text");
            const transcribedLabel = document.getElementById("transcribed_label");
            const audioInput = document.getElementById("audio_input");
            
            // tab switching
            speechText.addEventListener("click", () => {
                speechText.classList.add("active");
                glossingText.classList.remove("active");
                speechWrapper.style.display = "flex";
                glossingWrapper.style.display = "none";
            });
            
            glossingText.addEventListener("click", () => {
                glossingText.classList.add("active");
                speechText.classList.remove("active");
                glossingWrapper.style.display = "flex";
                speechWrapper.style.display = "none";
            });

            const manualText = document.getElementById("manual_text");
            const manualWrapper = document.getElementById("manual_wrapper");

            manualText.addEventListener("click", () => {
                manualText.classList.add("active");
                speechText.classList.remove("active");
                glossingText.classList.remove("active");
                manualWrapper.style.display = "flex";
                speechWrapper.style.display = "none";
                glossingWrapper.style.display = "none";
            });

            speechText.addEventListener("click", () => {
                speechText.classList.add("active");
                glossingText.classList.remove("active");
                manualText.classList.remove("active");
                speechWrapper.style.display = "flex";
                glossingWrapper.style.display = "none";
                manualWrapper.style.display = "none";
            });

            glossingText.addEventListener("click", () => {
                glossingText.classList.add("active");
                speechText.classList.remove("active");
                manualText.classList.remove("active");
                glossingWrapper.style.display = "flex";
                speechWrapper.style.display = "none";
                manualWrapper.style.display = "none";
            });
            
            // audio file processing
            audioInput.addEventListener("change", async () => {
                const file = audioInput.files[0];
                if (verifyFile(file)) {
                    try {
                        // show loading state
                        transcribedLabel.style.display = "block";
                        transcribedText.style.display = "block";
                        transcribedText.textContent = "Processing audio... This may take a few minutes.";
                        
                        const text = await transcribeText(file);
                        transcribedText.textContent = text;
                        document.getElementById("port_to_glossing").style.display = "block";

                    } catch (error) {
                        transcribedText.textContent = "Error: " + error.message;
                        document.getElementById("port_to_glossing").style.display = "none";
                    }
                } else {
                    alert("Invalid file type. Please select an audio or video file.");
                }
            });
        });