import React, { useState } from "react";
import axios from "axios";

export default function Chat({ backendBase }) {
  const [messages, setMessages] = useState([
    { role: "agent", text: "Hi — where would you like to go or ask about weather?" }
  ]);
  const [input, setInput] = useState("");
  const [conversation, setConversation] = useState([]);

  async function send() {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages((m) => [...m, { role: "user", text: userMessage }]);

    const updatedConversation = [
      ...conversation,
      { role: "user", content: userMessage }
    ];
    setConversation(updatedConversation);

    setInput("");

    try {
      const res = await axios.post(`${backendBase}/chat`, {
        message: userMessage,
        conversation: updatedConversation
      });

      const reply = res.data.reply || JSON.stringify(res.data);

      setMessages((m) => [...m, { role: "agent", text: reply }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Error: " + err.message }
      ]);
    }
  }

  return (
    <div style={{ maxWidth: 900 }}>
      <div
        style={{
          border: "1px solid #ddd",
          padding: 12,
          height: 420,
          overflowY: "auto",
          background: "#fafafa"
        }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              textAlign: m.role === "user" ? "right" : "left",
              margin: "8px 0"
            }}
          >
            <div
              style={{
                display: "inline-block",
                padding: 8,
                borderRadius: 8,
                background: m.role === "user" ? "#0ea5e9" : "#fff"
              }}
            >
              <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{m.text}</pre>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 8 }}>
        <input
          style={{ width: "70%", padding: 8 }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Plan 3 days in Manali for February - Mid budget"
        />
        <button style={{ padding: 8, marginLeft: 8 }} onClick={send}>
          Send
        </button>
      </div>
    </div>
  );
}
             