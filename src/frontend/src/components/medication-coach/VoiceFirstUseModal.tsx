/**
 * VoiceFirstUseModal — privacy disclosure shown before first mic access.
 *
 * Displayed once per profile. User acknowledges before browser mic prompt fires.
 */

import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { Mic, Shield } from 'lucide-react';

interface VoiceFirstUseModalProps {
  onAccept: () => void;
  onDecline: () => void;
}

export function VoiceFirstUseModal({ onAccept, onDecline }: VoiceFirstUseModalProps) {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" aria-hidden />
      <Card className="relative z-10 w-full max-w-sm shadow-elevated">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Mic className="w-4 h-4 text-accent" />
            Voice Logging
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-3 rounded-xl bg-surface-muted p-3">
            <Shield className="w-5 h-5 text-accent mt-0.5 shrink-0" />
            <div className="text-sm text-ink-secondary space-y-1">
              <p>
                We don't store audio. We store only the text you confirm.
              </p>
              <p>
                Speech recognition may be processed by your browser's speech service.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onDecline} className="flex-1">
              Not Now
            </Button>
            <Button onClick={onAccept} className="flex-1">
              Enable Voice
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
