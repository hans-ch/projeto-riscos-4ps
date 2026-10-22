<script setup>
const props = defineProps({
  modelValue: { type: Array, required: true },
  prefix: { type: String, required: true },
});

const emit = defineEmits(["update:modelValue"]);
const dimensions = [
  { key: "pessoas", name: "Pessoas", description: "Saúde, segurança, competências e disponibilidade" },
  { key: "processos", name: "Processos", description: "Operação, controles, continuidade e qualidade" },
  { key: "produtos", name: "Produtos", description: "Segurança, desempenho e ciclo de vida" },
  { key: "politicas", name: "Políticas governamentais", description: "Leis, normas, licenças e mudanças regulatórias" },
];
const levels = [1, 2, 3, 4, 5];
const levelLabel = (value) => ["Muito baixa", "Baixa", "Moderada", "Alta", "Muito alta"][value - 1];

function updateDimension(name, key, value) {
  emit(
    "update:modelValue",
    props.modelValue.map((assessment) =>
      assessment.dimension === name ? { ...assessment, [key]: Number(value) } : assessment),
  );
}
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
@media (max-width: 700px) {
  .dimension-score-grid { grid-template-columns: 1fr; }
}
</style>
