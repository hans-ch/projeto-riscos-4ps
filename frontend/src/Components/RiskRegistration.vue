<script setup>
import { computed, reactive, ref } from "vue";

const props = defineProps({
  risks: { type: Array, default: () => [] },
});

const emit = defineEmits(["created"]);
const saving = ref(false);
const error = ref("");
const query = ref("");
const form = reactive({
  title: "",
  description: "",
  category: "",
  severity: 3,
  probability: 3,
});
const levels = [1, 2, 3, 4, 5];
const levelLabel = (value) => ["Muito baixa", "Baixa", "Moderada", "Alta", "Muito alta"][value - 1];
const categories = computed(() => [...new Set(props.risks.map((risk) => risk.category).filter(Boolean))]);
const filteredRisks = computed(() => {
  const search = query.value.trim().toLocaleLowerCase("pt-BR");
  return props.risks.filter((risk) =>
    `${risk.title} ${risk.category} ${risk.description ?? ""}`.toLocaleLowerCase("pt-BR").includes(search));
});

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
    Object.assign(form, { title: "", description: "", category: "", severity: 3, probability: 3 });
  } catch (cause) {
    error.value = cause.message || "Falha ao conectar com a API. Verifique se o servidor está ativo.";
  } finally {
    saving.value = false;
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
        <div class="form-field-grid">
          <label class="form-field">
            <span>Severidade <b>*</b></span>
            <select v-model.number="form.severity" required>
              <option v-for="level in levels" :key="level" :value="level">{{ level }} — {{ levelLabel(level) }}</option>
            </select>
          </label>
          <label class="form-field">
            <span>Probabilidade <b>*</b></span>
            <select v-model.number="form.probability" required>
              <option v-for="level in levels" :key="level" :value="level">{{ level }} — {{ levelLabel(level) }}</option>
            </select>
          </label>
        </div>
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
        <div class="matrix-note"><strong>Próximo passo</strong><p>Após cadastrar, execute uma nova análise para calcular as perdas estimadas pelo modelo FAIR.</p></div>
      </aside>
    </section>

    <section class="panel risks-panel registered-risks-panel">
      <div class="panel-heading table-heading">
        <div><p class="eyebrow">CARTEIRA DE RISCOS</p><h2>Riscos cadastrados <span class="count-pill">{{ risks.length }}</span></h2></div>
        <label class="search-box"><span>⌕</span><input v-model="query" placeholder="Buscar risco..." /></label>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>RISCO</th><th>CATEGORIA</th><th>DESCRIÇÃO</th><th>SEVERIDADE</th><th>PROBABILIDADE</th><th>MATRIZ</th></tr></thead>
          <tbody>
            <tr v-for="risk in filteredRisks" :key="risk.id">
              <td><strong>{{ risk.title }}</strong><small>ID {{ risk.id }}</small></td>
              <td><span class="category-tag">{{ risk.category }}</span></td>
              <td class="description-cell">{{ risk.description || "Sem descrição" }}</td>
              <td>{{ risk.severity }} — {{ levelLabel(risk.severity) }}</td>
              <td>{{ risk.probability }} — {{ levelLabel(risk.probability) }}</td>
              <td><span class="risk-level" :class="risk.severity * risk.probability >= 15 ? 'alto' : risk.severity * risk.probability >= 8 ? 'médio' : 'baixo'">{{ risk.severity * risk.probability }} / 25</span></td>
            </tr>
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
</style>
