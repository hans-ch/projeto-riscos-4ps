<script setup>
import { reactive, watch } from "vue";

const props = defineProps({
  risks: { type: Array, default: () => [] },
  portfolioDecision: { type: Object, default: null },
});

const generatingPrevention = reactive({});
const preventionSuggestions = reactive({});
const preventionErrors = reactive({});

watch(
  () => props.risks,
  () => {
    for (const key of Object.keys(preventionSuggestions)) delete preventionSuggestions[key];
    for (const key of Object.keys(preventionErrors)) delete preventionErrors[key];
  },
  { deep: true },
);

function priorityLabel(priority) {
  if (priority === 1) return "Imediata";
  if (priority === 2) return "Alta";
  if (priority === 3) return "Recomendada";
  return "Preventiva";
}

async function generatePreventionSuggestions(risk) {
  generatingPrevention[risk.id] = true;
  delete preventionErrors[risk.id];
  delete preventionSuggestions[risk.id];

  try {
    const response = await fetch("/api/ai/resolution-suggestions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: risk.risco,
        category: risk.categoria,
        description: risk.descricao,
        dimensions: risk.dimensoes.map((dimension) => ({
          dimension: dimension.dimension,
          severity: dimension.severity,
          probability: dimension.probability,
          evidence: dimension.evidence || "",
          justification: dimension.justification || "",
        })),
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(result.detail)
        ? result.detail.map((item) => item.msg).join(" ")
        : result.detail;
      throw new Error(detail || "Não foi possível gerar recomendações de prevenção.");
    }
    if (!Array.isArray(result.suggestions) || result.suggestions.length === 0) {
      throw new Error("A IA não retornou recomendações de prevenção válidas.");
    }
    preventionSuggestions[risk.id] = result.suggestions;
  } catch (cause) {
    preventionErrors[risk.id] = cause.message || "Não foi possível conectar à IA local.";
  } finally {
    generatingPrevention[risk.id] = false;
  }
}
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

        <section class="prevention-section" aria-live="polite">
          <div class="prevention-heading">
            <div>
              <p class="eyebrow">APOIO DA IA LOCAL</p>
              <h3>Prevenção deste risco</h3>
            </div>
            <button
              type="button"
              :disabled="generatingPrevention[risk.id]"
              @click="generatePreventionSuggestions(risk)"
            >
              {{ generatingPrevention[risk.id] ? "Analisando risco..." : "Analisar risco e sugerir prevenção" }}
            </button>
          </div>
          <p v-if="preventionErrors[risk.id]" class="prevention-error" role="alert">
            {{ preventionErrors[risk.id] }}
          </p>
          <div v-if="preventionSuggestions[risk.id]?.length" class="prevention-list">
            <article
              v-for="suggestion in preventionSuggestions[risk.id]"
              :key="suggestion.priority"
              class="prevention-item"
            >
              <strong>Prioridade {{ suggestion.priority }} · {{ priorityLabel(suggestion.priority) }}</strong>
              <p>{{ suggestion.action }}</p>
              <small>{{ suggestion.justification }}</small>
            </article>
            <p class="prevention-disclaimer">
              Recomendações geradas pela IA com base nas informações cadastradas. Valide as medidas com a pessoa responsável antes de aplicá-las.
            </p>
          </div>
        </section>
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
.prevention-section { margin-top: 14px; padding: 13px; border: 1px solid #d3e6d9; border-radius: 5px; background: #f3f8f3; }
.prevention-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.prevention-heading .eyebrow { margin: 0 0 4px; color: #63816d; font-size: 8px; letter-spacing: 1px; }
.prevention-heading h3 { margin: 0; color: #29493b; font-size: 12px; }
.prevention-heading button { padding: 8px 10px; border: 1px solid #c9ddd0; border-radius: 4px; color: #315d4b; background: white; font-size: 9px; font-weight: 700; cursor: pointer; }
.prevention-heading button:disabled { cursor: wait; opacity: .6; }
.prevention-list { display: grid; gap: 8px; margin-top: 12px; }
.prevention-item { padding: 10px; border-left: 3px solid #7da18b; border-radius: 3px; background: white; }
.prevention-item strong { color: #476b54; font-size: 9px; }
.prevention-item p { margin: 5px 0; color: #3a5445; font-size: 10px; line-height: 1.5; }
.prevention-item small, .prevention-disclaimer { color: #76847a; font-size: 8px; line-height: 1.5; }
.prevention-item small { display: block; }
.prevention-disclaimer { margin: 0; }
.prevention-error { margin: 9px 0 0; color: #a55b46; font-size: 9px; }
.verdict-empty { padding: 25px 8px; color: #87948c; font-size: 10px; text-align: center; }
@media (max-width: 700px) {
  .verdict-panel { padding: 16px 13px; }
  .dimension-verdict-list { grid-template-columns: 1fr; }
  .verdict-risk { padding: 10px; }
  .prevention-heading { align-items: flex-start; flex-direction: column; }
}
</style>
