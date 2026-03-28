import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  FileText,
  ExternalLink,
  Sparkles,
  AlertCircle,
  BookOpen,
  Clock,
  CheckCircle2,
  XCircle,
  Info,
  Settings,
  Filter,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useAuthStore } from '@/stores/authStore';
import { useAnalyteList } from '@/services';
import {
  DOCUMENT_CATEGORIES,
  useSendMessage,
  formatResponseText,
  type ChatResponse,
  type ChatMessage as ChatHistoryMessage,
  type DocumentCategory,
} from '@/services/assistant';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: { source: string; page: number | null; docId: string | null }[];
  timestamp: Date;
  insufficientContext?: boolean;
  verification?: {
    enabled: boolean;
    faithfulnessScore: number;
    verifiedClaims: number;
    totalClaims: number;
  };
  error?: string;
}

const suggestedQuestions = [
  'What does my hemoglobin level mean?',
  'Are my glucose levels normal?',
  'Explain my cholesterol results',
  'What questions should I ask my doctor?',
];

const documentCategoryLabels: Record<DocumentCategory, string> = {
  lab: 'Lab',
  imaging: 'Imaging',
  pathology: 'Pathology',
  visit_notes: 'Visit Notes',
};

type DocumentCategoryFilterValue = '' | DocumentCategory;

