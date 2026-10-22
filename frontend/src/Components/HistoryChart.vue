<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  history: { type: Array, default: () => [] },
  reference: { type: Object, default: null },
  formatCurrency: { type: Function, required: true },
  formatPercent: { type: Function, required: true },
});

const metric = ref("residual_loss");
const selectedDimension = ref("total");
const dimensions = [
  { key: "total", label: "Total consolidado (4Ps)" },
  { key: "Pessoas", label: "Pessoas" },
  { key: "Processos", label: "Processos" },
  { key: "Produtos", label: "Produtos" },
  { key: "Políticas governamentais", label: "Políticas governamentais" },
];
const metrics = [
  { key: "residual_loss", label: "Perda residual", referenceKey: "residual_loss", kind: "currency" },
  { key: "p95_total", label: "P95 total", referenceKey: "p95_total", kind: "currency" },
  { key: "control_reduction", label: "Redução", referenceKey: "control_reduction", kind: "percent" },
];
const selectedMetric = computed(() => metrics.find((item) => item.key === metric.value) ?? metrics[0]);
const visibleRuns = computed(() => props.history
  .map((run) => ({
    run,
    value: historyValue(run),
  }))
  .filter((item) => item.value !== null));
const chartWidth = 720;
const chartHeight = 270;
const padding = { top: 28, right: 30, bottom: 48, left: 88 };

const chart = computed(() => {
  const values = visibleRuns.value.map((item) => Number(item.value));
  const benchmark = props.reference?.[selectedMetric.value.referenceKey];
  const hasBenchmark = selectedDimension.value === "total"
    && benchmark !== null
    && benchmark !== undefined
    && Number.isFinite(Number(benchmark));
  const allValues = [...values, ...(hasBenchmark ? [Number(benchmark)] : [])];
  const maxValue = Math.max(...allValues, 1);
  const chartTop = padding.top;
  const chartBottom = chartHeight - padding.bottom;
  const chartLeft = padding.left;
  const chartRight = chartWidth - padding.right;
  const xFor = (index) => visibleRuns.value.length < 2
    ? (chartLeft + chartRight) / 2
    : chartLeft + (index / (visibleRuns.value.length - 1)) * (chartRight - chartLeft);
  const yFor = (value) => chartBottom - (value / maxValue) * (chartBottom - chartTop);

  return {
    maxValue,
    points: visibleRuns.value.map(({ run, value }, index) => ({
      id: run.id,
      x: xFor(index),
      y: yFor(Number(value)),
      value: Number(value),
      label: formatDate(run.analyzed_at),
    })),
    line: visibleRuns.value.map(({ value }, index) =>
      `${xFor(index)},${yFor(Number(value))}`).join(" "),
    grid: [0, 0.5, 1].map((fraction) => ({
      y: chartBottom - fraction * (chartBottom - chartTop),
      value: maxValue * fraction,
    })),
    benchmarkY: hasBenchmark ? yFor(Number(benchmark)) : null,
    labelPoints: visibleRuns.value
      .map(({ run }, index) => ({
        id: run.id,
        x: xFor(index),
        label: formatDate(run.analyzed_at),
      }))
      .filter((_, index) =>
        visibleRuns.value.length <= 6
        || index % Math.ceil(visibleRuns.value.length / 5) === 0
        || index === visibleRuns.value.length - 1),
  };
});

function historyValue(run) {
  if (selectedDimension.value === "total") {
    return run[selectedMetric.value.key] ?? null;
  }
  const dimension = run.dimensions?.find(
    (item) => item.dimension === selectedDimension.value,
  );
  return dimension?.[selectedMetric.value.key] ?? null;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(date);
}

function formatValue(value) {
  return selectedMetric.value.kind === "percent"
    ? props.formatPercent(value)
    : props.formatCurrency(value);
}

</script>

