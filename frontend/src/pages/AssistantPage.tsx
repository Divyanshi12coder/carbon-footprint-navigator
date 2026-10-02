import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { clsx } from 'clsx'
import { AnimatePresence, motion } from 'framer-motion'
import { Bot, Loader2, MessageSquarePlus, SendHorizonal, ShieldAlert, ShieldCheck, Trash2, UserRound } from 'lucide-react'
import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { toast } from 'sonner'

import { assistantApi } from '../api/endpoints'
import { images } from '../assets/images'
import { Button } from '../components/ui/Button'
import { EmptyState, ErrorState, Skeleton } from '../components/ui/feedback'
import { Badge, PageHeader } from '../components/ui/misc'
import type { ChatMessage, ConversationDetail } from '../types/api'
import { errorMessage } from '../utils/format'

/** Minimal, safe markdown: **bold**, _italic_ and "- " bullet lists. No HTML injection. */
function RichText({ text }: { text: string }) {
  const inline = (s: string): ReactNode[] =>
    s.split(/(\*\*[^*]+\*\*|_[^_]+_)/g).map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong>
        : part.startsWith('_') && part.endsWith('_') && part.length > 2 ? <em key={i} className="text-muted">{part.slice(1, -1)}</em>
          : <Fragment key={i}>{part}</Fragment>)
  return (
    <div className="space-y-2">
      {text.split(/\n{2,}/).map((block, i) => {
        const lines = block.split('\n')
        if (lines.every((l) => /^\s*[-•]\s/.test(l))) {
          return <ul key={i} className="list-disc space-y-1 pl-5">{lines.map((l, j) => <li key={j}>{inline(l.replace(/^\s*[-•]\s/, ''))}</li>)}</ul>
        }
        return <p key={i}>{lines.map((l, j) => <Fragment key={j}>{j > 0 && <br />}{inline(l)}</Fragment>)}</p>
      })}
    </div>
  )
}

function MessageBubble({ m }: { m: ChatMessage }) {
  const mine = m.role === 'user'
  const [showFacts, setShowFacts] = useState(false)
  return (
    <motion.li initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={clsx('flex gap-3', mine && 'flex-row-reverse')}>
      <div className={clsx('grid h-8 w-8 shrink-0 place-items-center rounded-full', mine ? 'bg-forest text-white' : 'bg-mint text-brand-deep')} aria-hidden>
        {mine ? <UserRound className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className={clsx('max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed', mine ? 'bg-forest text-white' : 'border border-line bg-white text-ink')}>
        <RichText text={m.content} />
        {!mine && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-line pt-2">
            <Badge tone={m.mode === 'llm' ? 'blue' : 'gray'}>{m.mode === 'llm' ? `AI · ${m.model}` : 'Demo mode · deterministic'}</Badge>
            {m.validation.status === 'verified' ? (
              <Badge tone="green"><ShieldCheck className="h-3 w-3" />{m.validation.numbers_checked} figures verified</Badge>
            ) : m.validation.status === 'flagged' ? (
              <Badge tone="amber"><ShieldAlert className="h-3 w-3" />{m.validation.unverified?.length} unverified figure(s)</Badge>
            ) : null}
            {m.context_used.facts && (
              <button type="button" onClick={() => setShowFacts(!showFacts)} aria-expanded={showFacts} className="text-xs font-semibold text-brand hover:underline">
                {showFacts ? 'Hide' : 'Show'} data used
              </button>
            )}
          </div>
        )}
        {showFacts && (
          <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-offwhite p-2 text-[11px] text-ink">{JSON.stringify(m.context_used.facts, null, 2)}</pre>
        )}
      </div>
    </motion.li>
  )
}

