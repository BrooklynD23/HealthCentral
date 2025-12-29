import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  FileText,
  ExternalLink,
  Sparkles,
  AlertCircle,
  BookOpen,
  Clock,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: { source: string; page: number }[];
  timestamp: Date;
}

const mockMessages: Message[] = [
  {
    id: '1',
    role: 'user',
    content: 'What does my hemoglobin level mean?',
    timestamp: new Date(Date.now() - 60000),
  },
  {
    id: '2',
    role: 'assistant',
    content: `**What your report shows:**
Your hemoglobin level is 14.2 g/dL, which falls within the reference range of 12.0-17.5 g/dL as stated in your Quest Diagnostics report from December 15, 2024.

**General information:**
Hemoglobin is a protein in red blood cells that carries oxygen throughout your body. Levels within the reference range typically indicate that your blood is carrying oxygen effectively.

**Uncertainties:**
Reference ranges can vary between laboratories and may depend on factors like age, sex, and altitude. Always discuss your specific results with your healthcare provider for personalized interpretation.`,
    citations: [
      { source: 'Quest Diagnostics Report', page: 1 },
      { source: 'Medical Reference Corpus', page: 0 },
    ],
    timestamp: new Date(Date.now() - 30000),
  },
];

const suggestedQuestions = [
  'What does WBC count indicate?',
  'Are my lipid levels healthy?',
  'Explain the CMP panel results',
  'What questions should I ask my doctor?',
];

export function ExplainAssistant() {
  const prefersReducedMotion = useReducedMotion();
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Simulate response
    await new Promise((r) => setTimeout(r, 1500));

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content:
        "I'll help you understand that. Based on your reports, here's what I found...\n\n*This is a simulated response. In the full implementation, this would provide grounded information based on your actual medical records.*",
      citations: [{ source: 'Your Documents', page: 1 }],
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setIsLoading(false);
  };

  return (
    <div className="h-[calc(100vh-10rem)] flex gap-6">
      <div className="flex-1 flex flex-col">
        <Card className="flex-1 flex flex-col overflow-hidden">
          <CardHeader className="border-b border-black/[0.04] flex-shrink-0">
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-accent-subtle flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-accent" />
                </div>
                <span>Explain Assistant</span>
              </div>
              <Badge variant="info" className="gap-1.5">
                <FileText className="w-3 h-3" />
                4 documents in context
              </Badge>
            </CardTitle>
          </CardHeader>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <AnimatePresence mode="popLayout">
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={prefersReducedMotion ? {} : { opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={cn(
                    'flex',
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  <div
                    className={cn(
                      'max-w-[80%] rounded-2xl px-4 py-3',
                      message.role === 'user'
                        ? 'bg-accent text-white'
                        : 'bg-surface-muted'
                    )}
                  >
                    <div
                      className={cn(
                        'text-sm whitespace-pre-wrap',
                        message.role === 'assistant' && 'prose prose-sm max-w-none'
                      )}
                    >
                      {message.content}
                    </div>

                    {message.citations && message.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-black/[0.08]">
                        <p className="text-xs text-ink-secondary mb-2">Sources:</p>
                        <div className="flex flex-wrap gap-2">
                          {message.citations.map((citation, i) => (
                            <button
                              key={i}
                              className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-lg bg-white/80 text-ink-secondary hover:text-accent transition-colors"
                            >
                              <FileText className="w-3 h-3" />
                              {citation.source}
                              {citation.page > 0 && ` (p.${citation.page})`}
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    <div
                      className={cn(
                        'text-xs mt-2',
                        message.role === 'user'
                          ? 'text-white/60'
                          : 'text-ink-tertiary'
                      )}
                    >
                      <Clock className="w-3 h-3 inline mr-1" />
                      {message.timestamp.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="bg-surface-muted rounded-2xl px-4 py-3">
                  <div className="flex items-center gap-2 text-ink-secondary">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-accent rounded-full animate-bounce animation-delay-0" />
                      <span className="w-2 h-2 bg-accent rounded-full animate-bounce animation-delay-150" />
                      <span className="w-2 h-2 bg-accent rounded-full animate-bounce animation-delay-300" />
                    </div>
                    <span className="text-sm">Thinking...</span>
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-black/[0.04] p-4 flex-shrink-0">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="Ask about your results..."
                className={cn(
                  'flex-1 px-4 py-3 rounded-xl',
                  'bg-surface-muted border-0',
                  'text-sm text-ink placeholder:text-ink-tertiary',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2'
                )}
                disabled={isLoading}
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="px-4"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <div className="w-80 space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-ink-secondary" />
              Suggested Questions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {suggestedQuestions.map((question, i) => (
              <button
                key={i}
                onClick={() => setInput(question)}
                className={cn(
                  'w-full text-left px-3 py-2.5 rounded-xl text-sm',
                  'bg-surface-muted hover:bg-accent-subtle hover:text-accent',
                  'transition-colors duration-200'
                )}
              >
                {question}
              </button>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-status-caution-subtle border-status-caution/20">
          <CardContent className="p-4">
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-status-caution flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-ink mb-1">Important</p>
                <p className="text-xs text-ink-secondary leading-relaxed">
                  This assistant provides information based on your documents
                  and general medical references. It does not provide medical
                  advice, diagnosis, or treatment recommendations. Always
                  consult your healthcare provider.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
