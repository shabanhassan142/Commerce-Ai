// src/components/ui/Pagination.tsx
// Pagination controls component

import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "../../utils/cn";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  perPage: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pages, total, perPage, onPageChange }: PaginationProps) {
  if (pages <= 1) return null;

  const from = (page - 1) * perPage + 1;
  const to = Math.min(page * perPage, total);

  const getPages = () => {
    const nums: (number | "...")[] = [];
    if (pages <= 7) {
      for (let i = 1; i <= pages; i++) nums.push(i);
    } else {
      nums.push(1);
      if (page > 3) nums.push("...");
      for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) {
        nums.push(i);
      }
      if (page < pages - 2) nums.push("...");
      nums.push(pages);
    }
    return nums;
  };

  return (
    <div className="flex items-center justify-between mt-6">
      <p className="text-xs text-[#8888aa]">
        Showing {from}–{to} of {total}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed text-[#8888aa] hover:text-white transition-colors"
          aria-label="Previous page"
        >
          <ChevronLeft size={16} />
        </button>
        {getPages().map((p, i) =>
          p === "..." ? (
            <span key={`dots-${i}`} className="px-2 text-[#8888aa]">…</span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p as number)}
              className={cn(
                "w-8 h-8 rounded-lg text-sm font-medium transition-colors",
                p === page
                  ? "bg-primary-600 text-white"
                  : "text-[#8888aa] hover:bg-white/5 hover:text-white"
              )}
            >
              {p}
            </button>
          )
        )}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === pages}
          className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed text-[#8888aa] hover:text-white transition-colors"
          aria-label="Next page"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
