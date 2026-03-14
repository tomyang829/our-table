import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useBrowserDictation } from '@/hooks/useBrowserDictation'
import { useCreateRecipe } from '@/hooks/useCreateRecipe'
import { useExtractRecipe } from '@/hooks/useExtractRecipe'
import { useSaveRecipe } from '@/hooks/useSaveRecipe'
import type { ExtractResponse } from '@/types'

interface ConflictData {
  sourceId: number
  userRecipeId?: number
}

type DictationTarget = 'ingredients' | 'instructions'

function MicrophoneIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <path d="M12 17v5" />
      <path d="M8 22h8" />
    </svg>
  )
}

function ListeningMicrophoneIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-4 w-4 animate-pulse"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <path d="M12 17v5" />
      <path d="M8 22h8" />
    </svg>
  )
}

export function AddRecipePage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'url' | 'manual'>('url')

  const [url, setUrl] = useState('')
  const [extractedData, setExtractedData] = useState<ExtractResponse | null>(null)
  const [conflict, setConflict] = useState<ConflictData | null>(null)

  const [manualTitle, setManualTitle] = useState('')
  const [manualIngredients, setManualIngredients] = useState('')
  const [manualInstructions, setManualInstructions] = useState('')
  const [manualServings, setManualServings] = useState('')
  const [manualNotes, setManualNotes] = useState('')
  const [dictationTarget, setDictationTarget] = useState<DictationTarget | null>(null)

  const extractMutation = useExtractRecipe()
  const saveMutation = useSaveRecipe()
  const createMutation = useCreateRecipe()
  const { isSupported, isListening, error: dictationError, start, stop, clearError } =
    useBrowserDictation()

  useEffect(() => {
    if (!isListening && dictationTarget !== null) {
      setDictationTarget(null)
    }
  }, [dictationTarget, isListening])

  useEffect(() => {
    if (mode === 'url' && isListening) {
      stop()
    }
  }, [isListening, mode, stop])

  useEffect(() => () => stop(), [stop])

  const appendDictationChunk = (current: string, chunk: string) => {
    const trimmed = chunk.trim()
    if (!trimmed) return current
    const base = current.trim()
    return base ? `${base}\n${trimmed}` : trimmed
  }

  const toggleDictation = (target: DictationTarget) => {
    if (isListening && dictationTarget === target) {
      stop()
      setDictationTarget(null)
      return
    }

    clearError()
    setDictationTarget(target)
    start({
      onTranscript: (chunk) => {
        if (target === 'ingredients') {
          setManualIngredients((prev) => appendDictationChunk(prev, chunk))
          return
        }
        setManualInstructions((prev) => appendDictationChunk(prev, chunk))
      },
    })
  }

  const handleExtract = async (e: React.FormEvent) => {
    e.preventDefault()
    setExtractedData(null)
    setConflict(null)
    try {
      const data = await extractMutation.mutateAsync(url)
      setExtractedData(data)
      if (data.already_saved) {
        setConflict({
          sourceId: data.source_recipe.id,
          userRecipeId: data.user_recipe_id,
        })
      }
    } catch (err) {
      const error = err as {
        status?: number
        body?: { detail?: { source_recipe_id?: number; existing_recipe_id?: number } }
      }
      const detail = error.body?.detail
      if (error.status === 409 && detail?.source_recipe_id !== undefined) {
        setConflict({
          sourceId: detail.source_recipe_id,
          userRecipeId: detail.existing_recipe_id,
        })
      }
    }
  }

  const handleSave = async (sourceId: number) => {
    try {
      const saved = await saveMutation.mutateAsync(sourceId)
      navigate(`/recipes/${saved.id}`)
    } catch {
      // error displayed via saveMutation.isError
    }
  }

  const handleCreateFromScratch = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const saved = await createMutation.mutateAsync({
        title: manualTitle.trim(),
        ingredients: manualIngredients
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        instructions: manualInstructions
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        notes: manualNotes.trim() || null,
        servings: manualServings.trim() || null,
      })
      navigate(`/recipes/${saved.id}`)
    } catch {
      // error displayed via createMutation.isError
    }
  }

  return (
    <div className="container mx-auto max-w-2xl p-6">
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/dashboard')}>
          ← Back
        </Button>
        <h1 className="text-2xl font-bold">Add a Recipe</h1>
      </div>

      <div className="mb-6 flex gap-2">
        <Button
          variant={mode === 'url' ? 'default' : 'outline'}
          type="button"
          onClick={() => setMode('url')}
        >
          Import from URL
        </Button>
        <Button
          variant={mode === 'manual' ? 'default' : 'outline'}
          type="button"
          onClick={() => setMode('manual')}
        >
          Create from Scratch
        </Button>
      </div>

      {mode === 'url' ? (
        <>
          <form onSubmit={handleExtract} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="url" className="text-sm font-medium">
                Recipe URL
              </label>
              <input
                id="url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/recipe"
                className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                required
              />
            </div>
            <div className="flex gap-3">
              <Button type="submit" disabled={extractMutation.isPending}>
                {extractMutation.isPending ? 'Extracting…' : 'Extract Recipe'}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
            </div>
          </form>

          {extractMutation.isError && conflict === null && (
            <div
              role="alert"
              className="mt-4 rounded-md border border-destructive/50 bg-destructive/10 p-4"
            >
              <p className="text-sm text-destructive">
                {(extractMutation.error as { message?: string })?.message ??
                  'Failed to extract recipe.'}
              </p>
            </div>
          )}

          {conflict !== null && (
            <div
              role="dialog"
              aria-label="Duplicate recipe"
              className="mt-4 space-y-3 rounded-md border p-4"
            >
              <h2 className="font-semibold">You've already saved this recipe</h2>
              <p className="text-sm text-muted-foreground">
                Would you like to view your existing copy or save another?
              </p>
              {saveMutation.isError && (
                <p role="alert" className="text-sm text-destructive">
                  {(saveMutation.error as { message?: string })?.message ?? 'Failed to save recipe.'}
                </p>
              )}
              <div className="flex flex-wrap gap-3">
                {conflict.userRecipeId !== undefined && (
                  <Button
                    variant="outline"
                    onClick={() => navigate(`/recipes/${conflict.userRecipeId}`)}
                  >
                    View Existing Recipe
                  </Button>
                )}
                <Button
                  onClick={() => handleSave(conflict.sourceId)}
                  disabled={saveMutation.isPending}
                >
                  {saveMutation.isPending ? 'Saving…' : 'Save Another Copy'}
                </Button>
                <Button variant="ghost" onClick={() => setConflict(null)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {extractedData !== null && conflict === null && (
            <div className="mt-6 space-y-4">
              {extractedData.partial_parse && (
                <div
                  role="alert"
                  className="rounded-md border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950/40"
                >
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                    Couldn't fully parse this page
                  </p>
                  <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                    This site doesn't use structured recipe markup, so ingredients and instructions
                    couldn't be extracted automatically. You can still save it and fill them in
                    manually.
                  </p>
                </div>
              )}

              <div className="rounded-lg border p-4">
                <h2 className="text-lg font-semibold">
                  {extractedData.source_recipe.title || 'Untitled recipe'}
                </h2>
                {(extractedData.source_recipe.description ||
                  (extractedData.partial_parse && extractedData.source_recipe.url)) && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    {extractedData.source_recipe.description || extractedData.source_recipe.url}
                  </p>
                )}
                {!extractedData.partial_parse && (
                  <p className="mt-2 text-sm text-muted-foreground">
                    {extractedData.source_recipe.ingredients.length} ingredient
                    {extractedData.source_recipe.ingredients.length !== 1 ? 's' : ''}
                  </p>
                )}
              </div>

              {saveMutation.isError && (
                <p role="alert" className="text-sm text-destructive">
                  {(saveMutation.error as { message?: string })?.message ?? 'Failed to save recipe.'}
                </p>
              )}

              <Button
                onClick={() => handleSave(extractedData.source_recipe.id)}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending
                  ? 'Saving…'
                  : extractedData.partial_parse
                    ? 'Save & Fill In Manually'
                    : 'Save Recipe'}
              </Button>
            </div>
          )}
        </>
      ) : (
        <form onSubmit={handleCreateFromScratch} className="space-y-4">
          {!isSupported && (
            <p className="text-sm text-muted-foreground">
              Dictation is not supported in this browser. You can still type your recipe details.
            </p>
          )}
          <div className="space-y-2">
            <label htmlFor="manual-title" className="text-sm font-medium">
              Title
            </label>
            <input
              id="manual-title"
              type="text"
              value={manualTitle}
              onChange={(e) => setManualTitle(e.target.value)}
              placeholder="My Weeknight Pasta"
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              required
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <label htmlFor="manual-ingredients" className="text-sm font-medium">
                Ingredients (one per line)
              </label>
              {isSupported && (
                <Button
                  type="button"
                  variant={dictationTarget === 'ingredients' && isListening ? 'default' : 'outline'}
                  size="icon"
                  onClick={() => toggleDictation('ingredients')}
                  disabled={isListening && dictationTarget === 'instructions'}
                  aria-label={
                    dictationTarget === 'ingredients' && isListening
                      ? 'Stop ingredients dictation'
                      : 'Start ingredients dictation'
                  }
                  title={
                    dictationTarget === 'ingredients' && isListening
                      ? 'Stop dictation'
                      : 'Start dictation'
                  }
                >
                  {dictationTarget === 'ingredients' && isListening ? (
                    <ListeningMicrophoneIcon />
                  ) : (
                    <MicrophoneIcon />
                  )}
                </Button>
              )}
            </div>
            <textarea
              id="manual-ingredients"
              value={manualIngredients}
              onChange={(e) => setManualIngredients(e.target.value)}
              rows={6}
              placeholder={'2 cups flour\n1 tsp salt\n1 cup water'}
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <label htmlFor="manual-instructions" className="text-sm font-medium">
                Instructions (one step per line)
              </label>
              {isSupported && (
                <Button
                  type="button"
                  variant={dictationTarget === 'instructions' && isListening ? 'default' : 'outline'}
                  size="icon"
                  onClick={() => toggleDictation('instructions')}
                  disabled={isListening && dictationTarget === 'ingredients'}
                  aria-label={
                    dictationTarget === 'instructions' && isListening
                      ? 'Stop instructions dictation'
                      : 'Start instructions dictation'
                  }
                  title={
                    dictationTarget === 'instructions' && isListening
                      ? 'Stop dictation'
                      : 'Start dictation'
                  }
                >
                  {dictationTarget === 'instructions' && isListening ? (
                    <ListeningMicrophoneIcon />
                  ) : (
                    <MicrophoneIcon />
                  )}
                </Button>
              )}
            </div>
            <textarea
              id="manual-instructions"
              value={manualInstructions}
              onChange={(e) => setManualInstructions(e.target.value)}
              rows={6}
              placeholder={'Mix dry ingredients\nAdd water\nBake for 20 minutes'}
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="manual-servings" className="text-sm font-medium">
              Servings
            </label>
            <input
              id="manual-servings"
              type="text"
              value={manualServings}
              onChange={(e) => setManualServings(e.target.value)}
              placeholder="e.g. 4 servings"
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="manual-notes" className="text-sm font-medium">
              Notes
            </label>
            <textarea
              id="manual-notes"
              value={manualNotes}
              onChange={(e) => setManualNotes(e.target.value)}
              rows={3}
              placeholder="Any optional notes..."
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {dictationError && (
            <p role="alert" className="text-sm text-destructive">
              {dictationError}
            </p>
          )}

          {createMutation.isError && (
            <p role="alert" className="text-sm text-destructive">
              {(createMutation.error as { message?: string })?.message ?? 'Failed to create recipe.'}
            </p>
          )}

          <div className="flex gap-3">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating…' : 'Create Recipe'}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate(-1)}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
