// src/components/ui/EmptyState.tsx
// Empty state component with icon, message, and optional CTA

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-20 gap-4 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center">
        <Icon size={28} className="text-primary-400" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-white mb-1">{title}</h3>
        {description && (
          <p className="text-[#8888aa] text-sm max-w-xs">{description}</p>
        )}
      </div>
      {action && (
        action.href ? (
          <Link
            to={action.href}
            className="btn-primary text-sm"
          >
            {action.label}
          </Link>
        ) : (
          <button
            onClick={action.onClick}
            className="btn-primary text-sm"
          >
            {action.label}
          </button>
        )
      )}
    </motion.div>
  );
}
