// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, style = {}, glow = false }) {
  return (
    <div style={{
      background: 'var(--bg1)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: '16px 18px',
      boxShadow: glow ? '0 0 20px rgba(79,156,249,0.08)' : 'none',
      ...style,
    }}>
      {children}
    </div>
  )
}

// ── Stat box ─────────────────────────────────────────────────────────────────
export function StatBox({ label, value, sub, accent = false }) {
  return (
    <div style={{
      background: 'var(--bg1)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: '14px 18px',
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', letterSpacing: 1, textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 22, fontFamily: 'var(--mono)', fontWeight: 600, color: accent ? 'var(--accent)' : 'var(--text)', lineHeight: 1.2 }}>{value ?? '—'}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text2)' }}>{sub}</div>}
    </div>
  )
}

// ── Section heading ───────────────────────────────────────────────────────────
export function SectionHead({ children, action }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      marginBottom: 14, paddingBottom: 10,
      borderBottom: '1px solid var(--border)',
    }}>
      <span style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text2)', letterSpacing: 2, textTransform: 'uppercase', fontWeight: 600 }}>{children}</span>
      {action}
    </div>
  )
}

// ── Btn ───────────────────────────────────────────────────────────────────────
export function Btn({ children, onClick, primary = false, danger = false, small = false, disabled = false, style = {} }) {
  const bg = primary ? 'var(--accent)' : danger ? 'rgba(240,82,82,0.15)' : 'var(--bg2)'
  const col = primary ? '#000' : danger ? 'var(--red)' : 'var(--text)'
  const border = primary ? 'var(--accent)' : danger ? 'var(--red)' : 'var(--border)'
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: small ? '5px 12px' : '7px 16px',
      background: bg, color: col,
      border: `1px solid ${border}`,
      borderRadius: 'var(--radius)', fontSize: small ? 11 : 12, fontWeight: 600,
      fontFamily: 'var(--mono)', letterSpacing: 0.5,
      transition: 'all 0.15s', opacity: disabled ? 0.4 : 1,
      cursor: disabled ? 'not-allowed' : 'pointer', ...style,
    }}>
      {children}
    </button>
  )
}

// ── Badge ─────────────────────────────────────────────────────────────────────
export function Badge({ children, color = 'blue' }) {
  const colors = {
    blue:   { bg: 'rgba(79,156,249,0.12)',  color: 'var(--accent)',  border: 'rgba(79,156,249,0.3)' },
    green:  { bg: 'rgba(61,214,140,0.12)', color: 'var(--green)',   border: 'rgba(61,214,140,0.3)' },
    amber:  { bg: 'rgba(245,166,35,0.12)', color: 'var(--amber)',   border: 'rgba(245,166,35,0.3)' },
    red:    { bg: 'rgba(240,82,82,0.12)',  color: 'var(--red)',     border: 'rgba(240,82,82,0.3)' },
    purple: { bg: 'rgba(155,127,244,0.12)',color: 'var(--purple)',  border: 'rgba(155,127,244,0.3)' },
    gray:   { bg: 'rgba(122,131,153,0.12)',color: 'var(--text2)',   border: 'rgba(122,131,153,0.3)' },
  }
  const c = colors[color] || colors.gray
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 20,
      fontSize: 10, fontFamily: 'var(--mono)', fontWeight: 600, letterSpacing: 0.5,
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
    }}>
      {children}
    </span>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size = 16 }) {
  return (
    <span style={{
      display: 'inline-block', width: size, height: size,
      border: `2px solid var(--border2)`,
      borderTopColor: 'var(--accent)', borderRadius: '50%',
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}

// ── Tag (pipeline node) ───────────────────────────────────────────────────────
export function PipeNode({ icon, label, color }) {
  const colors = {
    indigo: { bg: 'rgba(99,102,241,0.1)',  border: '#4338ca', text: '#818cf8' },
    amber:  { bg: 'rgba(180,83,9,0.12)',   border: '#b45309', text: '#fbbf24' },
    gray:   { bg: 'rgba(100,116,139,0.12)',border: '#64748b', text: '#cbd5e1' },
    gold:   { bg: 'rgba(234,179,8,0.12)',  border: '#ca8a04', text: '#fde047' },
    purple: { bg: 'rgba(168,85,247,0.12)', border: '#7c3aed', text: '#c084fc' },
  }
  const c = colors[color] || colors.gray
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '8px 14px', minWidth: 76, flexShrink: 0,
      background: c.bg, border: `1px solid ${c.border}`, borderRadius: 'var(--radius)',
      color: c.text,
    }}>
      <span style={{ fontSize: 18 }}>{icon}</span>
      <span style={{ fontSize: 9, fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', marginTop: 4 }}>{label}</span>
    </div>
  )
}

// ── Table ─────────────────────────────────────────────────────────────────────
export function Table({ rows, columns }) {
  if (!rows || rows.length === 0) return (
    <div style={{ textAlign: 'center', color: 'var(--text3)', padding: '24px', fontFamily: 'var(--mono)', fontSize: 12 }}>— no data —</div>
  )
  const cols = columns || Object.keys(rows[0])
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: 'var(--mono)' }}>
        <thead>
          <tr>
            {cols.map(c => (
              <th key={c} style={{
                padding: '8px 12px', textAlign: 'left',
                color: 'var(--text3)', fontWeight: 600, fontSize: 10,
                letterSpacing: 1, textTransform: 'uppercase',
                borderBottom: '1px solid var(--border)',
              }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
              {cols.map(c => (
                <td key={c} style={{ padding: '8px 12px', color: 'var(--text)' }}>
                  {r[c] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Error/Info banners ────────────────────────────────────────────────────────
export function Alert({ type = 'info', children }) {
  const styles = {
    info:    { bg: 'rgba(79,156,249,0.08)',  border: 'rgba(79,156,249,0.3)',  color: 'var(--accent2)' },
    warn:    { bg: 'rgba(245,166,35,0.08)', border: 'rgba(245,166,35,0.3)',  color: 'var(--amber)' },
    error:   { bg: 'rgba(240,82,82,0.08)',  border: 'rgba(240,82,82,0.3)',   color: 'var(--red)' },
    success: { bg: 'rgba(61,214,140,0.08)', border: 'rgba(61,214,140,0.3)', color: 'var(--green)' },
  }
  const s = styles[type]
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 'var(--radius)',
      background: s.bg, border: `1px solid ${s.border}`, color: s.color,
      fontSize: 12, fontFamily: 'var(--mono)',
    }}>
      {children}
    </div>
  )
}
