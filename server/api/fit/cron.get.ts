import { runFitCrawl } from '../../utils/fit-store'

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
  const batch = Number(query.batch || useRuntimeConfig().fitCronBatch || 20)
  const budgetMs = Number(query.budgetMs || 48_000)
  return await runFitCrawl({
    batch: Number.isFinite(batch) ? Math.min(Math.max(batch, 1), 80) : 20,
    budgetMs: Number.isFinite(budgetMs) ? Math.min(Math.max(budgetMs, 5000), 55_000) : 48_000,
  })
})
