<script setup>
import { computed } from "vue";

const props = defineProps({
  risks: { type: Array, default: () => [] },
  portfolioDecision: { type: Object, default: null },
  formatCurrency: { type: Function, required: true },
});

const dimensionColors = [
  { name: "Pessoas", className: "people" },
  { name: "Processos", className: "processes" },
  { name: "Produtos", className: "products" },
  { name: "Políticas governamentais", className: "government" },
];
const maxExposure = computed(() => Math.max(
  ...props.risks.map((risk) => Number(risk.perda_residual) || 0),
  1,
));

function dimensionColor(dimension) {
  return dimensionColors.find((item) => item.name === dimension)?.className ?? "";
}
</script>

<template>
  <section class="panel verdict-panel">
    <div class="verdict-heading">
      <div>
        <p class="eyebrow">PARECER FINAL · VISÃO 4Ps</p>
        <h2>O risco é favorável?</h2>
      </div>
      <span
        class="verdict-badge"
        :class="portfolioDecision?.riscos_provisorios
          ? 'provisional'
          : portfolioDecision?.status === 'Favorável' ? 'favorable' : 'unfavorable'"
      >
        {{ portfolioDecision?.riscos_provisorios ? "Provisório · " : "" }}
        {{ portfolioDecision?.status ?? "Aguardando análise" }}
      </span>
    </div>
    <p v-if="portfolioDecision" class="portfolio-explanation">
      {{ portfolioDecision.justificativa }}
    </p>
    <p class="verdict-criteria">
      Critério: {{ portfolioDecision?.criterio ?? "Execute a análise para ver os limites aplicados." }}
      A estimativa não substitui avaliação profissional nem significa ausência de risco.
    </p>

    <div class="risk-chart-heading">
      <div>
        <p class="eyebrow">EXPOSIÇÃO RESIDUAL POR RISCO</p>
        <h3>Quais dimensões mais contribuem?</h3>
      </div>
      <span>{{ risks.length }} riscos</span>
    </div>
    <div class="verdict-chart-legend">
      <span v-for="dimension in dimensionColors" :key="dimension.name">
        <i :class="dimension.className"></i>{{ dimension.name }}
      </span>
    </div>

    <div v-if="risks.length" class="verdict-risk-list">
      <article v-for="risk in risks" :key="risk.id" class="verdict-risk">
        <div class="verdict-risk-title">
          <div>
            <strong>{{ risk.risco }}</strong>
            <small>{{ risk.categoria }}</small>
          </div>
          <span
            class="verdict-badge risk-verdict-badge"
            :class="risk.parecer_final?.status === 'Favorável' ? 'favorable' : 'unfavorable'"
          >
            {{ risk.parecer_final?.provisorio ? "Provisório · " : "" }}
            {{ risk.parecer_final?.status ?? "Sem parecer" }}
          </span>
        </div>

        <div class="verdict-risk-chart" role="img" :aria-label="`Exposição residual por dimensão para ${risk.risco}`">
          <span
            v-for="dimension in dimensionColors"
            :key="dimension.name"
            :class="dimension.className"
            :style="{
              width: `${Math.max(
                0,
                Number(risk.dimensoes?.find((item) => item.dimension === dimension.name)?.residual_loss ?? 0),
              ) / maxExposure * 100}%`,
            }"
          ></span>
        </div>
        <div class="verdict-risk-totals">
          <span>Exposição somada: <strong>{{ formatCurrency(risk.perda_residual) }}</strong></span>
          <span>P95: <strong>{{ formatCurrency(risk.p95_residual) }}</strong></span>
        </div>
        <p class="verdict-explanation">
          {{ risk.parecer_final?.justificativa ?? "Execute uma nova análise para gerar o parecer das quatro dimensões." }}
        </p>

        <div class="dimension-verdict-grid">
          <div v-for="dimension in risk.dimensoes" :key="dimension.dimension" class="dimension-verdict">
            <span>{{ dimension.dimension }}</span>
            <strong :class="dimension.classification.toLowerCase()">{{ dimension.classification }}</strong>
            <small>{{ dimension.severity }}×{{ dimension.probability }} · {{ formatCurrency(dimension.residual_loss) }}/ano</small>
          </div>
        </div>
      </article>
    </div>
    <div v-else class="verdict-empty">Cadastre riscos e execute uma análise para receber o parecer final.</div>
  </section>
