<script setup>
import { computed } from "vue";

const props = defineProps({
  history: { type: Array, default: () => [] },
});

const chartWidth = 720;
const chartHeight = 270;
const padding = { top: 28, right: 30, bottom: 48, left: 54 };
const runs = computed(() => props.history.filter((run) => Number(run.quantidade_riscos) > 0));
const maxCount = computed(() => Math.max(
  ...runs.value.map((run) => Number(run.quantidade_riscos) || 0),
  1,
));
const chart = computed(() => {
  const chartTop = padding.top;
  const chartBottom = chartHeight - padding.bottom;
  const chartLeft = padding.left;
  const chartRight = chartWidth - padding.right;
  const xFor = (index) => runs.value.length < 2
    ? (chartLeft + chartRight) / 2
    : chartLeft + index / (runs.value.length - 1) * (chartRight - chartLeft);
  const yFor = (value) => chartBottom - value / maxCount.value * (chartBottom - chartTop);
  const series = (key) => runs.value.map((run, index) =>
    `${xFor(index)},${yFor(Number(run[key]) || 0)}`).join(" ");

  return {
    favorableLine: series("riscos_favoraveis"),
    unfavorableLine: series("riscos_nao_favoraveis"),
    points: runs.value.map((run, index) => ({
      id: run.id,
      x: xFor(index),
      favorableY: yFor(Number(run.riscos_favoraveis) || 0),
      unfavorableY: yFor(Number(run.riscos_nao_favoraveis) || 0),
      favorable: Number(run.riscos_favoraveis) || 0,
      unfavorable: Number(run.riscos_nao_favoraveis) || 0,
      label: formatDate(run.analyzed_at),
    })),
    grid: [0, 0.5, 1].map((fraction) => ({
      y: chartBottom - fraction * (chartBottom - chartTop),
      value: Math.round(maxCount.value * fraction),
    })),
    labelPoints: runs.value
      .map((run, index) => ({ id: run.id, x: xFor(index), label: formatDate(run.analyzed_at) }))
      .filter((_, index) =>
        runs.value.length <= 6
        || index % Math.ceil(runs.value.length / 5) === 0
        || index === runs.value.length - 1),
  };
});

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(date);
}
</script>

<template>
  <article class="panel history-panel">
    <div class="panel-heading history-heading">
      <div><p class="eyebrow">EVOLUÇÃO DAS AVALIAÇÕES</p><h2>Histórico das notas 4Ps</h2></div>
    </div>
    <div v-if="runs.length" class="history-chart">
      <div class="history-legend">
        <span><i class="favorable-line-key"></i>Favoráveis</span>
        <span><i class="unfavorable-line-key"></i>Não favoráveis</span>
      </div>
      <svg viewBox="0 0 720 270" role="img" aria-label="Histórico da quantidade de riscos favoráveis e não favoráveis">
        <g v-for="tick in chart.grid" :key="tick.y">
          <line :x1="padding.left" :x2="chartWidth - padding.right" :y1="tick.y" :y2="tick.y" class="grid-line" />
          <text :x="padding.left - 10" :y="tick.y + 4" text-anchor="end" class="axis-text">{{ tick.value }}</text>
        </g>
        <polyline v-if="chart.points.length > 1" :points="chart.favorableLine" class="favorable-line" />
        <polyline v-if="chart.points.length > 1" :points="chart.unfavorableLine" class="unfavorable-line" />
        <g v-for="point in chart.points" :key="point.id">
          <circle :cx="point.x" :cy="point.favorableY" r="4.5" class="favorable-point">
            <title>{{ point.label }} · Favoráveis: {{ point.favorable }}</title>
          </circle>
          <circle :cx="point.x" :cy="point.unfavorableY" r="4.5" class="unfavorable-point">
            <title>{{ point.label }} · Não favoráveis: {{ point.unfavorable }}</title>
          </circle>
        </g>
        <g v-for="point in chart.labelPoints" :key="`date-${point.id}`">
          <text :x="point.x" y="244" text-anchor="middle" class="axis-text">{{ point.label }}</text>
        </g>
      </svg>
    </div>
    <div v-else class="history-empty">
      <strong>{{ history.length ? "O histórico existente não contém notas dos quatro P’s." : "Ainda não há análises registradas." }}</strong>
      <span>Execute uma nova análise para iniciar o histórico de riscos favoráveis e não favoráveis.</span>
    </div>
    <footer class="history-footer">
      <span>{{ runs.length }} de 20 execuções com notas 4Ps</span>
      <span v-if="runs.length">Cada ponto representa uma análise salva.</span>
    </footer>
  </article>
</template>

<style scoped>
.history-panel { padding: 20px; }
.history-heading { align-items: center; }
.history-heading .eyebrow { margin: 0 0 6px; color: #b16d51; font-size: 8px; }
.history-heading h2 { margin: 0; color: #29493b; font-size: 15px; }
.history-legend { display: flex; justify-content: flex-end; gap: 13px; min-height: 24px; margin-top: 8px; color: #76877c; font-size: 8px; }
.history-legend span { display: inline-flex; align-items: center; gap: 5px; }
.history-legend i { width: 14px; height: 3px; border-radius: 3px; }
.favorable-line-key, .favorable-line { background: #43836c; stroke: #43836c; }
.unfavorable-line-key, .unfavorable-line { background: #dc9166; stroke: #dc9166; }
.history-chart svg { display: block; width: 100%; overflow: visible; }
.grid-line { stroke: #e9ede7; stroke-width: 1; }
.axis-text { fill: #89968e; font-size: 10px; }
.favorable-line, .unfavorable-line { fill: none; stroke-linecap: round; stroke-linejoin: round; stroke-width: 3; }
.favorable-point { fill: #43836c; stroke: #fff; stroke-width: 2; }
.unfavorable-point { fill: #dc9166; stroke: #fff; stroke-width: 2; }
.history-empty { display: grid; gap: 7px; padding: 42px 16px; color: #87948c; text-align: center; }
.history-empty strong { color: #52685c; font-size: 11px; }
.history-empty span { font-size: 9px; line-height: 1.5; }
.history-footer { display: flex; justify-content: space-between; margin-top: 9px; padding-top: 10px; border-top: 1px solid #edf0eb; color: #9ba49d; font-size: 8px; }
</style>
