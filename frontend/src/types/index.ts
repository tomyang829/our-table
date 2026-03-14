export interface User {
  id: number
  email: string
  name: string | null
  avatar_url: string | null
  oauth_provider: string
  flavor_profile: Record<string, unknown> | null
  created_at: string
}

export interface SourceRecipe {
  id: number
  url: string
  title: string
  description: string | null
  ingredients: string[]
  instructions: string[]
  image_url: string | null
  servings: string | null
  extracted_at: string
}

export interface UserRecipe {
  id: number
  user_id: number
  source_recipe_id: number
  title: string
  ingredients: string[]
  instructions: string[]
  notes: string | null
  image_url: string | null
  servings: string | null
  created_at: string
  updated_at: string
  source_recipe?: SourceRecipe
  deviates_from_source?: boolean
}

export interface RecipeShare {
  id: number
  user_recipe_id: number
  slug: string
  created_at: string
}

export interface ExtractResponse {
  source_recipe: SourceRecipe
  already_saved: boolean
  user_recipe_id?: number
  partial_parse?: boolean
}

export interface ApiError {
  detail: string
}

export interface CreateRecipeInput {
  title: string
  ingredients: string[]
  instructions: string[]
  notes?: string | null
  servings?: string | null
}