</template>

<style scoped>
.verdict-panel { padding: 22px; }
.verdict-heading, .risk-chart-heading, .verdict-risk-title { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.verdict-heading .eyebrow, .risk-chart-heading .eyebrow { margin: 0 0 6px; color: #b16d51; font-size: 8px; letter-spacing: 1px; }
.verdict-heading h2, .risk-chart-heading h3 { margin: 0; color: #29493b; font-size: 16px; }
.verdict-badge { display: inline-block; flex-shrink: 0; padding: 7px 11px; border-radius: 4px; font-size: 9px; font-weight: 700; }
.verdict-badge.favorable { color: #31704c; background: #e5f1e6; }
.verdict-badge.unfavorable { color: #a34e3c; background: #f8e7e0; }
.verdict-badge.provisional { color: #8d6c36; background: #f9f0d8; }
.portfolio-explanation { margin: 15px 0 0; color: #435e4f; font-size: 11px; line-height: 1.65; }
.verdict-criteria { margin: 12px 0 20px; padding: 10px 12px; border-left: 3px solid #d7aa68; color: #7d6c4e; background: #fbf7ec; font-size: 9px; line-height: 1.6; }
.risk-chart-heading { padding-top: 17px; border-top: 1px solid #e9ede7; }
.risk-chart-heading h3 { font-size: 13px; }
.risk-chart-heading > span { color: #8b988f; font-size: 9px; }
.verdict-chart-legend { display: flex; flex-wrap: wrap; gap: 12px; margin: 14px 0 7px; color: #77877c; font-size: 8px; }
.verdict-chart-legend span { display: inline-flex; align-items: center; gap: 5px; }
.verdict-chart-legend i { width: 9px; height: 9px; border-radius: 2px; }
.people { background: #4f8b70; }
.processes { background: #d49759; }
.products { background: #7693bd; }
.government { background: #a47caa; }
.verdict-risk-list { display: grid; gap: 12px; }
.verdict-risk { padding: 13px; border: 1px solid #edf0eb; border-radius: 5px; background: #fcfdfa; }
.verdict-risk-title > div { display: grid; gap: 3px; }
.verdict-risk-title strong { color: #3a5445; font-size: 10px; }
.verdict-risk-title small { color: #98a199; font-size: 8px; }
.risk-verdict-badge { padding: 5px 8px; font-size: 8px; }
.verdict-risk-chart { display: flex; width: 100%; height: 10px; margin: 12px 0 6px; overflow: hidden; border-radius: 6px; background: #eff2ed; }
.verdict-risk-chart span { min-width: 0; transition: width .2s ease; }
.verdict-risk-totals { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 5px 14px; color: #89958d; font-size: 8px; }
.verdict-risk-totals strong { color: #536d5e; }
.verdict-explanation { margin: 10px 0; color: #53675a; font-size: 9px; line-height: 1.6; }
.dimension-verdict-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 7px; }
.dimension-verdict { display: grid; gap: 4px; min-width: 0; padding: 8px; border-radius: 4px; background: #f4f6f2; }
.dimension-verdict > span { overflow: hidden; color: #65766b; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
.dimension-verdict strong { font-size: 8px; }
.dimension-verdict strong.baixo { color: #44845b; }
.dimension-verdict strong.médio { color: #ab7a35; }
.dimension-verdict strong.alto { color: #ad533f; }
.dimension-verdict small { overflow: hidden; color: #8b978e; font-size: 7px; text-overflow: ellipsis; white-space: nowrap; }
.verdict-empty { padding: 25px 8px; color: #87948c; font-size: 10px; text-align: center; }
@media (max-width: 700px) {
  .verdict-panel { padding: 16px 13px; }
  .dimension-verdict-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .verdict-risk { padding: 10px; }
}
</style>
