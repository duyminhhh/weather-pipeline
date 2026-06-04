import { Card, SectionHead, Badge } from '../components/UI'

const LAYERS = [
  {
    id: 'bronze',
    icon: '🟤',
    label: 'Bronze',
    subtitle: 'Raw Ingestion Layer',
    color: { bg: 'rgba(180,83,9,0.10)', border: '#b45309', text: '#fbbf24', badgeColor: 'amber' },
    notebook: '01_bronze_ingest',
    storage: 'Delta Table — weather_bronze.raw_weather',
    description:
      'Lưu trữ dữ liệu thô nguyên bản từ API thời tiết, không qua xử lý. ' +
      'Mọi bản ghi đều được giữ nguyên để có thể truy xuất lại bất cứ lúc nào.',
    input: { icon: '🕷️', label: 'Crawler output (JSON)', detail: 'JSON thô từ OpenWeatherMap API' },
    output: { icon: '📦', label: 'Delta Table (append-only)', detail: 'Schema cố định, ghi thêm (append)' },
    fields: [
      { name: 'city', type: 'STRING', note: 'Tên thành phố' },
      { name: 'country', type: 'STRING', note: 'Mã quốc gia' },
      { name: 'temperature_c', type: 'DOUBLE', note: 'Nhiệt độ thô (°C)' },
      { name: 'humidity', type: 'INT', note: 'Độ ẩm (%)' },
      { name: 'wind_speed_kmh', type: 'DOUBLE', note: 'Tốc độ gió (km/h)' },
      { name: 'weather_desc', type: 'STRING', note: 'Mô tả thời tiết' },
      { name: 'ingested_at', type: 'TIMESTAMP', note: 'Thời điểm ingest' },
      { name: 'raw_json', type: 'STRING', note: 'Toàn bộ JSON gốc' },
    ],
    transforms: [],
    quality: [
      { label: 'Kiểm tra', ok: false, text: 'Không validate' },
      { label: 'Dedup', ok: false, text: 'Không loại bỏ trùng' },
      { label: 'Lưu trữ', ok: true,  text: 'Giữ toàn bộ lịch sử' },
    ],
  },
  {
    id: 'silver',
    icon: '🥈',
    label: 'Silver',
    subtitle: 'Cleansed & Validated Layer',
    color: { bg: 'rgba(100,116,139,0.10)', border: '#64748b', text: '#cbd5e1', badgeColor: 'gray' },
    notebook: '02_silver_transform',
    storage: 'Delta Table — weather_silver.clean_weather',
    description:
      'Dữ liệu được làm sạch, chuẩn hoá kiểu dữ liệu, loại bỏ bản ghi lỗi và trùng lặp. ' +
      'Đây là nguồn dữ liệu tin cậy cho các bước phân tích phía sau.',
    input: { icon: '🟤', label: 'Bronze Delta Table', detail: 'Đọc từ weather_bronze.raw_weather' },
    output: { icon: '✅', label: 'Validated Delta Table', detail: 'Schema mở rộng + derived fields' },
    fields: [
      { name: 'city', type: 'STRING', note: 'Đã chuẩn hoá chữ hoa/thường' },
      { name: 'temperature_c', type: 'DOUBLE', note: 'Đã kiểm tra range [-60, 60]' },
      { name: 'feels_like_c', type: 'DOUBLE', note: 'Derived từ temp + humidity' },
      { name: 'temp_min_c', type: 'DOUBLE', note: 'Nhiệt độ thấp nhất trong ngày' },
      { name: 'temp_max_c', type: 'DOUBLE', note: 'Nhiệt độ cao nhất trong ngày' },
      { name: 'humidity', type: 'INT', note: 'Đã kiểm tra range [0, 100]' },
      { name: 'cloud_cover_pct', type: 'INT', note: 'Độ mây che phủ (%)' },
      { name: 'is_valid', type: 'BOOLEAN', note: 'Flag bản ghi hợp lệ' },
      { name: 'processed_at', type: 'TIMESTAMP', note: 'Thời điểm xử lý silver' },
    ],
    transforms: [
      '✦ Cast kiểu dữ liệu (string → double/int/timestamp)',
      '✦ Loại bỏ bản ghi NULL ở các cột quan trọng',
      '✦ Deduplication theo (city, ingested_at)',
      '✦ Tính derived fields: feels_like_c, cloud_cover_pct',
      '✦ Gắn cờ is_valid cho anomaly detection',
    ],
    quality: [
      { label: 'Null check', ok: true,  text: 'Drop NULL rows' },
      { label: 'Range check', ok: true, text: 'Temp [-60,60], Humidity [0,100]' },
      { label: 'Dedup', ok: true,       text: 'Theo city + timestamp' },
    ],
  },
  {
    id: 'gold',
    icon: '🥇',
    label: 'Gold',
    subtitle: 'Aggregated Business Layer',
    color: { bg: 'rgba(234,179,8,0.10)', border: '#ca8a04', text: '#fde047', badgeColor: 'amber' },
    notebook: '03_gold_aggregate',
    storage: 'Delta Tables — weather_gold.*',
    description:
      'Dữ liệu được tổng hợp theo ngày và thành phố, sẵn sàng phục vụ dashboard, ' +
      'báo cáo BI và đào tạo mô hình ML. Đây là lớp cuối cùng hướng tới end-user.',
    input: { icon: '🥈', label: 'Silver Delta Table', detail: 'Đọc từ weather_silver.clean_weather' },
    output: { icon: '📊', label: 'Aggregated Delta Tables', detail: 'gold_daily_city + gold_latest + gold_ml_features' },
    fields: [
      { name: 'date', type: 'DATE', note: 'Ngày (nhóm theo ngày)' },
      { name: 'city', type: 'STRING', note: 'Tên thành phố' },
      { name: 'avg_temp_c', type: 'DOUBLE', note: 'Nhiệt độ trung bình ngày' },
      { name: 'temp_max_c', type: 'DOUBLE', note: 'Nhiệt độ cao nhất ngày' },
      { name: 'temp_min_c', type: 'DOUBLE', note: 'Nhiệt độ thấp nhất ngày' },
      { name: 'avg_humidity', type: 'DOUBLE', note: 'Độ ẩm trung bình' },
      { name: 'avg_wind_speed_kmh', type: 'DOUBLE', note: 'Gió trung bình' },
      { name: 'avg_precipitation_mm', type: 'DOUBLE', note: 'Lượng mưa trung bình' },
      { name: 'record_count', type: 'INT', note: 'Số bản ghi silver đã gộp' },
    ],
    transforms: [
      '✦ GROUP BY date, city → tính các chỉ số avg/min/max',
      '✦ Window function: tính rolling_avg_7d',
      '✦ Feature engineering cho ML: lag_1d, lag_3d, temp_delta',
      '✦ Tạo bảng gold_latest (snapshot mới nhất mỗi thành phố)',
      '✦ Tạo bảng gold_ml_features cho pipeline ML',
    ],
    quality: [
      { label: 'Completeness', ok: true, text: 'Kiểm tra record_count > 0' },
      { label: 'Freshness', ok: true,    text: 'Assert max(date) = today' },
      { label: 'Accuracy', ok: true,     text: 'avg_temp trong [silver_min, silver_max]' },
    ],
  },
]

