'use client';
import { useState } from 'react';
export function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      const fallback = document.createElement('textarea');
      fallback.value = command;
      fallback.style.position = 'fixed';
      fallback.style.opacity = '0';
      document.body.appendChild(fallback);
      fallback.select();
      document.execCommand('copy');
      fallback.remove();
    }
  }
  return <div className="install-line" aria-label="Installation command"><span>$</span><code>{command}</code><button type="button" onClick={copy}>{copied ? 'COPIED' : 'COPY'}</button></div>;
}
