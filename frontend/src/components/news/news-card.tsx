"use client";

import { motion } from "framer-motion";
import { ExternalLink, Globe } from "lucide-react";
import type { NewsItem } from "@/lib/types";
import { formatRelativeTime } from "@/lib/utils";

export function NewsCard({ item, index = 0 }: { item: NewsItem; index?: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.03 }}
      className="group flex flex-col rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 transition-all duration-200 hover:border-[var(--border-hover)] hover:shadow-[0_4px_24px_var(--accent-glow)]"
    >
      {/* Source line */}
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.08em] text-[var(--accent)]">
        <Globe className="h-3 w-3" />
        <span>{item.source}</span>
        <span className="text-[var(--text-muted)]">·</span>
        <span className="text-[var(--text-muted)]">{item.source_type}</span>
        {item.language && (
          <>
            <span className="text-[var(--text-muted)]">·</span>
            <span className="text-[var(--text-muted)]">{item.language.toUpperCase()}</span>
          </>
        )}
      </div>

      {/* Title */}
      <h3 className="mt-2.5 line-clamp-3 text-[14px] font-semibold leading-snug text-[var(--text-primary)] group-hover:text-white transition-colors">
        {item.title}
      </h3>

      {/* Summary */}
      {item.summary && (
        <p className="mt-2 line-clamp-2 text-[12px] leading-relaxed text-[var(--text-muted)]">
          {item.summary}
        </p>
      )}

      {/* Footer */}
      <div className="mt-auto flex items-center justify-between pt-4 border-t border-[var(--border-subtle)]">
        <span className="text-[11px] font-medium text-[var(--text-muted)]">
          {formatRelativeTime(item.published_at)}
        </span>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-[var(--accent)] transition-colors hover:text-[var(--accent-hover)]"
          >
            Leer
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
    </motion.article>
  );
}
