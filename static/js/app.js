// static/js/app.js
document.addEventListener('DOMContentLoaded', function() {
    // Références aux éléments DOM
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const sendButton = document.getElementById('sendButton');
    const userInput = document.getElementById('userInput');
    const conversation = document.getElementById('conversation');
    const statusDiv = document.getElementById('status');
    const voiceStatusDiv = document.getElementById('voiceStatus');
    const profileSelector = document.getElementById('profileSelector');
    const aiResponseButton = document.getElementById('ai-response-button'); // facultatif

    // Sélection de mode
    const textModeButton = document.getElementById('textModeButton');
    const voiceModeButton = document.getElementById('voiceModeButton');
    const textInputMode = document.getElementById('textInputMode');
    const voiceInputMode = document.getElementById('voiceInputMode');

    // Variables globales
    let recognizer;
    let synthesizer;
    let isRecognizing = false;
    let conversationHistory = [];
    let currentMode = 'text';
    let voicesList = null;
    let currentProfile = profileSelector ? profileSelector.value : null;

    // --- Push-To-Talk (PTT) ---
    let pttEnabled = false;     // actif uniquement en mode vocal
    let spaceHeld = false;      // barre espace maintenue
    let isSpeaking = false;     // TTS en cours
    let pttBufferText = "";     // buffer texte accumulé pendant l'appui
    let lastPartialText = "";   // dernier fragment partiel

    // Anti course/doublons
    let pttSessionActive = false; // keydown -> fin d’envoi (vrai durant la session PTT)
    let isFlushingPTT = false;    // stop() + flush en cours
    let pttFinalizing = false;    // évite double flush (keyup & blur simultanés)

    // Déduplication des finals ajoutés au buffer
    let lastFinalAppendedNorm = "";  // dernier segment final ajouté (normalisé)

    // Helpers normalisation segments (retire ponctuation fin de segment)
    function normalizeSegment(seg) {
        if (!seg) return "";
        let s = seg.replace(/\s+/g, ' ').trim();
        // retire ponctuation terminale (. , ! ? … etc.)
        s = s.replace(/[.,!?؛،؟:;…\u3002\uFF0E\uFE12\uFE52]+$/u, "");
        return s.trim();
    }

    // Concatène proprement dans le buffer
    function appendToBuffer(cleanSeg) {
        if (!cleanSeg) return;
        if (!pttBufferText) pttBufferText = cleanSeg;
        else pttBufferText += " " + cleanSeg;
    }

    // Si le texte final est exactement la même moitié répétée 2x, on ne garde qu'une moitié
    function squashDuplicateHalf(text) {
        const norm = text.replace(/\s+/g, ' ').trim();
        const lower = norm.toLowerCase();
        if (lower.length >= 10 && lower.length % 2 === 0) {
            const mid = lower.length / 2;
            const a = lower.slice(0, mid).trim();
            const b = lower.slice(mid).trim();
            if (a === b) return norm.slice(0, mid).trim();
        }
        return norm;
    }

    // Changement de mode
    function switchMode(mode) {
        if (isRecognizing && mode === 'text') {
            stopRecognition();
        }
        currentMode = mode;

        if (mode === 'text') {
            disablePTT();
            textModeButton && textModeButton.classList.add('active');
            voiceModeButton && voiceModeButton.classList.remove('active');
            textInputMode && textInputMode.classList.add('active');
            voiceInputMode && voiceInputMode.classList.remove('active');
            updateStatus("Mode texte activé");
        } else {
            textModeButton && textModeButton.classList.remove('active');
            voiceModeButton && voiceModeButton.classList.add('active');
            textInputMode && textInputMode.classList.remove('active');
            voiceInputMode && voiceInputMode.classList.add('active');
            updateStatus("Mode vocal activé - prêt à l'utilisation");

            const ensureSDK = async () => {
                if (!recognizer || !synthesizer) {
                    const ok = await initializeSpeechSDK();
                    if (!ok) return;
                }
                enablePTT();
            };
            ensureSDK();
        }
    }

    if (textModeButton) textModeButton.onclick = () => switchMode('text');
    if (voiceModeButton) voiceModeButton.onclick = () => switchMode('voice');

    // Fonction pour récupérer un token d'autorisation Speech
    async function fetchSpeechToken() {
        try {
            const response = await fetch('/get_speech_token');
            const data = await response.json();
            
            if (data.success) {
                authToken = data.token;
                serviceRegion = data.region;
                tokenExpiryTime = Date.now() + (9 * 60 * 1000); // Token valide 10 min, on renouvelle après 9 min
                console.log('✅ Token Speech obtenu (valide 10 minutes)');
                return true;
            } else {
                console.error('❌ Erreur lors de l\'obtention du token Speech:', data.error);
                updateVoiceStatus('Erreur d\'authentification Speech');
                return false;
            }
        } catch (error) {
            console.error('❌ Exception lors de l\'obtention du token:', error);
            updateVoiceStatus('Erreur de connexion Speech');
            return false;
        }
    }

    // Fonction pour vérifier et renouveler le token si nécessaire
    async function ensureValidToken() {
        if (!authToken || !tokenExpiryTime || Date.now() >= tokenExpiryTime) {
            console.log('🔄 Renouvellement du token Speech...');
            return await fetchSpeechToken();
        }
        return true;
    }

    // Initialisation Azure Speech
    async function initializeSpeechSDK() {
        if (!voicesList) voicesList = await loadVoices();
        
        // Vérifier qu'on a un token valide
        const hasValidToken = await ensureValidToken();
        if (!hasValidToken) {
            updateVoiceStatus("Erreur: impossible d'obtenir l'autorisation Speech");
            disableSpeechButtons();
            return false;
        }
        
        try {
            // Configuration avec token d'autorisation au lieu de la clé
            const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(authToken, serviceRegion);
            speechConfig.speechRecognitionLanguage = "fr-FR";

            // Étendre la tolérance aux silences pour éviter l’endpoint pendant l’appui
            speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "60000"); // 60 s
            speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000");
            speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_ContinuousSpeechTimeoutMs, "300000"); // 5 min

            // Choix voix selon profil
            const personDetails = await getPersonDetails();
            const sexe = personDetails?.Sexe || "Homme";
            speechConfig.speechSynthesisVoiceName = getRandomVoice(sexe);

            const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
            recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
            synthesizer = new SpeechSDK.SpeechSynthesizer(speechConfig);

            configureRecognizer();
            updateVoiceStatus("SDK Azure Speech initialisé avec succès");
            updateVoiceStatus("Mode vocal prêt ✅ — maintiens ESPACE pour parler");
            return true;
        } catch (error) {
            console.error("Erreur d'initialisation du SDK Azure Speech:", error);
            updateVoiceStatus("Erreur d'initialisation du SDK Azure Speech");
            disableSpeechButtons();
            return false;
        }
    }

    // Configuration du recognizer
    function configureRecognizer() {
        recognizer.recognized = async (s, e) => {
            if (!e.result) return;

            if (e.result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
                const clean = normalizeSegment(e.result.text || "");
                const norm = clean.toLowerCase();

                // Pendant PTT ou flush : on bufferise sans envoyer, en dédoublonnant
                if (pttSessionActive || isFlushingPTT) {
                    if (norm && norm !== lastFinalAppendedNorm) {
                        appendToBuffer(clean);
                        lastFinalAppendedNorm = norm;
                    }
                    if (spaceHeld) {
                        // Mettre à jour uniquement le texte final dans la popup
                        updateLiveRecordingText(pttBufferText, lastPartialText);
                    }
                    return;
                }

                // Cas non-PTT (boutons start/stop)
                if (clean) {
                    updateVoiceStatus("Message reconnu: " + clean);
                    await sendMessageToServer(clean);
                }
            } // NoMatch: ignorer
        };

        recognizer.recognizing = (s, e) => {
            if (e.result && e.result.text) {
                lastPartialText = normalizeSegment(e.result.text);
                if (spaceHeld) {
                    // Mettre à jour uniquement le texte en temps réel dans la popup
                    updateLiveRecordingText(pttBufferText, lastPartialText);
                }
            }
        };

        recognizer.canceled = () => {
            updateVoiceStatus("Reconnaissance annulée");
            isRecognizing = false;
            updateButtons();
        };
        recognizer.sessionStopped = () => {
            updateVoiceStatus("Session de reconnaissance terminée");
            isRecognizing = false;
            updateButtons();
        };
    }

    // --- PTT utilitaires ---
    function isTypingInField(target) {
        if (!target) return false;
        const tag = (target.tagName || "").toUpperCase();
        return tag === "INPUT" || tag === "TEXTAREA" || target.isContentEditable;
    }

    function startRecognitionPTT() {
        if (!recognizer || isRecognizing) return;
        if (isSpeaking) return; // sécurité TTS
        pttBufferText = "";
        lastPartialText = "";
        lastFinalAppendedNorm = ""; // reset déduplication à chaque nouvel appui
        
        // Afficher l'animation de captation vocale
        showVoiceRecordingAnimation();
        
        try {
            recognizer.startContinuousRecognitionAsync(
                () => {
                    isRecognizing = true;
                    updateButtons();
                    updateVoiceStatus("🔴 Enregistrement en cours...");
                },
                error => {
                    console.error("Erreur de reconnaissance vocale:", error);
                    updateVoiceStatus("Erreur de reconnaissance vocale");
                    hideVoiceRecordingAnimation();
                }
            );
        } catch (err) {
            console.error("Exception startRecognitionPTT:", err);
            updateVoiceStatus("Erreur: impossible de démarrer la reconnaissance (PTT)");
            hideVoiceRecordingAnimation();
        }
    }

    async function stopRecognition() {
        if (!(recognizer && isRecognizing)) return;
        return new Promise((resolve) => {
            try {
                recognizer.stopContinuousRecognitionAsync(
                    () => {
                        isRecognizing = false;
                        updateVoiceStatus("Reconnaissance arrêtée");
                        updateButtons();
                        resolve();
                    },
                    error => {
                        console.error("Erreur lors de l'arrêt de la reconnaissance:", error);
                        updateVoiceStatus("Erreur lors de l'arrêt de la reconnaissance");
                        isRecognizing = false;
                        updateButtons();
                        resolve();
                    }
                );
            } catch (error) {
                console.error("Exception lors de l'arrêt de la reconnaissance:", error);
                updateVoiceStatus("Erreur: Impossible d'arrêter la reconnaissance vocale");
                isRecognizing = false;
                updateButtons();
                resolve();
            }
        });
    }

    async function stopRecognitionPTTAndSend() {
        if (pttFinalizing) return;  // évite double flush
        pttFinalizing = true;

        // Masquer l'animation de captation vocale
        hideVoiceRecordingAnimation();

        await stopRecognition();

        // ⚠️ On NE FLUSH PAS lastPartialText ici (source classique de doublons)
        const finalText = (pttBufferText || "").trim();

        // Reset des états
        pttBufferText = "";
        lastPartialText = "";
        lastFinalAppendedNorm = "";
        isFlushingPTT = false;
        pttSessionActive = false;
        pttFinalizing = false;

        if (finalText) {
            const toSend = squashDuplicateHalf(finalText);
            updateVoiceStatus("Envoi du message...");
            await sendMessageToServer(toSend);
        } else {
            updateVoiceStatus("Aucun texte détecté. Maintenez ESPACE et parlez.");
        }
    }

    function handleKeyDownPTT(e) {
        if (!pttEnabled || isSpeaking) return;
        const isSpace = e.code === "Space" || e.key === " " || e.key === "Spacebar";
        if (!isSpace) return;
        if (isTypingInField(e.target)) return;
        if (e.repeat) { e.preventDefault(); return; }

        e.preventDefault();
        if (!spaceHeld) {
            spaceHeld = true;
            pttSessionActive = true; // démarrage session PTT
            startRecognitionPTT();
        }
    }

    function handleKeyUpPTT(e) {
        if (!pttEnabled) return;
        const isSpace = e.code === "Space" || e.key === " " || e.key === "Spacebar";
        if (!isSpace) return;
        if (isTypingInField(e.target)) return;

        e.preventDefault();
        if (spaceHeld) {
            spaceHeld = false;
            isFlushingPTT = true; // on entre en phase de flush
            stopRecognitionPTTAndSend(); // stop + envoi
        }
    }

    function onWindowBlurPTT() {
        // Si perte de focus en plein appui, on flush une seule fois
        if (pttEnabled && spaceHeld && !isFlushingPTT) {
            spaceHeld = false;
            isFlushingPTT = true;
            hideVoiceRecordingAnimation(); // Masquer l'animation
            stopRecognitionPTTAndSend();
        }
    }

    // --- Fonctions pour la gestion tactile mobile ---
    let touchHeld = false;
    let mobilePttButton = null;

    function isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || 
               ('ontouchstart' in window) || 
               (navigator.maxTouchPoints > 0);
    }

    function handleTouchStart(e) {
        if (!pttEnabled || isSpeaking) return;
        e.preventDefault();
        
        if (!touchHeld) {
            touchHeld = true;
            spaceHeld = true; // Réutiliser la logique existante
            pttSessionActive = true;
            
            // Mettre à jour l'apparence du bouton
            if (mobilePttButton) {
                mobilePttButton.classList.add('recording');
                mobilePttButton.querySelector('.ptt-text').textContent = 'Parlez maintenant...';
            }
            
            startRecognitionPTT();
        }
    }

    function handleTouchEnd(e) {
        if (!pttEnabled) return;
        e.preventDefault();
        
        if (touchHeld) {
            touchHeld = false;
            spaceHeld = false;
            
            // Remettre l'apparence normale du bouton
            if (mobilePttButton) {
                mobilePttButton.classList.remove('recording');
                mobilePttButton.querySelector('.ptt-text').textContent = 'Maintenir pour parler';
            }
            
            isFlushingPTT = true;
            stopRecognitionPTTAndSend();
        }
    }

    function setupMobilePTT() {
        mobilePttButton = document.getElementById('mobilePttButton');
        if (!mobilePttButton) return;

        // Événements tactiles
        mobilePttButton.addEventListener('touchstart', handleTouchStart, { passive: false });
        mobilePttButton.addEventListener('touchend', handleTouchEnd, { passive: false });
        mobilePttButton.addEventListener('touchcancel', handleTouchEnd, { passive: false });
        
        // Fallback pour les événements de souris (test sur desktop)
        mobilePttButton.addEventListener('mousedown', handleTouchStart);
        mobilePttButton.addEventListener('mouseup', handleTouchEnd);
        mobilePttButton.addEventListener('mouseleave', handleTouchEnd);
        
        // Empêcher le comportement par défaut du navigateur
        mobilePttButton.addEventListener('contextmenu', (e) => e.preventDefault());
        mobilePttButton.addEventListener('selectstart', (e) => e.preventDefault());
    }

    function enablePTT() {
        if (pttEnabled) return;
        pttEnabled = true;
        window.addEventListener("keydown", handleKeyDownPTT, true);
        window.addEventListener("keyup", handleKeyUpPTT, true);
        window.addEventListener("blur", onWindowBlurPTT, true);
        
        // Configurer le PTT mobile si on est sur mobile
        if (isMobileDevice()) {
            setupMobilePTT();
            updateVoiceStatus("Mode vocal: utilisez le bouton tactile pour parler");
        } else {
            updateVoiceStatus("Mode vocal: maintiens ESPACE pour parler");
        }
    }

    function disablePTT() {
        if (!pttEnabled) return;
        window.removeEventListener("keydown", handleKeyDownPTT, true);
        window.removeEventListener("keyup", handleKeyUpPTT, true);
        window.removeEventListener("blur", onWindowBlurPTT, true);
        
        // Nettoyer les événements tactiles mobiles
        if (mobilePttButton) {
            mobilePttButton.removeEventListener('touchstart', handleTouchStart);
            mobilePttButton.removeEventListener('touchend', handleTouchEnd);
            mobilePttButton.removeEventListener('touchcancel', handleTouchEnd);
            mobilePttButton.removeEventListener('mousedown', handleTouchStart);
            mobilePttButton.removeEventListener('mouseup', handleTouchEnd);
            mobilePttButton.removeEventListener('mouseleave', handleTouchEnd);
            mobilePttButton.classList.remove('recording');
            if (mobilePttButton.querySelector('.ptt-text')) {
                mobilePttButton.querySelector('.ptt-text').textContent = 'Maintenir pour parler';
            }
        }
        
        pttEnabled = false;
        spaceHeld = false;
        touchHeld = false;
        pttBufferText = "";
        lastPartialText = "";
        lastFinalAppendedNorm = "";
        isFlushingPTT = false;
        pttSessionActive = false;
        pttFinalizing = false;
        
        // S'assurer que l'animation est masquée
        hideVoiceRecordingAnimation();
    }

    // Fonctions pour l'animation de captation vocale
    function showVoiceRecordingAnimation() {
        const overlay = document.getElementById('voiceRecordingOverlay');
        if (overlay) {
            overlay.classList.add('active');
            // Réinitialiser le contenu du texte détecté
            updateLiveRecordingText("", "");
        }
    }

    function hideVoiceRecordingAnimation() {
        const overlay = document.getElementById('voiceRecordingOverlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    }

    // Fonction pour mettre à jour le texte détecté en temps réel dans la popup
    function updateLiveRecordingText(finalText, partialText) {
        const liveTextContent = document.getElementById('liveTextContent');
        if (!liveTextContent) return;

        let displayText = "";
        
        // Afficher le texte final déjà confirmé
        if (finalText && finalText.trim()) {
            displayText += `<span class="live-text-final">${finalText}</span>`;
        }
        
        // Afficher le texte partiel en cours de reconnaissance
        if (partialText && partialText.trim()) {
            if (displayText) displayText += " ";
            displayText += `<span class="live-text-partial">${partialText}</span>`;
        }
        
        liveTextContent.innerHTML = displayText;
    }

    // Envoi au serveur
    async function sendMessageToServer(message) {
        try {
            // Afficher immédiatement le message utilisateur
            const userTimestamp = new Date().toISOString();
            conversationHistory.push({
                role: 'Vous',
                text: message,
                timestamp: userTimestamp
            });
            updateConversation();
            
            updateStatus("Envoi du message au serveur...");
            const response = await fetch('/chat', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message })
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            if (data.error) {
                updateStatus(`Erreur: ${data.error}`);
                return;
            }
            
            // Mettre à jour avec l'historique complet du serveur
            conversationHistory = data.history;
            updateConversation();

            if (currentMode === 'voice' && synthesizer) {
                const lastBotMessage = conversationHistory.filter(entry => entry.role === 'Assistant').pop();
                if (lastBotMessage) {
                    isSpeaking = true;
                    await speakText(lastBotMessage.text);
                }
            }
            updateStatus("Prêt");
        } catch (error) {
            console.error("Erreur lors de l'envoi du message:", error);
            updateStatus("Erreur: Impossible de communiquer avec le serveur");
        }
    }    // Synthèse vocale (demi-duplex)
    async function speakText(text) {
        return new Promise((resolve, reject) => {
            try {
                isSpeaking = true;
                disablePTT(); // empêche tout démarrage reco pendant TTS
                if (isRecognizing) { stopRecognition(); }
                synthesizer.speakTextAsync(
                    text,
                    result => {
                        isSpeaking = false;
                        if (currentMode === 'voice') enablePTT();
                        resolve(result);
                    },
                    error => {
                        console.error("Erreur lors de la synthèse vocale:", error);
                        isSpeaking = false;
                        if (currentMode === 'voice') enablePTT();
                        reject(error);
                    }
                );
            } catch (e) {
                isSpeaking = false;
                if (currentMode === 'voice') enablePTT();
                reject(e);
            }
        });
    }

    // Boutons historiques (mode non-PTT)
    if (startButton) startButton.onclick = () => {
        if (!isRecognizing && recognizer) {
            try {
                recognizer.startContinuousRecognitionAsync(
                    () => {
                        isRecognizing = true;
                        updateVoiceStatus("Reconnaissance démarrée, parlez maintenant...");
                        updateButtons();
                    },
                    error => {
                        console.error("Erreur lors du démarrage de la reconnaissance:", error);
                        updateVoiceStatus("Erreur lors du démarrage de la reconnaissance");
                    }
                );
            } catch (error) {
                console.error("Exception lors du démarrage de la reconnaissance:", error);
                updateVoiceStatus("Erreur: Impossible de démarrer la reconnaissance vocale");
            }
        }
    };
    if (stopButton) stopButton.onclick = () => { stopRecognition(); };

        // Envoi manuel (texte)
    if (sendButton) sendButton.onclick = async () => {
        const message = userInput ? userInput.value.trim() : '';
        if (message) {
            if (userInput) userInput.value = ''; // Vider immédiatement le champ
            await sendMessageToServer(message);
        }
    };
    if (userInput) userInput.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter') {
            const message = userInput.value.trim();
            if (message) {
                userInput.value = ''; // Vider immédiatement le champ
                await sendMessageToServer(message);
            }
        }
    });

    // Helper pour décoder les entités HTML (&#x27; -> ')
    function decodeHtmlEntities(text) {
        const textarea = document.createElement('textarea');
        textarea.innerHTML = text;
        return textarea.value;
    }

    // UI helpers
    function updateConversation() {
        if (!conversation) return;
        
        // Synchroniser avec la variable globale pour l'accès depuis HTML
        window.conversationHistory = conversationHistory;
        
        // Sauvegarder le message d'avertissement avant de vider
        const disclaimerElement = conversation.querySelector('.conversation-disclaimer');
        
        conversation.innerHTML = "";
        
        // Restaurer le message d'avertissement en premier
        if (disclaimerElement) {
            conversation.appendChild(disclaimerElement);
        }
        
        conversationHistory.forEach(entry => {
            const messageWrap = document.createElement('div');
            messageWrap.classList.add('message');
            if (entry.role === 'Vous') messageWrap.classList.add('user-message');
            else if (entry.role === 'Assistant') messageWrap.classList.add('bot-message');

            const roleSpan = document.createElement('strong');
            roleSpan.textContent = entry.role + ": ";
            messageWrap.appendChild(roleSpan);
            
            // Décoder les entités HTML avant d'afficher
            const decodedText = decodeHtmlEntities(entry.text);
            messageWrap.appendChild(document.createTextNode(decodedText));

            const ts = entry.timestamp || entry.time || null;
            if (ts) {
                const tsDiv = document.createElement('div');
                tsDiv.className = 'timestamp';
                try {
                    const d = new Date(ts);
                    const fr = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' }).format(d);
                    tsDiv.textContent = fr;
                } catch {
                    tsDiv.textContent = ts;
                }
                messageWrap.appendChild(tsDiv);
            }
            conversation.appendChild(messageWrap);
        });
        conversation.scrollTop = conversation.scrollHeight;
    }
    function updateStatus(message) { if (statusDiv) statusDiv.textContent = message; }
    function updateVoiceStatus(message) { if (voiceStatusDiv) voiceStatusDiv.textContent = message; }
    function updateButtons() {
        if (startButton) startButton.disabled = isRecognizing;
        if (stopButton) stopButton.disabled = !isRecognizing;
    }
    function disableSpeechButtons() {
        if (startButton) startButton.disabled = true;
        if (stopButton) stopButton.disabled = true;
    }

    // Chargement des voix
    async function loadVoices() {
        try {
            const response = await fetch('/static/data/liste_des_voix.txt');
            if (!response.ok) throw new Error('Erreur lors du chargement de la liste des voix');
            const text = await response.text();
            const lines = text.split('\n').filter(line => line.trim() && !line.startsWith('//'));
            const voicesData = lines.slice(1);
            const voices = { Homme: [], Femme: [] };
            voicesData.forEach(line => {
                const [sexe, nomVoix] = line.split(';');
                if (sexe && nomVoix && (sexe === 'Homme' || sexe === 'Femme')) {
                    voices[sexe].push(nomVoix.trim());
                }
            });
            return voices;
        } catch (error) {
            console.error('Erreur lors du chargement des voix:', error);
            return { Homme: ['fr-FR-HenriNeural'], Femme: ['fr-FR-DeniseNeural'] };
        }
    }

    function getRandomVoice(sexe) {
        if (!voicesList) {
            return sexe === 'Femme' ? 'fr-FR-DeniseNeural' : 'fr-FR-HenriNeural';
        }
        const voices = voicesList[sexe] || [];
        if (voices.length === 0) return sexe === 'Femme' ? 'fr-FR-DeniseNeural' : 'fr-FR-HenriNeural';
        const randomIndex = Math.floor(Math.random() * voices.length);
        return voices[randomIndex];
    }

    // Profil (inchangé)
    async function getPersonDetails() {
        try {
            const profileSelectorEl = document.getElementById('profileSelector');
            const profile = profileSelectorEl ? profileSelectorEl.value : null;
            const response = await fetch('/get_person_details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile })
            });
            if (!response.ok) throw new Error('Erreur lors de la récupération des détails du profil');
            return await response.json();
        } catch (error) {
            console.error('Erreur:', error);
            return { Sexe: 'Homme' };
        }
    }

    // Changement de profil
    window.handleProfileChange = function(newProfile) {
        currentProfile = newProfile;
        if (currentMode === 'voice' && synthesizer) {
            try { disablePTT(); } catch {}
            try { synthesizer.close(); } catch {}
            try { recognizer && recognizer.close(); } catch {}
            synthesizer = null; recognizer = null;
            initializeSpeechSDK().then(() => {
                updateStatus("Voix mise à jour selon le nouveau profil");
                if (currentMode === 'voice') enablePTT();
            });
        }
        
        // Ne pas vider automatiquement l'historique lors du changement de profil
        // L'utilisateur peut utiliser le bouton Reset s'il le souhaite
        updateStatus('Profil client changé : ' + newProfile);
    };

    // "Réponse IA"
    if (aiResponseButton) {
        aiResponseButton.addEventListener('click', function () {
            const conversationDiv = document.getElementById('conversation');
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message bot-message';
            loadingDiv.textContent = 'Génération de la réponse IA...';
            conversationDiv.appendChild(loadingDiv);

            fetch('/get_ai_response', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                conversationDiv.removeChild(loadingDiv);
                if (data.success && data.messages) {
                    data.messages.forEach(message => {
                        const messageDiv = document.createElement('div');
                        messageDiv.className = message.role === 'Assistant' ? 'message bot-message' : 'message user-message';
                        messageDiv.textContent = message.text;
                        conversationDiv.appendChild(messageDiv);
                    });
                    conversationHistory = data.history || conversationHistory;
                    conversationDiv.scrollTop = conversationDiv.scrollHeight;
                } else if (data.error) {
                    console.error('Erreur:', data.error);
                    updateStatus('Erreur lors de la génération de la réponse IA: ' + data.error);
                }
            })
            .catch(error => {
                conversationDiv.removeChild(loadingDiv);
                console.error('Erreur:', error);
                updateStatus('Erreur lors de la génération de la réponse IA');
            });
        });
    }

    // Initialisation
    updateStatus("Initialisation...");
    switchMode('text');  // par défaut
    
    // Récupérer l'historique existant depuis le serveur au lieu de le vider
    fetch('/get_conversation_history')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.history) {
                conversationHistory = data.history;
                window.conversationHistory = conversationHistory;
                updateConversation();
                updateStatus("Prêt");
            } else {
                conversationHistory = [];
                window.conversationHistory = conversationHistory;
                updateConversation();
                updateStatus("Prêt");
            }
        })
        .catch(error => {
            console.error('Erreur lors de la récupération de l\'historique:', error);
            conversationHistory = [];
            window.conversationHistory = conversationHistory;
            updateConversation();
            updateStatus("Prêt");
        });
});
