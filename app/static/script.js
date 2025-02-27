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
    sendButton.addEventListener('click', () => {
        const message = chatInput.value.trim();
        if (message) {
            addMessage(message, 'user');
            chatInput.value = ''; // 清空輸入框
            // 模擬系統回應
            setTimeout(() => {
                addMessage('系統回應', 'system');
            }, 1000);
        }
    });
});