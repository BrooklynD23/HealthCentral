import { useState, useRef, useEffect, useLayoutEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { m } from 'framer-motion';
import {
  Send,
  FileText,
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
  ExternalLink,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, IconButton } from '@/components/ui';
import { Pending } from '@/components/ui/Pending';
import { CitationTooltip } from '@/components/lab-interpreter/CitationTooltip';
import { SourceBlock } from '@/components/lab-interpreter/InterpretedResultCard';
import { ObservationSourceTrace } from '@/components/results/SourceTrace';
import { useSafetyMode } from '@/hooks/useSafetyMode';
import { duration, ease } from '@/motion/tokens';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useAuthStore } from '@/stores/authStore';
import { useAnalyteList, useModelSettings, useExternalApiSettings, useProviderInfo, ApiError } from '@/services';
import { useObservations } from '@/services/observations';
import type { Observation } from '@/services/types';
import { ExternalApiBreakGlassWarning } from '@/components/settings/ExternalApiBreakGlassWarning';
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

/**
 * A citation as rendered in the chat (CITE-SRC-001).
 *
 * `observationId` / `entityId` are the deep-link target. Which control a citation gets (AskCitation):
 *  - its observation is in the loaded list: the UI-PROVENANCE CitationTooltip. With a `doc_id` it offers "Open source",
 *    the Source Trace sheet with the document's real file name and excerpt, fetched only once the sheet opens (never
 *    the citation's doc_title as a file name); without one it keeps the record text and offers no sheet;
 *  - else it has a target: a button to the Verification Workbench;
 *  - else it has a real quote: the CitationTooltip with the quote only;
 *  - else (a care task, a timeline event, a bare locator) a plain label, because a button that opens nothing or
 *    navigates nowhere is worse than plain text.
 */
interface CitationChip {
  source: string;
  page: number | null;
  docId: string | null;
  observationId: string | null;
  entityId: string | null;
  /** The backend's text_snippet. Not always a quote: see quoteOf. */
  snippet: string | null;
}

/**
 * Build the Verification Workbench deep link for a citation, or null when it
 * has no inspectable source (CITE-SRC-001).
 */
function citationTarget(citation: CitationChip): string | null {
  const params = new URLSearchParams();
  if (citation.observationId) {
    params.set('observation', citation.observationId);
  } else if (citation.entityId && citation.docId) {
    // An entity is only inspectable with its document — the workbench loads
    // entities per doc. Without docId this rendered as a chip that navigated
    // nowhere, which on a health record is worse than a plain label.
    params.set('entity', citation.entityId);
  } else {
    return null;
  }
  if (citation.docId) params.set('doc', citation.docId);
  if (citation.page != null) params.set('page', String(citation.page));
  return `/verify?${params.toString()}`;
}

/**
 * The quoted passage in a text_snippet, or null when it is not one. The legacy RAG path sends a sentence. The default
 * agent path sends a row id: be/api/assistant.py `_to_api_citation` sets text_snippet = `c.locator or c.source_id`, and a
 * locator is an observation, task, document or event id, or "docId:page". Those are never shown as a quote, and a
 * passage of words always has whitespace where an id never does, so this does not depend on which id it is.
 */
function quoteOf(snippet: string | null): string | null {
  const text = snippet?.trim();
  return text && /\s/.test(text) ? text : null;
}

/** What the record itself says, for a citation that has no quote of its own: the analyte and its result. */
function recordText(observation: Observation): string {
  const name = observation.analyte_raw || observation.analyte_canonical;
  // `||`, as SourceTrace's result line has it: an empty value_text falls through to the number in both places.
  const result =
    observation.value_text ||
    (observation.value !== null ? `${observation.value}${observation.unit ? ` ${observation.unit}` : ''}` : null);
  return result ? `${name}: ${result}` : name;
}

/**
 * One citation under an answer. Chips are T0: the quote, the page and the source never move once they render.
 */
