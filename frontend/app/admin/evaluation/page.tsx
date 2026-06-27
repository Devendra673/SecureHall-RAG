'use client';

import { useState, useEffect, useCallback } from 'react';
import { ApiService, EvaluationMetricEntry } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  ArrowLeft, 
  RotateCw, 
  Settings, 
  Sparkles, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  TrendingUp, 
  History, 
  Play, 
  ChevronDown, 
  ChevronUp, 
  BarChart4 
} from 'lucide-react';
import { toast } from 'sonner';

/* ─── Circular Progress Indicator ─── */
function CircularProgress({ value, label, theme = 'default' }: { value: number | null | undefined; label: string; theme?: 'default' | 'purple' }) {
  const percent = value !== null && value !== undefined ? Math.round(value * 100) : null;
  const radius = 36;
  const stroke = 8;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = percent !== null ? circumference - (percent / 100) * circumference : circumference;

  let color = 'stroke-rose-500';
  let bgColor = 'bg-rose-500/5 border-rose-500/20';
  let textColor = 'text-rose-600 dark:text-rose-400';
  
  if (percent !== null) {
    if (theme === 'purple') {
      color = 'stroke-purple-500';
      bgColor = 'bg-purple-500/5 border-purple-500/20';
      textColor = 'text-purple-600 dark:text-purple-400';
    } else {
      if (percent >= 80) {
        color = 'stroke-emerald-500';
        bgColor = 'bg-emerald-500/5 border-emerald-500/20';
        textColor = 'text-emerald-600 dark:text-emerald-400';
      } else if (percent >= 50) {
        color = 'stroke-amber-500';
        bgColor = 'bg-amber-500/5 border-amber-500/20';
        textColor = 'text-amber-600 dark:text-amber-400';
      }
    }
  }

  return (
    <div className={`flex items-center justify-between p-6 rounded-2xl border glass-panel ${bgColor} transition-all duration-300 hover:-translate-y-0.5`}>
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</p>
        <p className="text-3xl font-extrabold mt-1 text-foreground">
          {percent !== null ? `${percent}%` : 'N/A'}
        </p>
      </div>
      <div className="relative w-20 h-20">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="40"
            cy="40"
            r={radius}
            className="stroke-muted/20 fill-none"
            strokeWidth={stroke}
          />
          {percent !== null && (
            <circle
              cx="40"
              cy="40"
              r={radius}
              className={`fill-none transition-all duration-1000 ease-out ${color}`}
              strokeWidth={stroke}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-bold text-sm text-foreground">
          {percent !== null ? `${(percent / 100).toFixed(2)}` : '-'}
        </div>
      </div>
    </div>
  );
}

/* ─── Custom SVG Line Chart ─── */
function SvgLineChart({ data }: { data: EvaluationMetricEntry[] }) {
  if (data.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
        No trend data available. Run evaluations to populate the chart.
      </div>
    );
  }

  // Take up to last 15 points, sorted chronologically
  const chartData = [...data]
    .slice(0, 15)
    .reverse();

  const width = 800;
  const height = 250;
  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 40;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  const pointsCount = chartData.length;
  const getX = (index: number) => {
    if (pointsCount <= 1) return paddingLeft + chartWidth / 2;
    return paddingLeft + (index / (pointsCount - 1)) * chartWidth;
  };

  const getY = (val: number | null | undefined) => {
    const numericVal = val !== null && val !== undefined ? val : 0;
    return paddingTop + chartHeight - numericVal * chartHeight;
  };

  // Helper to build SVG path
  const buildPath = (getField: (item: EvaluationMetricEntry) => number | null | undefined) => {
    return chartData.map((item, idx) => {
      const val = getField(item);
      const x = getX(idx);
      const y = getY(val);
      return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  };

  const pathFaithfulness = buildPath(item => item.faithfulness_score);
  const pathRelevance = buildPath(item => item.answer_relevance_score);
  const pathRecall = buildPath(item => item.context_recall_score);
  const pathNli = buildPath(item => item.nli_faithfulness_score);

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto min-w-[600px]">
        {/* Y Axis Gridlines */}
        {[0, 0.25, 0.5, 0.75, 1.0].map((tick) => {
          const y = getY(tick);
          return (
            <g key={tick} className="opacity-40">
              <line
                x1={paddingLeft}
                y1={y}
                x2={width - paddingRight}
                y2={y}
                className="stroke-muted/30 stroke-1 stroke-dasharray-[4,4]"
              />
              <text
                x={paddingLeft - 8}
                y={y + 4}
                className="fill-muted-foreground text-[10px] text-right font-medium"
                textAnchor="end"
              >
                {tick.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* X Axis Labels */}
        {chartData.map((item, idx) => {
          const x = getX(idx);
          const date = new Date(item.evaluated_at);
          const label = `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
          return (
            <text
              key={item.id}
              x={x}
              y={height - 15}
              className="fill-muted-foreground text-[9px] font-medium"
              textAnchor="middle"
              transform={`rotate(-15, ${x}, ${height - 15})`}
            >
              {label}
            </text>
          );
        })}

        {/* Render Lines */}
        {pathFaithfulness && (
          <path
            d={pathFaithfulness}
            fill="none"
            className="stroke-emerald-500 stroke-[3px] transition-all duration-500"
          />
        )}
        {pathNli && (
          <path
            d={pathNli}
            fill="none"
            className="stroke-purple-500 stroke-[3px] transition-all duration-500"
          />
        )}
        {pathRelevance && (
          <path
            d={pathRelevance}
            fill="none"
            className="stroke-blue-500 stroke-[3px] transition-all duration-500"
          />
        )}
        {pathRecall && (
          <path
            d={pathRecall}
            fill="none"
            className="stroke-amber-500 stroke-[3px] transition-all duration-500"
          />
        )}

        {/* Render Dots */}
        {chartData.map((item, idx) => {
          const x = getX(idx);
          return (
            <g key={`dots-${item.id}`}>
              {item.faithfulness_score !== null && item.faithfulness_score !== undefined && (
                <circle
                  cx={x}
                  cy={getY(item.faithfulness_score)}
                  r="4"
                  className="fill-emerald-500 stroke-background stroke-2 hover:r-6 cursor-pointer transition-all"
                />
              )}
              {item.nli_faithfulness_score !== null && item.nli_faithfulness_score !== undefined && (
                <circle
                  cx={x}
                  cy={getY(item.nli_faithfulness_score)}
                  r="4"
                  className="fill-purple-500 stroke-background stroke-2 hover:r-6 cursor-pointer transition-all"
                />
              )}
              {item.answer_relevance_score !== null && item.answer_relevance_score !== undefined && (
                <circle
                  cx={x}
                  cy={getY(item.answer_relevance_score)}
                  r="4"
                  className="fill-blue-500 stroke-background stroke-2 hover:r-6 cursor-pointer transition-all"
                />
              )}
              {item.context_recall_score !== null && item.context_recall_score !== undefined && (
                <circle
                  cx={x}
                  cy={getY(item.context_recall_score)}
                  r="4"
                  className="fill-amber-500 stroke-background stroke-2 hover:r-6 cursor-pointer transition-all"
                />
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function EvaluationDashboard() {
  const { user } = useAuthStore();
  const router = useRouter();

  // Route security
  useEffect(() => {
    if (user && user.role !== 'admin' && user.role !== 'hr') {
      router.replace('/');
    }
  }, [user, router]);

  const [history, setHistory] = useState<EvaluationMetricEntry[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Single runner state
  const [query, setQuery] = useState('');
  const [groundTruth, setGroundTruth] = useState('');
  const [testing, setTesting] = useState(false);

  // Expanded log item ID
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Averages
  const [avgFaithfulness, setAvgFaithfulness] = useState<number | null>(null);
  const [avgNliFaithfulness, setAvgNliFaithfulness] = useState<number | null>(null);
  const [avgRelevance, setAvgRelevance] = useState<number | null>(null);
  const [avgRecall, setAvgRecall] = useState<number | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await ApiService.getEvaluationHistory();
      setHistory(data);

      // Compute averages
      if (data.length > 0) {
        let fSum = 0, fCount = 0;
        let rSum = 0, rCount = 0;
        let recSum = 0, recCount = 0;
        let nliSum = 0, nliCount = 0;

        data.forEach(item => {
          if (item.faithfulness_score !== null && item.faithfulness_score !== undefined) {
            fSum += item.faithfulness_score;
            fCount++;
          }
          if (item.nli_faithfulness_score !== null && item.nli_faithfulness_score !== undefined) {
            nliSum += item.nli_faithfulness_score;
            nliCount++;
          }
          if (item.answer_relevance_score !== null && item.answer_relevance_score !== undefined) {
            rSum += item.answer_relevance_score;
            rCount++;
          }
          if (item.context_recall_score !== null && item.context_recall_score !== undefined) {
            recSum += item.context_recall_score;
            recCount++;
          }
        });

        setAvgFaithfulness(fCount > 0 ? fSum / fCount : null);
        setAvgNliFaithfulness(nliCount > 0 ? nliSum / nliCount : null);
        setAvgRelevance(rCount > 0 ? rSum / rCount : null);
        setAvgRecall(recCount > 0 ? recSum / recCount : null);
      }
    } catch (e) {
      toast.error('Failed to load evaluation history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleRunEvaluation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      toast.error('Query cannot be empty');
      return;
    }

    setTesting(true);
    const toastId = toast.loading('Querying pipeline and scoring response...');
    try {
      // First, get the answer from the standard query API
      const response = await ApiService.submitQuery({
        query: query,
      });

      const context_text = response.citations
        ? response.citations.map((c) => c.text_excerpt).join('\n\n')
        : '';

      // Run evaluation
      const evalResult = await ApiService.runEvaluation({
        query,
        answer: response.answer,
        context: context_text,
        ground_truth: groundTruth,
      });

      toast.success('Evaluation completed!', { id: toastId });
      setQuery('');
      setGroundTruth('');
      fetchHistory();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Evaluation failed', { id: toastId });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-muted/30 to-background p-4 sm:p-8">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href="/admin">
            <Button variant="ghost" size="icon" className="rounded-xl">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent flex items-center gap-2">
              <BarChart4 className="w-8 h-8 text-violet-500" />
              RAGAS Evaluation Dashboard
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Verify faithfulness, answer relevance, and recall metrics using LLM assistance.
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchHistory}
          disabled={loading}
          className="rounded-xl border-muted/50 font-medium hover:bg-muted"
        >
          <RotateCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh Metrics
        </Button>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: Overview & Manual Runner */}
        <div className="lg:col-span-1 flex flex-col gap-8">
          
          {/* Summary Stats */}
          <section className="flex flex-col gap-4">
            <h2 className="text-lg font-bold tracking-tight text-foreground/90 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-violet-400" />
              Quality Overview
            </h2>
            <div className="grid grid-cols-1 gap-4">
              <CircularProgress value={avgFaithfulness} label="Faithfulness (LLM)" />
              <CircularProgress value={avgNliFaithfulness} label="NLI Faithfulness (Model)" theme="purple" />
              <CircularProgress value={avgRelevance} label="Answer Relevance" />
              <CircularProgress value={avgRecall} label="Context Recall" />
            </div>
          </section>

          {/* Test Runner Form */}
          <section className="glass-panel border bg-card p-6 rounded-2xl">
            <h2 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2 mb-4">
              <Play className="w-5 h-5 text-violet-500 fill-violet-500" />
              Evaluate New Query
            </h2>
            <form onSubmit={handleRunEvaluation} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5">
                  Query / Question
                </label>
                <Input
                  placeholder="Enter evaluation query..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={testing}
                  className="rounded-xl border-muted/50 bg-background/50 focus:bg-background"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5 flex items-center justify-between">
                  <span>Ground Truth (Optional)</span>
                  <span className="text-[10px] lowercase text-muted-foreground/60">Needed for recall</span>
                </label>
                <textarea
                  placeholder="Reference answer for Context Recall calculation..."
                  value={groundTruth}
                  onChange={(e) => setGroundTruth(e.target.value)}
                  disabled={testing}
                  rows={3}
                  className="w-full rounded-xl border border-muted/50 bg-background/50 p-3 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-input focus:bg-background transition-all"
                />
              </div>
              <Button
                type="submit"
                disabled={testing}
                className="w-full rounded-xl bg-violet-600 hover:bg-violet-700 text-white font-semibold py-2.5"
              >
                {testing ? 'Evaluating...' : 'Run Evaluation'}
              </Button>
            </form>
          </section>
        </div>

        {/* Right Side: Charts & Logs */}
        <div className="lg:col-span-2 flex flex-col gap-8">
          
          {/* Trend Chart */}
          <section className="glass-panel border bg-card p-6 rounded-2xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-violet-500" />
                Historical Trend (Last 15 Runs)
              </h2>
              {/* Legend */}
              <div className="flex items-center gap-4 text-xs font-medium">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                  <span className="text-muted-foreground">Faithfulness (LLM)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-purple-500" />
                  <span className="text-muted-foreground">Faithfulness (NLI)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-muted-foreground">Relevance</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-amber-500" />
                  <span className="text-muted-foreground">Recall</span>
                </div>
              </div>
            </div>
            <div className="h-64 flex items-center justify-center bg-background/30 rounded-xl p-4 border border-muted/20">
              <SvgLineChart data={history} />
            </div>
          </section>

          {/* Historical Logs Table */}
          <section className="glass-panel border bg-card rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-muted/20 flex items-center gap-2">
              <History className="w-5 h-5 text-violet-500" />
              <h2 className="text-lg font-bold tracking-tight text-foreground">Evaluation Log</h2>
            </div>
            
            <div className="overflow-x-auto">
              {history.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground text-sm">
                  No evaluations recorded yet. Use the runner to execute your first test.
                </div>
              ) : (
                <table className="w-full text-sm text-left border-collapse">
                  <thead>
                    <tr className="bg-muted/30 border-b border-muted/20 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      <th className="px-6 py-4">Query</th>
                      <th className="px-4 py-4 text-center">Faithfulness (LLM/NLI)</th>
                      <th className="px-4 py-4 text-center">Relevance</th>
                      <th className="px-4 py-4 text-center">Recall</th>
                      <th className="px-6 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item) => {
                      const isExpanded = expandedId === item.id;
                      return (
                        <g key={item.id}>
                          <tr className={`border-b border-muted/10 hover:bg-muted/10 transition-colors ${isExpanded ? 'bg-muted/10' : ''}`}>
                            <td className="px-6 py-4 font-medium max-w-xs truncate text-foreground">
                              {item.query}
                            </td>
                            <td className="px-4 py-4 text-center font-bold">
                              <div className="flex flex-col items-center">
                                {item.faithfulness_score !== null && item.faithfulness_score !== undefined ? (
                                  <span className={item.faithfulness_score >= 0.8 ? 'text-emerald-500' : item.faithfulness_score >= 0.5 ? 'text-amber-500' : 'text-rose-500'}>
                                    {item.faithfulness_score.toFixed(2)}
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground">-</span>
                                )}
                                {item.nli_faithfulness_score !== null && item.nli_faithfulness_score !== undefined ? (
                                  <span className="text-purple-500 text-xs font-semibold">
                                    NLI: {item.nli_faithfulness_score.toFixed(2)}
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground/40 text-xs">NLI: -</span>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-4 text-center font-bold">
                              {item.answer_relevance_score !== null && item.answer_relevance_score !== undefined ? (
                                <span className={item.answer_relevance_score >= 0.8 ? 'text-emerald-500' : item.answer_relevance_score >= 0.5 ? 'text-amber-500' : 'text-rose-500'}>
                                  {item.answer_relevance_score.toFixed(2)}
                                </span>
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </td>
                            <td className="px-4 py-4 text-center font-bold">
                              {item.context_recall_score !== null && item.context_recall_score !== undefined ? (
                                <span className={item.context_recall_score >= 0.8 ? 'text-emerald-500' : item.context_recall_score >= 0.5 ? 'text-amber-500' : 'text-rose-500'}>
                                  {item.context_recall_score.toFixed(2)}
                                </span>
                              ) : (
                                <span className="text-muted-foreground/40">N/A</span>
                              )}
                            </td>
                            <td className="px-6 py-4 text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setExpandedId(isExpanded ? null : item.id)}
                                className="rounded-xl text-muted-foreground hover:text-foreground"
                              >
                                {isExpanded ? (
                                  <>
                                    <span className="mr-1">Hide</span>
                                    <ChevronUp className="w-4 h-4" />
                                  </>
                                ) : (
                                  <>
                                    <span className="mr-1">Details</span>
                                    <ChevronDown className="w-4 h-4" />
                                  </>
                                )}
                              </Button>
                            </td>
                          </tr>

                          {/* Expandable row */}
                          {isExpanded && (
                            <tr>
                              <td colSpan={5} className="px-6 py-4 bg-muted/5 border-b border-muted/20">
                                <div className="flex flex-col gap-4 text-xs">
                                  <div>
                                    <h4 className="font-bold text-muted-foreground uppercase tracking-wider mb-1">Generated Answer</h4>
                                    <p className="bg-background/50 border border-muted/10 rounded-xl p-3 text-foreground whitespace-pre-wrap">
                                      {item.answer}
                                    </p>
                                  </div>
                                  <div>
                                    <h4 className="font-bold text-muted-foreground uppercase tracking-wider mb-1">Context Chunks</h4>
                                    <p className="bg-background/50 border border-muted/10 rounded-xl p-3 text-muted-foreground whitespace-pre-wrap max-h-48 overflow-y-auto">
                                      {item.context}
                                    </p>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </g>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
