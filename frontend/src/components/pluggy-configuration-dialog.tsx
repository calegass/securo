import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { bankProviderConfigurations } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface PluggyConfigurationDialogProps {
  open: boolean
  onClose: () => void
}

/** Collects credentials over the authenticated API, but never reads them back. */
export function PluggyConfigurationDialog({ open, onClose }: PluggyConfigurationDialogProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')

  const saveMutation = useMutation({
    mutationFn: () => bankProviderConfigurations.savePluggy({
      client_id: clientId.trim(),
      client_secret: clientSecret,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections', 'providers'] })
      queryClient.invalidateQueries({ queryKey: ['bank-provider-configurations'] })
      setClientId('')
      setClientSecret('')
      toast.success(t('accounts.pluggyConfigured', 'Credenciais Pluggy salvas'))
      onClose()
    },
    onError: () => toast.error(t('common.error')),
  })

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t('accounts.configurePluggy', 'Configurar Pluggy')}</DialogTitle>
          <p className="text-sm text-muted-foreground">
            {t('accounts.configurePluggyHint', 'As credenciais ficam cifradas no servidor e nunca são exibidas novamente.')}
          </p>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="pluggy-client-id">Client ID</Label>
            <Input
              id="pluggy-client-id"
              autoComplete="off"
              value={clientId}
              onChange={(event) => setClientId(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="pluggy-client-secret">Client Secret</Label>
            <Input
              id="pluggy-client-secret"
              type="password"
              autoComplete="new-password"
              value={clientSecret}
              onChange={(event) => setClientSecret(event.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            onClick={() => saveMutation.mutate()}
            disabled={!clientId.trim() || !clientSecret || saveMutation.isPending}
          >
            {saveMutation.isPending ? t('common.loading') : t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
