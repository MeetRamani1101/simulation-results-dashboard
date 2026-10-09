import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const SERIES_COLORS = ["#2456c9", "#d9730d", "#1a7f4e", "#8b3fe8", "#c9254a", "#117a86"];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #dde2e8",
        borderRadius: 6,
        padding: "8px 10px",
        fontSize: 12,
        boxShadow: "0 2px 8px rgba(16,24,40,0.12)",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label} Hz</div>
      {payload.map((p) => (
        <div key={p.dataKey + p.name} style={{ color: p.color }}>
          {p.name}: {p.value?.toFixed ? p.value.toFixed(2) : p.value} mm
        </div>
      ))}
    </div>
  );
}

/**
 * Overlays one or more revisions' frequency-response curves. Each revision
 * may have its own (sparse, irregular) frequency samples, so each is given
 * to recharts as an independent <Line data=...> series sharing a numeric
 * frequency x-axis, rather than being pre-merged into one dense table.
 */
export default function FrequencyChart({
  revisions,
  limitMm,
  freqMin,
  freqMax,
  height = 360,
  showPeakMarkers = true,
}) {
  const allFreqs = revisions.flatMap((r) => r.samples.map((s) => s.frequency_hz));
  const maxFreq = allFreqs.length ? Math.max(...allFreqs) : freqMax;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart margin={{ top: 10, right: 24, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
        <XAxis
          dataKey="frequency_hz"
          type="number"
          domain={[0, Math.max(maxFreq, freqMax)]}
          label={{ value: "Frequency [Hz]", position: "insideBottom", offset: -4, fontSize: 12 }}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          label={{ value: "Magnitude [mm]", angle: -90, position: "insideLeft", fontSize: 12 }}
          tick={{ fontSize: 11 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: 12 }} />

        <ReferenceArea
          x1={freqMin}
          x2={freqMax}
          fill="#2456c9"
          fillOpacity={0.045}
          ifOverflow="extendDomain"
        />
        <ReferenceLine
          y={limitMm}
          stroke="#b3261e"
          strokeDasharray="6 4"
          label={{
            value: `${limitMm} mm limit (${freqMin}-${freqMax} Hz)`,
            position: "right",
            fill: "#b3261e",
            fontSize: 11,
          }}
        />

        {revisions.map((revision, idx) => {
          const color = SERIES_COLORS[idx % SERIES_COLORS.length];
          return (
            <Line
              key={revision.revisionId ?? revision.label}
              data={revision.samples}
              dataKey="magnitude_mm"
              name={revision.label}
              stroke={color}
              strokeWidth={2}
              dot={{ r: 2 }}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
              connectNulls
            />
          );
        })}

        {showPeakMarkers &&
          revisions.map((revision, idx) => {
            const { assessment } = revision;
            if (
              assessment.assessed_peak_frequency === null ||
              assessment.assessed_peak_frequency === undefined
            ) {
              return null;
            }
            const color = SERIES_COLORS[idx % SERIES_COLORS.length];
            return (
              <ReferenceDot
                key={`peak-${revision.revisionId ?? revision.label}`}
                x={assessment.assessed_peak_frequency}
                y={assessment.assessed_max_magnitude}
                r={5}
                fill={assessment.passes_limit ? "#1a7f4e" : "#b3261e"}
                stroke={color}
                strokeWidth={2}
                label={{
                  value: `${assessment.assessed_max_magnitude?.toFixed(1)} mm`,
                  position: "top",
                  fontSize: 11,
                  fill: assessment.passes_limit ? "#1a7f4e" : "#b3261e",
                }}
              />
            );
          })}
      </LineChart>
    </ResponsiveContainer>
  );
}
