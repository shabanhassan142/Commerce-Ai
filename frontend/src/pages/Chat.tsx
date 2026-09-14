// src/pages/Chat.tsx
// AI Chat interface — ChatGPT/Perplexity-style with citations

import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bot,
  Check,
  ChevronDown,
  Copy,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  Trash2,
  User,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import chatService from "../services/chat.service";
import type { ChatConversation, ChatMessage } from "../types";

// ── Simple inline Markdown renderer ──────────────────────────────────────────
function SimpleMarkdown({ content }: { content: string }) {
  const html = content
    .replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/^[\-\*] (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br/>");

  return (
    <div
      className="prose-chat"
      dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
    />
  );
}

// ── AI Thinking indicator ─────────────────────────────────────────────────────
const THINKING_STEPS = [
  "Understanding your request",
  "Searching knowledge base",
  "Checking your orders",
  "Generating response",
];

function ThinkingIndicator() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setStep((s) => (s + 1) % THINKING_STEPS.length), 1200);
    return () => clearInterval(t);
  }, []);
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center flex-shrink-0">
        <Bot size={14} className="text-white" />
      </div>
      <div className="card px-4 py-3 max-w-sm">
        <div className="flex items-center gap-2 mb-2">
          <div className="flex gap-1">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
          <span className="text-xs text-[#8888aa]">AI is thinking</span>
        </div>
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-xs text-primary-400"
          >
            {THINKING_STEPS[step]}…
          </motion.p>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ── Citation chips ────────────────────────────────────────────────────────────
