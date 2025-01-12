document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const voiceInputBtn = document.getElementById('voice-input-btn');
    
    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let recognition = null;

    // Check for browser support and request permissions
    async function initializeSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window)) {
            voiceInputBtn.style.display = 'none';
            console.error('Speech recognition not supported');
            return;
        }

        try {
            // Request microphone permission
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop()); // Stop the stream after permission check

            recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
        } catch (err) {
            console.error('Microphone permission denied:', err);
            voiceInputBtn.style.display = 'none';
        }
    }

    // Initialize speech recognition when page loads
    initializeSpeechRecognition();

    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage(message, 'user');
        messageInput.value = '';

        try {
            const response = await fetch('/api/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();
            if (data.success) {
                if (data.response.type === 'order') {
                    addOrderMessage(data.response.data, 'bot');
                } else {
                    addMessage(data.response.message, 'bot');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('Sorry, there was an error processing your message.', 'bot');
        }
    });

    voiceInputBtn.addEventListener('click', async function() {
        if (!recognition) {
            addMessage('Speech recognition is not supported or microphone access was denied.', 'bot');
            return;
        }

        if (!isRecording) {
            try {
                isRecording = true;
                voiceInputBtn.querySelector('img').classList.add('recording'); // Update selector to match your HTML
                addMessage('Listening... Please speak now.', 'bot');

                recognition.start();

                recognition.onresult = function(event) {
                    const text = event.results[0][0].transcript;
                    messageInput.value = text;
                    
                    chatForm.dispatchEvent(new Event('submit'));
                };

                recognition.onerror = function(event) {
                    console.error('Speech recognition error:', event.error);
                    addMessage(`Error: ${event.error}. Please try again.`, 'bot');
                    stopRecording();
                };

                recognition.onend = function() {
                    stopRecording();
                };

            } catch (error) {
                console.error('Error during speech recognition:', error);
                addMessage('Error processing voice input. Please try again.', 'bot');
                stopRecording();
            }
        } else {
            recognition.stop();
        }
    });

    function stopRecording() {
        isRecording = false;
        voiceInputBtn.querySelector('img').classList.remove('recording');
    }

    function addMessage(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = content;
        
        // Add timestamp
        const now = new Date();
        const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageContent.setAttribute('data-time', time);
        
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Add animation class
        setTimeout(() => {
            messageDiv.classList.add('message-appear');
        }, 100);
    }

    function addOrderMessage(order, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content order-details';
        messageContent.innerHTML = `
            <h3>Order Details</h3>
            <p><strong>Order ID:</strong> ${order.order_id}</p>
            <p><strong>Customer:</strong> ${order.customer_name}</p>
            <p><strong>Product:</strong> ${order.product_name}</p>
            <p><strong>Address:</strong> ${order.address}</p>
            <p><strong>Status:</strong> <span class="status-${order.status.toLowerCase().replace(' ', '-')}">${order.status}</span></p>
            <p><strong>Date:</strong> ${order.date}</p>
        `;
        
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } 
});