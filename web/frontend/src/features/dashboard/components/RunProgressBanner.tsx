import { Loader2 } from 'lucide-react'

export function RunProgressBanner() {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 dark:border-blue-900/50 dark:bg-blue-950/30">
      <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-blue-600 dark:text-blue-400" />
      <div>
        <p className="text-sm font-medium text-blue-900 dark:text-blue-300">Run in progress</p>
        <p className="text-xs text-blue-700 dark:text-blue-400">
          Checking seat availability — this usually takes 30–90 seconds
        </p>
      </div>
    </div>
  )
}
