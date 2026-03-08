import { useState, useRef, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useRecipe } from '@/hooks/useRecipes'
import { useUpdateRecipe } from '@/hooks/useUpdateRecipe'
import { useUploadRecipeImage } from '@/hooks/useUploadRecipeImage'
import { useDeleteRecipe } from '@/hooks/useDeleteRecipe'

// Auto-grows to fit its content so long steps don't get clipped.
function AutoTextarea({
  value,
  onChange,
  placeholder,
  'aria-label': ariaLabel,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  'aria-label': string
}) {
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [value])

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={ariaLabel}
      rows={1}
      className="w-full resize-none overflow-hidden rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
    />
  )
}

interface ListEditorProps {
  label: string
  items: string[]
  onChange: (items: string[]) => void
  addLabel: string
  itemLabel: (i: number) => string
  placeholder?: string
}

function ListEditor({ label, items, onChange, addLabel, itemLabel, placeholder }: ListEditorProps) {
  const update = (i: number, value: string) => {
    const next = [...items]
    next[i] = value
    onChange(next)
  }

  const remove = (i: number) => onChange(items.filter((_, idx) => idx !== i))

  const add = () => onChange([...items, ''])

  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{label}</legend>
      <ol className="space-y-2" aria-label={label}>
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className="mt-2 w-6 shrink-0 text-right text-sm text-muted-foreground">
              {i + 1}.
            </span>
            <AutoTextarea
              value={item}
              onChange={(v) => update(i, v)}
              placeholder={placeholder}
              aria-label={itemLabel(i)}
            />
            <button
              type="button"
              onClick={() => remove(i)}
              aria-label={`Remove ${itemLabel(i)}`}
              className="mt-2 shrink-0 text-muted-foreground hover:text-destructive"
            >
              ✕
            </button>
          </li>
        ))}
      </ol>
      <Button type="button" variant="outline" size="sm" onClick={add}>
        {addLabel}
      </Button>
    </fieldset>
  )
}

