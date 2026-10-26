<script setup>
import { reactive, ref } from "vue";

const props = defineProps({
  modelValue: { type: Array, required: true },
  prefix: { type: String, required: true },
  riskTitle: { type: String, default: "" },
  riskCategory: { type: String, default: "" },
  riskDescription: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);
const generating = ref({});
const errors = reactive({});
const aiStatus = ref(null);
const dimensions = [
  { key: "pessoas", name: "Pessoas", description: "Saúde, segurança, competências e disponibilidade" },
  { key: "processos", name: "Processos", description: "Operação, controles, continuidade e qualidade" },
  { key: "produtos", name: "Produtos", description: "Segurança, desempenho e ciclo de vida" },
  { key: "politicas", name: "Políticas governamentais", description: "Leis, normas, licenças e mudanças regulatórias" },
];
const levels = [1, 2, 3, 4, 5];
const levelLabel = (value) => ["Muito baixa", "Baixa", "Moderada", "Alta", "Muito alta"][value - 1];

function updateDimension(name, key, value) {
  const updatedValue = key === "severity" || key === "probability"
    ? Number(value)
    : value;
  emit(
    "update:modelValue",
    props.modelValue.map((assessment) =>
      assessment.dimension === name ? { ...assessment, [key]: updatedValue } : assessment),
  );
}

async function generateJustification(dimension) {
  const assessment = props.modelValue.find((item) => item.dimension === dimension.name);
  if (!assessment) return;
  if (!props.riskTitle.trim() || !props.riskCategory.trim()) {
    errors[dimension.key] = "Informe o nome e a categoria do risco antes de gerar a justificativa.";
    return;
  }
  if (
    !Number.isInteger(Number(assessment.severity))
    || Number(assessment.severity) < 1
    || Number(assessment.severity) > 5
    || !Number.isInteger(Number(assessment.probability))
    || Number(assessment.probability) < 1
    || Number(assessment.probability) > 5
  ) {
    errors[dimension.key] = "Selecione a severidade e a probabilidade desta dimensão.";
    return;
  }
  if ((assessment.evidence?.trim().length ?? 0) < 10) {
    errors[dimension.key] = "Informe pelo menos 10 caracteres de evidências observadas.";
    return;
  }
  generating.value = { ...generating.value, [dimension.key]: true };
  errors[dimension.key] = "";
  try {
    const response = await fetch("/api/ai/dimension-justification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: props.riskTitle,
        category: props.riskCategory,
        description: props.riskDescription,
        dimension: assessment.dimension,
        severity: assessment.severity,
        probability: assessment.probability,
        evidence: assessment.evidence,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(result.detail)
        ? result.detail.map((item) => item.msg).join(" ")
        : result.detail;
      throw new Error(detail || "Não foi possível gerar a justificativa.");
    }
    updateDimension(dimension.name, "justification", result.justification);
  } catch (cause) {
    errors[dimension.key] = cause.message || "Não foi possível conectar à IA local.";
  } finally {
    generating.value = { ...generating.value, [dimension.key]: false };
  }
}

async function checkAiStatus() {
  try {
    const response = await fetch("/api/ai/status");
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Status da IA local indisponível.");
    aiStatus.value = result;
  } catch (cause) {
    aiStatus.value = { available: false, message: cause.message };
  }
}

checkAiStatus();
</script>

<template>
  <div class="dimension-score-grid">
    <fieldset v-for="(dimension, index) in dimensions" :key="dimension.name" class="dimension-score">
      <legend><span>{{ String(index + 1).padStart(2, "0") }}</span>{{ dimension.name }}</legend>
      <p>{{ dimension.description }}</p>
      <label class="dimension-select" :for="`${prefix}-${dimension.key}-severity`">
        <span>Severidade</span>
        <select
          :id="`${prefix}-${dimension.key}-severity`"
          :value="modelValue.find((item) => item.dimension === dimension.name)?.severity ?? ''"
          required
          @change="updateDimension(dimension.name, 'severity', $event.target.value)"
        >
          <option value="" disabled>Selecione a severidade</option>
          <option v-for="level in levels" :key="level" :value="level">{{ level }} — {{ levelLabel(level) }}</option>
        </select>
      </label>
      <label class="dimension-select" :for="`${prefix}-${dimension.key}-probability`">
        <span>Probabilidade</span>
        <select
          :id="`${prefix}-${dimension.key}-probability`"
          :value="modelValue.find((item) => item.dimension === dimension.name)?.probability ?? ''"
          required
          @change="updateDimension(dimension.name, 'probability', $event.target.value)"
        >
          <option value="" disabled>Selecione a probabilidade</option>
          <option v-for="level in levels" :key="level" :value="level">{{ level }} — {{ levelLabel(level) }}</option>
        </select>
      </label>
      <label class="dimension-context" :for="`${prefix}-${dimension.key}-evidence`">
        <span>Contexto e evidências observadas <b>*</b></span>
        <textarea
          :id="`${prefix}-${dimension.key}-evidence`"
          :value="modelValue.find((item) => item.dimension === dimension.name)?.evidence ?? ''"
          required
          minlength="10"
          maxlength="1200"
          rows="3"
          placeholder="Descreva fatos que sustentam severidade e probabilidade"
          @input="updateDimension(dimension.name, 'evidence', $event.target.value)"
        ></textarea>
      </label>
      <label class="dimension-context" :for="`${prefix}-${dimension.key}-justification`">
        <span>Por que esta dimensão recebeu essa nota? <b>*</b></span>
        <textarea
          :id="`${prefix}-${dimension.key}-justification`"
          :value="modelValue.find((item) => item.dimension === dimension.name)?.justification ?? ''"
          required
          minlength="10"
          maxlength="1200"
          rows="3"
          placeholder="Gere uma sugestão local ou escreva sua justificativa"
          @input="updateDimension(dimension.name, 'justification', $event.target.value)"
        ></textarea>
      </label>
      <div class="ai-explanation-actions">
        <button
          type="button"
          :disabled="generating[dimension.key]"
          @click="generateJustification(dimension)"
        >
          {{ generating[dimension.key] ? "IA local escrevendo..." : "Gerar justificativa com IA local" }}
        </button>
        <span v-if="aiStatus" :class="aiStatus.available ? 'ai-ready' : 'ai-unavailable'">
          {{ aiStatus.message }}
        </span>
      </div>
      <p v-if="errors[dimension.key]" class="ai-error" role="alert">{{ errors[dimension.key] }}</p>
    </fieldset>
  </div>
</template>

<style scoped>
.dimension-score-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin: 6px 0 17px; }

