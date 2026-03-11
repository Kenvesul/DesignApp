/**
 * components/InputField.jsx
 *
 * Reusable labelled input with inline error display and unit suffix.
 *
 * Props:
 *   label    — string — field label
 *   name     — string — input name/id
 *   value    — string — controlled value
 *   onChange — (e) => void
 *   type     — "text" | "number" (default "text")
 *   unit     — string — optional unit suffix, e.g. "kN/m²"
 *   error    — string — error message (shown in red below input)
 *   required — bool
 *   min, max, step — number — passed to <input> for number type
 *   help     — string — optional tooltip / hint text
 *   readOnly — bool
 */

export default function InputField({
  label, name, value, onChange,
  type = "text", unit, error, required = false,
  min, max, step, help, readOnly = false,
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={name}
             className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>

      <div className="relative flex">
        <input
          id={name}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          required={required}
          readOnly={readOnly}
          min={min} max={max} step={step}
          aria-describedby={help ? `${name}-help` : undefined}
          aria-invalid={!!error}
          className={`input flex-1 ${error ? "input-error" : ""} ${
            unit ? "rounded-r-none" : ""
          } ${readOnly ? "bg-gray-50 dark:bg-gray-700 cursor-default" : ""}`}
        />
        {unit && (
          <span className="inline-flex items-center px-3 rounded-r-md border border-l-0
                           border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700
                           text-gray-500 dark:text-gray-400 text-sm whitespace-nowrap">
            {unit}
          </span>
        )}
      </div>

      {help && !error && (
        <p id={`${name}-help`} className="text-xs text-gray-500 dark:text-gray-400">
          {help}
        </p>
      )}
      {error && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
