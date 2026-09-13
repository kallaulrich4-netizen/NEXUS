import { useEffect, useRef, useState } from "react";
import { Send, Sparkles, Plus } from "lucide-react";
import { apiRequest } from "../../api/client";

export default function AiAssistant() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadConversations() {
    try {
      const data = await apiRequest("/ai/conversations");
      setConversations(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger les conversations.");
    }
  }

  async function openConversation(id) {
    setActiveConversationId(id);
    try {
      const detail = await apiRequest(`/ai/conversations/${id}`);
      setMessages(detail.messages);
    } catch (err) {
      setError(err.detail || "Impossible de charger cette conversation.");
    }
  }

  function startNewConversation() {
    setActiveConversationId(null);
    setMessages([]);
  }

  async function handleSend(e) {
    e.preventDefault();
    const content = input.trim();
    if (!content || isSending) return;

    setIsSending(true);
    setError("");
    setInput("");
    // Affichage optimiste du message utilisateur avant la réponse du serveur.
    setMessages((prev) => [...prev, { id: "temp", role: "user", content, created_at: new Date().toISOString() }]);

    try {
      const response = await apiRequest("/ai/messages", {
        method: "POST",
        body: { content, conversation_id: activeConversationId },
      });
      setActiveConversationId(response.conversation_id);
      setMessages((prev) => [...prev.slice(0, -1), response.user_message, response.assistant_message]);
      loadConversations();
    } catch (err) {
      setError(err.detail || "Le message n'a pas pu être envoyé.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4 max-w-6xl mx-auto">
      {/* Liste des conversations */}
      <div className="hidden md:flex flex-col w-64 shrink-0 nexus-card p-3">
        <button
          onClick={startNewConversation}
          className="nexus-btn-secondary w-full flex items-center justify-center gap-2 text-sm mb-3"
        >
          <Plus size={16} /> Nouvelle conversation
        </button>
        <div className="flex-1 overflow-y-auto space-y-1">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => openConversation(conv.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate ${
                activeConversationId === conv.id ? "bg-nexus-surface-hover" : "hover:bg-nexus-surface"
              }`}
            >
              {conv.title}
            </button>
          ))}
        </div>
      </div>

      {/* Fenêtre de conversation */}
      <div className="flex-1 flex flex-col nexus-card p-4 min-w-0">
        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center text-nexus-text-muted gap-3">
              <div className="w-14 h-14 rounded-full bg-nexus-gradient flex items-center justify-center">
                <Sparkles size={26} className="text-white" />
              </div>
              <p>Posez n'importe quelle question à Nexus AI pour commencer.</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={msg.id || i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                  msg.role === "user" ? "bg-nexus-gradient text-white" : "bg-nexus-surface text-nexus-text"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {error && <p className="text-sm text-red-400 mt-2">{error}</p>}

        <form onSubmit={handleSend} className="flex items-center gap-2 mt-4">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Écrivez votre message..."
            className="nexus-input flex-1"
          />
          <button type="submit" disabled={isSending} className="nexus-btn-primary p-2.5" aria-label="Envoyer">
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