function Citations({ citations }: { citations: NonNullable<ChatMessage["citations"]> }) {
  if (!citations.length) return null;
  return (
    <div className="mt-3 space-y-1">
      <p className="text-[10px] font-semibold text-[#8888aa] uppercase tracking-wide">Sources</p>
      <div className="flex flex-wrap gap-2">
        {citations.map((c, i) => {
          const score = c.relevance ?? c.score;
          const pct = score != null ? Math.round(score * 100) : null;
          return (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-500/8 border border-primary-500/15 text-xs"
              title={c.content}
            >
              <span className="text-base">📄</span>
              <div>
                <p className="font-medium text-[color:var(--color-text)]">
                  {c.title ?? c.source ?? `Source ${i + 1}`}
                </p>
                {pct != null && (
                  <p className="text-[#8888aa]">Relevance: {pct}%</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────
function MessageBubble({
  message,
  onCopy,
  onRegenerate,
}: {
  message: ChatMessage;
  onCopy: (content: string) => void;
  onRegenerate?: () => void;
}) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    onCopy(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser
          ? "bg-primary-500/20 border border-primary-500/30"
          : "bg-gradient-to-br from-primary-500 to-accent-500"
      }`}>
        {isUser
          ? <User size={14} className="text-primary-400" />
          : <Bot size={14} className="text-white" />
        }
      </div>

      {/* Content */}
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[80%]`}>
        {/* Intent badge */}
        {!isUser && message.intent && (
          <span className="text-[10px] text-[#8888aa] mb-1 px-2 py-0.5 rounded-full bg-white/5 border border-white/10">
            {message.intent} · {message.agent}
          </span>
        )}

        {/* Bubble */}
        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-primary-600 text-white rounded-tr-sm"
            : message.error
            ? "card border-red-500/30 bg-red-500/5"
            : "card rounded-tl-sm"
        }`}>
          {isUser ? (
            <p className="text-sm leading-relaxed">{message.content}</p>
          ) : (
            <SimpleMarkdown content={message.content} />
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <Citations citations={message.citations} />
        )}

        {/* Actions row */}
        <div className="flex items-center gap-2 mt-1.5 text-[#8888aa]">
          <span className="text-[10px]">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          {!isUser && (
            <>
              <button
                onClick={handleCopy}
                className="p-1 hover:text-[color:var(--color-text)] transition-colors"
                aria-label="Copy"
              >
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
              </button>
              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  className="p-1 hover:text-[color:var(--color-text)] transition-colors"
                  aria-label="Regenerate"
                >
                  <RefreshCw size={12} />
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── Main Chat Page ────────────────────────────────────────────────────────────
export default function Chat() {
  const location = useLocation();
  const [conversations, setConversations] = useState<ChatConversation[]>(
    () => chatService.getConversations()
  );
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  // Module 10: product context from ProductDetail navigation state
  const locationState = location.state as { initialMessage?: string; product_id?: string; product_name?: string } | null;
  const [productId] = useState<string | undefined>(locationState?.product_id ?? undefined);
  const [productName] = useState<string | undefined>(locationState?.product_name ?? undefined);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const initialSentRef = useRef(false);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }, []);

  useEffect(() => scrollToBottom(), [messages, isTyping]);

  const mutation = useMutation({
    mutationFn: chatService.sendMessage,
    onSuccess: (result) => {
      setIsTyping(false);
      if (result.conversation_id) setConversationId(result.conversation_id);

      const answerText = result.answer || (result as any).message || "Response generated successfully.";

      const aiMsg = chatService.newMessage("assistant", answerText, {
        citations: result.citations,
        intent: result.intent,
        agent: result.agent,
        confidence: result.confidence,
      });

      setMessages((prev) => {
        const next = [...prev, aiMsg];
        // Save to history
        const conv: ChatConversation = {
          id: result.conversation_id ?? activeId ?? crypto.randomUUID(),
          title: chatService.generateTitle(prev[0]?.content ?? "Conversation"),
          lastMessage: answerText.slice(0, 60),
          timestamp: aiMsg.timestamp,
          messages: next,
        };
        chatService.saveConversation(conv);
        setConversations(chatService.getConversations());
        if (!activeId) setActiveId(conv.id);
        return next;
      });
    },
    onError: () => {
      setIsTyping(false);
      const errMsg = chatService.newMessage(
        "assistant",
        "Sorry, I couldn't process your request. Please try again.",
        { error: true }
      );
      setMessages((prev) => [...prev, errMsg]);
    },
  });

  const sendMessage = useCallback(
    (content?: string) => {
      const text = (content ?? input).trim();
      if (!text) return;

      const userMsg = chatService.newMessage("user", text);
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsTyping(true);
      // Module 10: include product_id in every message of this conversation
      mutation.mutate({ message: text, conversation_id: conversationId, product_id: productId });
    },
    [input, conversationId, productId, mutation]
  );

  // Auto-send initial message if navigated from ProductDetail
  useEffect(() => {
    const initMsg = (location.state as { initialMessage?: string })?.initialMessage;
    if (initMsg && !initialSentRef.current) {
      initialSentRef.current = true;
      sendMessage(initMsg);
    }
  }, [location.state, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNew = () => {
    setMessages([]);
    setConversationId(undefined);
    setActiveId(null);
    setHistoryOpen(false);
    inputRef.current?.focus();
  };

  const loadConversation = (conv: ChatConversation) => {
    setMessages(conv.messages);
    setConversationId(conv.id);
    setActiveId(conv.id);
    setHistoryOpen(false);
  };

  const deleteConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    chatService.deleteConversation(id);
    setConversations(chatService.getConversations());
    if (id === activeId) startNew();
  };

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const regenerateLast = () => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (lastUser) {
      setMessages((prev) => prev.slice(0, -1));
      setIsTyping(true);
      mutation.mutate({ message: lastUser.content, conversation_id: conversationId });
    }
  };

  const lastAiIndex = messages.map((m, i) => ({ m, i })).filter(({ m }) => m.role === "assistant").at(-1)?.i;

  return (
    <div className="h-[calc(100vh-4rem)] flex overflow-hidden">
      {/* ── History sidebar ────────────────────────────────────────────────── */}
      <AnimatePresence>
        {historyOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="flex-shrink-0 card border-r border-white/5 flex flex-col overflow-hidden mr-4 rounded-2xl"
          >
            <div className="p-3 border-b border-white/5 flex items-center justify-between">
              <span className="text-sm font-semibold text-[color:var(--color-text)]">History</span>
              <button onClick={() => setHistoryOpen(false)} className="text-[#8888aa] hover:text-[color:var(--color-text)]"><X size={14} /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {conversations.length === 0 ? (
                <p className="text-xs text-[#8888aa] text-center py-8">No conversations yet</p>
              ) : (
                conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversation(conv)}
                    className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-colors group flex items-start gap-2 ${conv.id === activeId ? "bg-primary-500/15 text-primary-300" : "text-[#8888aa] hover:bg-white/5 hover:text-[color:var(--color-text)]"}`}
                  >
                    <MessageSquare size={13} className="mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate text-xs">{conv.title}</p>
                      <p className="text-[10px] text-[#8888aa] truncate">{conv.lastMessage}</p>
                    </div>
                    <button
                      onClick={(e) => deleteConversation(conv.id, e)}
                      className="opacity-0 group-hover:opacity-100 text-[#8888aa] hover:text-red-400 transition-all"
                    >
                      <Trash2 size={11} />
                    </button>
                  </button>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Chat panel ────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 card rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setHistoryOpen(!historyOpen)}
              className="p-1.5 rounded-lg text-[#8888aa] hover:text-[color:var(--color-text)] hover:bg-white/5"
              aria-label="Chat history"
            >
              <MessageSquare size={16} />
            </button>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                <Bot size={12} className="text-white" />
              </div>
              <span className="text-sm font-semibold text-[color:var(--color-text)]">CommerceFlow AI</span>
            </div>
            {/* Module 10: Product context badge */}
            {productName && (
              <span className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary-500/15 border border-primary-500/25 text-[10px] text-primary-300 font-medium">
                <Bot size={9} />
                {productName}
              </span>
            )}
          </div>
          <button
            onClick={startNew}
            className="flex items-center gap-1.5 text-xs text-[#8888aa] hover:text-[color:var(--color-text)] px-3 py-1.5 rounded-lg hover:bg-white/5 transition-colors border border-white/10"
          >
            <Plus size={13} /> New
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center h-full gap-6 text-center"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow-md">
                <Bot size={30} className="text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-[color:var(--color-text)]">CommerceFlow AI</h2>
                <p className="text-[#8888aa] text-sm mt-1">Ask me about your orders, products, returns, or anything else.</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md w-full">
                {[
                  "Where is my order?",
                  "What is your return policy?",
                  "I need help with my refund",
                  "Tell me about wireless earbuds",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="text-left px-4 py-3 rounded-xl border border-white/10 text-sm text-[#8888aa] hover:text-[color:var(--color-text)] hover:bg-white/5 hover:border-primary-500/30 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {messages.map((msg, idx) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onCopy={copyToClipboard}
              onRegenerate={idx === lastAiIndex ? regenerateLast : undefined}
            />
          ))}

          {isTyping && <ThinkingIndicator />}

          <div ref={bottomRef} />
        </div>

        {/* Scroll-to-bottom */}
        {messages.length > 3 && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-24 right-6 w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-[#8888aa] hover:text-white transition-colors"
          >
            <ChevronDown size={16} />
          </button>
        )}

        {/* Input */}
        <div className="p-4 border-t border-white/5">
          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask CommerceFlow AI…"
              rows={1}
              className="flex-1 input-field resize-none min-h-[44px] max-h-32 py-3 leading-5"
              style={{ height: "auto" }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 128) + "px";
              }}
              disabled={isTyping}
              aria-label="Chat input"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isTyping}
              className="w-11 h-11 rounded-xl bg-primary-600 hover:bg-primary-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors flex-shrink-0"
              aria-label="Send message"
            >
              <Send size={16} className="text-white" />
            </button>
          </div>
          <p className="text-[10px] text-[#8888aa] mt-2 text-center">
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}
