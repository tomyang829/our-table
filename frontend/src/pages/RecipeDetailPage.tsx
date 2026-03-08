import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  return (
    <div className="container mx-auto max-w-2xl p-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/dashboard')}>
          ← Back
        </Button>
        <h1 className="text-2xl font-bold">Recipe #{id}</h1>
      </div>
      <p className="mt-4 text-muted-foreground">Recipe details coming soon.</p>
    </div>
  )
}
