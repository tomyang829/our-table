import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export function DashboardPage() {
  return (
    <div className="container mx-auto max-w-4xl p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Recipes</h1>
        <Button asChild>
          <Link to="/recipes/add">Add Recipe</Link>
        </Button>
      </div>
      <p className="mt-4 text-muted-foreground">No recipes yet. Add your first one!</p>
    </div>
  )
}
