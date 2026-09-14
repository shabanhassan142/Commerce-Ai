// src/pages/Landing.tsx
// Hero landing page for CommerceFlow AI

import { motion } from "framer-motion";
import { ArrowRight, Bot, Brain, MessageSquare, Shield, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { fadeInUp, stagger, staggerItem } from "../animations/variants";

const FEATURES = [
  {
    icon: Bot,
    title: "Multi-Agent AI",
    desc: "9 specialized agents — Order, Refund, Billing, Product, Knowledge, Support, and more.",
  },
  {
    icon: Brain,
    title: "RAG-Powered",
    desc: "Semantic search over company policies with FAISS and local BAAI embeddings.",
  },
  {
    icon: MessageSquare,
    title: "Natural Conversations",
    desc: "Understands intent, retrieves data, and responds with cited, accurate answers.",
  },
  {
    icon: Shield,
    title: "Role-Based Access",
    desc: "Customer, Support Agent, and Admin roles with JWT-secured endpoints.",
  },
  {
    icon: Zap,
    title: "LangGraph Orchestration",
    desc: "Supervisor routes every message to the right specialist agent automatically.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-mesh text-white">
      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-5 glass border-b border-primary-500/10 sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-glow-sm">
            <Bot size={16} className="text-white" />
          </div>
          <span className="font-bold text-white">CommerceFlow AI</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="btn-ghost text-sm">Sign in</Link>
          <Link to="/register" className="btn-primary text-sm px-4 py-2">Get started</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative py-24 px-6 text-center overflow-hidden">
        {/* Glow orbs */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full bg-primary-600/15 blur-[120px] pointer-events-none" />
        <div className="absolute top-20 right-1/4 w-[300px] h-[300px] rounded-full bg-accent-600/10 blur-[80px] pointer-events-none" />

        <motion.div
          variants={stagger}
          initial="hidden"
          animate="visible"
          className="max-w-4xl mx-auto relative"
        >
          <motion.div variants={staggerItem} className="inline-flex items-center gap-2 mb-6 px-4 py-2 rounded-full glass border border-primary-500/20 text-sm text-primary-400">
            <div className="glow-dot" />
            <span>Multi-Agent AI Platform</span>
          </motion.div>

          <motion.h1 variants={staggerItem} className="text-5xl sm:text-6xl font-extrabold leading-tight mb-6">
            <span className="gradient-text">AI-Powered</span>
            <br />
            Customer Support
            <br />
            <span className="text-white">for E-Commerce</span>
          </motion.h1>

          <motion.p variants={staggerItem} className="text-xl text-[#8888aa] max-w-2xl mx-auto mb-10 leading-relaxed">
            CommerceFlow AI routes every customer question to the right specialist agent —
            orders, refunds, billing, products, policies — automatically.
          </motion.p>

          <motion.div variants={staggerItem} className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/register" className="btn-primary flex items-center gap-2 px-8 py-3 text-base">
              Start for free <ArrowRight size={16} />
            </Link>
            <Link to="/login" className="btn-ghost text-base px-8 py-3">
              Sign in
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <motion.h2
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="text-3xl font-bold text-center text-white mb-12"
          >
            Everything you need for AI-powered support
          </motion.h2>
          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <motion.div
                key={title}
                variants={staggerItem}
                className="card card-hover p-6"
              >
                <div className="w-10 h-10 rounded-xl bg-primary-500/15 flex items-center justify-center mb-4">
                  <Icon size={18} className="text-primary-400" />
                </div>
                <h3 className="font-semibold text-white mb-2">{title}</h3>
                <p className="text-sm text-[#8888aa] leading-relaxed">{desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-primary-500/10 py-8 text-center text-[#8888aa] text-sm">
        <p>© 2025 CommerceFlow AI · ShopVerse Platform · Built with LangGraph + FastAPI + React</p>
      </footer>
    </div>
  );
}
