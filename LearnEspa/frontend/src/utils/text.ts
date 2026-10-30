/**
 * 纯文本工具函数（与框架无关，可直接迁移到任何项目）
 * ------------------------------------------------------------
 * 背词拼写由后端判分；这里仅保留前端输入和原文显示工具。
 */

/* ---------- 输入统计 ---------- */

/**
 * 字符数统计（按 Unicode 字形计数，西语单个字符算一个）
 * 替代原型的 input.value.length，避免代理对造成的误差
 */
export function countChars(input: string): number {
  return Array.from(input.trim()).length
}

/**
 * 在指定光标处插入字符，返回新字符串
 * @param source 原字符串
 * @param char   待插入字符
 * @param start  选区起点
 * @param end    选区终点
 */
export function insertAt(source: string, char: string, start: number, end: number): string {
  return source.slice(0, start) + char + source.slice(end)
}

/* ---------- 原文渲染 ---------- */

/**
 * 把原文按重点词切分成片段，供模板渲染
 * @param text       原文（可含换行）
 * @param highlights 需要高亮的重点词
 * @returns [{ text: 'Este ', hit: true }, { text: 'es ', hit: false }, ...]
 */
export function splitSource(
  text: string,
  highlights: string[]
): Array<{ text: string; hit: boolean }> {
  if (!highlights.length) return [{ text, hit: false }]

  // 长词优先，避免 "es" 抢先命中 "este"
  const sorted = [...new Set(highlights)].sort((a, b) => b.length - a.length)
  const escaped = sorted.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  // 前后都必须是「非字母」边界，防止 es 误命中 estudiante / español 的词中片段
  const re = new RegExp(
    `(?<![\\p{L}\\p{N}])(${escaped.join('|')})(?![\\p{L}\\p{N}])`,
    'giu'
  )
  const hitSet = new Set(sorted.map((w) => w.toLowerCase()))

  return text.split(re).filter(Boolean).map((part) => ({
    text: part,
    hit: hitSet.has(part.toLowerCase()),
  }))
}
