document.addEventListener('DOMContentLoaded', () => {
    const queryForm = document.getElementById('queryForm');
    const queryInput = document.getElementById('queryInput');
    const chatMessages = document.getElementById('chatMessages');
    const voiceBtn = document.getElementById('voiceBtn');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileList = document.getElementById('fileList');
    const uploadStatus = document.getElementById('uploadStatus');
    const documentList = document.getElementById('documentList');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const menuBtn = document.getElementById('menu-btn');
    const closeSidebar = document.querySelector('.close-sidebar');
    const fab = document.getElementById('fab');
    const themeToggle = document.querySelector('.theme-toggle');
    const welcomeTooltip = document.getElementById('welcomeTooltip');
    const closeTooltip = welcomeTooltip.querySelector('.close-btn');

    // Speech synthesis setup
    const synth = window.speechSynthesis;
    let currentUtterance = null;
    let speechState = 'stopped'; // 'playing', 'paused', 'stopped'

    // Chat submission
    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = queryInput.value.trim();
        if (!question) return;

        // Display user message
        const userDiv = document.createElement('div');
        userDiv.className = 'chat-message user-message';
        userDiv.textContent = question;
        chatMessages.appendChild(userDiv);
        queryInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, customer_data: '' })
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${await response.text()}`);
            }
            const data = await response.json();
            const botDiv = document.createElement('div');
            botDiv.className = 'chat-message bot-message';
            const sourcesText = data.sources.length ? data.sources.join(', ') : 'No sources found';
            const controlPanel = document.createElement('div');
            controlPanel.className = 'speech-controls';
            controlPanel.innerHTML = `
                <button class="speech-btn play-btn" aria-label="Play speech">▶️</button>
                <button class="speech-btn pause-btn" aria-label="Pause speech" disabled>⏸️</button>
                <button class="speech-btn stop-btn" aria-label="Stop speech" disabled>⏹️</button>
            `;
            botDiv.innerHTML = `<strong>LoanBot:</strong> ${data.answer}<br><small>Sources: ${sourcesText}</small>`;
            botDiv.appendChild(controlPanel);
            chatMessages.appendChild(botDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Speech synthesis
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(data.answer);
                utterance.lang = 'en-GB';
                utterance.volume = 1;
                utterance.rate = 1.1;
                utterance.pitch = 1;

                // Voice selection
                const voices = synth.getVoices();
                const selectedVoice = voices.find(voice => voice.lang.includes('en-GB') && voice.name.includes('Male')) || voices[0];
                if (selectedVoice) utterance.voice = selectedVoice;

                // Speech control buttons
                const playBtn = controlPanel.querySelector('.play-btn');
                const pauseBtn = controlPanel.querySelector('.pause-btn');
                const stopBtn = controlPanel.querySelector('.stop-btn');

                playBtn.addEventListener('click', () => {
                    if (speechState === 'stopped' || speechState === 'paused') {
                        if (speechState === 'stopped') {
                            currentUtterance = utterance;
                            synth.speak(utterance);
                        } else {
                            synth.resume();
                        }
                        speechState = 'playing';
                        playBtn.disabled = true;
                        pauseBtn.disabled = false;
                        stopBtn.disabled = false;
                    }
                });

                pauseBtn.addEventListener('click', () => {
                    if (speechState === 'playing') {
                        synth.pause();
                        speechState = 'paused';
                        playBtn.disabled = false;
                        pauseBtn.disabled = true;
                        stopBtn.disabled = false;
                    }
                });

                stopBtn.addEventListener('click', () => {
                    if (speechState !== 'stopped') {
                        synth.cancel();
                        speechState = 'stopped';
                        playBtn.disabled = false;
                        pauseBtn.disabled = true;
                        stopBtn.disabled = true;
                    }
                });

                utterance.onend = () => {
                    speechState = 'stopped';
                    playBtn.disabled = false;
                    pauseBtn.disabled = true;
                    stopBtn.disabled = true;
                };

                utterance.onerror = (e) => {
                    console.error('Speech synthesis error:', e);
                    speechState = 'stopped';
                    playBtn.disabled = false;
                    pauseBtn.disabled = true;
                    stopBtn.disabled = true;
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'status-message status-error';
                    errorDiv.textContent = `❌ Speech synthesis error: ${e.error}`;
                    chatMessages.appendChild(errorDiv);
                };

                // Auto-play if no other speech is active
                if (speechState === 'stopped') {
                    currentUtterance = utterance;
                    synth.speak(utterance);
                    speechState = 'playing';
                    playBtn.disabled = true;
                    pauseBtn.disabled = false;
                    stopBtn.disabled = false;
                }
            } else {
                console.warn('SpeechSynthesis not supported');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'status-message status-error';
                errorDiv.textContent = '❌ Speech synthesis not supported in this browser.';
                chatMessages.appendChild(errorDiv);
            }
        } catch (error) {
            console.error('Query error:', error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'status-message status-error';
            errorDiv.textContent = `❌ Failed to get response: ${error.message}`;
            chatMessages.appendChild(errorDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    });

    // Voice input
    let isRecording = false;
    voiceBtn.addEventListener('click', () => {
        if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'status-message status-error';
            errorDiv.textContent = '❌ Voice input not supported in this browser.';
            chatMessages.appendChild(errorDiv);
            return;
        }

        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'en-US';
        recognition.interimResults = false;

        if (!isRecording) {
            recognition.start();
            voiceBtn.textContent = '🛑';
            voiceBtn.setAttribute('aria-label', 'Stop voice input');
            isRecording = true;
        } else {
            recognition.stop();
            voiceBtn.textContent = '🎙️';
            voiceBtn.setAttribute('aria-label', 'Toggle voice input');
            isRecording = false;
        }

        recognition.onresult = async (event) => {
            const transcript = event.results[0][0].transcript;
            queryInput.value = transcript;
            voiceBtn.textContent = '🎙️';
            voiceBtn.setAttribute('aria-label', 'Toggle voice input');
            isRecording = false;
            queryForm.dispatchEvent(new Event('submit'));
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'status-message status-error';
            errorDiv.textContent = `❌ Voice input error: ${event.error}`;
            chatMessages.appendChild(errorDiv);
            voiceBtn.textContent = '🎙️';
            voiceBtn.setAttribute('aria-label', 'Toggle voice input');
            isRecording = false;
        };
    });

    // File upload
    fileInput.addEventListener('change', () => {
        fileList.innerHTML = '';
        uploadBtn.disabled = fileInput.files.length === 0;
        uploadBtn.setAttribute('aria-disabled', fileInput.files.length === 0);
        Array.from(fileInput.files).forEach(file => {
            const li = document.createElement('li');
            li.textContent = `${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
            fileList.appendChild(li);
        });
    });

    uploadBtn.addEventListener('click', async () => {
        const formData = new FormData();
        Array.from(fileInput.files).forEach(file => formData.append('files', file));
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${await response.text()}`);
            }
            const data = await response.json();
            const successDiv = document.createElement('div');
            successDiv.className = 'status-message status-success';
            successDiv.textContent = `✅ Successfully uploaded: ${data.files_uploaded.join(', ')}`;
            uploadStatus.appendChild(successDiv);
            fileInput.value = '';
            fileList.innerHTML = '';
            uploadBtn.disabled = true;
            uploadBtn.setAttribute('aria-disabled', 'true');
            await loadDocuments();
        } catch (error) {
            console.error('Upload error:', error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'status-message status-error';
            errorDiv.textContent = `❌ Upload failed: ${error.message}`;
            uploadStatus.appendChild(errorDiv);
        }
    });

    // Load documents
    async function loadDocuments() {
        try {
            const response = await fetch('/documents');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${await response.text()}`);
            }
            const data = await response.json();
            documentList.innerHTML = '';
            if (data.documents.length === 0) {
                const li = document.createElement('li');
                li.textContent = 'No documents uploaded';
                documentList.appendChild(li);
            } else {
                data.documents.forEach(doc => {
                    const li = document.createElement('li');
                    li.innerHTML = `${doc.filename} (${doc.size_kb} KB, Last Modified: ${doc.last_modified}) 
                        <button class="delete-btn" data-filename="${doc.filename}" aria-label="Delete ${doc.filename}">🗑️</button>`;
                    documentList.appendChild(li);
                });
            }
        } catch (error) {
            console.error('Document load error:', error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'status-message status-error';
            errorDiv.textContent = `❌ Failed to load documents: ${error.message}`;
            documentList.appendChild(errorDiv);
        }
    }

    // Delete document
    documentList.addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-btn')) {
            const filename = e.target.getAttribute('data-filename');
            try {
                const response = await fetch('/documents', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename })
                });
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
                }
                const data = await response.json();
                const successDiv = document.createElement('div');
                successDiv.className = 'status-message status-success';
                successDiv.textContent = `✅ ${data.message}`;
                documentList.appendChild(successDiv);
                await loadDocuments();
            } catch (error) {
                console.error('Delete error:', error);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'status-message status-error';
                errorDiv.textContent = `❌ Failed to delete ${filename}: ${error.message}`;
                documentList.appendChild(errorDiv);
            }
        }
    });

    // Clear chat
    clearChatBtn.addEventListener('click', () => {
        chatMessages.innerHTML = '';
        synth.cancel(); // Stop any ongoing speech
        speechState = 'stopped';
        const welcomeMessage = document.createElement('div');
        welcomeMessage.className = 'chat-message bot-message';
        welcomeMessage.innerHTML = `<strong>LoanBot:</strong> Welcome to HDB Financial Services Q&A! How can I assist you today?`;
        chatMessages.appendChild(welcomeMessage);
    });

    // Sidebar controls
    menuBtn.addEventListener('click', () => {
        sidebar.classList.add('open');
        sidebarOverlay.classList.add('active');
        menuBtn.setAttribute('aria-expanded', 'true');
    });

    closeSidebar.addEventListener('click', () => {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
        menuBtn.setAttribute('aria-expanded', 'false');
    });

    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
        menuBtn.setAttribute('aria-expanded', 'false');
    });

    fab.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        sidebarOverlay.classList.toggle('active');
        menuBtn.setAttribute('aria-expanded', sidebar.classList.contains('open'));
    });

    // Theme toggle
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        themeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        themeToggle.querySelector('.theme-icon').textContent = isDark ? '☀️' : '🌙';
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });

    // Load saved theme
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
        themeToggle.querySelector('.theme-icon').textContent = '☀️';
    }

    // Close tooltip
    closeTooltip.addEventListener('click', () => {
        welcomeTooltip.style.display = 'none';
    });

    // Health check
    async function checkHealth(retries = 5, delay = 3000) {
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch('/health');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                if (data.status === 'unhealthy') {
                    const statusDiv = document.createElement('div');
                    statusDiv.className = 'status-message status-error';
                    statusDiv.innerHTML = `❌ AI assistant is unavailable: ${data.detail}. Please try again later or contact support.`;
                    chatMessages.appendChild(statusDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
                return;
            } catch (error) {
                console.error(`Health check attempt ${i + 1} failed:`, error);
                if (i === retries - 1) {
                    const statusDiv = document.createElement('div');
                    statusDiv.className = 'status-message status-error';
                    statusDiv.innerHTML = `❌ Failed to connect to AI assistant: ${error.message}. Check your network or contact support.`;
                    chatMessages.appendChild(statusDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    // Initial setup
    async function init() {
        await loadDocuments();
        await checkHealth();
        const welcomeMessage = document.createElement('div');
        welcomeMessage.className = 'chat-message bot-message';
        welcomeMessage.innerHTML = `<strong>LoanBot:</strong> Welcome to HDB Financial Services Q&A! How can I assist you today?`;
        chatMessages.appendChild(welcomeMessage);
    }

    init();
});