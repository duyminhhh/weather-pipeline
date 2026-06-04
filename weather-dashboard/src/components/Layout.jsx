const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard',    icon: '▦' },
  { id: 'live',      label: 'Live Weather', icon: '◎' },
  { id: 'ml',        label: 'ML Insights',  icon: '⬡' },
  { id: 'pipeline',  label: 'Pipeline',     icon: '⇢' },
  { id: 'workflows', label: 'Workflows',    icon: '≡' },
]

export default function Layout({ tab, setTab, children }) {
  const now = new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px', height: 52,
        background: 'var(--bg1)', borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 16, color: 'var(--accent)', letterSpacing: 3, fontWeight: 600 }}>WX</span>
          <span style={{ color: 'var(--border2)', fontSize: 14 }}>/</span>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text2)', letterSpacing: 2 }}>WEATHER PIPELINE</span>
        </div>

        <nav style={{ display: 'flex', gap: 2 }}>
          {NAV_ITEMS.map(n => (
            <button key={n.id} onClick={() => setTab(n.id)} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 'var(--radius)',
              border: 'none', fontSize: 12, fontWeight: 500,
              background: tab === n.id ? 'rgba(79,156,249,0.1)' : 'transparent',
              color: tab === n.id ? 'var(--accent)' : 'var(--text2)',
              borderBottom: tab === n.id ? '2px solid var(--accent)' : '2px solid transparent',
              transition: 'all 0.15s', cursor: 'pointer',
            }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{n.icon}</span>
              {n.label}
            </button>
          ))}
        </nav>

        <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text3)' }}>{now}</div>
      </header>

      <main style={{ flex: 1, padding: '20px 24px', maxWidth: 1400, width: '100%', margin: '0 auto' }}>
        {children}
      </main>
    </div>
  )
}
