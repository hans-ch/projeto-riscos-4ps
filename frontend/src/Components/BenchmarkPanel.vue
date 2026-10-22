<script setup>
import { computed, reactive, watch } from "vue";

const props = defineProps({
  reference: { type: Object, default: null },
  summary: { type: Object, default: null },
  summaryLabel: { type: String, default: "Análise atual" },
  formatCurrency: { type: Function, required: true },
  formatPercent: { type: Function, required: true },
  compact: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

const emit = defineEmits(["save"]);
const draft = reactive({
  name: "",
  residual_loss: "",
  p95_total: "",
  control_reduction: "",
});

watch(
  () => props.reference,
  (reference) => {
    draft.name = reference?.name ?? "";
    draft.residual_loss = reference?.residual_loss ?? "";
    draft.p95_total = reference?.p95_total ?? "";
    draft.control_reduction = reference?.control_reduction == null
      ? ""
      : Number((reference.control_reduction * 100).toFixed(2));
  },
  { immediate: true },
);

const metrics = computed(() => {
  const rows = [
    {
      key: "residual_loss",
      label: "Perda residual anual",
      value: props.summary?.perda_residual,
      target: props.reference?.residual_loss,
      format: props.formatCurrency,
    },
    {
      key: "p95_total",
      label: "P95 total",
      value: props.summary?.p95_total,
      target: props.reference?.p95_total,
      format: props.formatCurrency,
    },
    {
      key: "control_reduction",
      label: "Redução pelos controles",
      value: props.summary?.reducao_geral,
      target: props.reference?.control_reduction,
      format: props.formatPercent,
    },
  ];
  return rows.map((row) => ({
    ...row,
    hasTarget: row.target !== null && row.target !== undefined,
    hasValue: row.value !== null && row.value !== undefined,
    valueWidth: row.value == null ? 0 : row.target == null
      ? 100
      : Math.min((row.value / Math.max(row.value, row.target, 1)) * 100, 100),
    targetWidth: row.target == null ? 0 : row.value == null
      ? 100
      : Math.min((row.target / Math.max(row.value, row.target, 1)) * 100, 100),
    comparison: row.value == null || row.target == null || row.target === 0
      ? null
      : (row.value - row.target) / row.target,
    comparisonIsFavorable: row.key === "control_reduction"
      ? row.value >= row.target
      : row.value <= row.target,
  }));
});

const hasReferenceMetric = computed(() => metrics.value.some((metric) => metric.hasTarget));

function submitReference() {
  emit("save", {
    name: draft.name,
    residual_loss: draft.residual_loss === "" ? null : Number(draft.residual_loss),
    p95_total: draft.p95_total === "" ? null : Number(draft.p95_total),
    control_reduction: draft.control_reduction === "" ? null : Number(draft.control_reduction) / 100,
  });
}
</script>

<template>
  <article class="panel benchmark-panel" :class="{ compact }">
    <div class="panel-heading benchmark-heading">
      <div>
        <p class="eyebrow">REFERÊNCIA CONFIGURÁVEL</p>
        <h2>{{ compact ? "Comparativo de referência" : "Compare com seus parâmetros" }}</h2>
      </div>
      <span v-if="hasReferenceMetric" class="reference-badge">Configurada</span>
      <span v-else class="reference-badge empty-badge">Sem referência</span>
    </div>

    <div class="benchmark-metrics">
      <div v-for="metric in metrics" :key="metric.key" class="benchmark-metric">
        <div class="benchmark-metric-header">
          <strong>{{ metric.label }}</strong>
          <span v-if="metric.comparison !== null" :class="metric.comparisonIsFavorable ? 'better' : 'worse'">
            {{ formatPercent(metric.comparison) }}
          </span>
        </div>
        <div class="benchmark-values">
          <span><small>{{ summaryLabel }}</small><b>{{ metric.hasValue ? metric.format(metric.value) : "Execute uma análise" }}</b></span>
          <span><small>{{ reference?.name || "Referência" }}</small><b>{{ metric.hasTarget ? metric.format(metric.target) : "Não configurada" }}</b></span>
        </div>
        <div class="benchmark-track" :aria-label="`${metric.label}: atual versus referência`">
          <span class="current-bar" :style="{ width: `${metric.valueWidth}%` }"></span>
          <span class="target-marker" :style="{ left: `${metric.targetWidth}%` }"></span>
        </div>
      </div>
    </div>

    <form class="benchmark-form" @submit.prevent="submitReference">
      <div class="benchmark-form-heading">
        <strong>{{ compact ? "Definir valores de comparação" : "Configurar referência" }}</strong>
        <span>Informe seus próprios dados; valores de mercado não são presumidos.</span>
      </div>
      <label class="benchmark-field benchmark-name">
        <span>Nome da referência</span>
        <input v-model.trim="draft.name" required maxlength="120" placeholder="Ex.: Meta interna 2026" />
      </label>
      <div class="benchmark-input-grid">
        <label class="benchmark-field">
          <span>Perda residual anual <small>R$</small></span>
          <input v-model="draft.residual_loss" type="number" min="0" step="1000" placeholder="Não informar" />
        </label>
        <label class="benchmark-field">
          <span>P95 total <small>R$</small></span>
          <input v-model="draft.p95_total" type="number" min="0" step="1000" placeholder="Não informar" />
        </label>
        <label class="benchmark-field">
          <span>Redução dos controles <small>%</small></span>
          <input v-model="draft.control_reduction" type="number" min="0" max="100" step="0.1" placeholder="Não informar" />
        </label>
      </div>
      <p v-if="error" class="benchmark-error" role="alert">{{ error }}</p>
      <button class="benchmark-save" type="submit" :disabled="saving">
        {{ saving ? "Salvando..." : "Salvar referência" }} <span>→</span>
      </button>
    </form>
    <p v-if="!hasReferenceMetric" class="benchmark-empty-note">Preencha ao menos uma métrica. Uma linha ou marcador de referência aparecerá nos comparativos após salvar.</p>
  </article>
</template>

<style scoped>
.benchmark-panel { padding: 20px; }
.benchmark-heading { align-items: center; }
.benchmark-heading .eyebrow { margin: 0 0 6px; color: #b16d51; font-size: 8px; }
.benchmark-heading h2 { margin: 0; color: #29493b; font-size: 15px; }
.reference-badge { padding: 5px 8px; border-radius: 12px; color: #447354; background: #eaf3eb; font-size: 8px; }
.empty-badge { color: #8c7960; background: #f6f0e4; }
.benchmark-metrics { display: grid; gap: 13px; margin-top: 17px; }
.benchmark-metric { padding: 0 0 11px; border-bottom: 1px solid #edf0eb; }
.benchmark-metric:last-child { padding-bottom: 0; border-bottom: 0; }
.benchmark-metric-header, .benchmark-values { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.benchmark-metric-header strong { color: #52695c; font-size: 9px; }
.benchmark-metric-header > span { font-size: 8px; }
.benchmark-metric-header > span.better { color: #4e835d; }
.benchmark-metric-header > span.worse { color: #bb704e; }
.benchmark-values { margin: 7px 0; }
.benchmark-values > span { display: grid; gap: 3px; }
.benchmark-values > span:last-child { text-align: right; }
.benchmark-values small { color: #9aa49c; font-size: 7px; }
.benchmark-values b { color: #426051; font-size: 9px; font-weight: 600; }
.benchmark-track { position: relative; height: 6px; overflow: visible; border-radius: 5px; background: #eef1eb; }
.current-bar { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #43836c, #82ad8e); }
.target-marker { position: absolute; top: -3px; width: 2px; height: 12px; background: #dc9166; }
.benchmark-form { margin-top: 18px; padding-top: 15px; border-top: 1px solid #edf0eb; }
.benchmark-form-heading { display: grid; gap: 4px; margin-bottom: 12px; }
.benchmark-form-heading strong { color: #52695c; font-size: 9px; }
.benchmark-form-heading span { color: #98a39a; font-size: 8px; line-height: 1.5; }
.benchmark-field { display: grid; gap: 5px; color: #65786c; font-size: 8px; }
.benchmark-field > span { display: flex; justify-content: space-between; gap: 5px; }
.benchmark-field small { color: #9ca79f; font-size: 7px; }
.benchmark-field input { width: 100%; min-width: 0; height: 31px; padding: 0 8px; border: 1px solid #e2e8e0; border-radius: 4px; outline: 0; color: #385348; background: white; font-size: 9px; }
.benchmark-field input:focus { border-color: #7da18b; box-shadow: 0 0 0 2px #6f9a7b18; }
.benchmark-name { margin-bottom: 10px; }
.benchmark-input-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.benchmark-save { display: flex; width: 100%; height: 33px; align-items: center; justify-content: space-between; margin-top: 12px; padding: 0 10px; border: 0; border-radius: 4px; color: white; background: #315f4c; font-size: 9px; font-weight: 600; }
.benchmark-save:disabled { cursor: wait; opacity: .65; }
.benchmark-save span { color: #efb68e; font-size: 14px; }
.benchmark-empty-note { margin: 9px 0 0; color: #9a8a70; font-size: 8px; line-height: 1.5; }
.benchmark-error { margin: 8px 0 0; color: #a74e3d; font-size: 8px; }
.compact { height: 100%; }
.compact .benchmark-form { margin-top: 14px; }
@media (max-width: 700px) {
  .benchmark-panel { padding: 16px 13px; }
  .benchmark-input-grid { grid-template-columns: 1fr; }
}
</style>