export function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const recipeId = Number(id)

  const { data: recipe, isLoading, isError } = useRecipe(recipeId)
  const updateMutation = useUpdateRecipe()
  const uploadImageMutation = useUploadRecipeImage()
  const deleteMutation = useDeleteRecipe()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [isEditing, setIsEditing] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editIngredients, setEditIngredients] = useState<string[]>([])
  const [editInstructions, setEditInstructions] = useState<string[]>([])
  const [editNotes, setEditNotes] = useState('')

  const startEdit = () => {
    if (!recipe) return
    setEditTitle(recipe.title)
    setEditIngredients([...recipe.ingredients])
    setEditInstructions([...recipe.instructions])
    setEditNotes(recipe.notes ?? '')
    setIsEditing(true)
  }

  const cancelEdit = () => {
    setIsEditing(false)
    updateMutation.reset()
  }

  const handleDelete = async () => {
    if (!recipe) return
    try {
      await deleteMutation.mutateAsync(recipe.id)
      navigate('/dashboard')
    } catch {
      // error displayed via deleteMutation.isError
    }
  }

  const handleSave = async () => {
    if (!recipe) return
    try {
      await updateMutation.mutateAsync({
        id: recipe.id,
        title: editTitle,
        ingredients: editIngredients.map((s) => s.trim()).filter(Boolean),
        instructions: editInstructions.map((s) => s.trim()).filter(Boolean),
        notes: editNotes.trim() || null,
      })
      setIsEditing(false)
    } catch {
      // error displayed via updateMutation.isError
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-2xl p-6">
        <div role="status" aria-label="Loading recipe" className="space-y-4">
          <div className="h-8 w-48 animate-pulse rounded bg-muted" />
          <div className="h-4 w-full animate-pulse rounded bg-muted" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
        </div>
      </div>
    )
  }

  if (isError || !recipe) {
    return (
      <div className="container mx-auto max-w-2xl p-6">
        <p role="alert" className="text-destructive">
          Failed to load recipe.
        </p>
        <Button variant="outline" onClick={() => navigate('/dashboard')} className="mt-4">
          Back to Recipes
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/dashboard')}>
          ← Back
        </Button>
        {!isEditing && (
          <>
            <Button variant="outline" onClick={startEdit}>
              Edit Recipe
            </Button>
            {confirmingDelete ? (
              <div className="flex items-center gap-2" role="group" aria-label="Confirm delete">
                <span className="text-sm text-muted-foreground">Delete this recipe?</span>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending ? 'Deleting…' : 'Yes, delete'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmingDelete(false)}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setConfirmingDelete(true)}
              >
                Delete
              </Button>
            )}
            {deleteMutation.isError && (
              <p role="alert" className="text-sm text-destructive">
                Failed to delete recipe.
              </p>
            )}
          </>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="title" className="text-sm font-medium">
              Title
            </label>
            <input
              id="title"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <ListEditor
            label="Ingredients"
            items={editIngredients}
            onChange={setEditIngredients}
            addLabel="+ Add ingredient"
            itemLabel={(i) => `Ingredient ${i + 1}`}
            placeholder="e.g. 2 cups flour"
          />

          <ListEditor
            label="Instructions"
            items={editInstructions}
            onChange={setEditInstructions}
            addLabel="+ Add step"
            itemLabel={(i) => `Step ${i + 1}`}
            placeholder="Describe this step…"
          />

          <div className="space-y-2">
            <label htmlFor="notes" className="text-sm font-medium">
              Notes
            </label>
            <textarea
              id="notes"
              value={editNotes}
              onChange={(e) => setEditNotes(e.target.value)}
              rows={3}
              className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {updateMutation.isError && (
            <p role="alert" className="text-sm text-destructive">
              Failed to save changes. Please try again.
            </p>
          )}

          <div className="flex gap-3">
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving…' : 'Save Changes'}
            </Button>
            <Button variant="outline" onClick={cancelEdit}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <h1 className="text-2xl font-bold">{recipe.title}</h1>

          {(recipe.image_url ?? recipe.source_recipe?.image_url) && (
            <div className="space-y-2">
              <img
                src={recipe.image_url ?? recipe.source_recipe?.image_url ?? ''}
                alt={recipe.title ?? ''}
                className="w-full rounded-xl object-cover max-h-80"
              />
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="sr-only"
                  aria-label="Upload recipe image"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) {
                      uploadImageMutation.mutate({ recipeId: recipe.id, file })
                      e.target.value = ''
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadImageMutation.isPending}
                >
                  {uploadImageMutation.isPending ? 'Uploading…' : 'Change image'}
                </Button>
                {uploadImageMutation.isError && (
                  <span className="text-sm text-destructive">Upload failed.</span>
                )}
              </div>
            </div>
          )}

          {!recipe.image_url && !recipe.source_recipe?.image_url && (
            <div className="space-y-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="sr-only"
                aria-label="Upload recipe image"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) {
                    uploadImageMutation.mutate({ recipeId: recipe.id, file })
                    e.target.value = ''
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadImageMutation.isPending}
              >
                {uploadImageMutation.isPending ? 'Uploading…' : 'Upload recipe image'}
              </Button>
              {uploadImageMutation.isError && (
                <p className="text-sm text-destructive">Upload failed. Please try again.</p>
              )}
            </div>
          )}

          <section>
            <h2 className="mb-2 text-lg font-semibold">Ingredients</h2>
            <ul className="list-inside list-disc space-y-1">
              {recipe.ingredients.map((ingredient, i) => (
                <li key={i} className="text-sm">
                  {ingredient}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="mb-2 text-lg font-semibold">Instructions</h2>
            <ol className="list-inside list-decimal space-y-2">
              {recipe.instructions.map((step, i) => (
                <li key={i} className="text-sm">
                  {step}
                </li>
              ))}
            </ol>
          </section>

          {recipe.notes && (
            <section>
              <h2 className="mb-2 text-lg font-semibold">Notes</h2>
              <p className="text-sm text-muted-foreground">{recipe.notes}</p>
            </section>
          )}

          {recipe.source_recipe && (
            <details className="rounded-lg border p-4">
              <summary className="cursor-pointer text-sm font-medium">
                Compare with original
              </summary>
              <div className="mt-3 space-y-3">
                <div className="space-y-1">
                  <p className="text-sm font-medium">{recipe.source_recipe.title}</p>
                  <a
                    href={recipe.source_recipe.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary underline-offset-2 hover:underline break-all"
                  >
                    {recipe.source_recipe.url}
                  </a>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                    Original ingredients:
                  </p>
                  <ul className="list-inside list-disc space-y-1">
                    {recipe.source_recipe.ingredients.map((ing, i) => (
                      <li key={i} className="text-xs text-muted-foreground">
                        {ing}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                    Original instructions:
                  </p>
                  <ol className="list-inside list-decimal space-y-1">
                    {recipe.source_recipe.instructions.map((step, i) => (
                      <li key={i} className="text-xs text-muted-foreground">
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
