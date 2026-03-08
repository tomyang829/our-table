import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useMyRecipes } from '@/hooks/useRecipes'
import { useUser } from '@/hooks/useUser'
import type { UserRecipe } from '@/types'

function RecipeCard({ recipe }: { recipe: UserRecipe }) {
  return (
    <Link
      to={`/recipes/${recipe.id}`}
      className="block rounded-lg border p-4 transition-colors hover:bg-accent"
    >
      <h3 className="font-semibold">{recipe.title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        {recipe.ingredients.length} ingredient{recipe.ingredients.length !== 1 ? 's' : ''}
      </p>
      {recipe.notes && (
        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{recipe.notes}</p>
      )}
    </Link>
  )
}

export function DashboardPage() {
  const { data: user } = useUser()
  const { data: recipes, isLoading, isError } = useMyRecipes()

  return (
    <div className="container mx-auto max-w-4xl p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Recipes</h1>
          {user?.name && (
            <p className="text-sm text-muted-foreground">Welcome, {user.name}</p>
          )}
        </div>
        <Button asChild>
          <Link to="/recipes/add">Add Recipe</Link>
        </Button>
      </div>

      <div className="mt-6">
        {isLoading && (
          <div role="status" aria-label="Loading recipes" className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-lg border bg-muted" />
            ))}
          </div>
        )}

        {isError && (
          <p role="alert" className="text-destructive">
            Failed to load recipes. Please try again.
          </p>
        )}

        {recipes && recipes.length === 0 && (
          <div className="py-12 text-center">
            <p className="mb-4 text-muted-foreground">No recipes yet. Add your first one!</p>
            <Button asChild>
              <Link to="/recipes/add">Add Recipe</Link>
            </Button>
          </div>
        )}

        {recipes && recipes.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {recipes.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
