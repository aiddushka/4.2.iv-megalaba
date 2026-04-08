import { Device } from "../api/devicesApi";

interface Props {
  device: Device;
}

export function DeviceHistoryBlock({ device }: Props) {
  const history = [...(device.change_history || [])].sort((a, b) =>
    a.timestamp > b.timestamp ? -1 : 1,
  );

  return (
    <div style={{ border: "1px solid #1f2937", borderRadius: 12, background: "#020617", padding: "1rem" }}>
      <h4 style={{ margin: "0 0 0.75rem 0", color: "#22d3ee" }}>История изменений</h4>
      {!history.length ? (
        <p style={{ margin: 0, color: "#6b7280", fontSize: "0.85rem" }}>История пока пустая</p>
      ) : (
        <div style={{ display: "grid", gap: "0.5rem" }}>
          {history.map((entry, index) => (
            <div key={`${entry.timestamp}-${entry.field}-${index}`} style={{ border: "1px solid #1f2937", borderRadius: 8, background: "#0f172a", padding: "0.5rem" }}>
              <div style={{ color: "#9ca3af", fontSize: "0.75rem" }}>
                {new Date(entry.timestamp).toLocaleString()} · {entry.changed_by || "system"}
              </div>
              <div style={{ color: "#e5e7eb", fontSize: "0.85rem" }}>
                {entry.field}: {String(entry.old_value ?? "null")} → {String(entry.new_value ?? "null")}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
