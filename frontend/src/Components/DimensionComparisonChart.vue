<script setup>
import { computed } from "vue";

const props = defineProps({
  dimensions: { type: Array, default: () => [] },
  formatCurrency: { type: Function, required: true },
  formatPercent: { type: Function, required: true },
});

const maxLoss = computed(() => Math.max(
  ...props.dimensions.map((item) => item.inherent_loss),
  1,
));
</script>

<template>
  <article class="panel dimension-chart">
    <div class="panel-heading chart-heading">
      <div><p class="eyebrow">EXPOSIÇÃO POR P</p><h2>Comparação das quatro dimensões</h2></div>
      <span class="chart-note">Total combinado = soma das dimensões</span>
    </div>
    <div v-if="dimensions.length" class="dimension-bars">
      <div class="dimension-legend"><span><i class="inherent-key"></i> Inerente</span><span><i class="residual-key"></i> Residual</span></div>
      <div v-for="item in dimensions" :key="item.dimension" class="dimension-row">
        <div class="dimension-name">{{ item.dimension }}</div>
        <div class="dimension-bar-pair">
          <div class="dimension-track"><span class="inherent-fill" :style="{ width: `${item.inherent_loss / maxLoss * 100}%` }"></span></div>
          <div class="dimension-track"><span class="residual-fill" :style="{ width: `${item.residual_loss / maxLoss * 100}%` }"></span></div>
        </div>
        <div class="dimension-numbers">
          <b>{{ formatCurrency(item.residual_loss) }}</b>
          <small>{{ formatPercent(item.control_reduction) }} redução</small>
        </div>
      </div>
      <div class="dimension-axis"><span>R$ 0</span><span>{{ formatCurrency(maxLoss) }}</span></div>
    </div>
    <div v-else class="chart-empty">Execute uma análise para comparar as quatro dimensões.</div>
    <p class="dimension-caveat">O total somado é uma estimativa de planejamento; pode haver sobreposição entre exposições.</p>
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
.inherent-key { background: #d8b082; }
.residual-key { background: #43836c; }
.dimension-row { display: grid; grid-template-columns: minmax(115px, 1fr) minmax(90px, 1.6fr) minmax(84px, .7fr); align-items: center; gap: 10px; margin: 14px 0; }
.dimension-name { color: #52685c; font-size: 9px; font-weight: 600; }
.dimension-bar-pair { display: grid; gap: 4px; }
.dimension-track { height: 6px; overflow: hidden; border-radius: 5px; background: #f0f2ed; }
.dimension-track span { display: block; height: 100%; min-width: 2px; border-radius: inherit; }
.inherent-fill { background: #d8b082; }
.residual-fill { background: linear-gradient(90deg, #43836c, #82ad8e); }
.dimension-numbers { display: grid; gap: 3px; text-align: right; }
.dimension-numbers b { color: #536e5e; font-size: 8px; }
.dimension-numbers small { color: #929e96; font-size: 7px; }
.dimension-axis { display: flex; justify-content: space-between; margin: 12px 90px 0 34%; color: #a1aaa3; font-size: 8px; }
.dimension-caveat { margin: 14px 0 0; padding-top: 10px; border-top: 1px solid #edf0eb; color: #9a8a70; font-size: 8px; line-height: 1.5; }
.chart-empty { padding: 32px 8px; color: #87948c; font-size: 10px; text-align: center; }
@media (max-width: 700px) {
  .dimension-chart { padding: 16px 13px; }
  .dimension-row { grid-template-columns: minmax(90px, 1fr) minmax(60px, 1fr) minmax(78px, .75fr); gap: 7px; }
  .dimension-axis { margin-left: 31%; margin-right: 82px; }
}
</style>
