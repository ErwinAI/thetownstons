const WINDOW_MS = 60 * 60 * 1000
const MAX_PER_WINDOW = 30
const hits = new Map<string, number[]>()

export function assertKarlRate(userId: string) {
  const now = Date.now()
  const recent = (hits.get(userId) || []).filter((at) => now - at < WINDOW_MS)
  if (recent.length >= MAX_PER_WINDOW) {
    throw createError({ statusCode: 429, statusMessage: 'KarlAI is tired. Try again later.' })
  }
  recent.push(now)
  hits.set(userId, recent)
}
