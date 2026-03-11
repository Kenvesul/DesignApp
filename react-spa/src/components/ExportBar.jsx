/**
 * components/ExportBar.jsx
 *
 * Download buttons for PDF, DOCX, and PNG exports.
 * Triggers GET requests to the Flask /api/<type>/export/* routes.
 *
 * Props:
 *   type     — "slope" | "foundation" | "wall" | "pile" | "sheet-pile"
 *   disabled — bool (disable all buttons, e.g. while analysis is running)
 *   showPng  — bool (default true — pile has no PNG export)
 */

export default function ExportBar({ type, disabled = false, showPng = true }) {
  const base = `/api/${type}/export`;

  function download(url, filename) {
    const a = document.createElement("a");
    a.href     = url;
    a.download = filename;
    a.click();
  }

  const label = type.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="flex flex-wrap gap-2 items-center">
      <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-1">
        Export:
      </span>

      <button
        disabled={disabled}
        onClick={() => download(`${base}/pdf`, `${type}.pdf`)}
        className="btn-secondary text-xs py-1 px-3"
        title={`Download ${label} PDF calculation sheet`}
      >
        📄 PDF
      </button>

      <button
        disabled={disabled}
        onClick={() => download(`${base}/docx`, `${type}.docx`)}
        className="btn-secondary text-xs py-1 px-3"
        title={`Download ${label} Word document`}
      >
        📝 DOCX
      </button>

      {showPng && (
        <button
          disabled={disabled}
          onClick={() => download(`${base}/png`, `${type}.png`)}
          className="btn-secondary text-xs py-1 px-3"
          title={`Download ${label} cross-section PNG`}
        >
          🖼 PNG
        </button>
      )}
    </div>
  );
}
