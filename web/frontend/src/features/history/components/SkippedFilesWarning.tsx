import { AlertTriangle, ChevronDown, ChevronUp, X } from 'lucide-react'
import { useState } from 'react'

interface SkippedFilesWarningProps {
  skippedFiles: string[]
}

export function SkippedFilesWarning({ skippedFiles }: SkippedFilesWarningProps) {
  const [dismissed, setDismissed] = useState(false)
  const [expanded, setExpanded] = useState(false)

  if (dismissed) return null

  const count = skippedFiles.length

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600 dark:text-amber-500" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
            {count} archived run file{count === 1 ? '' : 's'} could not be read and{' '}
            {count === 1 ? 'was' : 'were'} skipped.
          </p>
          <p className="mt-0.5 text-xs text-amber-700 dark:text-amber-400">
            These files may be corrupt or incompatible with the current schema version.
          </p>
          <button
            className="mt-2 flex items-center gap-1 rounded-sm text-xs font-medium text-amber-800 transition-colors hover:text-amber-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 dark:text-amber-300 dark:hover:text-amber-100"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            {expanded ? 'Hide details' : 'Show details'}
          </button>
          {expanded && (
            <div className="mt-2 max-h-40 overflow-y-auto rounded-lg bg-amber-100 p-3 dark:bg-amber-950/40">
              <ul className="space-y-0.5">
                {skippedFiles.map((file) => (
                  <li
                    key={file}
                    className="break-all font-mono text-xs text-amber-800 dark:text-amber-400"
                  >
                    {file}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <button
          className="flex-shrink-0 rounded-sm text-amber-500 transition-colors hover:text-amber-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 dark:text-amber-400 dark:hover:text-amber-200"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss warning"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
