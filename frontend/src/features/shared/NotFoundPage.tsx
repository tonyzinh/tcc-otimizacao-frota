import { Compass } from 'lucide-react'
import { Link } from 'react-router'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/feedback'

export function NotFoundPage() {
  return (
    <div className="flex h-full items-center justify-center">
      <EmptyState
        icon={<Compass />}
        title="Página não encontrada"
        description="O endereço não corresponde a nenhuma tela do FleetLab."
        action={
          <Button asChild size="sm" className="mt-2">
            <Link to="/">Voltar ao Dashboard</Link>
          </Button>
        }
      />
    </div>
  )
}
