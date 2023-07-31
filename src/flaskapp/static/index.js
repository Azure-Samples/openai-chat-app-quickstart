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

    const response = await fetch(`/chat?message=${message}`);
    messageDiv.innerHTML = "";
    let answer = "";
    for await (const event of readNDJSONStream(response.body)) {
        if (event["choices"][0]["delta"]["content"]) {
            answer += event["choices"][0]["delta"]["content"];
            messageDiv.innerHTML = converter.makeHtml(answer);
            messageDiv.scrollIntoView();
        }
    }

    messageInput.value = "";
});