<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  history: { type: Array, default: () => [] },
});

const chartWidth = 720;
const chartHeight = 270;
const padding = { top: 28, right: 30, bottom: 48, left: 54 };
const selectedMetric = ref("favorable_rate");
const selectedRunId = ref("");
const referenceRunId = ref("");
const runs = computed(() => props.history.filter((run) => Number(run.quantidade_riscos) > 0));
const selectedRun = computed(() =>
  runs.value.find((run) => String(run.id) === String(selectedRunId.value)) ?? runs.value.at(-1) ?? null,
);
const referenceRun = computed(() =>
  runs.value.find((run) => String(run.id) === String(referenceRunId.value))
  ?? (runs.value.length > 1 ? runs.value.at(-2) : null),
);
const metrics = [
  { value: "risk_count", label: "Quantidade de riscos avaliados", suffix: " riscos" },
  { value: "favorable_rate", label: "Percentual de riscos favoráveis", suffix: "%" },
  { value: "unfavorable_rate", label: "Percentual de riscos não favoráveis", suffix: "%" },
  { value: "average_score", label: "Nota média dos quatro Ps", suffix: "/25" },
  { value: "Pessoas", label: "Nota média · Pessoas", suffix: "/25" },
  { value: "Processos", label: "Nota média · Processos", suffix: "/25" },
  { value: "Produtos", label: "Nota média · Produtos", suffix: "/25" },
  { value: "Políticas governamentais", label: "Nota média · Políticas", suffix: "/25" },
];
const selectedMetricInfo = computed(() =>
  metrics.find((metric) => metric.value === selectedMetric.value) ?? metrics[0],
);

function getDimension(run, dimensionName) {
  return run?.dimensoes?.find((dimension) => dimension.dimension === dimensionName);
}

function getAverageScore(run) {
  const dimensions = run?.dimensoes ?? [];
  const totalCount = dimensions.reduce((total, item) => total + (Number(item.risk_count) || 0), 0);
  if (!totalCount) return null;
  const totalScore = dimensions.reduce(
    (total, item) => total + (Number(item.average_score) || 0) * (Number(item.risk_count) || 0),
    0,
  );
  return totalScore / totalCount;
}

function metricValue(run, metric) {
  if (!run) return null;
  const riskCount = Number(run.quantidade_riscos) || 0;
  if (metric === "risk_count") return riskCount;
  if (metric === "favorable_rate") {
    return riskCount ? Number(run.riscos_favoraveis || 0) / riskCount * 100 : null;
  }
  if (metric === "unfavorable_rate") {
    return riskCount ? Number(run.riscos_nao_favoraveis || 0) / riskCount * 100 : null;
  }
  if (metric === "average_score") return getAverageScore(run);
  const average = getDimension(run, metric)?.average_score;
  return average === undefined ? null : Number(average);
}

function formatValue(value, digits = 1) {
  if (value === null || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: Number.isInteger(value) ? 0 : digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatDate(value, includeTime = false) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", includeTime
    ? { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "2-digit", month: "short" }).format(date);
}

function runLabel(run) {
  return `Análise ${run.id} · ${formatDate(run.analyzed_at, true)}`;
}

function scoreDelta(current, baseline, metric) {
  const currentValue = metricValue(current, metric);
  const baselineValue = metricValue(baseline, metric);
  return currentValue === null || baselineValue === null ? null : currentValue - baselineValue;
}

function countDelta(current, baseline) {
  if (!current || !baseline) return null;
  return Number(current.quantidade_riscos) - Number(baseline.quantidade_riscos);
}

