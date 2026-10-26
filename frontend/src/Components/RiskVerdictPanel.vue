<script setup>
defineProps({
  risks: { type: Array, default: () => [] },
  portfolioDecision: { type: Object, default: null },
});
</script>

<template>
  <section class="panel verdict-panel">
    <div class="verdict-heading">
      <div>
        <p class="eyebrow">PARECER FINAL · VISÃO 4Ps</p>
        <h2>Resultado pelas notas</h2>
      </div>
      <span
        class="verdict-badge"
        :class="portfolioDecision?.riscos_provisorios
          || portfolioDecision?.justificativas_pendentes
          ? 'provisional'
          : portfolioDecision?.status === 'Favorável' ? 'favorable' : 'unfavorable'"
      >
        {{ portfolioDecision?.riscos_provisorios
          || portfolioDecision?.justificativas_pendentes ? "Revisão necessária · " : "" }}
        {{ portfolioDecision?.status ?? "Aguardando análise" }}
      </span>
    </div>
    <p v-if="portfolioDecision" class="portfolio-explanation">
      {{ portfolioDecision.justificativa }}
    </p>
    <p class="verdict-criteria">
      {{ portfolioDecision?.criterio ?? "Execute uma análise para avaliar a matriz dos quatro P’s." }}
      A classificação é uma referência de priorização e deve ser validada por uma pessoa responsável.
    </p>

    <div class="risk-chart-heading">
      <div>
        <p class="eyebrow">NOTAS POR RISCO</p>
        <h3>Severidade × probabilidade em cada dimensão</h3>
      </div>
      <span>{{ risks.length }} riscos · {{ risks.length * 4 }} notas</span>
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
            :class="risk.parecer_final?.provisorio
              || risk.parecer_final?.justificativas_pendentes
              ? 'provisional'
              : risk.parecer_final?.status === 'Favorável' ? 'favorable' : 'unfavorable'"
          >
            {{ risk.parecer_final?.provisorio
              || risk.parecer_final?.justificativas_pendentes ? "Revisão · " : "" }}
            {{ risk.parecer_final?.status ?? "Sem parecer" }}
          </span>
        </div>
        <p class="verdict-explanation">
          {{ risk.parecer_final?.justificativa ?? "Execute uma análise para classificar as notas deste risco." }}
        </p>

        <div class="dimension-verdict-list">
          <section
            v-for="dimension in risk.dimensoes"
            :key="dimension.dimension"
            class="dimension-verdict"
          >
            <div class="dimension-title">
              <strong>{{ dimension.dimension }}</strong>
              <span class="dimension-rating" :class="dimension.classification.toLowerCase()">
                {{ dimension.classification }} · {{ dimension.matrix_score }}/25
              </span>
            </div>
            <div
              class="score-track"
              role="img"
              :aria-label="`${dimension.dimension}: nota ${dimension.matrix_score} de 25`"
            >
              <span :class="dimension.classification.toLowerCase()" :style="{ width: `${dimension.matrix_score / 25 * 100}%` }"></span>
            </div>
            <p><b>Severidade {{ dimension.severity }}/5</b> × <b>probabilidade {{ dimension.probability }}/5</b></p>
            <p class="dimension-evidence"><strong>Evidências:</strong> {{ dimension.evidence || "Não informadas; avaliação herdada precisa de revisão." }}</p>
            <p class="dimension-justification"><strong>Por que recebeu essa nota:</strong> {{ dimension.justification || "Justificativa pendente. Edite o risco para informar o contexto e gerar uma sugestão com a IA local." }}</p>
          </section>
        </div>
      </article>
    </div>
    <div v-else class="verdict-empty">Cadastre riscos e execute uma análise para ver as notas e justificativas dos quatro P’s.</div>
  </section>
</template>

<style scoped>
.verdict-panel { padding: 22px; }
.verdict-heading, .risk-chart-heading, .verdict-risk-title, .dimension-title { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
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
.verdict-risk-list { display: grid; gap: 12px; margin-top: 14px; }
.verdict-risk { padding: 14px; border: 1px solid #edf0eb; border-radius: 5px; background: #fcfdfa; }
.verdict-risk-title > div { display: grid; gap: 3px; }
.verdict-risk-title strong { color: #3a5445; font-size: 10px; }
.verdict-risk-title small { color: #98a199; font-size: 8px; }
.risk-verdict-badge { padding: 5px 8px; font-size: 8px; }
.verdict-explanation { margin: 10px 0; color: #53675a; font-size: 9px; line-height: 1.6; }
.dimension-verdict-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.dimension-verdict { min-width: 0; padding: 10px; border-radius: 4px; background: #f4f6f2; }
.dimension-title { align-items: flex-start; }
.dimension-title > strong { color: #52685c; font-size: 9px; }
.dimension-rating { flex-shrink: 0; font-size: 8px; font-weight: 700; }
.dimension-rating.baixo { color: #44845b; }
.dimension-rating.médio { color: #ab7a35; }
.dimension-rating.alto { color: #ad533f; }
.score-track { height: 7px; margin: 8px 0; overflow: hidden; border-radius: 5px; background: #e8ece6; }
.score-track span { display: block; height: 100%; border-radius: inherit; }
.score-track span.baixo { background: #65a376; }
.score-track span.médio { background: #d3a64e; }
.score-track span.alto { background: #c96f58; }
.dimension-verdict > p { margin: 5px 0 0; color: #76847a; font-size: 8px; line-height: 1.5; overflow-wrap: anywhere; }
.dimension-verdict > p strong { color: #52675a; }
.dimension-evidence, .dimension-justification { padding-top: 5px; border-top: 1px solid #e5eae3; }
.verdict-empty { padding: 25px 8px; color: #87948c; font-size: 10px; text-align: center; }
@media (max-width: 700px) {
  .verdict-panel { padding: 16px 13px; }
  .dimension-verdict-list { grid-template-columns: 1fr; }
  .verdict-risk { padding: 10px; }
}
</style>