export default function AssistantPage() {
  const qc = useQueryClient()
  const status = useQuery({ queryKey: ['assistant-status'], queryFn: assistantApi.status })
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: assistantApi.conversations })
  const [selectedId, setActiveId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const listEnd = useRef<HTMLDivElement>(null)

  // Default to the most recent conversation until the user picks one.
  const activeId = selectedId ?? conversations.data?.[0]?.id ?? null

  const conversation = useQuery({ queryKey: ['conversation', activeId], queryFn: () => assistantApi.get(activeId!), enabled: Boolean(activeId) })

  const create = useMutation({
    mutationFn: assistantApi.create,
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
      setActiveId(c.id)
    },
  })
  const remove = useMutation({
    mutationFn: (id: string) => assistantApi.remove(id),
    onSuccess: () => {
      setActiveId(null)
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
  const ask = useMutation({
    mutationFn: async (question: string) => {
      const id = activeId ?? (await assistantApi.create()).id
      if (!activeId) setActiveId(id)
      return { id, reply: await assistantApi.ask(id, question) }
    },
    onMutate: (question) => {
      // Optimistically show the user's message.
      if (!activeId) return
      qc.setQueryData<ConversationDetail>(['conversation', activeId], (old) => old && {
        ...old,
        messages: [...old.messages, { id: `tmp-${Date.now()}`, role: 'user', content: question, mode: null, model: null, validation: {}, context_used: {}, created_at: new Date().toISOString() }],
      })
    },
    onSuccess: ({ id }) => {
      qc.invalidateQueries({ queryKey: ['conversation', id] })
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
    onError: (e) => {
      toast.error(errorMessage(e))
      qc.invalidateQueries({ queryKey: ['conversation', activeId] })
    },
  })

  useEffect(() => {
    // Block body: scrollIntoView returns a Promise in recent browsers, which must not become the effect cleanup.
    listEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [conversation.data?.messages.length, ask.isPending])

  const submit = (e?: FormEvent, q?: string) => {
    e?.preventDefault()
    const question = (q ?? draft).trim()
    if (question.length < 2 || ask.isPending) return
    setDraft('')
    ask.mutate(question)
  }

  const messages = conversation.data?.messages ?? []

  return (
    <div>
      <PageHeader eyebrow="Sustainability assistant" title="AI Assistant"
        description="Answers are built from your own computed data. The language model explains; it never calculates emissions, and every figure it writes is checked against your data." />
      {status.data && (
        <div className={clsx('mb-5 flex items-start gap-3 rounded-2xl border p-4 text-sm', status.data.mode === 'llm' ? 'border-sky-200 bg-sky-50/60' : 'border-line bg-white')}>
          <Bot className="mt-0.5 h-5 w-5 shrink-0 text-brand" aria-hidden />
          <p><span className="font-semibold">{status.data.mode === 'llm' ? `Live AI mode (${status.data.model})` : 'Demo mode'}</span> — {status.data.description}</p>
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <aside className="card h-fit p-3" aria-label="Conversations">
          <Button className="mb-3 w-full" variant="secondary" size="sm" loading={create.isPending} onClick={() => create.mutate()} icon={<MessageSquarePlus className="h-4 w-4" />}>New conversation</Button>
          {conversations.isLoading ? <Skeleton className="h-24" /> : (
            <ul className="space-y-1">
              {(conversations.data ?? []).map((c) => (
                <li key={c.id} className="group flex items-center gap-1">
                  <button type="button" onClick={() => setActiveId(c.id)} aria-current={c.id === activeId}
                    className={clsx('flex-1 truncate rounded-lg px-3 py-2 text-left text-sm', c.id === activeId ? 'bg-mint font-semibold text-forest' : 'text-ink hover:bg-offwhite')}>
                    {c.title}
                  </button>
                  <button type="button" aria-label={`Delete conversation ${c.title}`} onClick={() => remove.mutate(c.id)} className="rounded-lg p-1.5 text-muted opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-red-600">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="card flex min-h-[560px] flex-col overflow-hidden" aria-label="Chat">
          <div className="flex-1 overflow-y-auto p-4 sm:p-6">
            {conversation.error ? <ErrorState error={conversation.error} onRetry={() => conversation.refetch()} /> : messages.length === 0 && !ask.isPending ? (
              <div className="flex h-full flex-col items-center justify-center">
                <img src={images.earth.src} alt="" aria-hidden className="mb-4 h-24 w-24 rounded-full object-cover shadow-[var(--shadow-lift)]" />
                <EmptyState className="!py-2" icon={<Bot className="h-6 w-6" />} title="Ask about your footprint" body="Try one of these questions:" />
                <div className="mt-2 flex max-w-xl flex-wrap justify-center gap-2">
                  {(status.data?.suggested_questions ?? []).map((q) => (
                    <button key={q} type="button" onClick={() => submit(undefined, q)} className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-medium text-ink transition hover:border-algae-light hover:bg-mint/60">{q}</button>
                  ))}
                </div>
              </div>
            ) : (
              <ul className="space-y-4" aria-live="polite">
                {messages.map((m) => <MessageBubble key={m.id} m={m} />)}
                <AnimatePresence>
                  {ask.isPending && (
                    <motion.li initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-2 text-sm text-muted">
                      <Loader2 className="h-4 w-4 animate-spin text-brand" /> Building context from your data…
                    </motion.li>
                  )}
                </AnimatePresence>
              </ul>
            )}
            <div ref={listEnd} />
          </div>
          <form onSubmit={submit} className="flex gap-2 border-t border-line bg-offwhite p-3">
            <label htmlFor="question" className="sr-only">Your question</label>
            <input id="question" className="input" maxLength={1000} placeholder="e.g. Why did my emissions increase this month?" value={draft} onChange={(e) => setDraft(e.target.value)} />
            <Button type="submit" loading={ask.isPending} disabled={draft.trim().length < 2} icon={<SendHorizonal className="h-4 w-4" />} aria-label="Send">
              <span className="hidden sm:inline">Send</span>
            </Button>
          </form>
        </section>
      </div>
    </div>
  )
}