.dimension-score { min-width: 0; margin: 0; padding: 12px; border: 1px solid #e6ebe4; border-radius: 5px; background: #fbfcf9; }
.dimension-score legend { padding: 0 5px; color: #385848; font-size: 9px; font-weight: 700; }
.dimension-score legend span { margin-right: 6px; color: #c38461; font-size: 8px; }
.dimension-score > p { min-height: 24px; margin: 3px 0 9px; color: #909b93; font-size: 8px; line-height: 1.45; }
.dimension-select { display: grid; grid-template-columns: 75px minmax(0, 1fr); align-items: center; gap: 6px; margin-top: 6px; color: #65776c; font-size: 8px; }
.dimension-select select { width: 100%; min-width: 0; height: 28px; padding: 0 5px; border: 1px solid #e2e8e0; border-radius: 4px; outline: 0; color: #385348; background: white; font-size: 8px; }
.dimension-select select:focus { border-color: #7da18b; }
.dimension-context { display: grid; gap: 5px; margin-top: 9px; color: #65776c; font-size: 8px; }
.dimension-context > span b { color: #cf6f50; }
.dimension-context textarea { width: 100%; resize: vertical; padding: 7px; border: 1px solid #e2e8e0; border-radius: 4px; color: #385348; background: white; font: inherit; font-size: 8px; line-height: 1.5; }
.ai-explanation-actions { display: grid; gap: 5px; margin-top: 8px; }
.ai-explanation-actions button { justify-self: start; padding: 6px 8px; border: 1px solid #d8e5dc; border-radius: 4px; color: #315d4b; background: #f1f6f1; font-size: 8px; font-weight: 700; }
.ai-explanation-actions button:disabled { cursor: not-allowed; opacity: .55; }
.ai-ready, .ai-unavailable, .ai-error { color: #74867b; font-size: 7px; line-height: 1.4; }
.ai-unavailable, .ai-error { color: #a55b46; }
.ai-error { margin: 5px 0 0; }

@media (max-width: 700px) {
  .dimension-score-grid { grid-template-columns: 1fr; }
}
</style>