function AskCitation({
  citation,
  index,
  observation,
  expanded = false,
}: {
  citation: CitationChip;
  index: number;
  observation: Observation | undefined;
  /** Stricter safety mode: the source is on screen without a click (SAFETY-MODE-CITATIONS). */
  expanded?: boolean;
}) {
  const navigate = useNavigate();
  const target = citationTarget(citation);
  const quote = quoteOf(citation.snippet);
  const label = `${citation.source}${citation.page ? ` (p.${citation.page})` : ''}`;
  const title = observation || citation.page == null ? citation.source : `${citation.source} \u00b7 page ${citation.page}`;
  const tone =
    citation.source === 'Your Results' ? 'bg-accent-subtle text-accent font-medium' : 'bg-surface-muted text-ink-secondary';

  if (expanded) {
    // The honesty rule: a quotation only for real words (quoteOf). A locator or row id is a place, and is never shown.
    return (
      <SourceBlock name={citation.source} page={citation.page} quote={quote}>
        {observation ? (
          // What the record itself says, as the chip's popover shows it; plain text, not a quotation.
          <p data-t0="" className="text-xs text-ink-secondary [overflow-wrap:anywhere]">
            {recordText(observation)}
          </p>
        ) : null}
        {observation?.doc_id ? (
          <ObservationSourceTrace
            observation={observation}
            trigger={
              <button
                type="button"
                className="inline-flex min-h-target items-center text-sm font-medium text-accent underline underline-offset-4"
              >
                Open source
              </button>
            }
          />
        ) : !observation && target ? (
          <button
            type="button"
            onClick={() => navigate(target)}
            className="inline-flex min-h-target items-center text-sm font-medium text-accent underline underline-offset-4"
          >
            Show this result in the source document
          </button>
        ) : null}
      </SourceBlock>
    );
  }

  if (observation || (!target && quote)) {
    return (
      <span className="inline-flex max-w-full items-center gap-1">
        <CitationTooltip
          index={index}
          citation={{
            type: title,
            id: citation.observationId ?? citation.entityId ?? '',
            text: quote ?? (observation ? recordText(observation) : ''),
          }}
          // The source's own title, as given ("Quest_Lab_Report.pdf"), never the machine type CitationTooltip rewrites.
          title={title}
          // Only a row with a document can open a sheet that has a file name to show (as InterpretedResultCard).
          traceObservation={observation?.doc_id ? observation : undefined}
        />
        <span data-t0="" className="min-w-0 text-xs text-ink-secondary [overflow-wrap:anywhere]">
          {label}
        </span>
      </span>
    );
  }

  if (target) {
    return (
      <button
        type="button"
        data-t0=""
        onClick={() => navigate(target)}
        title="Show this result in the source document"
        className={cn(
          'inline-flex min-h-target max-w-full items-center gap-1 rounded-lg px-2 text-left text-xs transition-colors [overflow-wrap:anywhere]',
          'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1',
          tone
        )}
      >
        <FileText className="w-3 h-3 shrink-0" aria-hidden="true" />[{index + 1}] {label}
        <ExternalLink className="w-3 h-3 shrink-0" aria-hidden="true" />
      </button>
    );
  }

  return (
    <span
      data-t0=""
      className={cn('inline-flex max-w-full items-center gap-1 rounded-lg px-2 py-1 text-xs [overflow-wrap:anywhere]', tone)}
    >
      <FileText className="w-3 h-3 shrink-0" aria-hidden="true" />[{index + 1}] {label}
    </span>
  );
}

/**
 * The citations under one answer. Under the stricter safety mode each source shows expanded (SAFETY-MODE-CITATIONS);
 * otherwise these are today's chips. The mode is unknown (false) until its GET answers, which is today's view.
 */
