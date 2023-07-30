let eventSource;
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const targetContainer = document.getElementById("messages");
const userTemplate = document.querySelector('#message-template-user');
const assistantTemplate = document.querySelector('#message-template-assistant');
const converter = new showdown.Converter();

form.addEventListener("submit", async function(e) {
    e.preventDefault();
    const message = messageInput.value;

    const userTemplateClone = userTemplate.content.cloneNode(true);
    userTemplateClone.querySelector(".message-content").innerText = message;
    targetContainer.appendChild(userTemplateClone);

    const assistantTemplateClone = assistantTemplate.content.cloneNode(true);
    let messageDiv = assistantTemplateClone.querySelector(".message-content");
    targetContainer.appendChild(assistantTemplateClone);

    //for await (const part of stream) {
    //    console.log(part.choices[0].delta);
    //}

    let answer = "";
    const response = await fetch(`/chat?message=${message}`);
    const reader = response.body.getReader();
    messageDiv.innerHTML = "";
    let runningText = "";
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        var text = new TextDecoder("utf-8").decode(value);
        const objects = text.split("\n");
        objects.forEach((obj) => {
            try {
                runningText += obj;
                result = JSON.parse(runningText);
                if (result["choices"] && result["choices"][0]["delta"]["content"]) {
                    answer += result["choices"][0]["delta"]["content"];
                    messageDiv.innerHTML = converter.makeHtml(answer);
                    messageDiv.scrollIntoView();
                }
                runningText = "";
            }
            catch { }
        });
    };

    messageInput.value = "";
});