export function ExplainAssistant() {
  const prefersReducedMotion = useReducedMotion();
  const navigate = useNavigate();
  const profileId = useAuthStore((state) => state.profileId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [modelUnavailable, setModelUnavailable] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Filter state
  const [selectedAnalytes, setSelectedAnalytes] = useState<string[]>([]);
  const [selectedPanel, setSelectedPanel] = useState('');
  const [selectedDocumentCategory, setSelectedDocumentCategory] = useState<DocumentCategoryFilterValue>('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const analyteList = useAnalyteList(profileId || undefined);
  const sendMessage = useSendMessage();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  }, [messages, prefersReducedMotion]);

  // Build conversation history for multi-turn context
  const buildHistory = (): ChatHistoryMessage[] => {
    return messages
      .filter((m) => !m.error)
      .map((m) => ({ role: m.role, content: m.content }));
  };

  const handleSend = async () => {
    if (!input.trim() || sendMessage.isPending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const question = input;
    setInput('');

    try {
      const response = await sendMessage.mutateAsync({
        question,
        include_references: true,
        enable_verification: true,
        selected_analytes: selectedAnalytes.length > 0 ? selectedAnalytes : undefined,
        selected_panel: selectedPanel || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        ...(selectedDocumentCategory ? { document_category: selectedDocumentCategory } : {}),
        history: buildHistory(),
      });

      // If we get a knowledge-base only response, flag model unavailable
      const isKnowledgeOnly = response.segments.some(
        (s) => s.segment_type === 'uncertainty' && s.content.includes('knowledge base only')
      );
      if (isKnowledgeOnly) {
        setModelUnavailable(true);
      }

      const assistantMessage = convertResponseToMessage(response);
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      // Handle error - create error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: getErrorContent(error),
        timestamp: new Date(),
        error: error instanceof Error ? error.message : 'Unknown error',
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const convertResponseToMessage = (response: ChatResponse): Message => {
    // Convert citations from all segments
    const allCitations: { source: string; page: number | null; docId: string | null }[] = [];
    response.segments.forEach((segment) => {
      segment.citations.forEach((citation) => {
        allCitations.push({
          source: citation.doc_title || (citation.source_type === 'user_document' ? 'Your Document' : 'Reference'),
          page: citation.page,
          docId: citation.doc_id,
        });
      });
    });

    // Format content - replace [cite:N] with [N]
    const content = formatResponseText(response.full_response);

    return {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content,
      citations: allCitations.length > 0 ? allCitations : undefined,
      timestamp: new Date(),
      insufficientContext: response.insufficient_context,
      verification: response.verification.enabled
        ? {
            enabled: true,
            faithfulnessScore: response.verification.faithfulness_score,
            verifiedClaims: response.verification.verified_claims,
            totalClaims: response.verification.total_claims,
          }
        : undefined,
    };
  };

  const getErrorContent = (error: unknown): string => {
    if (error instanceof Error) {
      if (error.message.includes('501')) {
        setModelUnavailable(true);
        return "No AI model is configured yet. Go to Settings to download a local model or connect an external API provider.";
      }
      if (error.message.includes('401') || error.message.includes('403')) {
        return 'Your session has expired. Please log in again to continue.';
      }
      if (error.message.includes('network') || error.message.includes('fetch')) {
        return 'Unable to connect to the server. Please check your connection and try again.';
      }
    }
    return "I encountered an error while processing your question. Please try again.";
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
                Grounded Answers
              </Badge>
            </CardTitle>
          </CardHeader>

          {modelUnavailable && (
            <div className="mx-6 mt-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-status-caution-subtle border border-status-caution/20">
              <Settings className="w-5 h-5 text-status-caution flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-ink">No AI model configured</p>
                <p className="text-xs text-ink-secondary">
                  Responses are limited to the knowledge base. Configure a model for full functionality.
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => navigate('/settings')}
                className="gap-1.5 flex-shrink-0"
              >
                <Settings className="w-3.5 h-3.5" />
                Settings
              </Button>
            </div>
          )}

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 rounded-2xl bg-accent-subtle flex items-center justify-center mb-4">
                  <Sparkles className="w-8 h-8 text-accent" />
                </div>
                <h3 className="text-lg font-medium text-ink mb-2">Ask about your lab results</h3>
                <p className="text-sm text-ink-secondary max-w-md">
                  I can help you understand your medical test results using information from your uploaded documents and trusted medical references. All answers are grounded with citations.
                </p>
              </div>
            )}

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
                        : message.error
                          ? 'bg-status-danger-subtle border border-status-danger/20'
                          : message.insufficientContext
                            ? 'bg-status-caution-subtle border border-status-caution/20'
                            : 'bg-surface-muted'
                    )}
                  >
                    {message.insufficientContext && (
                      <div className="flex items-center gap-2 mb-2 text-status-caution">
                        <Info className="w-4 h-4" />
                        <span className="text-xs font-medium">Limited Context Available</span>
                      </div>
                    )}

                    {message.error && (
                      <div className="flex items-center gap-2 mb-2 text-status-danger">
                        <XCircle className="w-4 h-4" />
                        <span className="text-xs font-medium">Error</span>
                      </div>
                    )}

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
                              [{i + 1}] {citation.source}
                              {citation.page && ` (p.${citation.page})`}
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {message.verification && message.verification.enabled && (
                      <div className="mt-3 pt-3 border-t border-black/[0.08]">
                        <div className="flex items-center gap-2 text-xs">
                          <CheckCircle2 className="w-3 h-3 text-status-success" />
                          <span className="text-ink-secondary">
                            {message.verification.verifiedClaims}/{message.verification.totalClaims} claims verified
                          </span>
                          <span className="text-ink-tertiary">
                            ({Math.round(message.verification.faithfulnessScore * 100)}% faithfulness)
                          </span>
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

            {sendMessage.isPending && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="bg-surface-muted rounded-2xl px-4 py-3">
                  <div className="flex items-center gap-2 text-ink-secondary">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm">Searching documents and generating response...</span>
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
                disabled={sendMessage.isPending}
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || sendMessage.isPending}
                className="px-4"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <div className="w-80 space-y-4">
        {/* Filters */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Filter className="w-4 h-4 text-ink-secondary" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-xs text-ink-secondary block mb-1">Date Range</label>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="flex-1 px-2 py-1.5 rounded-lg bg-surface-muted text-xs text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <span className="text-xs text-ink-tertiary">to</span>
                <input
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  className="flex-1 px-2 py-1.5 rounded-lg bg-surface-muted text-xs text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>
            <div>
              <label htmlFor="document-category-select" className="text-xs text-ink-secondary block mb-1">
                Document Category
              </label>
              <select
                id="document-category-select"
                value={selectedDocumentCategory}
                onChange={(e) => setSelectedDocumentCategory(e.target.value as DocumentCategoryFilterValue)}
                className="w-full px-2 py-1.5 rounded-lg bg-surface-muted text-xs text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="">All documents</option>
                {DOCUMENT_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {documentCategoryLabels[category]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-ink-secondary block mb-1">
                Analytes ({selectedAnalytes.length} selected)
              </label>
              <div className="max-h-32 overflow-y-auto rounded-xl bg-surface-muted p-2 space-y-1">
                {analyteList && analyteList.length > 0 ? (
                  analyteList.slice(0, 20).map((analyte: string) => (
                    <button
                      key={analyte}
                      onClick={() =>
                        setSelectedAnalytes((prev) =>
                          prev.includes(analyte)
                            ? prev.filter((a) => a !== analyte)
                            : [...prev, analyte]
                        )
                      }
                      className={cn(
                        'w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors',
                        selectedAnalytes.includes(analyte)
                          ? 'bg-accent-subtle text-accent font-medium'
                          : 'text-ink-secondary hover:bg-white'
                      )}
                    >
                      {analyte}
                    </button>
                  ))
                ) : (
                  <p className="text-xs text-ink-tertiary text-center py-2">
                    No analytes found
                  </p>
                )}
              </div>
            </div>
            <div>
              <label htmlFor="panel-select" className="text-xs text-ink-secondary block mb-1">
                Panel
              </label>
              <select
                id="panel-select"
                value={selectedPanel}
                onChange={(e) => setSelectedPanel(e.target.value)}
                className="w-full px-2 py-1.5 rounded-lg bg-surface-muted text-xs text-ink border border-black/[0.06] focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="">All panels</option>
                <option value="Lipid Panel">Lipid Panel</option>
                <option value="Metabolic Panel">Metabolic Panel</option>
                <option value="CBC">CBC</option>
                <option value="Thyroid Panel">Thyroid Panel</option>
                <option value="Liver Panel">Liver Panel</option>
                <option value="Kidney Panel">Kidney Panel</option>
              </select>
            </div>
            {(selectedAnalytes.length > 0 || fromDate || toDate || selectedPanel || selectedDocumentCategory) && (
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs"
                onClick={() => {
                  setSelectedAnalytes([]);
                  setSelectedPanel('');
                  setSelectedDocumentCategory('');
                  setFromDate('');
                  setToDate('');
                }}
              >
                Clear Filters
              </Button>
            )}
          </CardContent>
        </Card>

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
                disabled={sendMessage.isPending}
                className={cn(
                  'w-full text-left px-3 py-2.5 rounded-xl text-sm',
                  'bg-surface-muted hover:bg-accent-subtle hover:text-accent',
                  'transition-colors duration-200',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
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
