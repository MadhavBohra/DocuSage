document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const filePages = document.getElementById('filePages');
    const pdfPreview = document.getElementById('pdfPreview');
    const chatMessages = document.getElementById('chatMessages');
    const questionInput = document.getElementById('questionInput');
    const sendBtn = document.getElementById('sendBtn');
    const documentsContainer = document.getElementById('documentsContainer');
    const activeDocumentName = document.getElementById('activeDocumentName');

    const API_BASE_URL = 'http://localhost:8000';
    let uploadedFiles = [];
    let activeFileIndex = -1;
    let processingStatus = 'idle';
    let pollingInterval = null;

    fileInput.addEventListener('change', (e) => {
        e.stopPropagation();
        handleFiles(e.target.files);
        // Reset the file input value to allow re-uploading the same file
        fileInput.value = '';
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-active');
    });

    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-active'));

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-active');
        handleFiles(e.dataTransfer.files);
    });

    dropZone.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    sendBtn.addEventListener('click', sendQuestion);
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendQuestion();
    });

    function handleFiles(files) {
        let newFiles = [...files].filter(file => isValidPDF(file));

        if (newFiles.length === 0) return;

        // Clear previous uploads and chat when uploading new files
        clearEverything();
        
        addMessage('system', `Uploading ${newFiles.length} document(s)...`);
        uploadFiles(newFiles)
            .then(() => {
                uploadedFiles.push(...newFiles);
                updateDocumentsList();
                if (uploadedFiles.length > 0) setActiveFile(0);
                startProcessingStatusPolling();
            })
            .catch(error => addMessage('system', `Error uploading files: ${error.message}`));
    }

    function isValidPDF(file) {
        if (file.type !== 'application/pdf') {
            alert(`"${file.name}" is not a PDF.`);
            return false;
        }
        if (file.size > 10 * 1024 * 1024) {
            alert(`"${file.name}" exceeds 10MB limit.`);
            return false;
        }
        return true;
    }

    async function uploadFiles(files) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));

        try {
            const response = await fetch(`${API_BASE_URL}/upload-pdfs/`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Upload failed');
            }
            return response.json();
        } catch (error) {
            addMessage('system', `Upload error: ${error.message || 'Unknown error'}`);
            throw error;
        }
    }

    function clearEverything() {
        uploadedFiles = [];
        chatMessages.innerHTML = '';
        pdfPreview.innerHTML = '';
        fileName.textContent = 'No file selected';
        filePages.textContent = '';
        activeDocumentName.textContent = '';
        activeFileIndex = -1;
        processingStatus = 'idle';
        
        // Clear any existing polling
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
        
        // Disable question input until processing completes
        questionInput.disabled = true;
        sendBtn.disabled = true;
        
        updateDocumentsList();
    }

    function startProcessingStatusPolling() {
        // Stop any existing polling
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        processingStatus = 'processing';
        pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/processing-status/`);
                const data = await response.json();
                processingStatus = data.status;

                if (processingStatus === 'completed') {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    questionInput.disabled = false;
                    sendBtn.disabled = false;
                    addMessage('system', 'Processing complete! Ask questions now.');
                } else if (processingStatus === 'failed') {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    addMessage('system', `Processing failed: ${data.message}`);
                }
            } catch (error) {
                clearInterval(pollingInterval);
                pollingInterval = null;
                addMessage('system', 'Error checking processing status.');
            }
        }, 3000);
    }

    function updateDocumentsList() {
        documentsContainer.innerHTML = uploadedFiles.length === 0
            ? '<p class="no-documents">No documents uploaded yet</p>'
            : uploadedFiles.map((file, index) => `
                <div class="document-card ${index === activeFileIndex ? 'active' : ''}" data-index="${index}">
                    <h3>${file.name}</h3>
                    <p>${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    <button class="remove-btn" data-index="${index}"><i class="fas fa-times"></i></button>
                </div>
            `).join('');

        document.querySelectorAll('.document-card').forEach(card => {
            card.addEventListener('click', () => setActiveFile(parseInt(card.dataset.index)));
        });

        document.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                removeFile(parseInt(btn.dataset.index));
            });
        });
    }

    function setActiveFile(index) {
        if (index < 0 || index >= uploadedFiles.length) return;
        
        activeFileIndex = index;
        const file = uploadedFiles[index];
        fileName.textContent = file.name;
        pdfPreview.innerHTML = `<iframe src="${URL.createObjectURL(file)}" width="100%" height="100%"></iframe>`;
        activeDocumentName.textContent = file.name;
        filePages.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
        
        // Update active class in document list
        document.querySelectorAll('.document-card').forEach((card, idx) => {
            if (idx === index) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });
    }

    function sendQuestion() {
        const question = questionInput.value.trim();
        if (!question) return;
        
        // Disable input while waiting for response
        questionInput.disabled = true;
        sendBtn.disabled = true;

        addMessage('user', question);
        questionInput.value = '';

        fetch(`${API_BASE_URL}/ask-question/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `question=${encodeURIComponent(question)}`
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            addMessage('assistant', data.answer);
        })
        .catch((error) => {
            addMessage('system', `Error processing request: ${error.message}`);
        })
        .finally(() => {
            // Re-enable input after response
            questionInput.disabled = false;
            sendBtn.disabled = false;
            questionInput.focus();
        });
    }

    function addMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        messageDiv.innerHTML = `<p>${text}</p>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeFile(index) {
        if (index < 0 || index >= uploadedFiles.length) return;
        
        uploadedFiles.splice(index, 1);
        updateDocumentsList();
        
        if (uploadedFiles.length > 0) {
            // If we removed the active file or one before it, adjust the active index
            if (index <= activeFileIndex) {
                const newIndex = Math.min(activeFileIndex, uploadedFiles.length - 1);
                setActiveFile(newIndex);
            }
        } else {
            // No files left
            activeFileIndex = -1;
            pdfPreview.innerHTML = '';
            fileName.textContent = 'No file selected';
            filePages.textContent = '';
            activeDocumentName.textContent = '';
        }
    }

    // Initialize the UI
    updateDocumentsList();
});