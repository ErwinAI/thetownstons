import { runFitOgBackfill } from '../../utils/fit-og'

function assertCron(event: Parameters<typeof getHeader>[0]) {
  const secret = String(process.env.CRON_SECRET || '')
  if (import.meta.dev && !secret) return
  const auth = getHeader(event, 'authorization') || ''
  if (!secret || auth !== `Bearer ${secret}`) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }
}

export default defineEventHandler(async (event) => {
  assertCron(event)
  const query = getQuery(event)
  const batch = Number(query.batch || 12)
  const budgetMs = Number(query.budgetMs || 50_000)
  return await runFitOgBackfill({
    batch: Number.isFinite(batch) ? Math.min(Math.max(batch, 1), 40) : 12,
    budgetMs: Number.isFinite(budgetMs) ? Math.min(Math.max(budgetMs, 5000), 120_000) : 50_000,
  })
})
