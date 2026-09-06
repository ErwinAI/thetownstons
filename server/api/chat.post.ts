import {
  convertToModelMessages,
  createGateway,
  createUIMessageStreamResponse,
  isStepCount,
  streamText,
  tool,
  toUIMessageStream,
  type UIMessage,
  type UIMessageChunk,
} from 'ai'
import { z } from 'zod'
import { assertEmailConfirmed } from '../utils/access'
import { KARL_INSTRUCTIONS, KARL_LIMITS, loadKarlPages, pageBlock, type KarlHit, type KarlPageRef } from '../utils/karl'
import { assertKarlRate } from '../utils/karl-rate'
import { matchChunks, retrieveWiki } from '../utils/rag'
import { userFromRequest } from '../utils/supabase'

function textOnlyMessages(messages: UIMessage[]): UIMessage[] {
  return messages
    .slice(-KARL_LIMITS.historyMessages)
    .map((message) => ({
      ...message,
      parts: (message.parts || []).filter((part) => part.type === 'text' && 'text' in part && String(part.text || '').trim()),
    }))
    .filter((message) => message.parts.length)
}

function redactChunkStream(stream: ReadableStream<UIMessageChunk>): ReadableStream<UIMessageChunk> {
  return stream.pipeThrough(new TransformStream<UIMessageChunk, UIMessageChunk>({
    transform(chunk, controller) {
      if (chunk.type === 'tool-output-available') {
        controller.enqueue({ ...chunk, output: { ok: true } })
        return
      }
      if (chunk.type === 'tool-input-delta') return
      controller.enqueue(chunk)
    },
  }))
}

export default defineEventHandler(async (event) => {
    const apiKey = String(
      useRuntimeConfig().aiGatewayApiKey
      || process.env.AI_GATEWAY_API_KEY
      || process.env.NUXT_AI_GATEWAY_API_KEY
      || '',
    )
    if (!apiKey) {
      throw createError({ statusCode: 503, statusMessage: 'Karl is not configured' })
    }
    const gateway = createGateway({ apiKey })

    const user = await userFromRequest(event)
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Log in to ask Karl' })
    }
    assertEmailConfirmed(user)
    assertKarlRate(user.id)

    const body = await readBody<{
      messages?: UIMessage[]
      page?: KarlPageRef
      mentions?: KarlPageRef[]
    }>(event)
    const incoming = Array.isArray(body?.messages) ? textOnlyMessages(body.messages) : []
    if (!incoming.length) {
      throw createError({ statusCode: 400, statusMessage: 'Ask something first' })
    }

    const last = incoming[incoming.length - 1]
    const lastText = last.parts
      .filter((part) => part.type === 'text')
      .map((part) => ('text' in part ? String(part.text) : ''))
      .join(' ')
      .trim()
    if (lastText.length > 1500) {
      throw createError({ statusCode: 400, statusMessage: 'That question is too long' })
    }

    const pages = await loadKarlPages(body?.page, body?.mentions)
    const extra = pageBlock(pages)
    const instructions = extra
      ? `${KARL_INSTRUCTIONS}\n\nThe Dungeon Runner has these wiki pages open. Use them. Still search if you need more.\n\n${extra}`
      : KARL_INSTRUCTIONS

    const embeds = new Map<string, Promise<KarlHit[]>>()
    function search(source: 'wiki' | 'game', query: string) {
      const key = `${source}:${query}`
      const pending = embeds.get(key)
      if (pending) return pending
      const next = source === 'wiki' ? retrieveWiki(query) : matchChunks(query, 'game')
      embeds.set(key, next)
      return next
    }

    const result = streamText({
      model: gateway('openai/gpt-5.6-luna'),
      instructions,
      messages: await convertToModelMessages(incoming),
      stopWhen: isStepCount(4),
      prepareStep: ({ stepNumber }) => ({
        toolChoice: stepNumber === 0 ? 'required' : stepNumber >= 2 ? 'none' : 'auto',
      }),
      tools: {
        searchArticles: tool({
          description: 'Search Townstons wiki articles. Use for write-ups, guides, quests, and item pages. For dual stats or name words, search Name Descriptors. For best in slot, search the slot and class.',
          inputSchema: z.object({
            query: z.string().min(2).max(200).describe('Item, quest, place, or mechanic name'),
          }),
          execute: async ({ query }) => {
            try {
              return { hits: await search('wiki', query) }
            }
            catch (err) {
              console.warn('Karl searchArticles failed', err)
              return { hits: [] }
            }
          },
        }),
        searchGame: tool({
          description: 'Search in-game item and quest facts. Use for numbers a wiki page may skip.',
          inputSchema: z.object({
            query: z.string().min(2).max(200).describe('In-game name as a player would say it'),
          }),
          execute: async ({ query }) => {
            try {
              return { hits: await search('game', query) }
            }
            catch (err) {
              console.warn('Karl searchGame failed', err)
              return { hits: [] }
            }
          },
        }),
      },
    })

  return createUIMessageStreamResponse({
    stream: redactChunkStream(toUIMessageStream({
      stream: result.stream,
      sendReasoning: false,
      sendSources: false,
    })),
  })
})
