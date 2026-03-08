import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useMyRecipes } from '@/hooks/useRecipes'
import { useUser } from '@/hooks/useUser'
import type { UserRecipe } from '@/types'

function RecipeCard({ recipe }: { recipe: UserRecipe }) {
  const imageUrl = recipe.image_url ?? recipe.source_recipe?.image_url
  const isEdited = recipe.deviates_from_source === true

  return (
    <Link
      to={`/recipes/${recipe.id}`}
      className="block overflow-hidden rounded-lg border transition-colors hover:bg-accent"
    >
      {imageUrl ? (
        <img src={imageUrl} alt="" className="h-40 w-full object-cover" />
      ) : (
        <div className="h-40 w-full bg-muted" />
      )}
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold">{recipe.title}</h3>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              isEdited
                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            {isEdited ? 'Edited' : 'As-is'}
          </span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {recipe.ingredients.length} ingredient{recipe.ingredients.length !== 1 ? 's' : ''}
        </p>
        {recipe.notes && (
          <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{recipe.notes}</p>
        )}
      </div>
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
