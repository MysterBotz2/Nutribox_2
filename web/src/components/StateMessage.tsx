export function StateMessage({ kind = 'info', children }: { kind?: 'info' | 'error' | 'success'; children: React.ReactNode }) {
  return <p className={`state-message ${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</p>
}
