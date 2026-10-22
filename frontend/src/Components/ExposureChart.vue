<script setup>
import { computed } from "vue";

const props = defineProps({
  risks: { type: Array, default: () => [] },
  formatCurrency: { type: Function, required: true },
});

const rankedRisks = computed(() => [...props.risks]
  .sort((left, right) => right.perda_residual - left.perda_residual)
  .slice(0, 7));
const maxLoss = computed(() => Math.max(
  ...rankedRisks.value.map((risk) => risk.perda_inerente),
  1,
));
</script>

<template>
  <article class="panel chart-panel">
    <div class="panel-heading chart-heading">
      <div><p class="eyebrow">COMPARAÇÃO POR RISCO</p><h2>Exposição inerente × residual</h2></div>
      <span class="chart-note">Perda estimada / ano</span>
    </div>
    <div v-if="rankedRisks.length" class="exposure-chart">
      <div class="chart-legend">
        <span><i class="legend-inherent"></i> Inerente</span>
        <span><i class="legend-residual"></i> Residual</span>
      </div>
      <div v-for="risk in rankedRisks" :key="risk.id" class="exposure-row">
        <div class="exposure-label" :title="risk.risco">{{ risk.risco }}</div>
        <div class="exposure-bars">
          <div class="exposure-track">
            <span class="inherent-bar" :style="{ width: `${risk.perda_inerente / maxLoss * 100}%` }"></span>
          </div>
          <div class="exposure-track">
            <span class="residual-bar" :style="{ width: `${risk.perda_residual / maxLoss * 100}%` }"></span>
          </div>
        </div>
        <div class="exposure-value">{{ formatCurrency(risk.perda_residual) }}</div>
      </div>
      <div class="chart-axis"><span>R$ 0</span><span>{{ formatCurrency(maxLoss) }}</span></div>
    </div>
    <div v-else class="chart-empty">Execute uma análise para ver a comparação por risco.</div>
  </article>
</template>

<style scoped>
.chart-panel { padding: 20px; }
.chart-heading { align-items: center; }
.chart-heading .eyebrow { margin: 0 0 6px; color: #b16d51; font-size: 8px; }
.chart-heading h2 { margin: 0; color: #29493b; font-size: 15px; }
.chart-note { color: #929e96; font-size: 9px; }
.exposure-chart { margin-top: 18px; }
.chart-legend { display: flex; justify-content: flex-end; gap: 14px; margin-bottom: 12px; color: #7b8980; font-size: 9px; }
.chart-legend span { display: inline-flex; align-items: center; gap: 5px; }
.chart-legend i { width: 8px; height: 8px; border-radius: 2px; }
.legend-inherent { background: #d8b082; }
.legend-residual { background: #43836c; }
.exposure-row { display: grid; grid-template-columns: minmax(95px, 1fr) minmax(100px, 2fr) 76px; align-items: center; gap: 10px; margin: 10px 0; }
.exposure-label { overflow: hidden; color: #52685c; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.exposure-bars { display: grid; gap: 4px; }
.exposure-track { height: 6px; overflow: hidden; border-radius: 5px; background: #f0f2ed; }
.exposure-track span { display: block; height: 100%; min-width: 2px; border-radius: inherit; }
.inherent-bar { background: #d8b082; }
.residual-bar { background: linear-gradient(90deg, #43836c, #82ad8e); }
.exposure-value { color: #536e5e; font-size: 8px; font-weight: 700; text-align: right; }
.chart-axis { display: flex; justify-content: space-between; margin: 13px 85px 0 33%; color: #a1aaa3; font-size: 8px; }
.chart-empty { padding: 34px 8px; color: #87948c; font-size: 10px; text-align: center; }
@media (max-width: 700px) {
  .chart-panel { padding: 16px 13px; }
  .exposure-row { grid-template-columns: minmax(76px, 1fr) minmax(70px, 1.4fr) 68px; gap: 7px; }
  .chart-axis { margin-left: 28%; margin-right: 75px; }
}
</style>
