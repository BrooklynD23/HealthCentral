import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  Filter,
  ExternalLink,
  Info,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const mockChartData = [
  { date: '2024-06', value: 13.8, refLow: 12.0, refHigh: 17.5 },
  { date: '2024-08', value: 14.1, refLow: 12.0, refHigh: 17.5 },
  { date: '2024-10', value: 13.5, refLow: 12.0, refHigh: 17.5 },
  { date: '2024-12', value: 14.2, refLow: 12.0, refHigh: 17.5 },
];

const panels = [
  { id: 'cbc', label: 'CBC', count: 8 },
  { id: 'cmp', label: 'CMP', count: 14 },
  { id: 'lipids', label: 'Lipids', count: 5 },
  { id: 'thyroid', label: 'Thyroid', count: 4 },
];

const analyteStats = [
  {
    name: 'Hemoglobin',
    current: '14.2',
    previous: '13.5',
    unit: 'g/dL',
    trend: 'up',
    status: 'normal',
  },
  {
    name: 'WBC Count',
    current: '11.8',
    previous: '10.2',
    unit: 'K/uL',
    trend: 'up',
    status: 'high',
  },
  {
    name: 'Platelets',
    current: '245',
    previous: '248',
    unit: 'K/uL',
    trend: 'stable',
    status: 'normal',
  },
  {
    name: 'RBC Count',
    current: '4.8',
    previous: '4.9',
    unit: 'M/uL',
    trend: 'down',
    status: 'normal',
  },
];

export function TrendsDashboard() {
  const prefersReducedMotion = useReducedMotion();
  const [activePanel, setActivePanel] = useState('cbc');
  const [selectedAnalyte, setSelectedAnalyte] = useState('Hemoglobin');

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4" />;
      case 'down':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return <Minus className="w-4 h-4" />;
    }
  };

  const getTrendColor = (trend: string, status: string) => {
    if (status === 'high' || status === 'low') return 'text-status-attention';
    if (trend === 'up') return 'text-status-verified';
    if (trend === 'down') return 'text-status-caution';
    return 'text-ink-secondary';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Trends Dashboard
          </h1>
          <p className="text-ink-secondary mt-1">
            Track changes in your test results over time
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" className="gap-2">
            <Calendar className="w-4 h-4" />
            Last 12 Months
          </Button>
          <Button variant="secondary" className="gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </Button>
        </div>
      </div>

      <div className="flex gap-2">
        {panels.map((panel) => (
          <button
            key={panel.id}
            onClick={() => setActivePanel(panel.id)}
            className={cn(
              'px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
              activePanel === panel.id
                ? 'bg-accent text-white shadow-soft'
                : 'bg-surface-elevated border border-black/[0.06] text-ink-secondary hover:bg-surface-muted'
            )}
          >
            {panel.label}
            <span
              className={cn(
                'ml-2 px-1.5 py-0.5 rounded text-xs',
                activePanel === panel.id
                  ? 'bg-white/20'
                  : 'bg-black/[0.06]'
              )}
            >
              {panel.count}
            </span>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span>{selectedAnalyte}</span>
                  <Badge variant="verified">Normal Range</Badge>
                </div>
                <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
                  <ExternalLink className="w-3.5 h-3.5" />
                  View Sources
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={mockChartData}
                    margin={{ top: 20, right: 20, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(0,0,0,0.06)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12, fill: '#6B6B6B' }}
                      tickLine={false}
                      axisLine={{ stroke: 'rgba(0,0,0,0.08)' }}
                    />
                    <YAxis
                      domain={[10, 20]}
                      tick={{ fontSize: 12, fill: '#6B6B6B' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid rgba(0,0,0,0.08)',
                        borderRadius: '12px',
                        boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
                      }}
                    />
                    <ReferenceLine
                      y={12.0}
                      stroke="#7BA387"
                      strokeDasharray="4 4"
                      strokeOpacity={0.6}
                    />
                    <ReferenceLine
                      y={17.5}
                      stroke="#7BA387"
                      strokeDasharray="4 4"
                      strokeOpacity={0.6}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#2D7D6F"
                      strokeWidth={2.5}
                      dot={{ fill: '#2D7D6F', strokeWidth: 0, r: 5 }}
                      activeDot={{ r: 7, fill: '#2D7D6F' }}
                      animationDuration={prefersReducedMotion ? 0 : 800}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-4 p-4 rounded-xl bg-surface-muted">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-ink-secondary flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-ink">
                      <strong>Latest value: 14.2 g/dL</strong> — Within the
                      reference range (12.0-17.5 g/dL per report).
                    </p>
                    <p className="text-sm text-ink-secondary mt-1">
                      Change from previous: +0.7 g/dL (5.2% increase)
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Analyte Summary</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-black/[0.04]">
                {analyteStats.map((stat, index) => (
                  <motion.button
                    key={stat.name}
                    initial={prefersReducedMotion ? {} : { opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => setSelectedAnalyte(stat.name)}
                    className={cn(
                      'w-full flex items-center justify-between p-4 text-left transition-colors',
                      'hover:bg-surface-muted/50 focus:outline-none focus:bg-accent-subtle',
                      selectedAnalyte === stat.name && 'bg-accent-subtle'
                    )}
                  >
                    <div>
                      <p className="font-medium text-ink text-sm">{stat.name}</p>
                      <p className="text-xs text-ink-secondary mt-0.5">
                        {stat.current} {stat.unit}
                      </p>
                    </div>
                    <div
                      className={cn(
                        'flex items-center gap-1',
                        getTrendColor(stat.trend, stat.status)
                      )}
                    >
                      {getTrendIcon(stat.trend)}
                      <span className="text-xs font-medium">
                        {stat.trend === 'up'
                          ? '+' + (parseFloat(stat.current) - parseFloat(stat.previous)).toFixed(1)
                          : stat.trend === 'down'
                          ? (parseFloat(stat.current) - parseFloat(stat.previous)).toFixed(1)
                          : '—'}
                      </span>
                    </div>
                  </motion.button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-accent-subtle border-accent/20">
            <CardContent className="p-4">
              <p className="text-sm text-ink font-medium mb-1">
                Need help understanding?
              </p>
              <p className="text-xs text-ink-secondary mb-3">
                Ask our assistant to explain any test result in plain language.
              </p>
              <Button size="sm" className="w-full">
                Open Explain
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
