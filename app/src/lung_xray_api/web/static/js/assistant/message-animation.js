const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function splitIntoChunks(value, maxChunkLength = 72) {
  const paragraphs = String(value || "").split(/\n{2,}/).filter(Boolean);
  const chunks = [];
  paragraphs.forEach((paragraph, paragraphIndex) => {
    const sentences = paragraph.match(/[^.!?…]+[.!?…]?/gu) || [paragraph];
    sentences.forEach((sentence) => {
      const trimmed = sentence.trim();
      if (!trimmed) return;
      if (trimmed.length <= maxChunkLength) {
        chunks.push(trimmed);
        return;
      }
      for (let index = 0; index < trimmed.length; index += maxChunkLength) {
        chunks.push(trimmed.slice(index, index + maxChunkLength));
      }
    });
    if (paragraphIndex < paragraphs.length - 1) chunks.push("\n\n");
  });
  return chunks;
}

export async function revealText(element, value, options = {}) {
  const text = String(value || "");
  const reducedMotion = window.matchMedia?.(REDUCED_MOTION_QUERY).matches;
  if (!text || reducedMotion) {
    element.textContent = text;
    return;
  }

  const chunks = splitIntoChunks(text);
  const totalDuration = Math.min(options.maxDurationMs || 1800, Math.max(320, chunks.length * 65));
  const delay = Math.max(24, Math.floor(totalDuration / Math.max(chunks.length, 1)));
  element.textContent = "";

  for (const chunk of chunks) {
    if (options.signal?.aborted) {
      element.textContent = text;
      return;
    }
    element.textContent += chunk === "\n\n" ? chunk : `${chunk} `;
    await new Promise((resolve) => window.setTimeout(resolve, delay));
  }
  element.textContent = text;
}