function AskCitations({
  citations,
  observationsById,
  strictSafetyMode,
}: {
  citations: CitationChip[];
  observationsById: Map<string, Observation>;
  strictSafetyMode: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {citations.map((citation, i) => (
        <AskCitation
          key={i}
          citation={citation}
          index={i}
          observation={citation.observationId ? observationsById.get(citation.observationId) : undefined}
          expanded={strictSafetyMode}
        />
      ))}
    </div>
  );
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationChip[];
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

// HC-M24: bounded record-navigation queries — one-click chips that send
// immediately (rather than just prefilling) through the same handleSend path.
const RECORD_QUERY_CHIPS = [
  'Which follow-up tasks are open?',
  'Show all medication changes',
  'What changed since my last visit?',
];

const documentCategoryLabels: Record<DocumentCategory, string> = {
  lab: 'Lab',
  imaging: 'Imaging',
  pathology: 'Pathology',
  visit_notes: 'Visit Notes',
};

type DocumentCategoryFilterValue = '' | DocumentCategory;

const EMPTY_FEEDBACK = {
  rating: null as 1 | -1 | null,
  tagsOpen: false,
  correctionOpen: false,
  correction: '',
  // The last correction and tags that "Submit feedback" stored. A thumb click resends these, never the draft in the
  // textarea or tags ticked since. They live in this component, so they last until it unmounts.
  savedCorrection: '',
  savedTags: [] as FeedbackTag[],
  submitting: false,
  submitted: false,
  selectedTags: [] as FeedbackTag[],
};

const EASE_OUT: [number, number, number, number] = [...ease.out];

export function ExplainAssistant() {
  const prefersReducedMotion = useReducedMotion();
  const { checked: strictSafetyMode } = useSafetyMode();
  const navigate = useNavigate();
  const profileId = useAuthStore((state) => state.profileId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [modelUnavailable, setModelUnavailable] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sessionLoaded, setSessionLoaded] = useState(false);
  const messageListRef = useRef<HTMLDivElement>(null);

  // Load the most recent session on mount (ASSIST-HIST-001)
  const { data: sessionsData, isFetched: sessionsFetched } = useChatSessions();
  const mostRecentSessionId = sessionsData?.sessions?.[0]?.session_id ?? null;
  const { data: sessionHistory, isLoading: historyLoading } = useChatSessionHistory(
    !sessionLoaded && !currentSessionId ? mostRecentSessionId : null,
  );

  // When session history loads, populate messages from DB
  useEffect(() => {
    if (sessionLoaded || historyLoading || !sessionsFetched) return;
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
  }, [sessionHistory, historyLoading, mostRecentSessionId, sessionLoaded, sessionsFetched]);

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
  const observationsById = useMemo(
    () => new Map((observationPool ?? []).map((observation) => [observation.id, observation])),
    [observationPool]
  );
  const hasUnverified = observationPool?.some((obs) => !obs.user_verified) ?? false;
  const sendMessage = useSendMessage();
  const submitFeedback = useSubmitFeedback();

  // Per-message feedback UI state: rating, tag picker open, correction text
  const [feedbackState, setFeedbackState] = useState<Record<string, typeof EMPTY_FEEDBACK>>({});

  const getFeedbackState = (msgId: string) => feedbackState[msgId] ?? EMPTY_FEEDBACK;

  // Merge into the latest state, not the one this render closed over: handleFeedback makes several updates in one
  // call, and merging into the render's copy made each one overwrite the last (a thumbs-down never showed as pressed).
  const updateFeedbackState = (msgId: string, patch: Partial<typeof EMPTY_FEEDBACK>) =>
    setFeedbackState((prev) => ({ ...prev, [msgId]: { ...(prev[msgId] ?? EMPTY_FEEDBACK), ...patch } }));

  const handleFeedback = async (msg: Message, rating: 1 | -1) => {
    if (!msg.turnId || !currentSessionId) return;
    const fs = getFeedbackState(msg.id);
    // The pressed thumb stays pressed: there is no request that withdraws a rating, so clearing it on screen would
    // show a state the stored row does not have.
    if (fs.rating === rating) return;
    updateFeedbackState(msg.id, { rating, submitting: true });
    // Open correction textarea on thumbs-down
    if (rating === -1) {
      updateFeedbackState(msg.id, { tagsOpen: true, correctionOpen: true });
    }
    try {
      await submitFeedback.mutateAsync({
        turnId: msg.turnId,
        data: {
          session_id: currentSessionId,
          rating,
          response_text: msg.content,
          // Only what was submitted: a draft in the textarea or a tag ticked since is not the patient's answer until
          // they press Submit. Left out, the upsert would erase what is already stored, but only within this mount:
          // after a reload these are empty and the backend upsert replaces the row (queued as a backend row).
          feedback_tags: fs.savedTags.length > 0 ? fs.savedTags : undefined,
          correction_text: fs.savedCorrection || undefined,
        },
      });
      updateFeedbackState(msg.id, { submitting: false, submitted: true });
    } catch {
      // Back to the stored rating (null if none), so the screen shows what the row has and the next click retries.
      updateFeedbackState(msg.id, { submitting: false, rating: fs.rating });
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
      updateFeedbackState(msg.id, {
        submitting: false,
        submitted: true,
        correctionOpen: false,
        tagsOpen: false,
        savedCorrection: fs.correction.trim(),
        savedTags: fs.selectedTags,
      });
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
      hba1c: 'A1C',
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
  const { data: externalApi, isError: externalApiError } = useExternalApiSettings();
  const { data: providerInfo, isPending: providerInfoPending } = useProviderInfo();
  const breakGlassActive =
    externalApi?.use_external_api === true && externalApi.redaction_break_glass === true;
  const breakGlassUnknown =
    externalApiError ||
    (externalApi?.use_external_api === true && externalApi.redaction_break_glass === undefined);

  const activeModelSummary = useMemo(() => {
    if (externalApi?.use_external_api && (externalApi.model || externalApi.provider)) {
      const p = externalApi.provider || 'External API';
      const m = externalApi.model || 'default';
      return `${p} · ${m}`;
    }
    // capabilities names the provider that really answers (llm_provider is wrong
    // after the Ollama-unreachable fallback; llm_model may be "(auto)" or a path).
    const providerName = providerInfo?.capabilities?.provider_name;
    const modelName = providerInfo?.capabilities?.model_name;
    if (providerName && modelName) {
      return `${providerName} · ${modelName}`;
    }
    // Avoid flashing the tier label (a different model) before provider info lands.
    if (providerInfoPending) return 'Local model';
    const tier = modelSettings?.current_tier;
    if (tier && modelSettings?.tier_availability?.[tier]?.model) {
      return modelSettings.tier_availability[tier].model as string;
    }
    if (tier) return `Tier: ${tier}`;
    return 'Local model';
  }, [modelSettings, externalApi, providerInfo, providerInfoPending]);

  // Keep the newest message in view by scrolling the list itself. scrollIntoView on a sentinel also scrolls every
  // ancestor, which moved the whole page on each send (and on load). Set before paint and without easing, so a
  // T0 answer is at its final position in the first frame it exists.
  // With no message and nothing pending there is nothing to follow: the list sits at its top, so the banners and the
  // empty state are in view (a list emptied by "New" is put back there, the browser only clamps it).
  useLayoutEffect(() => {
    const list = messageListRef.current;
    if (!list) return;
    const nothingToFollow = messages.length === 0 && !sendMessage.isPending;
    list.scrollTop = nothingToFollow ? 0 : list.scrollHeight;
  }, [messages, sendMessage.isPending]);

  const handleSend = async (overrideQuestion?: string) => {
    const question = (overrideQuestion ?? input).trim();
    if (!question || sendMessage.isPending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
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
    const allCitations: CitationChip[] = [];
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
          page: citation.page ?? citation.source_page ?? null,
          docId: citation.doc_id,
          observationId: citation.observation_id ?? null,
          entityId: citation.entity_id ?? null,
          snippet: citation.text_snippet || null,
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
    if (error instanceof ApiError) {
      if (error.status === 501) {
        setModelUnavailable(true);
        return "No AI model is configured yet. Go to Settings to download a local model or connect an external API provider.";
      }
      if (error.status === 401 || error.status === 403) {
        return 'Your session has expired. Please log in again to continue.';
      }
    }
    if (error instanceof Error) {
      if (error.message.includes('network') || error.message.includes('fetch')) {
        return 'Unable to connect to the server. Please check your connection and try again.';
      }
    }
    return "I encountered an error while processing your question. Please try again.";
  };

  const renderBubble = (message: Message) => {
    const isAssistant = message.role === 'assistant';
    return (
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-3 lg:max-w-[80%]',
          message.role === 'user'
            ? 'bg-accent text-[var(--on-accent)]'
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

        {/* T0: an answer's values, and the text of a chat error, never move once they render. The patient's own
            words are not T0. */}
        <div
          {...(isAssistant ? { 'data-t0': '' } : {})}
          className={cn('text-sm whitespace-pre-wrap break-words', isAssistant && 'prose prose-sm max-w-none')}
        >
          {message.content}
        </div>

        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-black/8">
            <p className="text-xs text-ink-secondary mb-2">Sources:</p>
            <AskCitations
              citations={message.citations}
              observationsById={observationsById}
              strictSafetyMode={strictSafetyMode}
            />
          </div>
        )}

        {message.verification && message.verification.enabled && (
          <div className="mt-3 pt-3 border-t border-black/8">
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
              ? 'text-[var(--on-accent)]'
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
            <div className="mt-3 pt-2 border-t border-black/6">
              <div className="flex items-center gap-1">
                <span className="text-xs text-ink-tertiary mr-1">Was this helpful?</span>
                <IconButton
                  variant="ghost"
                  aria-label="Helpful"
                  aria-pressed={fs.rating === 1}
                  title="Helpful"
                  onClick={() => handleFeedback(message, 1)}
                  disabled={fs.submitting}
                  className={cn(
                    'rounded-lg',
                    fs.rating === 1
                      ? 'bg-status-success/20 text-status-success'
                      : 'text-ink-tertiary hover:text-status-success hover:bg-status-success/10'
                  )}
                >
                  <ThumbsUp className="w-4 h-4" aria-hidden="true" />
                </IconButton>
                <IconButton
                  variant="ghost"
                  aria-label="Not helpful"
                  aria-pressed={fs.rating === -1}
                  title="Not helpful"
                  onClick={() => handleFeedback(message, -1)}
                  disabled={fs.submitting}
                  className={cn(
                    'rounded-lg',
                    fs.rating === -1
                      ? 'bg-status-danger/20 text-status-danger'
                      : 'text-ink-tertiary hover:text-status-danger hover:bg-status-danger/10'
                  )}
                >
                  <ThumbsDown className="w-4 h-4" aria-hidden="true" />
                </IconButton>
                {fs.rating === -1 && (
                  <IconButton
                    variant="ghost"
                    aria-label="Feedback options"
                    aria-expanded={fs.tagsOpen}
                    onClick={() => updateFeedbackState(message.id, { tagsOpen: !fs.tagsOpen, correctionOpen: !fs.correctionOpen })}
                    className="rounded-lg text-ink-tertiary hover:text-ink"
                  >
                    <Tag className="w-3.5 h-3.5" aria-hidden="true" />
                    {fs.tagsOpen ? <ChevronUp className="w-3 h-3" aria-hidden="true" /> : <ChevronDown className="w-3 h-3" aria-hidden="true" />}
                  </IconButton>
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
                        type="button"
                        aria-pressed={fs.selectedTags.includes(tag)}
                        onClick={() => {
                          const tags = fs.selectedTags.includes(tag)
                            ? fs.selectedTags.filter((t) => t !== tag)
                            : [...fs.selectedTags, tag];
                          updateFeedbackState(message.id, { selectedTags: tags });
                        }}
                        className={cn(
                          'text-xs px-3 py-1.5 rounded-full border transition-colors',
                          fs.selectedTags.includes(tag)
                            ? 'bg-accent text-[var(--on-accent)] border-accent'
                            : 'bg-surface-elevated text-ink-secondary border-border hover:border-accent hover:text-accent'
                        )}
                      >
                        {tag.replace(/_/g, ' ')}
                      </button>
                    ))}
                  </div>

                  {fs.correctionOpen && (
                    <div className="space-y-1">
                      <textarea
                        aria-label="Suggest a better answer"
                        value={fs.correction}
                        onChange={(e) => updateFeedbackState(message.id, { correction: e.target.value })}
                        placeholder="Optional: write a better answer…"
                        rows={3}
                        className="w-full text-xs px-2 py-1.5 rounded-lg bg-surface-elevated border border-border text-ink placeholder:text-ink-tertiary focus:outline-hidden focus:ring-2 focus:ring-accent resize-none"
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
    );
  };

  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      <div className="flex min-w-0 flex-1 flex-col">
        {/* The card is as tall as the space between the shell's header and its Safety Rail / tab bar (AppLayout writes
            --shell-top-h and --shell-bottom-h), so the composer and the disclaimer under it are in view without a page
            scroll and the message list is the only thing that scrolls. 2.5rem / 4rem: the main area's padding.
            min-h-min is the floor: the card never gets shorter than its fixed parts plus the list's min-h-48, so on a
            short screen, or with the privacy banner pinned, it grows and the window scrolls to the composer and the
            disclaimer instead of an overflow clipping them. The list is absolutely positioned in its wrapper so its
            messages add nothing to that floor.
            overflow-anchor: none keeps the browser from treating a node inside the list as the page's scroll anchor:
            when the list scrolls itself to the newest message, the anchor moved and the page was scrolled to follow. */}
        <Card
          data-testid="ask-card"
          className={cn(
            'flex flex-col min-h-min [overflow-anchor:none]',
            'h-[calc(100dvh-var(--shell-top-h,4rem)-var(--shell-bottom-h,3rem)-2.5rem)]',
            'lg:h-[calc(100dvh-var(--shell-top-h,4rem)-var(--shell-bottom-h,3rem)-4rem)]'
          )}
        >
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-black/4 px-4 py-3 lg:px-6 lg:py-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent-subtle flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-accent" />
              </div>
              <h1 className="font-display text-xl font-semibold tracking-tight text-ink">Explain Assistant</h1>
            </div>
            <div className="flex min-h-target min-w-0 items-center gap-2">
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
                  <span className="inline-block h-3.5 w-28 bg-white/50 animate-pulse rounded-sm" aria-hidden />
                ) : (
                  <span className="truncate">{activeModelSummary}</span>
                )}
              </Badge>
            </div>
          </div>

          {(breakGlassActive || breakGlassUnknown) && (
            <div className="mx-4 mt-4 shrink-0 lg:mx-6">
              <ExternalApiBreakGlassWarning active={breakGlassActive} unknown={breakGlassUnknown} />
            </div>
          )}

          <div className="relative min-h-48 flex-1">
            {/* The banners that are not privacy warnings live in the list, so they scroll away instead of taking height
                from the composer on a short screen. The break-glass warning above stays pinned (W-6 Q3, D12). From lg up
                the list has the room to keep these two pinned as well, so a value that is missing is never explained
                by a banner that has scrolled out of view. Below lg they scroll with the list. */}
            <div
              ref={messageListRef}
              role="log"
              aria-label="Conversation"
              tabIndex={0}
              className="absolute inset-0 flex flex-col gap-6 overflow-y-auto p-4 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent lg:p-6"
            >
              {(modelUnavailable || hasUnverified) && (
                <div className="flex shrink-0 flex-col gap-3 lg:sticky lg:top-0 lg:z-10 lg:-mx-6 lg:-mt-6 lg:bg-surface-elevated lg:px-6 lg:pb-3 lg:pt-6">
                  {modelUnavailable && (
                    <div className="flex shrink-0 items-center gap-3 rounded-xl border border-status-caution/20 bg-status-caution-subtle px-4 py-3">
                      <Settings className="w-5 h-5 text-status-caution shrink-0" />
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
                        className="gap-1.5 shrink-0"
                      >
                        <Settings className="w-3.5 h-3.5" />
                        Settings
                      </Button>
                    </div>
                  )}

                  {hasUnverified && (
                    <div className="flex shrink-0 items-center gap-3 rounded-xl border border-status-caution/20 bg-status-caution-subtle px-4 py-3">
                      <AlertCircle className="w-5 h-5 text-status-caution shrink-0" />
                      <p className="text-xs text-ink-secondary">
                        Some values are still unverified. Answers stay grounded, but confirm key numbers in Verify for highest confidence.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {messages.length === 0 && (
                <div className="flex flex-1 flex-col items-center justify-center text-center">
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

              {messages.map((message) => {
                const rowClass = cn('flex shrink-0', message.role === 'user' ? 'justify-end' : 'justify-start');
                // M6: the patient's own message rises 6 px and fades in from .35 (opacity only under reduced motion).
                // An assistant message holds T0 values and citations, so it renders with no motion at all. A message
                // restored from history is not new, so it does not replay M6 either.
                const restored = message.id.startsWith('restored-');
                return message.role === 'user' ? (
                  <m.div
                    key={message.id}
                    data-testid="chat-message"
                    data-role={message.role}
                    initial={restored ? false : prefersReducedMotion ? { opacity: 0.35 } : { opacity: 0.35, y: 6 }}
                    animate={prefersReducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
                    transition={{ duration: prefersReducedMotion ? 0.12 : duration.md, ease: EASE_OUT }}
                    className={rowClass}
                  >
                    {renderBubble(message)}
                  </m.div>
                ) : (
                  <div key={message.id} data-testid="chat-message" data-role={message.role} className={rowClass}>
                    {renderBubble(message)}
                  </div>
                );
              })}

              {sendMessage.isPending && (
                <div className="flex shrink-0 justify-start">
                  <div className="bg-surface-muted rounded-2xl px-4 py-3">
                    <Pending>Reading your verified results…</Pending>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="shrink-0 border-t border-black/4 p-4">
            <div className="mb-3 flex items-center gap-2 max-lg:overflow-x-auto max-lg:pb-1 lg:flex-wrap">
              <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-ink-tertiary max-lg:sr-only">
                <History className="w-3 h-3" />
                Ask about your records
              </span>
              {RECORD_QUERY_CHIPS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => handleSend(question)}
                  disabled={sendMessage.isPending}
                  className={cn(
                    'shrink-0 px-3 py-1.5 rounded-full text-xs',
                    'bg-surface-muted hover:bg-accent-subtle hover:text-accent',
                    'transition-colors duration-200',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  {question}
                </button>
              ))}
            </div>
            <div className="flex gap-3">
              <input
                type="text"
                aria-label="Your question"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="Ask about your results..."
                className={cn(
                  'flex-1 px-4 py-3 rounded-xl',
                  'bg-surface-muted border-0',
                  'text-sm text-ink placeholder:text-ink-tertiary',
                  'focus:outline-hidden focus:ring-2 focus:ring-accent focus:ring-offset-2'
                )}
                disabled={sendMessage.isPending}
              />
              <Button
                onClick={() => handleSend()}
                aria-label="Send question"
                disabled={!input.trim() || sendMessage.isPending}
                className="px-4"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="shrink-0 border-t border-status-caution/20 bg-status-caution-subtle px-4 py-3 lg:px-6">
            <div className="flex gap-3">
              <AlertCircle className="w-4 h-4 text-status-caution shrink-0 mt-0.5" aria-hidden="true" />
              <p data-t0="" data-testid="ask-disclaimer" className="text-xs text-ink-secondary leading-relaxed">
                <span className="font-medium text-ink">Important. </span>
                This assistant provides information based on your documents
                and general medical references. It does not provide medical
                advice, diagnosis, or treatment recommendations. Always
                consult your healthcare provider.
              </p>
            </div>
          </div>
        </Card>
      </div>

      <div className="w-full space-y-4 lg:w-80 lg:shrink-0">
        {/* Filters */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Filter className="w-4 h-4 text-ink-secondary" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <fieldset className="min-w-0">
              <legend className="text-xs text-ink-secondary mb-1">Date Range</legend>
              <div className="flex flex-wrap gap-2">
                <div className="min-w-[8.5rem] flex-1">
                  <label htmlFor="ask-from-date" className="text-xs text-ink-secondary block mb-1">
                    From date
                  </label>
                  <input
                    id="ask-from-date"
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    className="w-full min-w-0 px-2 py-1.5 rounded-lg bg-surface-muted text-xs text-ink border border-black/6 focus:outline-hidden focus:ring-2 focus:ring-accent"
                  />
                </div>
                <div className="min-w-[8.5rem] flex-1">
                  <label htmlFor="ask-to-date" className="text-xs text-ink-secondary block mb-1">
                    To date
                  </label>
                  <input
                    id="ask-to-date"
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    className="w-full min-w-0 px-2 py-1.5 rounded-lg bg-surface-muted text-xs text-ink border border-black/6 focus:outline-hidden focus:ring-2 focus:ring-accent"
                  />
                </div>
              </div>
            </fieldset>
            <div>
              <label htmlFor="document-category-select" className="text-xs text-ink-secondary block mb-1">
                Document Category
              </label>
              <select
                id="document-category-select"
                value={selectedDocumentCategory}
                onChange={(e) => setSelectedDocumentCategory(e.target.value as DocumentCategoryFilterValue)}
                className="w-full px-2 py-1.5 rounded-lg bg-surface-muted text-xs text-ink border border-black/6 focus:outline-hidden focus:ring-2 focus:ring-accent"
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
                className="w-full px-2 py-1.5 rounded-lg bg-surface-muted text-xs text-ink border border-black/6 focus:outline-hidden focus:ring-2 focus:ring-accent"
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
      </div>
    </div>
  );
}
