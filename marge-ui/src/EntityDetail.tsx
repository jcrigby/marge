import { useEffect, useState } from 'react';
import type { EntityState } from './types';

interface Props {
  entity: EntityState;
  onClose: () => void;
}

interface HistoryEntry {
  state: string;
  last_changed: string;
  attributes: Record<string, unknown>;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function EntityDetail({ entity, onClose }: Props) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    const now = new Date();
    const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const url = `/api/history/period/${encodeURIComponent(entity.entity_id)}?start=${start.toISOString()}&end=${now.toISOString()}`;
    fetch(url)
      .then((r) => r.json())
      .then((data: HistoryEntry[]) => setHistory(data.slice(-50))) // last 50 entries
      .catch(() => setHistory([]));
  }, [entity.entity_id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const attrs = Object.entries(entity.attributes);

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="detail-header">
          <h3>{entity.entity_id}</h3>
          <button className="detail-close" onClick={onClose}>X</button>
        </div>

        <div className="detail-state">
          <span className="detail-state-value">{entity.state}</span>
          <span className="detail-state-time">
            Changed {formatTime(entity.last_changed)}
          </span>
        </div>

        {attrs.length > 0 && (
          <div className="detail-section">
            <h4>Attributes</h4>
            <table className="detail-attrs">
              <tbody>
                {attrs.map(([key, val]) => (
                  <tr key={key}>
                    <td className="attr-key">{key}</td>
                    <td className="attr-val">
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {history.length > 0 && (
          <div className="detail-section">
            <h4>History (24h)</h4>
            <div className="detail-history">
              {history.map((entry, i) => (
                <div key={i} className="history-row">
                  <span className="history-state">{entry.state}</span>
                  <span className="history-time">{formatTime(entry.last_changed)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