<template>
  <article class="panel history-panel">
    <div class="panel-heading history-heading">
      <div><p class="eyebrow">EVOLUÇÃO DAS ANÁLISES</p><h2>Histórico da carteira</h2></div>
      <div class="history-filters">
        <select v-model="selectedDimension" aria-label="Dimensão do histórico">
          <option v-for="item in dimensions" :key="item.key" :value="item.key">{{ item.label }}</option>
        </select>
        <select v-model="metric" aria-label="Métrica do histórico">
          <option v-for="item in metrics" :key="item.key" :value="item.key">{{ item.label }}</option>
        </select>
      </div>
    </div>
    <div v-if="visibleRuns.length" class="history-chart">
      <div class="history-legend">
        <span><i class="history-line-key"></i>{{ selectedMetric.label }}</span>
        <span v-if="chart.benchmarkY !== null"><i class="benchmark-line-key"></i>{{ reference.name }}</span>
      </div>
      <svg viewBox="0 0 720 270" role="img" :aria-label="`Gráfico histórico de ${selectedMetric.label}`">
        <g v-for="tick in chart.grid" :key="tick.y">
          <line :x1="padding.left" :x2="chartWidth - padding.right" :y1="tick.y" :y2="tick.y" class="grid-line" />
          <text :x="padding.left - 10" :y="tick.y + 4" text-anchor="end" class="axis-text">{{ formatValue(tick.value) }}</text>
        </g>
        <line
          v-if="chart.benchmarkY !== null"
          :x1="padding.left"
          :x2="chartWidth - padding.right"
          :y1="chart.benchmarkY"
          :y2="chart.benchmarkY"
          class="benchmark-line"
        />
        <polyline v-if="chart.points.length > 1" :points="chart.line" class="history-line" />
        <g v-for="point in chart.points" :key="point.id">
          <circle :cx="point.x" :cy="point.y" r="4.5" class="history-point">
            <title>{{ point.label }} · {{ formatValue(point.value) }}</title>
          </circle>
        </g>
        <g v-for="point in chart.labelPoints" :key="`date-${point.id}`">
          <text :x="point.x" y="244" text-anchor="middle" class="axis-text">{{ point.label }}</text>
        </g>
        <text v-if="chart.benchmarkY !== null" :x="chartWidth - padding.right" :y="chart.benchmarkY - 7" text-anchor="end" class="benchmark-label">
          {{ formatValue(reference[selectedMetric.referenceKey]) }}
        </text>
      </svg>
    </div>
    <div v-else class="history-empty">
      <strong>{{ history.length ? "Não há histórico salvo para esta dimensão." : "Ainda não há análises anteriores." }}</strong>
      <span>{{ history.length ? "As execuções antigas não continham pontuações separadas por dimensão. Rode uma nova análise." : "Execute uma análise para iniciar o histórico. Cada execução ficará registrada para comparação." }}</span>
    </div>
    <footer class="history-footer">
      <span>{{ visibleRuns.length }} de 20 execuções com esta dimensão</span>
      <span v-if="history.length">Cada ponto representa uma execução salva.</span>
    </footer>
  </article>
</template>

<style scoped>
.history-panel { padding: 20px; }
.history-heading { align-items: center; }
.history-heading .eyebrow { margin: 0 0 6px; color: #b16d51; font-size: 8px; }
.history-heading h2 { margin: 0; color: #29493b; font-size: 15px; }
.history-filters { display: flex; gap: 6px; }
.history-heading select { max-width: 145px; height: 31px; padding: 0 8px; border: 1px solid #e5e9e2; border-radius: 5px; color: #65776c; background: white; font-size: 9px; }
.history-legend { display: flex; justify-content: flex-end; gap: 13px; min-height: 24px; margin-top: 8px; color: #76877c; font-size: 8px; }
.history-legend span { display: inline-flex; align-items: center; gap: 5px; }
.history-legend i { width: 14px; height: 3px; border-radius: 3px; background: #43836c; }
.history-legend i.benchmark-line-key { height: 0; border-top: 2px dashed #dc9166; background: transparent; }
.history-chart svg { display: block; width: 100%; overflow: visible; }
.grid-line { stroke: #e9ede7; stroke-width: 1; }
.axis-text { fill: #89968e; font-size: 10px; }
.history-line { fill: none; stroke: #43836c; stroke-linecap: round; stroke-linejoin: round; stroke-width: 3; }
.history-point { fill: #fff; stroke: #43836c; stroke-width: 3; }
.benchmark-line { stroke: #dc9166; stroke-dasharray: 7 5; stroke-width: 2; }
.benchmark-label { fill: #b16d51; font-size: 10px; font-weight: 700; }
.history-empty { display: grid; min-height: 185px; align-content: center; gap: 7px; color: #839087; text-align: center; }
.history-empty strong { color: #4e6959; font-size: 11px; }
.history-empty span { font-size: 9px; }
.history-footer { display: flex; justify-content: space-between; margin-top: 2px; color: #9ba49d; font-size: 8px; }
@media (max-width: 700px) {
  .history-panel { padding: 16px 12px; }
  .history-heading { align-items: flex-start; flex-direction: column; }
  .history-filters { width: 100%; }
  .history-heading select { max-width: none; flex: 1; }
  .axis-text { font-size: 9px; }
}
</style>
