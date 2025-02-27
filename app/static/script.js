document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('file-upload');
    const fileList = document.getElementById('file-list');
    const screenshotImg = document.getElementById('screenshot-img');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatHistory = document.getElementById('chat-history');


    // 處理檔案上傳
    fileUpload.addEventListener('change', (event) => {
        const files = event.target.files;
        Array.from(files).forEach(file => {
            const li = document.createElement('li');
            li.textContent = file.name;
            const removeButton = document.createElement('button');
            removeButton.textContent = '移除';
            removeButton.className = 'remove-button';
            removeButton.addEventListener('click', () => {
                fileList.removeChild(li);
            });
            li.appendChild(removeButton);
            fileList.appendChild(li);

            // 如果是圖片，顯示截圖
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    screenshotImg.src = e.target.result;
                    screenshotImg.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    });

    // 添加訊息到對話歷史的函數
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.textContent = text;
        messageDiv.className = sender === 'user' ? 'user-message' : 'system-message';
        chatHistory.insertBefore(messageDiv, chatHistory.firstChild); // 插入到最前面
    }

    // 發送按鈕的事件監聽器
    sendButton.addEventListener('click', async () => {
        const message = chatInput.value.trim();
        if (message) {
            // 1. 將用戶的訊息添加到聊天歷史中
            addMessage(message, 'user');
            chatInput.value = ''; // 清空輸入框

            // 2. 將訊息發送到後端並接收回應
            try {
                const formData = new FormData();
                formData.append('text', message);

                const response = await fetch('/chat-submit', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('後端回應異常');
                }

                const data = await response.json();

                // 3. 將後端的回應添加到聊天歷史中
                addMessage(data.result, 'system');
            } catch (error) {
                console.error('錯誤:', error);
                addMessage('系統錯誤，請稍後再試。', 'system');
            }
        }
    });
});