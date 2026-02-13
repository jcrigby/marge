import { useEffect, useState } from 'react';

interface HistoryEntry {
  state: string;
  last_changed: string;
}

interface SparklineProps {
  entityId: string;
  width?: number;
  height?: number;
  color?: string;
}

export default function Sparkline({
  entityId,
  width = 180,
  height = 40,
  color = '#6c8cff',
}: SparklineProps) {
  const [points, setPoints] = useState<{ x: number; y: number }[]>([]);

  useEffect(() => {
    const now = new Date();
    const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const url = `/api/history/period/${encodeURIComponent(entityId)}?start=${start.toISOString()}&end=${now.toISOString()}`;

    fetch(url)
      .then((r) => r.json())
      .then((entries: HistoryEntry[]) => {
        // Filter to numeric states only
        const numeric = entries
          .map((e) => ({
            time: new Date(e.last_changed).getTime(),
            value: parseFloat(e.state),
          }))
          .filter((e) => !isNaN(e.value));

        if (numeric.length < 2) {
          setPoints([]);
          return;
        }

        const startTime = numeric[0].time;
        const endTime = numeric[numeric.length - 1].time;
        const timeRange = endTime - startTime || 1;
        const minVal = Math.min(...numeric.map((n) => n.value));
        const maxVal = Math.max(...numeric.map((n) => n.value));
        const valRange = maxVal - minVal || 1;

        const pad = 2;
        const plotW = width - pad * 2;
        const plotH = height - pad * 2;

        const pts = numeric.map((n) => ({
          x: pad + ((n.time - startTime) / timeRange) * plotW,
          y: pad + plotH - ((n.value - minVal) / valRange) * plotH,
        }));

        setPoints(pts);
      })
      .catch(() => setPoints([]));
  }, [entityId, width, height]);

  if (points.length < 2) return null;

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(' ');

  // Fill area under the line
  const fillD = `${pathD} L${points[points.length - 1].x.toFixed(1)},${height} L${points[0].x.toFixed(1)},${height} Z`;

  return (
    <svg
      className="sparkline"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
    >
      <path d={fillD} fill={color} opacity={0.1} />
      <path d={pathD} fill="none" stroke={color} strokeWidth={1.5} />
      <circle
        cx={points[points.length - 1].x}
        cy={points[points.length - 1].y}
        r={2.5}
        fill={color}
      />
    </svg>
  );
}
