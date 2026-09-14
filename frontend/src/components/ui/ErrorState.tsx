// src/components/ui/ErrorState.tsx
// Error state component with retry button

import { motion } from "framer-motion";
import { AlertTriangle, RefreshCw, WifiOff } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  type?: "generic" | "network" | "notfound" | "forbidden";
}

const ERROR_CONFIG = {
  generic:   { icon: AlertTriangle, title: "Something went wrong",   color: "text-red-400",    bg: "bg-red-500/10 border-red-500/20" },
  network:   { icon: WifiOff,       title: "Connection failed",      color: "text-amber-400",  bg: "bg-amber-500/10 border-amber-500/20" },
  notfound:  { icon: AlertTriangle, title: "Not found",              color: "text-[#8888aa]",  bg: "bg-white/5 border-white/10" },
  forbidden: { icon: AlertTriangle, title: "Access denied",          color: "text-red-400",    bg: "bg-red-500/10 border-red-500/20" },
};

export function ErrorState({
  title,
  message = "We couldn't load this content.",
  onRetry,
  type = "generic",
}: ErrorStateProps) {
  const cfg = ERROR_CONFIG[type];
  const Icon = cfg.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-20 gap-4 text-center"
    >
      <div className={`w-14 h-14 rounded-2xl border flex items-center justify-center ${cfg.bg}`}>
        <Icon size={24} className={cfg.color} />
      </div>
      <div>
        <h3 className="text-base font-semibold text-white mb-1">
          {title ?? cfg.title}
        </h3>
        <p className="text-[#8888aa] text-sm max-w-xs">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-sm text-white transition-colors border border-white/10"
        >
          <RefreshCw size={14} />
          Try Again
        </button>
      )}
    </motion.div>
  );
}
