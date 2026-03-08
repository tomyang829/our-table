import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useExtractRecipe } from '@/hooks/useExtractRecipe'
import { useSaveRecipe } from '@/hooks/useSaveRecipe'
import type { ExtractResponse } from '@/types'

interface ConflictData {
  sourceId: number
  userRecipeId?: number
}

export function AddRecipePage() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [extractedData, setExtractedData] = useState<ExtractResponse | null>(null)
  const [conflict, setConflict] = useState<ConflictData | null>(null)

  const extractMutation = useExtractRecipe()
  const saveMutation = useSaveRecipe()

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

  return (
    <div className="container mx-auto max-w-2xl p-6">
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/dashboard')}>
          ← Back
        </Button>
        <h1 className="text-2xl font-bold">Add a Recipe</h1>
      </div>

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
            {(extractMutation.error as { message?: string })?.message ?? 'Failed to extract recipe.'}
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
                couldn't be extracted automatically. You can still save it and fill them in manually.
              </p>
            </div>
          )}

          <div className="rounded-lg border p-4">
            <h2 className="text-lg font-semibold">
              {extractedData.source_recipe.title || 'Untitled recipe'}
            </h2>
            {(extractedData.source_recipe.description || (extractedData.partial_parse && extractedData.source_recipe.url)) && (
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
            {saveMutation.isPending ? 'Saving…' : extractedData.partial_parse ? 'Save & Fill In Manually' : 'Save Recipe'}
          </Button>
        </div>
      )}
    </div>
  )
}
