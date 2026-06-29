import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
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
  PlusCircle,
  History,
  ThumbsUp,
  ThumbsDown,
  ChevronDown,
  ChevronUp,
  Tag,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useAuthStore } from '@/stores/authStore';
import { useAnalyteList, useModelSettings, useExternalApiSettings } from '@/services';
import { useObservations } from '@/services/observations';
import {
  DOCUMENT_CATEGORIES,
  useSendMessage,
  useChatSessions,
  useChatSessionHistory,
  formatResponseText,
  type ChatResponse,
  type DocumentCategory,
} from '@/services/assistant';
import { useSubmitFeedback, FEEDBACK_TAGS, type FeedbackTag } from '@/services/feedback';

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
  /** Backend turn ID for the assistant ChatTurn row (used for feedback). */
  turnId?: string;
}

const FALLBACK_QUESTIONS = [
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
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sessionLoaded, setSessionLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load the most recent session on mount (ASSIST-HIST-001)
  const { data: sessionsData } = useChatSessions();
  const mostRecentSessionId = sessionsData?.sessions?.[0]?.session_id ?? null;
  const { data: sessionHistory, isLoading: historyLoading } = useChatSessionHistory(
    !sessionLoaded && !currentSessionId ? mostRecentSessionId : null,
  );

  // When session history loads, populate messages from DB
  useEffect(() => {
    if (sessionLoaded || historyLoading) return;
    if (!mostRecentSessionId) {
      setSessionLoaded(true);
      return;
    }
    if (!sessionHistory) return;

    setCurrentSessionId(mostRecentSessionId);
    setSessionLoaded(true);

    const restored: Message[] = sessionHistory.turns.map((turn, i) => ({
      id: `restored-${i}`,
      role: turn.role as 'user' | 'assistant',
      content: turn.content,
      timestamp: new Date(),
      // Real ChatTurn.id so feedback works after a reload.
      turnId: turn.turn_id ?? undefined,
    }));
    if (restored.length > 0) {
      setMessages(restored);
    }
  }, [sessionHistory, historyLoading, mostRecentSessionId, sessionLoaded]);

  const startNewConversation = useCallback(() => {
    setCurrentSessionId(null);
    setMessages([]);
    setInput('');
    setModelUnavailable(false);
  }, []);

  // Filter state
  const [selectedAnalytes, setSelectedAnalytes] = useState<string[]>([]);
  const [selectedPanel, setSelectedPanel] = useState('');
  const [selectedDocumentCategory, setSelectedDocumentCategory] = useState<DocumentCategoryFilterValue>('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const analyteList = useAnalyteList(profileId || undefined);
  const { data: observationPool } = useObservations({ profile_id: profileId || '' });
  const sendMessage = useSendMessage();
  const submitFeedback = useSubmitFeedback();

  // Per-message feedback UI state: rating, tag picker open, correction text
  const [feedbackState, setFeedbackState] = useState<
    Record<string, { rating: 1 | -1 | null; tagsOpen: boolean; correctionOpen: boolean; correction: string; submitting: boolean; submitted: boolean; selectedTags: FeedbackTag[] }>
  >({});

  const getFeedbackState = (msgId: string) =>
    feedbackState[msgId] ?? { rating: null, tagsOpen: false, correctionOpen: false, correction: '', submitting: false, submitted: false, selectedTags: [] };

  const updateFeedbackState = (msgId: string, patch: Partial<ReturnType<typeof getFeedbackState>>) =>
    setFeedbackState((prev) => ({ ...prev, [msgId]: { ...getFeedbackState(msgId), ...patch } }));

  const handleFeedback = async (msg: Message, rating: 1 | -1) => {
    if (!msg.turnId || !currentSessionId) return;
    const fs = getFeedbackState(msg.id);
    const newRating = fs.rating === rating ? null : rating; // toggle
    updateFeedbackState(msg.id, { rating: newRating, submitting: true });
    if (newRating === null) {
      updateFeedbackState(msg.id, { submitting: false });
      return;
    }
    // Open correction textarea on thumbs-down
    if (newRating === -1) {
      updateFeedbackState(msg.id, { tagsOpen: true, correctionOpen: true });
    }
    try {
      await submitFeedback.mutateAsync({
        turnId: msg.turnId,
        data: {
          session_id: currentSessionId,
          rating: newRating,
          response_text: msg.content,
          feedback_tags: fs.selectedTags.length > 0 ? fs.selectedTags : undefined,
          correction_text: fs.correction.trim() || undefined,
        },
      });
      updateFeedbackState(msg.id, { submitting: false, submitted: true });
    } catch {
      updateFeedbackState(msg.id, { submitting: false });
    }
  };

  const handleSubmitCorrection = async (msg: Message) => {
    if (!msg.turnId || !currentSessionId) return;
    const fs = getFeedbackState(msg.id);
    updateFeedbackState(msg.id, { submitting: true });
    try {
      await submitFeedback.mutateAsync({
        turnId: msg.turnId,
        data: {
          session_id: currentSessionId,
          rating: fs.rating ?? -1,
          response_text: msg.content,
          feedback_tags: fs.selectedTags.length > 0 ? fs.selectedTags : undefined,
          correction_text: fs.correction.trim() || undefined,
        },
      });
      updateFeedbackState(msg.id, { submitting: false, submitted: true, correctionOpen: false, tagsOpen: false });
    } catch {
      updateFeedbackState(msg.id, { submitting: false });
    }
  };

  // Build suggested-question chips from the user's actual analytes.
  // Up to 4 analyte-specific chips; fall back to the static list when
  // the user has no observations yet.
  const suggestedQuestions = useMemo(() => {
    const analytes: string[] = analyteList && analyteList.length > 0
      ? analyteList.slice(0, 4)
      : [];
    if (analytes.length === 0) return FALLBACK_QUESTIONS;

    const DISPLAY: Record<string, string> = {
      ldl_cholesterol: 'LDL Cholesterol',
      hdl_cholesterol: 'HDL Cholesterol',
      total_cholesterol: 'Total Cholesterol',
      triglycerides: 'Triglycerides',
      hemoglobin_a1c: 'A1C',
      glucose_fasting: 'Fasting Glucose',
      glucose: 'Glucose',
      hemoglobin: 'Hemoglobin',
      tsh: 'TSH',
      creatinine: 'Creatinine',
      vitamin_d: 'Vitamin D',
    };
    const chips = analytes.map((a) => {
      const name = DISPLAY[a] ?? a.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      return `How's my ${name}?`;
    });
    // Append one generic follow-up question
    chips.push("What questions should I ask my doctor?");
    return chips;
  }, [analyteList]);
  const { data: modelSettings, isLoading: modelSettingsLoading } = useModelSettings();
  const { data: externalApi } = useExternalApiSettings();

  const activeModelSummary = useMemo(() => {
    if (externalApi?.use_external_api && (externalApi.model || externalApi.provider)) {
      const p = externalApi.provider || 'External API';
      const m = externalApi.model || 'default';
      return `${p} · ${m}`;
    }
    const tier = modelSettings?.current_tier;
    if (tier && modelSettings?.tier_availability?.[tier]?.model) {
      return modelSettings.tier_availability[tier].model as string;
    }
    if (tier) return `Tier: ${tier}`;
    return 'Local model';
  }, [modelSettings, externalApi]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  }, [messages, prefersReducedMotion]);

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
        min_faithfulness_score: 0.6,
        use_memory: true,
        selected_analytes: selectedAnalytes.length > 0 ? selectedAnalytes : undefined,
        selected_panel: selectedPanel || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        ...(selectedDocumentCategory ? { document_category: selectedDocumentCategory } : {}),
        session_id: currentSessionId,
      });

      // Track the session_id returned by the backend (may be new implicit session)
      if (response.session_id && response.session_id !== currentSessionId) {
        setCurrentSessionId(response.session_id);
      }

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
          source: citation.doc_title || (
            citation.source_type === 'user_observation'
              ? 'Your Results'
              : citation.source_type === 'user_document'
                ? 'Your Document'
                : 'Reference'
          ),
          page: citation.page,
          docId: citation.doc_id,
        });
      });
    });

    // Format content - replace [cite:N] with [N]
    const content = formatResponseText(response.full_response);

    const msgId = (Date.now() + 1).toString();
    return {
      id: msgId,
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
      // Use the persisted assistant ChatTurn.id so feedback joins back to the
      // real turn. Fall back to the local id only if the backend omitted it
      // (e.g. an unpersisted response).
      turnId: response.turn_id ?? msgId,
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
              <div className="flex items-center gap-2">
                {messages.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={startNewConversation}
                    className="gap-1.5 text-xs text-ink-secondary"
                    title="Start a new conversation"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    New
                  </Button>
                )}
                <Badge variant="info" className="gap-1.5 max-w-[min(20rem,55vw)]" title={activeModelSummary}>
                <FileText className="w-3 h-3 shrink-0" />
                {modelSettingsLoading ? (
                  <span className="inline-block h-3.5 w-28 bg-white/50 animate-pulse rounded" aria-hidden />
                ) : (
                  <span className="truncate">{activeModelSummary}</span>
                )}
              </Badge>
              </div>
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

          {(observationPool?.some((obs) => !obs.user_verified) ?? false) && (
            <div className="mx-6 mt-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-status-caution-subtle border border-status-caution/20">
              <AlertCircle className="w-5 h-5 text-status-caution flex-shrink-0" />
              <p className="text-xs text-ink-secondary">
                Some values are still unverified. Answers stay grounded, but confirm key numbers in Verify for highest confidence.
              </p>
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
                {(sessionsData?.sessions?.length ?? 0) > 0 && !sessionLoaded && (
                  <p className="text-xs text-ink-tertiary mt-2 flex items-center gap-1">
                    <History className="w-3 h-3" />
                    Loading previous conversation…
                  </p>
                )}
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
                              className={cn(
                                'inline-flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors',
                                citation.source === 'Your Results'
                                  ? 'bg-accent-subtle text-accent font-medium hover:bg-accent hover:text-white'
                                  : 'bg-white/80 text-ink-secondary hover:text-accent'
                              )}
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

                    {/* ── Feedback widget (assistant turns only) ── */}
                    {message.role === 'assistant' && !message.error && (() => {
                      const fs = getFeedbackState(message.id);
                      return (
                        <div className="mt-3 pt-2 border-t border-black/[0.06]">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-ink-tertiary mr-1">Was this helpful?</span>
                            <button
                              onClick={() => handleFeedback(message, 1)}
                              disabled={fs.submitting}
                              title="Helpful"
                              className={cn(
                                'p-1 rounded-lg transition-colors',
                                fs.rating === 1
                                  ? 'bg-status-success/20 text-status-success'
                                  : 'text-ink-tertiary hover:text-status-success hover:bg-status-success/10'
                              )}
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleFeedback(message, -1)}
                              disabled={fs.submitting}
                              title="Not helpful"
                              className={cn(
                                'p-1 rounded-lg transition-colors',
                                fs.rating === -1
                                  ? 'bg-status-danger/20 text-status-danger'
                                  : 'text-ink-tertiary hover:text-status-danger hover:bg-status-danger/10'
                              )}
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                            {fs.rating === -1 && (
                              <button
                                onClick={() => updateFeedbackState(message.id, { tagsOpen: !fs.tagsOpen, correctionOpen: !fs.correctionOpen })}
                                className="ml-1 flex items-center gap-1 text-xs text-ink-tertiary hover:text-ink transition-colors"
                              >
                                <Tag className="w-3 h-3" />
                                {fs.tagsOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                              </button>
                            )}
                            {fs.submitted && (
                              <span className="text-xs text-status-success ml-1">Thanks!</span>
                            )}
                          </div>

                          {/* Tag picker + correction (shown on thumbs-down) */}
                          {fs.rating === -1 && fs.tagsOpen && (
                            <div className="mt-2 space-y-2">
                              <div className="flex flex-wrap gap-1">
                                {FEEDBACK_TAGS.map((tag) => (
                                  <button
                                    key={tag}
                                    onClick={() => {
                                      const tags = fs.selectedTags.includes(tag)
                                        ? fs.selectedTags.filter((t) => t !== tag)
                                        : [...fs.selectedTags, tag];
                                      updateFeedbackState(message.id, { selectedTags: tags });
                                    }}
                                    className={cn(
                                      'text-xs px-2 py-0.5 rounded-full border transition-colors',
                                      fs.selectedTags.includes(tag)
                                        ? 'bg-accent text-white border-accent'
                                        : 'bg-white/60 text-ink-secondary border-black/10 hover:border-accent hover:text-accent'
                                    )}
                                  >
                                    {tag.replace(/_/g, ' ')}
                                  </button>
                                ))}
                              </div>

                              {fs.correctionOpen && (
                                <div className="space-y-1">
                                  <textarea
                                    value={fs.correction}
                                    onChange={(e) => updateFeedbackState(message.id, { correction: e.target.value })}
                                    placeholder="Optional: write a better answer…"
                                    rows={3}
                                    className="w-full text-xs px-2 py-1.5 rounded-lg bg-white/80 border border-black/10 text-ink placeholder:text-ink-tertiary focus:outline-none focus:ring-2 focus:ring-accent resize-none"
                                  />
                                  <Button
                                    size="sm"
                                    onClick={() => handleSubmitCorrection(message)}
                                    disabled={fs.submitting}
                                    className="text-xs py-1 h-auto"
                                  >
                                    {fs.submitting ? 'Saving…' : 'Submit feedback'}
                                  </Button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })()}
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
