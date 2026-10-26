<script setup>
defineProps({
  dimensions: { type: Array, default: () => [] },
});
</script>

<template>
  <article class="panel dimension-chart">
    <div class="panel-heading chart-heading">
      <div><p class="eyebrow">DISTRIBUIÇÃO DAS NOTAS</p><h2>Classificação por dimensão</h2></div>
      <span class="chart-note">Quantidade de riscos por faixa</span>
    </div>
    <div v-if="dimensions.length" class="dimension-bars">
      <div class="dimension-legend">
        <span><i class="low-key"></i> Baixo</span>
        <span><i class="medium-key"></i> Médio</span>
        <span><i class="high-key"></i> Alto</span>
      </div>
      <div v-for="item in dimensions" :key="item.dimension" class="dimension-row">
        <div class="dimension-name">{{ item.dimension }}</div>
        <div class="dimension-bar-pair">
          <div class="dimension-track">
            <span class="low-fill" :style="{ width: `${item.low_count / Math.max(item.risk_count, 1) * 100}%` }"></span>
          </div>
          <div class="dimension-track">
            <span class="medium-fill" :style="{ width: `${item.medium_count / Math.max(item.risk_count, 1) * 100}%` }"></span>
          </div>
          <div class="dimension-track">
            <span class="high-fill" :style="{ width: `${item.high_count / Math.max(item.risk_count, 1) * 100}%` }"></span>
          </div>
        </div>
        <div class="dimension-counts">
          <b>{{ item.average_score }}<small>/25 média</small></b>
          <span>{{ item.low_count }} baixo · {{ item.medium_count }} médio · {{ item.high_count }} alto</span>
        </div>
      </div>
    </div>
    <div v-else class="chart-empty">Execute uma análise para comparar as notas dos quatro P’s.</div>
  </article>
</template>

<style scoped>
.dimension-chart { padding: 20px; }
.chart-heading { align-items: center; }
.chart-heading .eyebrow { margin: 0 0 6px; color: #b16d51; font-size: 8px; }
.chart-heading h2 { margin: 0; color: #29493b; font-size: 15px; }
.chart-note { color: #929e96; font-size: 8px; text-align: right; }
.dimension-bars { margin-top: 16px; }
.dimension-legend { display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 12px; color: #7b8980; font-size: 8px; }
.dimension-legend span { display: inline-flex; align-items: center; gap: 5px; }
.dimension-legend i { width: 8px; height: 8px; border-radius: 2px; }
.low-key { background: #65a376; }
.medium-key { background: #d3a64e; }
.high-key { background: #c96f58; }
.dimension-row { display: grid; grid-template-columns: minmax(115px, 1fr) minmax(90px, 1.5fr) minmax(115px, 1fr); align-items: center; gap: 10px; margin: 14px 0; }
.dimension-name { color: #52685c; font-size: 9px; font-weight: 600; }
.dimension-bar-pair { display: grid; gap: 4px; }
.dimension-track { height: 5px; overflow: hidden; border-radius: 5px; background: #f0f2ed; }
.dimension-track span { display: block; height: 100%; min-width: 0; border-radius: inherit; }
.low-fill { background: #65a376; }
.medium-fill { background: #d3a64e; }
.high-fill { background: #c96f58; }
.dimension-counts { display: grid; gap: 3px; text-align: right; }
.dimension-counts b { color: #536e5e; font-size: 9px; }
.dimension-counts b small { margin-left: 4px; color: #929e96; font-size: 7px; font-weight: 400; }
.dimension-counts > span { color: #929e96; font-size: 7px; }
.chart-empty { padding: 32px 8px; color: #87948c; font-size: 10px; text-align: center; }
@media (max-width: 700px) {
  .dimension-chart { padding: 16px 13px; }
  .dimension-row { grid-template-columns: minmax(90px, 1fr) minmax(55px, 1fr) minmax(110px, .9fr); gap: 7px; }
}
</style>
