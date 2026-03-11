/**
 * components/SoilPicker.jsx
 *
 * Dropdown that lists soils from /api/soils.  Selecting a preset populates
 * the parent's soil field values automatically.
 *
 * Props:
 *   soils    — array from useSoilLibrary()
 *   loading  — bool
 *   onSelect — (soil: object) => void  — called with the full soil object
 *   label    — string (default "Load preset soil")
 */

export default function SoilPicker({ soils = [], loading = false, onSelect, label = "Load preset soil" }) {
  function handleChange(e) {
    const name = e.target.value;
    if (!name) return;
    const soil = soils.find(s => s.name === name);
    if (soil && onSelect) onSelect(soil);
    e.target.value = ""; // reset so user can re-select same preset
  }

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">
        {label}:
      </label>
      <select
        onChange={handleChange}
        disabled={loading}
        defaultValue=""
        className="input flex-1 py-1.5 text-sm"
        aria-label={label}
      >
        <option value="" disabled>
          {loading ? "Loading soils…" : "— select —"}
        </option>
        {soils.map(s => (
          <option key={s.name} value={s.name}>
            {s.name} (φ′={s.phi_k}°, γ={s.gamma} kN/m³)
          </option>
        ))}
      </select>
    </div>
  );
}
