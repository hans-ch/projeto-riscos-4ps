<script setup>
import { computed, reactive, ref } from "vue";
import DimensionScoreFields from "./DimensionScoreFields.vue";

const props = defineProps({
  risks: { type: Array, default: () => [] },
});

const emit = defineEmits(["created", "updated"]);
const saving = ref(false);
const savingEdit = ref(false);
const error = ref("");
const editError = ref("");
const query = ref("");
const form = reactive({
  title: "",
  description: "",
  category: "",
  dimensions: createDefaultDimensions(),
});
const editingRisk = ref(null);
const editDimensions = ref([]);
const levels = [1, 2, 3, 4, 5];
const levelLabel = (value) => ["Muito baixa", "Baixa", "Moderada", "Alta", "Muito alta"][value - 1];
const dimensionNames = ["Pessoas", "Processos", "Produtos", "Políticas governamentais"];
const categories = computed(() => [...new Set(props.risks.map((risk) => risk.category).filter(Boolean))]);
const filteredRisks = computed(() => {
  const search = query.value.trim().toLocaleLowerCase("pt-BR");
  return props.risks.filter((risk) =>
    `${risk.title} ${risk.category} ${risk.description ?? ""}`.toLocaleLowerCase("pt-BR").includes(search));
});

function createDefaultDimensions() {
  return [
    "Pessoas",
    "Processos",
    "Produtos",
    "Políticas governamentais",
  ].map((dimension) => ({ dimension, severity: null, probability: null }));
}

function getDimension(risk, name) {
  return risk.dimensions?.find((item) => item.dimension === name);
}

function openDimensionEditor(risk) {
  editingRisk.value = risk.id;
  editError.value = "";
  editDimensions.value = dimensionNames.map((dimension) => {
    const existing = getDimension(risk, dimension);
    return {
      dimension,
      severity: existing?.severity ?? null,
      probability: existing?.probability ?? null,
    };
  });
}

async function createRisk() {
  saving.value = true;
  error.value = "";
  try {
    const response = await fetch("/api/risks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join(" ")
        : payload.detail;
      throw new Error(detail || "Não foi possível cadastrar o risco.");
    }
    emit("created", payload);
    Object.assign(form, {
      title: "",
      description: "",
      category: "",
      dimensions: createDefaultDimensions(),
    });
  } catch (cause) {
    error.value = cause.message || "Falha ao conectar com a API. Verifique se o servidor está ativo.";
  } finally {
    saving.value = false;
  }
}

async function saveDimensions(risk) {
  savingEdit.value = true;
  editError.value = "";
  try {
    const response = await fetch(`/api/risks/${risk.id}/dimensions`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dimensions: editDimensions.value }),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join(" ")
        : payload.detail;
      throw new Error(detail || "Não foi possível atualizar as dimensões.");
    }
    emit("updated", payload);
    editingRisk.value = null;
  } catch (cause) {
    editError.value = cause.message || "Falha ao conectar com a API.";
  } finally {
    savingEdit.value = false;
  }
}
</script>

