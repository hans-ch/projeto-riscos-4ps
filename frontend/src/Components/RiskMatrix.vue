<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  risks: { type: Array, default: () => [] },
});

const levels = [5, 4, 3, 2, 1];
const dimensionNames = [
  "Pessoas",
  "Processos",
  "Produtos",
  "Políticas governamentais",
];
const selectedDimension = ref(dimensionNames[0]);
const selectedAssessments = computed(() =>
  props.risks.flatMap((risk) => {
    const assessments = risk.dimensoes ?? risk.dimensions ?? [];
    return assessments
      .filter((assessment) => assessment.dimension === selectedDimension.value)
      .map((assessment) => ({
        title: risk.risco ?? risk.title,
        severity: assessment.severity,
        probability: assessment.probability,
      }));
  }),
);
const matrixCells = computed(() => levels.flatMap((severity) =>
  [1, 2, 3, 4, 5].map((probability) => {
    const matched = selectedAssessments.value.filter((risk) =>
      Number(risk.severity) === severity && Number(risk.probability) === probability);
    const score = severity * probability;
    return {
      severity,
      probability,
      score,
      count: matched.length,
      titles: matched.map((risk) => risk.title),
      level: score >= 15 ? "high" : score >= 8 ? "medium" : "low",
    };
  }),
));
</script>

<template>
  <article class="panel matrix-panel">
    <div class="panel-heading chart-heading">
      <div><p class="eyebrow">MATRIZ DE RISCO 5 × 5</p><h2>Onde está a concentração?</h2></div>
      <select v-model="selectedDimension" aria-label="Dimensão da matriz">
        <option v-for="dimension in dimensionNames" :key="dimension" :value="dimension">{{ dimension }}</option>
      </select>
    </div>
    <div class="matrix-wrap">
      <span class="matrix-y-label">SEVERIDADE</span>
      <div class="matrix-content">
        <div class="matrix-grid">
          <template v-for="cell in matrixCells" :key="`${cell.severity}-${cell.probability}`">
            <div
              class="matrix-cell"
              :class="[cell.level, { occupied: cell.count > 0 }]"
              :title="`Severidade ${cell.severity}, probabilidade ${cell.probability}${cell.titles.length ? ': ' + cell.titles.join(', ') : ''}`"
            >
              <span>{{ cell.score }}</span>
              <strong v-if="cell.count">{{ cell.count }}</strong>
            </div>
          </template>
        </div>
        <div class="matrix-x-ticks"><span v-for="level in [1, 2, 3, 4, 5]" :key="level">{{ level }}</span></div>
        <span class="matrix-x-label">PROBABILIDADE</span>
      </div>
      <div class="matrix-y-ticks"><span v-for="level in levels" :key="level">{{ level }}</span></div>
    </div>
    <div class="matrix-legend">
      <span><i class="low"></i> Baixo</span><span><i class="medium"></i> Médio</span><span><i class="high"></i> Alto</span>
      <small>{{ selectedAssessments.length }} riscos mapeados</small>
    </div>
  </article>
</template>

<style scoped>
.matrix-panel { padding: 20px; }
.chart-heading .eyebrow { margin: 0 0 6px; color: #b16d51; font-size: 8px; }
.chart-heading h2 { margin: 0; color: #29493b; font-size: 15px; }
.chart-heading select { max-width: 155px; height: 29px; padding: 0 6px; border: 1px solid #e5e9e2; border-radius: 4px; color: #65776c; background: white; font-size: 8px; }
.matrix-wrap { display: flex; align-items: stretch; gap: 9px; margin: 20px 7px 0; }
.matrix-y-label { align-self: center; color: #9ba69e; font-size: 7px; letter-spacing: .8px; writing-mode: vertical-rl; transform: rotate(180deg); }
.matrix-content { flex: 1; }
.matrix-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; }
.matrix-cell { position: relative; display: grid; min-height: 44px; place-items: center; border: 1px solid transparent; border-radius: 4px; font-size: 8px; }
.matrix-cell.low { color: #598365; background: #e9f2e8; }
.matrix-cell.medium { color: #9a763e; background: #faf0da; }
.matrix-cell.high { color: #a85942; background: #f7e4dc; }
.matrix-cell.occupied { border-color: currentColor; box-shadow: inset 0 0 0 1px #ffffff99; }
.matrix-cell strong { position: absolute; top: 3px; right: 5px; display: grid; width: 13px; height: 13px; place-items: center; border-radius: 50%; color: white; background: #315b49; font-size: 7px; }
.matrix-y-ticks { display: flex; flex-direction: column; justify-content: space-around; padding: 1px 0 18px; color: #819087; font-size: 8px; }
.matrix-x-ticks { display: grid; grid-template-columns: repeat(5, 1fr); padding-top: 4px; color: #819087; font-size: 8px; text-align: center; }
.matrix-x-label { display: block; margin-top: 8px; color: #9ba69e; font-size: 7px; letter-spacing: .8px; text-align: center; }
.matrix-legend { display: flex; align-items: center; gap: 11px; margin-top: 13px; color: #77877d; font-size: 8px; }
.matrix-legend span { display: inline-flex; align-items: center; gap: 4px; }
.matrix-legend i { width: 8px; height: 8px; border-radius: 2px; }
.matrix-legend i.low { background: #cfe2cf; }
.matrix-legend i.medium { background: #efd9a4; }
.matrix-legend i.high { background: #e9c1b0; }
.matrix-legend small { margin-left: auto; color: #99a39b; font-size: 8px; }
@media (max-width: 700px) {
  .matrix-panel { padding: 16px 13px; }
  .matrix-cell { min-height: 38px; }
}
</style>
