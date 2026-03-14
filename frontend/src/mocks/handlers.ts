import { http, HttpResponse } from 'msw'
import type { User, UserRecipe, SourceRecipe, ExtractResponse } from '@/types'

export const mockUser: User = {
  id: 1,
  email: 'test@example.com',
  name: 'Test User',
  avatar_url: null,
  oauth_provider: 'google',
  flavor_profile: null,
  created_at: '2024-01-01T00:00:00Z',
}

export const mockSourceRecipe: SourceRecipe = {
  id: 1,
  url: 'https://example.com/recipe',
  title: 'Test Recipe',
  description: 'A test recipe',
  ingredients: ['1 cup flour', '2 eggs'],
  instructions: ['Mix ingredients', 'Bake at 350°F'],
  image_url: null,
  servings: '4 servings',
  extracted_at: '2024-01-01T00:00:00Z',
}

export const mockUserRecipe: UserRecipe = {
  id: 1,
  user_id: 1,
  source_recipe_id: 1,
  title: 'My Test Recipe',
  ingredients: ['1 cup flour', '2 eggs'],
  instructions: ['Mix ingredients', 'Bake at 350°F'],
  notes: null,
  image_url: null,
  servings: '4 servings',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  source_recipe: mockSourceRecipe,
  deviates_from_source: false,
}

export const mockManualUserRecipe: UserRecipe = {
  ...mockUserRecipe,
  id: 2,
  source_recipe_id: 2,
  title: 'Homemade Soup',
  ingredients: ['2 carrots', '1 onion'],
  instructions: ['Chop vegetables', 'Simmer 30 minutes'],
  notes: 'Add parsley at the end',
  servings: '4',
  source_recipe: {
    ...mockSourceRecipe,
    id: 2,
    url: 'manual://1/mock',
    title: 'Homemade Soup',
    ingredients: ['2 carrots', '1 onion'],
    instructions: ['Chop vegetables', 'Simmer 30 minutes'],
    servings: '4',
  },
}

export const handlers = [
  http.get('/api/users/me', () => HttpResponse.json(mockUser)),

  http.get('/api/recipes/mine', () => HttpResponse.json([mockUserRecipe])),

  http.get('/api/recipes/mine/:id', ({ params }) => {
    const id = Number(params['id'])
    if (id !== mockUserRecipe.id) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(mockUserRecipe)
  }),

  http.put('/api/recipes/mine/:id', async ({ request }) => {
    const body = (await request.json()) as Partial<UserRecipe>
    return HttpResponse.json({ ...mockUserRecipe, ...body })
  }),

  http.post('/api/recipes/extract', async ({ request }) => {
    const body = (await request.json()) as { url: string }
    const response: ExtractResponse = {
      source_recipe: { ...mockSourceRecipe, url: body.url },
      already_saved: false,
    }
    return HttpResponse.json(response)
  }),

  http.post('/api/recipes/source/:id/save', () =>
    HttpResponse.json(mockUserRecipe, { status: 201 }),
  ),

  http.post('/api/recipes/mine', async ({ request }) => {
    const body = (await request.json()) as {
      title: string
      ingredients?: string[]
      instructions?: string[]
      notes?: string | null
      servings?: string | null
    }
    return HttpResponse.json(
      {
        ...mockManualUserRecipe,
        title: body.title,
        ingredients: body.ingredients ?? [],
        instructions: body.instructions ?? [],
        notes: body.notes ?? null,
        servings: body.servings ?? null,
        source_recipe: {
          ...mockManualUserRecipe.source_recipe!,
          title: body.title,
          ingredients: body.ingredients ?? [],
          instructions: body.instructions ?? [],
          servings: body.servings ?? null,
        },
      },
      { status: 201 },
    )
  }),

  http.delete('/api/recipes/mine/:id', ({ params }) => {
    const id = Number(params['id'])
    if (id !== mockUserRecipe.id) return new HttpResponse(null, { status: 404 })
    return new HttpResponse(null, { status: 204 })
  }),

  http.post('/api/recipes/mine/:id/image', ({ params }) => {
    const id = Number(params['id'])
    if (id !== mockUserRecipe.id) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json({
      ...mockUserRecipe,
      image_url: '/api/uploads/recipes/1.jpg',
    })
  }),
]
