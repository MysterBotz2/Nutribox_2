import { useEffect, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { chatApi } from '../api/chat'
import { queryKeys } from '../api/query-keys'

export function FloatingAiChat() {
  const queryClient = useQueryClient(); const [open, setOpen] = useState(false); const [conversationId, setConversationId] = useState<number | null>(null); const [draft, setDraft] = useState('')
  const launcher = useRef<HTMLButtonElement>(null); const composer = useRef<HTMLTextAreaElement>(null)
  const conversation = useQuery({ queryKey: queryKeys.conversation(conversationId ?? 0), queryFn: () => chatApi.get(conversationId as number), enabled: open && conversationId !== null, retry: false })
  const send = useMutation({ mutationFn: () => chatApi.send({ message: draft.trim(), conversation_id: conversationId }), onSuccess: (reply) => { setDraft(''); setConversationId(reply.conversation_id); queryClient.invalidateQueries({ queryKey: queryKeys.conversation(reply.conversation_id) }); queryClient.invalidateQueries({ queryKey: queryKeys.conversations }) } })
  useEffect(() => { if (open) composer.current?.focus() }, [open])
  useEffect(() => { const close = (event: KeyboardEvent | globalThis.KeyboardEvent) => { if (event.key === 'Escape') setOpen(false) }; window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close) }, [])
  useEffect(() => { if (!open) launcher.current?.focus() }, [open])
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!send.isPending && draft.trim()) send.mutate() }
  function keydown(event: KeyboardEvent<HTMLTextAreaElement>) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); if (!send.isPending && draft.trim()) send.mutate() } }
  const messages = conversation.data?.messages ?? []
  return <div className="floating-ai"><button ref={launcher} type="button" className="ai-launcher" aria-label="Open NutriBox AI assistant" title="NutriBox AI" onClick={() => setOpen(true)} aria-expanded={open}>✦</button>{open && <section className="ai-panel" role="dialog" aria-modal="true" aria-label="NutriBox AI assistant"><header><div><strong>NutriBox AI</strong><span>Nutrition Assistant</span></div><button type="button" className="ai-close" aria-label="Close NutriBox AI assistant" onClick={() => setOpen(false)}>×</button></header><div className="ai-panel-messages">{conversation.isPending ? <p className="muted">Loading conversation…</p> : messages.length === 0 ? <p className="ai-empty">Ask NutriBox a nutrition question.</p> : messages.map((message) => <article className={`floating-message ${message.role === 'assistant' ? 'assistant' : 'user'}`} key={message.id}><strong>{message.role === 'assistant' ? 'NutriBox AI' : 'You'}</strong><p>{message.content}</p></article>)}{send.isPending && <div className="thinking" aria-live="polite"><strong>NutriBox AI</strong><span>Thinking <i>●</i><i>●</i><i>●</i></span></div>}{send.isError && <p className="floating-error">{send.error instanceof ApiError ? send.error.detail : 'Unable to send your message. Please retry.'}</p>}</div><form onSubmit={submit} className="floating-composer"><textarea ref={composer} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={keydown} maxLength={1000} placeholder="Ask NutriBox…" aria-label="Message NutriBox AI" /><button type="submit" disabled={!draft.trim() || send.isPending}>{send.isPending ? '…' : 'Send'}</button></form></section>}</div>
}