function deltaLabel(delta, suffix = "") {
  if (delta === null) return "Sem dados para comparar";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${formatValue(delta)}${suffix}`;
}

function deltaTone(delta, lowerIsBetter = false) {
  if (delta === null || delta === 0) return "neutral";
  return (delta < 0) === lowerIsBetter ? "improved" : "worsened";
}

const chart = computed(() => {
  const validRuns = runs.value.filter((run) => metricValue(run, selectedMetric.value) !== null);
  if (!validRuns.length) return null;

  const values = validRuns.map((run) => metricValue(run, selectedMetric.value));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = Math.max(maxValue - minValue, selectedMetric.value.includes("rate") ? 10 : 2);
  const chartTop = padding.top;
  const chartBottom = chartHeight - padding.bottom;
  const chartLeft = padding.left;
  const chartRight = chartWidth - padding.right;
  const xFor = (index) => validRuns.length < 2
    ? (chartLeft + chartRight) / 2
    : chartLeft + index / (validRuns.length - 1) * (chartRight - chartLeft);
  const yFor = (value) => chartBottom - (value - (minValue - range * 0.1)) / (range * 1.2) * (chartBottom - chartTop);
  const points = validRuns.map((run, index) => ({
    id: run.id,
    x: xFor(index),
    y: yFor(values[index]),
    value: values[index],
    label: formatDate(run.analyzed_at),
    current: String(run.id) === String(selectedRun.value?.id),
    baseline: String(run.id) === String(referenceRun.value?.id),
  }));
  const labels = validRuns
    .map((run, index) => ({ id: run.id, x: xFor(index), label: formatDate(run.analyzed_at) }))
    .filter((_, index) =>
      validRuns.length <= 6
      || index % Math.ceil(validRuns.length / 5) === 0
      || index === validRuns.length - 1);
  const ticks = [0, 0.5, 1].map((fraction) => {
    const value = minValue - range * 0.1 + range * 1.2 * fraction;
    return { y: chartBottom - fraction * (chartBottom - chartTop), label: formatValue(value) };
  });

  return {
    points,
    line: points.map((point) => `${point.x},${point.y}`).join(" "),
    labels,
    ticks,
    chartBottom,
  };
});

const dimensionComparison = computed(() => ["Pessoas", "Processos", "Produtos", "Políticas governamentais"]
  .map((dimension) => {
    const current = Number(getDimension(selectedRun.value, dimension)?.average_score);
    const baseline = Number(getDimension(referenceRun.value, dimension)?.average_score);
    return {
      dimension,
      current: Number.isFinite(current) ? current : null,
      baseline: Number.isFinite(baseline) ? baseline : null,
      delta: Number.isFinite(current) && Number.isFinite(baseline) ? current - baseline : null,
    };
  }));

function selectLatestRun() {
  if (runs.value.length && !runs.value.some((run) => String(run.id) === String(selectedRunId.value))) {
    selectedRunId.value = String(runs.value.at(-1).id);
  }
  if (runs.value.length > 1 && !runs.value.some((run) => String(run.id) === String(referenceRunId.value))) {
    referenceRunId.value = String(runs.value.at(-2).id);
  }
}

selectLatestRun();
</script>

<template>
  <div class="history-dashboard">
    <article class="panel benchmark-panel">
      <div class="panel-heading history-heading">
        <div>
          <p class="eyebrow">BENCHMARK DO PAINEL</p>
          <h2>Compare análises anteriores</h2>
        </div>
        <span class="history-count">{{ runs.length }} análises com dados 4Ps</span>
      </div>

      <div v-if="runs.length" class="benchmark-controls">
        <label>
          <span>Análise em foco</span>
          <select v-model="selectedRunId" @change="selectLatestRun">
            <option v-for="run in runs" :key="run.id" :value="String(run.id)">{{ runLabel(run) }}</option>
          </select>
        </label>
        <label>
          <span>Comparar com</span>
          <select v-model="referenceRunId">
            <option v-for="run in runs" :key="run.id" :value="String(run.id)">{{ runLabel(run) }}</option>
          </select>
        </label>
      </div>

      <template v-if="runs.length">
        <div v-if="referenceRun && selectedRun?.id !== referenceRun.id" class="benchmark-summary">
          <div class="benchmark-metric">
            <span>Riscos avaliados</span>
            <strong>{{ selectedRun.quantidade_riscos }}</strong>
              <small class="neutral">
                {{ deltaLabel(countDelta(selectedRun, referenceRun)) }}
              vs. {{ runLabel(referenceRun) }}
            </small>
          </div>
          <div class="benchmark-metric">
            <span>Riscos favoráveis</span>
            <strong>{{ formatValue(metricValue(selectedRun, "favorable_rate")) }}%</strong>
            <small :class="deltaTone(scoreDelta(selectedRun, referenceRun, 'favorable_rate'))">
              {{ deltaLabel(scoreDelta(selectedRun, referenceRun, "favorable_rate"), " p.p.") }} em favoráveis
            </small>
          </div>
          <div class="benchmark-metric">
            <span>Nota média 4Ps</span>
            <strong>{{ formatValue(metricValue(selectedRun, "average_score")) }}/25</strong>
            <small :class="deltaTone(scoreDelta(selectedRun, referenceRun, 'average_score'))">
              {{ deltaLabel(scoreDelta(selectedRun, referenceRun, "average_score")) }} pontos · menor é melhor
            </small>
          </div>
        </div>
        <p v-else class="benchmark-hint">
          Selecione duas análises diferentes para comparar a evolução dos indicadores.
        </p>

        <div class="dimension-benchmark">
          <div class="subheading">
            <div><p class="eyebrow">COMPARAÇÃO POR DIMENSÃO</p><h3>Nota média de cada P</h3></div>
            <span v-if="referenceRun && selectedRun?.id !== referenceRun.id">
              {{ formatDate(referenceRun.analyzed_at, true) }} → {{ formatDate(selectedRun?.analyzed_at, true) }}
            </span>
          </div>
          <div class="dimension-table" role="table" aria-label="Comparação de notas médias por dimensão">
            <div class="dimension-table-row dimension-table-head" role="row">
              <span role="columnheader">Dimensão</span><span role="columnheader">Referência</span>
              <span role="columnheader">Foco</span><span role="columnheader">Variação</span>
            </div>
            <div v-for="item in dimensionComparison" :key="item.dimension" class="dimension-table-row" role="row">
              <strong role="cell">{{ item.dimension }}</strong>
              <span role="cell">{{ formatValue(item.baseline) }}/25</span>
              <span role="cell">{{ formatValue(item.current) }}/25</span>
              <b role="cell" :class="deltaTone(item.delta)">
                {{ deltaLabel(item.delta) }}
              </b>
            </div>
          </div>
          <p class="benchmark-hint">Nas notas médias, uma variação negativa indica redução da exposição avaliada; revise mudanças no cadastro antes de concluir que houve melhora.</p>
        </div>
      </template>
      <div v-else class="history-empty">
        <strong>{{ history.length ? "O histórico existente não contém notas dos quatro P’s." : "Ainda não há análises registradas." }}</strong>
        <span>Execute novas análises para começar a comparar a evolução dos riscos.</span>
      </div>
    </article>

    <article class="panel history-panel">
      <div class="panel-heading history-heading">
        <div><p class="eyebrow">EVOLUÇÃO DAS AVALIAÇÕES</p><h2>Gráfico histórico variável</h2></div>
        <label class="metric-select">
          <span>Indicador</span>
          <select v-model="selectedMetric" :disabled="!runs.length">
            <option v-for="metric in metrics" :key="metric.value" :value="metric.value">{{ metric.label }}</option>
          </select>
        </label>
      </div>
      <div v-if="chart" class="history-chart">
        <div class="chart-caption">
          <span>{{ selectedMetricInfo.label }}</span>
          <strong>{{ chart.points.length }} análises · unidade {{ selectedMetricInfo.suffix }}</strong>
        </div>
        <svg viewBox="0 0 720 270" role="img" :aria-label="`Evolução histórica: ${selectedMetricInfo.label}`">
          <g v-for="tick in chart.ticks" :key="tick.y">
            <line :x1="padding.left" :x2="chartWidth - padding.right" :y1="tick.y" :y2="tick.y" class="grid-line" />
            <text :x="padding.left - 10" :y="tick.y + 4" text-anchor="end" class="axis-text">{{ tick.label }}</text>
          </g>
          <polyline v-if="chart.points.length > 1" :points="chart.line" class="history-line" />
          <g v-for="point in chart.points" :key="point.id">
            <circle
              :cx="point.x"
              :cy="point.y"
              :r="point.current || point.baseline ? 6 : 4"
              :class="{ 'selected-point': point.current, 'baseline-point': point.baseline && !point.current }"
              class="history-point"
            >
              <title>{{ point.label }} · {{ formatValue(point.value) }}{{ selectedMetricInfo.suffix }}</title>
            </circle>
          </g>
          <g v-for="point in chart.labels" :key="`date-${point.id}`">
            <text :x="point.x" y="244" text-anchor="middle" class="axis-text">{{ point.label }}</text>
          </g>
        </svg>
        <div class="chart-legend">
          <span><i class="selected-key"></i>Análise em foco</span>
          <span><i class="baseline-key"></i>Referência</span>
          <span>Menor nota média é melhor; maior percentual favorável é melhor.</span>
        </div>
      </div>
      <div v-else class="history-empty">
        <strong>Sem dados para montar o gráfico.</strong>
        <span>Execute uma análise 4Ps para iniciar a série histórica.</span>
      </div>
    </article>
  </div>
</template>

<style scoped>
.history-dashboard { display: grid; gap: 14px; }
.benchmark-panel, .history-panel { padding: 20px; }
.history-heading { align-items: center; }
.history-heading .eyebrow, .subheading .eyebrow { margin: 0 0 6px; color: #b16d51; font-size: 8px; }
.history-heading h2, .subheading h3 { margin: 0; color: #29493b; font-size: 15px; }
.history-count { padding: 5px 8px; border-radius: 4px; color: #73877c; background: #f1f5f0; font-size: 9px; }
.benchmark-controls { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 17px; }
.benchmark-controls label, .metric-select { display: grid; gap: 5px; color: #65776c; font-size: 9px; }
.benchmark-controls select, .metric-select select { width: 100%; min-width: 0; height: 34px; padding: 0 8px; border: 1px solid #e2e8e0; border-radius: 4px; color: #385348; background: white; font-size: 9px; }
.benchmark-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }
.benchmark-metric { display: grid; gap: 5px; padding: 12px; border: 1px solid #edf0eb; border-radius: 5px; background: #fcfdfa; }
.benchmark-metric > span { color: #87948c; font-size: 8px; }
.benchmark-metric > strong { color: #29493b; font-size: 19px; }
.benchmark-metric > small { color: #76847a; font-size: 8px; line-height: 1.45; }
.improved { color: #43836c !important; }
.worsened { color: #ad533f !important; }
.neutral { color: #76847a !important; }
.benchmark-hint { margin: 10px 0 0; color: #849188; font-size: 8px; line-height: 1.5; }
.dimension-benchmark { margin-top: 18px; padding-top: 15px; border-top: 1px solid #edf0eb; }
.subheading { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
.subheading h3 { font-size: 12px; }
.subheading > span { color: #929e96; font-size: 8px; text-align: right; }
.dimension-table { display: grid; }
.dimension-table-row { display: grid; grid-template-columns: minmax(150px, 1.5fr) repeat(3, minmax(72px, .7fr)); gap: 8px; align-items: center; padding: 9px 7px; border-bottom: 1px solid #f0f2ee; color: #76847a; font-size: 9px; }
.dimension-table-row > :not(:first-child) { text-align: right; }
.dimension-table-row strong { color: #52685c; font-weight: 600; }
.dimension-table-head { color: #9ba49d; font-size: 8px; }
.dimension-table-head > span { font-weight: 600; }
.metric-select { width: min(100%, 270px); }
.chart-caption { display: flex; justify-content: space-between; gap: 10px; margin-top: 12px; color: #536e5e; font-size: 9px; }
.chart-caption strong { color: #929e96; font-size: 8px; font-weight: 400; }
.history-chart svg { display: block; width: 100%; overflow: visible; }
.grid-line { stroke: #e9ede7; stroke-width: 1; }
.axis-text { fill: #89968e; font-size: 10px; }
.history-line { fill: none; stroke: #43836c; stroke-linecap: round; stroke-linejoin: round; stroke-width: 3; }
.history-point { fill: #77a88a; stroke: #fff; stroke-width: 2; }
.history-point.selected-point { fill: #174b40; stroke: #d3e6d9; stroke-width: 3; }
.history-point.baseline-point { fill: #e47756; stroke: #fff; stroke-width: 2; }
.chart-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 4px; color: #76877c; font-size: 8px; }
.chart-legend span { display: inline-flex; align-items: center; gap: 5px; }
.chart-legend i { width: 8px; height: 8px; border-radius: 50%; }
.selected-key { background: #174b40; }
.baseline-key { background: #e47756; }
.history-empty { display: grid; gap: 7px; padding: 42px 16px; color: #87948c; text-align: center; }
.history-empty strong { color: #52685c; font-size: 11px; }
.history-empty span { font-size: 9px; line-height: 1.5; }
@media (max-width: 700px) {
  .benchmark-panel, .history-panel { padding: 16px 13px; }
  .benchmark-controls, .benchmark-summary { grid-template-columns: 1fr; }
  .dimension-table-row { grid-template-columns: minmax(100px, 1.2fr) repeat(3, minmax(55px, .7fr)); gap: 4px; font-size: 8px; }
  .history-heading { align-items: flex-start; flex-direction: column; }
  .metric-select { width: 100%; }
}
</style>