function FieldTable({ fields }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: 'var(--mono)' }}>
      <thead>
        <tr>
          {['Column', 'Type', 'Mô tả'].map(h => (
            <th key={h} style={{
              padding: '6px 10px', textAlign: 'left',
              color: 'var(--text3)', fontSize: 10, fontWeight: 700,
              letterSpacing: 1, textTransform: 'uppercase',
              borderBottom: '1px solid var(--border)',
            }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {fields.map(f => (
          <tr key={f.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
            <td style={{ padding: '6px 10px', color: 'var(--accent)', fontWeight: 600 }}>{f.name}</td>
            <td style={{ padding: '6px 10px', color: '#3dd68c' }}>{f.type}</td>
            <td style={{ padding: '6px 10px', color: 'var(--text2)' }}>{f.note}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function QualityBadge({ label, ok, text }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '5px 10px', borderRadius: 'var(--radius)',
      background: ok ? 'rgba(61,214,140,0.07)' : 'rgba(240,82,82,0.07)',
      border: `1px solid ${ok ? 'rgba(61,214,140,0.25)' : 'rgba(240,82,82,0.25)'}`,
    }}>
      <span style={{ fontSize: 13 }}>{ok ? '✓' : '✗'}</span>
      <div>
        <div style={{ fontSize: 10, fontWeight: 700, color: ok ? '#3dd68c' : '#f05252', letterSpacing: 0.5 }}>{label}</div>
        <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 1 }}>{text}</div>
      </div>
    </div>
  )
}

function IoArrow({ from, to }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
      <div style={{
        flex: 1, padding: '8px 12px', borderRadius: 'var(--radius)',
        background: 'var(--bg2)', border: '1px solid var(--border)',
        fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text2)',
      }}>
        <span style={{ fontSize: 16, marginRight: 6 }}>{from.icon}</span>
        <span style={{ color: 'var(--text3)', marginRight: 4 }}>INPUT:</span>
        <span style={{ fontWeight: 600 }}>{from.label}</span>
        <div style={{ marginTop: 3, color: 'var(--text3)', fontSize: 10, paddingLeft: 24 }}>{from.detail}</div>
      </div>
      <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)', fontSize: 18 }}>→</span>
      <div style={{
        flex: 1, padding: '8px 12px', borderRadius: 'var(--radius)',
        background: 'var(--bg2)', border: '1px solid var(--border)',
        fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text2)',
      }}>
        <span style={{ fontSize: 16, marginRight: 6 }}>{to.icon}</span>
        <span style={{ color: 'var(--text3)', marginRight: 4 }}>OUTPUT:</span>
        <span style={{ fontWeight: 600 }}>{to.label}</span>
        <div style={{ marginTop: 3, color: 'var(--text3)', fontSize: 10, paddingLeft: 24 }}>{to.detail}</div>
      </div>
    </div>
  )
}

