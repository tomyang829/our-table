import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export function AddRecipePage() {
  const navigate = useNavigate()

  return (
    <div className="container mx-auto max-w-2xl p-6">
      <h1 className="mb-6 text-2xl font-bold">Add a Recipe</h1>
      <div className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="url" className="text-sm font-medium">
            Recipe URL
          </label>
          <input
            id="url"
            type="url"
            placeholder="https://example.com/recipe"
            className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div className="flex gap-3">
          <Button>Extract Recipe</Button>
          <Button variant="outline" onClick={() => navigate(-1)}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  )
}
