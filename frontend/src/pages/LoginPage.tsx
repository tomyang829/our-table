import { Button } from '@/components/ui/button'

export function LoginPage() {
  const handleLogin = (provider: 'google' | 'github') => {
    window.location.href = `/api/auth/${provider}`
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-6 rounded-xl border p-8 shadow-sm">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold">Our Table</h1>
          <p className="text-muted-foreground">Save and personalise your favourite recipes.</p>
        </div>
        <div className="space-y-3">
          <Button className="w-full" onClick={() => handleLogin('google')}>
            Continue with Google
          </Button>
          <Button className="w-full" variant="outline" onClick={() => handleLogin('github')}>
            Continue with GitHub
          </Button>
        </div>
      </div>
    </div>
  )
}