export default function DataLayersTab() {
  return (
    <div>
      {/* Header overview */}
      <div style={{
        background: 'var(--bg1)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)', padding: '16px 20px', marginBottom: 24,
      }}>
        <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 2, marginBottom: 10 }}>
          Medallion Architecture — Data Flow
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {LAYERS.map((layer, i) => (
            <div key={layer.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 18px', borderRadius: 'var(--radius)',
                background: layer.color.bg, border: `1px solid ${layer.color.border}`,
              }}>
                <span style={{ fontSize: 20 }}>{layer.icon}</span>
                <div>
                  <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 12, color: layer.color.text, letterSpacing: 1 }}>{layer.label}</div>
                  <div style={{ fontSize: 10, color: 'var(--text3)' }}>{layer.subtitle}</div>
                </div>
              </div>
              {i < LAYERS.length - 1 && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                  <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)', fontSize: 20 }}>→</span>
                  <span style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>transform</span>
                </div>
              )}
            </div>
          ))}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)', fontSize: 20 }}>→</span>
              <span style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>train</span>
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '10px 18px', borderRadius: 'var(--radius)',
              background: 'rgba(168,85,247,0.10)', border: '1px solid #7c3aed',
            }}>
              <span style={{ fontSize: 20 }}>🤖</span>
              <div>
                <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 12, color: '#c084fc', letterSpacing: 1 }}>ML</div>
                <div style={{ fontSize: 10, color: 'var(--text3)' }}>Forecasting Model</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Layer cards */}
      {LAYERS.map(layer => (
        <div key={layer.id} style={{ marginBottom: 28 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14,
            paddingBottom: 10, borderBottom: '1px solid var(--border)',
          }}>
            <span style={{ fontSize: 24 }}>{layer.icon}</span>
            <div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 14, fontWeight: 700, color: layer.color.text }}>
                {layer.label} Layer
              </div>
              <div style={{ fontSize: 11, color: 'var(--text2)' }}>{layer.subtitle}</div>
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
              <Badge color="gray">Notebook: {layer.notebook}</Badge>
              <Badge color={layer.color.badgeColor}>{layer.storage}</Badge>
            </div>
          </div>

          <p style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.7, marginBottom: 16, marginTop: 0 }}>
            {layer.description}
          </p>

          <IoArrow from={layer.input} to={layer.output} />

          <div style={{ display: 'grid', gridTemplateColumns: layer.transforms.length ? '1fr 1fr' : '1fr', gap: 16 }}>
            {/* Schema */}
            <Card>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
                Schema Fields
              </div>
              <FieldTable fields={layer.fields} />
            </Card>

            {/* Transforms + Quality */}
            {layer.transforms.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <Card>
                  <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
                    Transformations
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {layer.transforms.map((t, i) => (
                      <div key={i} style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text2)', lineHeight: 1.5 }}>{t}</div>
                    ))}
                  </div>
                </Card>
                <Card>
                  <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
                    Data Quality Checks
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {layer.quality.map((q, i) => <QualityBadge key={i} {...q} />)}
                  </div>
                </Card>
              </div>
            )}

            {/* Bronze only: quality in same column */}
            {layer.transforms.length === 0 && (
              <Card style={{ display: 'none' }} />
            )}
          </div>

          {layer.transforms.length === 0 && (
            <Card style={{ marginTop: 16 }}>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
                Data Quality Policy
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {layer.quality.map((q, i) => <QualityBadge key={i} {...q} />)}
              </div>
            </Card>
          )}
        </div>
      ))}
    </div>
  )
}