<template>
  <div>
    <section class="risk-create-layout">
      <form class="panel risk-form" @submit.prevent="createRisk">
        <div class="panel-heading form-heading">
          <div><p class="eyebrow">NOVO REGISTRO</p><h2>Descreva o risco</h2></div>
          <span class="form-step">01 / 01</span>
        </div>
        <label class="form-field">
          <span>Nome do risco <b>*</b></span>
          <input v-model.trim="form.title" required maxlength="200" placeholder="Ex.: Queda durante trabalho em altura" />
        </label>
        <label class="form-field">
          <span>Categoria <b>*</b></span>
          <input v-model.trim="form.category" required maxlength="100" list="risk-categories" placeholder="Selecione ou informe uma categoria" />
          <datalist id="risk-categories">
            <option v-for="category in categories" :key="category" :value="category" />
            <option value="Mecânico" /><option value="Elétrico" /><option value="Químico" />
            <option value="Físico" /><option value="Ergonômico" /><option value="Incêndio" />
          </datalist>
        </label>
        <label class="form-field">
          <span>Descrição <small>OPCIONAL</small></span>
          <textarea v-model.trim="form.description" maxlength="2000" rows="3" placeholder="Contexto, local ou situação que pode causar o evento"></textarea>
        </label>
        <div class="dimension-fields-heading">
          <div><strong>Avalie cada dimensão <b>*</b></strong><small>Selecione severidade e probabilidade para os quatro P’s. Não há notas pré-preenchidas.</small></div>
        </div>
        <DimensionScoreFields v-model="form.dimensions" prefix="new-risk" />
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <div class="form-actions">
          <p><b>*</b> Campos obrigatórios</p>
          <button class="run-button" type="submit" :disabled="saving">
            <span v-if="saving" class="spinner"></span><span v-else>＋</span>
            {{ saving ? "Salvando risco..." : "Cadastrar risco" }}
          </button>
        </div>
      </form>

      <aside class="panel risk-guidance">
        <div class="guidance-icon">◇</div>
        <p class="eyebrow">ESCALA DE AVALIAÇÃO</p>
        <h2>Uma base para priorizar.</h2>
        <p>Use a escala de 1 a 5 para estimar a severidade do impacto e a chance de ocorrência. Os valores podem ser refinados conforme sua avaliação.</p>
        <div class="scale-row"><span>1</span><i></i><span>2</span><i></i><span>3</span><i></i><span>4</span><i></i><span>5</span></div>
        <div class="scale-caption"><span>Muito baixa</span><span>Muito alta</span></div>
        <div class="matrix-note"><strong>Os quatro P’s</strong><p>Registre cada risco em Pessoas, Processos, Produtos e Políticas governamentais. Cada dimensão precisa de duas notas independentes.</p></div>
        <div class="matrix-note"><strong>Critério do parecer</strong><p>Favorável somente quando as quatro exposições residuais estiverem em nível baixo. Qualquer dimensão média ou alta pede revisão e mitigação.</p></div>
        <div class="matrix-note"><strong>Risco herdado</strong><p>As notas antigas aparecem marcadas como herdadas. Revise cada dimensão; não são avaliações independentes.</p></div>
      </aside>
    </section>

    <section class="panel risks-panel registered-risks-panel">
      <div class="panel-heading table-heading">
        <div><p class="eyebrow">CARTEIRA DE RISCOS</p><h2>Riscos cadastrados <span class="count-pill">{{ risks.length }}</span></h2></div>
        <label class="search-box"><span>⌕</span><input v-model="query" placeholder="Buscar risco..." /></label>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>RISCO</th><th>CATEGORIA</th><th>DESCRIÇÃO</th><th>DIMENSÕES</th><th>MATRIZ MÁXIMA</th><th>AVALIAÇÃO</th></tr></thead>
          <tbody>
            <template v-for="risk in filteredRisks" :key="risk.id">
            <tr>
              <td><strong>{{ risk.title }}</strong><small>ID {{ risk.id }}</small></td>
              <td><span class="category-tag">{{ risk.category }}</span></td>
              <td class="description-cell">{{ risk.description || "Sem descrição" }}</td>
              <td class="dimension-summary">
                <span v-for="dimension in risk.dimensions" :key="dimension.dimension" :title="`${dimension.dimension}: severidade ${dimension.severity}, probabilidade ${dimension.probability}`">
                  {{ dimension.dimension.replace("Políticas governamentais", "Políticas") }} {{ dimension.severity }}×{{ dimension.probability }}
                </span>
              </td>
              <td>
                <span
                  class="risk-level"
                  :class="Math.max(...risk.dimensions.map((item) => item.severity * item.probability), 0) >= 15 ? 'alto' : Math.max(...risk.dimensions.map((item) => item.severity * item.probability), 0) >= 8 ? 'médio' : 'baixo'"
                >{{ Math.max(...risk.dimensions.map((item) => item.severity * item.probability), 0) }} / 25</span>
              </td>
              <td class="assessment-cell">
                <span v-if="risk.dimensions.some((item) => item.inherited)" class="inherited-label">Herdada · revise</span>
                <span v-else class="assessed-label">Avaliada</span>
                <button class="edit-dimensions-button" @click="openDimensionEditor(risk)">Revisar</button>
              </td>
            </tr>
            <tr v-if="editingRisk === risk.id">
              <td colspan="6" class="dimension-editor-cell">
                <form class="dimension-editor" @submit.prevent="saveDimensions(risk)">
                  <div class="editor-heading"><strong>Atualizar avaliação · {{ risk.title }}</strong><button type="button" @click="editingRisk = null">Fechar</button></div>
                  <DimensionScoreFields v-model="editDimensions" :prefix="`edit-${risk.id}`" />
                  <p v-if="editError" class="form-error" role="alert">{{ editError }}</p>
                  <button class="run-button" type="submit" :disabled="savingEdit">{{ savingEdit ? "Salvando..." : "Salvar as quatro dimensões" }}</button>
                </form>
              </td>
            </tr>
            </template>
            <tr v-if="!filteredRisks.length"><td colspan="6" class="empty-cell">{{ risks.length ? "Nenhum risco corresponde à busca." : "Nenhum risco cadastrado." }}</td></tr>
          </tbody>
        </table>
      </div>
      <footer class="table-footer"><span>{{ risks.length }} riscos salvos no SQLite</span><span>Edite os níveis no próximo ciclo de análise</span></footer>
    </section>
  </div>
</template>

<style scoped>
.form-error { margin: -3px 0 10px; color: #aa503d; font-size: 9px; }
.dimension-fields-heading { margin: 18px 0 7px; }
.dimension-fields-heading > div { display: grid; gap: 4px; }
.dimension-fields-heading strong { color: #50675b; font-size: 9px; }
.dimension-fields-heading strong b { color: #cf6f50; }
.dimension-fields-heading small { color: #909b93; font-size: 8px; }
.dimension-summary { white-space: normal; }
.dimension-summary span { display: inline-block; margin: 2px; padding: 3px 5px; border-radius: 3px; color: #60796a; background: #f0f4ef; font-size: 7px; white-space: nowrap; }
.assessment-cell { min-width: 112px; }
.inherited-label, .assessed-label { display: block; margin-bottom: 4px; color: #a57343; font-size: 7px; }
.assessed-label { color: #4f805f; }
.edit-dimensions-button, .editor-heading button { padding: 0; border: 0; color: #315d4b; background: transparent; font-size: 8px; font-weight: 700; }
.dimension-editor-cell { padding: 0; white-space: normal; }
.dimension-editor { padding: 17px; background: #fafbf8; }
.editor-heading { display: flex; justify-content: space-between; margin-bottom: 10px; color: #405b4a; font-size: 10px; }
</style>
