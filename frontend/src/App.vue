<script setup>
import { computed, onMounted, ref } from "vue";

const analysis = ref(null);
const registeredRisks = ref([]);
const activeView = ref("Visão geral");
const search = ref("");
const selectedCategory = ref("Todas");
const loading = ref(false);
const savingRisk = ref(false);
const error = ref("");
const success = ref("");
const newRisk = ref({
  title: "",
  description: "",
  category: "",
  severity: 3,
  probability: 3,
});

const categories = computed(() => [
  "Todas",
  ...new Set((analysis.value?.riscos ?? []).map((risk) => risk.categoria).filter(Boolean)),
]);

const filteredRisks = computed(() => {
  const query = search.value.trim().toLocaleLowerCase("pt-BR");
  return (analysis.value?.riscos ?? []).filter((risk) => {
    const matchesSearch = `${risk.risco} ${risk.categoria}`.toLocaleLowerCase("pt-BR").includes(query);
    const matchesCategory = selectedCategory.value === "Todas" || risk.categoria === selectedCategory.value;
    return matchesSearch && matchesCategory;
  });
});

const topRisks = computed(() => (analysis.value?.riscos ?? []).slice(0, 5));
const maxLoss = computed(() => Math.max(...topRisks.value.map((risk) => risk.perda_residual), 1));
const riskSeverityLabel = (value) => ["Muito baixa", "Baixa", "Moderada", "Alta", "Muito alta"][value - 1];

async function loadRisks() {
  const response = await fetch("/api/risks");
  if (!response.ok) throw new Error("Não foi possível carregar os riscos cadastrados.");
  registeredRisks.value = await response.json();
}

function formatCurrency(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value ?? 0);
}

function formatPercent(value) {
  return new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 }).format(value ?? 0);
}

async function executeAnalysis() {
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    const response = await fetch("/api/analysis", { method: "POST" });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join(" ")
        : payload.detail;
      throw new Error(detail || "Não foi possível executar a análise.");
    }
    analysis.value = payload;
    await loadRisks();
  } catch (cause) {
    error.value = cause.message || "Falha ao conectar com a API. Verifique se o servidor está ativo.";
  } finally {
    loading.value = false;
  }
}

async function createRisk() {
  savingRisk.value = true;
  error.value = "";
  success.value = "";
  try {
    const response = await fetch("/api/risks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newRisk.value),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join(" ")
        : payload.detail;
      throw new Error(detail || "Não foi possível cadastrar o risco.");
    }
    registeredRisks.value.unshift(payload);
    analysis.value = null;
    success.value = "Risco cadastrado com sucesso. Execute uma nova análise para atualizar os resultados.";
    newRisk.value = { title: "", description: "", category: "", severity: 3, probability: 3 };
  } catch (cause) {
    error.value = cause.message || "Falha ao conectar com a API. Verifique se o servidor está ativo.";
  } finally {
    savingRisk.value = false;
  }
}

function downloadReport(kind) {
  window.open(`/api/reports/${kind}`, "_blank", "noopener");
}

onMounted(async () => {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("A API não está disponível.");
    await loadRisks();
  } catch (cause) {
    error.value = cause.message || "Não foi possível conectar à API. Inicie o servidor Python para continuar.";
  }
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#" aria-label="Risco em Perspectiva">
        <span class="brand-mark">4P</span>
        <span class="brand-copy"><strong>perspectiva</strong><small>GESTÃO DE RISCOS</small></span>
      </a>
      <div class="nav-label">ESPAÇO DE TRABALHO</div>
      <nav class="navigation" aria-label="Navegação principal">
        <button
          v-for="item in ['Visão geral', 'Cadastro de riscos']"
          :key="item"
          :class="{ active: activeView === item }"
          @click="activeView = item"
        >
          <span class="nav-icon">{{ item === "Visão geral" ? "◫" : "◇" }}</span>{{ item }}
        </button>
      </nav>
      <div class="sidebar-bottom">
        <span class="status-dot"></span>
        <div><strong>Modelo OpenFAIR</strong><small>10 mil simulações por risco</small></div>
      </div>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <div class="breadcrumb">Carteira <span>/</span> <strong>{{ activeView }}</strong></div>
        <div class="topbar-meta"><span class="live-dot"></span> Base local SQLite <i></i> Análise quantitativa</div>
      </header>

      <section class="page">
        <div class="page-heading">
          <div>
            <p class="eyebrow">SEGURANÇA OPERACIONAL · 4Ps</p>
            <h1>{{ activeView === "Cadastro de riscos" ? "Cadastro de riscos" : "Risco em perspectiva" }}<span>.</span></h1>
            <p class="intro">
              {{ activeView === "Cadastro de riscos" ? "Registre os perigos e parâmetros para incluir na próxima análise." : "Uma leitura clara da exposição, dos controles e do impacto potencial." }}
            </p>
          </div>
          <button v-if="activeView !== 'Cadastro de riscos'" class="run-button" :disabled="loading" @click="executeAnalysis">
            <span v-if="loading" class="spinner"></span>
            <span v-else>↗</span>
            {{ loading ? "Calculando riscos..." : "Executar análise" }}
          </button>
        </div>

        <div v-if="error" class="notice error-notice" role="alert">
          <span>!</span><div><strong>Não foi possível concluir a operação</strong><p>{{ error }}</p></div>
        </div>
        <div v-if="success" class="notice success-notice" role="status">
          <span>✓</span><div><strong>Cadastro concluído</strong><p>{{ success }}</p></div>
        </div>

        <template v-if="activeView === 'Cadastro de riscos'">
          <section class="risk-create-layout">
            <form class="panel risk-form" @submit.prevent="createRisk">
              <div class="panel-heading form-heading">
                <div><p class="eyebrow">NOVO REGISTRO</p><h2>Descreva o risco</h2></div>
                <span class="form-step">01 / 01</span>
              </div>
              <label class="form-field">
                <span>Nome do risco <b>*</b></span>
                <input v-model.trim="newRisk.title" required maxlength="200" placeholder="Ex.: Queda durante trabalho em altura" />
              </label>
              <label class="form-field">
                <span>Categoria <b>*</b></span>
                <input v-model.trim="newRisk.category" required maxlength="100" list="risk-categories" placeholder="Selecione ou informe uma categoria" />
                <datalist id="risk-categories">
                  <option v-for="category in [...new Set(registeredRisks.map((risk) => risk.category).filter(Boolean))]" :key="category" :value="category" />
                  <option value="Mecânico" /><option value="Elétrico" /><option value="Químico" />
                  <option value="Físico" /><option value="Ergonômico" /><option value="Incêndio" />
                </datalist>
              </label>
              <label class="form-field">
                <span>Descrição <small>OPCIONAL</small></span>
                <textarea v-model.trim="newRisk.description" maxlength="2000" rows="3" placeholder="Contexto, local ou situação que pode causar o evento"></textarea>
              </label>
              <div class="form-field-grid">
                <label class="form-field">
                  <span>Severidade <b>*</b></span>
                  <select v-model.number="newRisk.severity" required>
                    <option v-for="level in [1, 2, 3, 4, 5]" :key="level" :value="level">{{ level }} — {{ riskSeverityLabel(level) }}</option>
                  </select>
                </label>
                <label class="form-field">
                  <span>Probabilidade <b>*</b></span>
                  <select v-model.number="newRisk.probability" required>
                    <option v-for="level in [1, 2, 3, 4, 5]" :key="level" :value="level">{{ level }} — {{ riskSeverityLabel(level) }}</option>
                  </select>
                </label>
              </div>
              <div class="form-actions">
                <p><b>*</b> Campos obrigatórios</p>
                <button class="run-button" type="submit" :disabled="savingRisk">
                  <span v-if="savingRisk" class="spinner"></span><span v-else>＋</span>
                  {{ savingRisk ? "Salvando risco..." : "Cadastrar risco" }}
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
              <div><p class="eyebrow">CARTEIRA DE RISCOS</p><h2>Riscos cadastrados <span class="count-pill">{{ registeredRisks.length }}</span></h2></div>
              <label class="search-box"><span>⌕</span><input v-model="search" placeholder="Buscar risco..." /></label>
            </div>
            <div class="table-scroll">
              <table>
                <thead><tr><th>RISCO</th><th>CATEGORIA</th><th>DESCRIÇÃO</th><th>SEVERIDADE</th><th>PROBABILIDADE</th><th>MATRIZ</th></tr></thead>
                <tbody>
                  <tr v-for="risk in registeredRisks.filter((item) => `${item.title} ${item.category}`.toLocaleLowerCase('pt-BR').includes(search.trim().toLocaleLowerCase('pt-BR')))" :key="risk.id">
                    <td><strong>{{ risk.title }}</strong><small>ID {{ risk.id }}</small></td>
                    <td><span class="category-tag">{{ risk.category }}</span></td>
                    <td class="description-cell">{{ risk.description || "Sem descrição" }}</td>
                    <td>{{ risk.severity }} — {{ riskSeverityLabel(risk.severity) }}</td>
                    <td>{{ risk.probability }} — {{ riskSeverityLabel(risk.probability) }}</td>
                    <td><span class="risk-level" :class="risk.severity * risk.probability >= 15 ? 'alto' : risk.severity * risk.probability >= 8 ? 'médio' : 'baixo'">{{ risk.severity * risk.probability }} / 25</span></td>
                  </tr>
                  <tr v-if="!registeredRisks.length"><td colspan="6" class="empty-cell">Nenhum risco cadastrado.</td></tr>
                  <tr v-else-if="!registeredRisks.some((item) => `${item.title} ${item.category}`.toLocaleLowerCase('pt-BR').includes(search.trim().toLocaleLowerCase('pt-BR')))"><td colspan="6" class="empty-cell">Nenhum risco corresponde à busca.</td></tr>
                </tbody>
              </table>
            </div>
            <footer class="table-footer"><span>{{ registeredRisks.length }} riscos salvos no SQLite</span><span>Edite os níveis no próximo ciclo de análise</span></footer>
          </section>
        </template>

        <template v-else-if="analysis">
          <div class="analysis-banner">
            <span class="check-mark">✓</span>
            <div><strong>Análise OpenFAIR concluída</strong><p>Resultados calculados e salvos no banco SQLite.</p></div>
            <span class="sim-count">{{ analysis.resumo.simulacoes_por_risco.toLocaleString("pt-BR") }} simulações / risco</span>
          </div>

          <section class="metric-grid" aria-label="Resumo da exposição">
            <article class="metric-card">
              <div class="metric-top"><span>PERDA INERENTE</span><span class="metric-icon">$</span></div>
              <strong>{{ formatCurrency(analysis.resumo.perda_inerente) }}</strong>
              <small>Exposição anual estimada</small>
            </article>
            <article class="metric-card featured">
              <div class="metric-top"><span>PERDA RESIDUAL</span><span class="metric-icon">↘</span></div>
              <strong>{{ formatCurrency(analysis.resumo.perda_residual) }}</strong>
              <small>Após aplicação dos controles</small>
            </article>
            <article class="metric-card">
              <div class="metric-top"><span>CENÁRIO P95</span><span class="metric-icon">⌁</span></div>
              <strong>{{ formatCurrency(analysis.resumo.p95_total) }}</strong>
              <small>Percentil 95 de perda residual</small>
            </article>
            <article class="metric-card">
              <div class="metric-top"><span>REDUÇÃO DOS CONTROLES</span><span class="metric-icon">◎</span></div>
              <strong>{{ formatPercent(analysis.resumo.reducao_geral) }}</strong>
              <small>Redução frente à exposição inerente</small>
            </article>
          </section>

          <section class="content-grid">
            <article class="panel exposure-panel">
              <div class="panel-heading">
                <div><p class="eyebrow">MAIOR EXPOSIÇÃO</p><h2>Riscos prioritários</h2></div>
                <span class="count-pill">{{ topRisks.length }} de {{ analysis.resumo.quantidade_riscos }}</span>
              </div>
              <div v-if="topRisks.length" class="bar-list">
                <div v-for="(risk, index) in topRisks" :key="risk.id" class="bar-row">
                  <div class="bar-label"><span class="bar-rank">0{{ index + 1 }}</span><strong>{{ risk.risco }}</strong><b>{{ formatCurrency(risk.perda_residual) }}</b></div>
                  <div class="bar-track"><span :style="{ width: `${Math.max((risk.perda_residual / maxLoss) * 100, 3)}%` }"></span></div>
                </div>
              </div>
              <div v-else class="empty-state">Nenhum risco corresponde aos filtros.</div>
            </article>

            <article class="panel report-panel">
              <div class="report-art"><span>FAIR</span><i>↗</i></div>
              <p class="eyebrow">RELATÓRIOS DA ANÁLISE</p>
              <h2>Leve os dados com você.</h2>
              <p>Exporte o relatório detalhado ou continue trabalhando com os resultados em uma planilha.</p>
              <button class="report-link" @click="downloadReport('html')">Abrir relatório completo <span>↗</span></button>
              <button class="report-link secondary" @click="downloadReport('excel')">Baixar planilha Excel <span>↓</span></button>
            </article>
          </section>

          <section class="panel risks-panel">
            <div class="panel-heading table-heading">
              <div><p class="eyebrow">INVENTÁRIO DE EXPOSIÇÃO</p><h2>{{ activeView === "Riscos" ? "Todos os riscos" : "Riscos analisados" }}</h2></div>
              <div class="filters">
                <label class="search-box"><span>⌕</span><input v-model="search" placeholder="Buscar risco..." /></label>
                <select v-model="selectedCategory" aria-label="Filtrar por categoria">
                  <option v-for="category in categories" :key="category">{{ category }}</option>
                </select>
              </div>
            </div>
            <div class="table-scroll">
              <table>
                <thead><tr><th>RISCO</th><th>CATEGORIA</th><th>MATRIZ</th><th>REDUÇÃO</th><th>PERDA RESIDUAL</th><th>P95</th><th>CLASSIFICAÇÃO</th></tr></thead>
                <tbody>
                  <tr v-for="risk in filteredRisks" :key="risk.id">
                    <td><strong>{{ risk.risco }}</strong><small>{{ risk.pessoa_afetada }} · {{ risk.data_ocorrencia }}</small></td>
                    <td><span class="category-tag">{{ risk.categoria }}</span></td>
                    <td>{{ risk.matriz }}</td>
                    <td>{{ formatPercent(risk.reducao_controles) }}</td>
                    <td class="money-cell">{{ formatCurrency(risk.perda_residual) }}</td>
                    <td>{{ formatCurrency(risk.p95_residual) }}</td>
                    <td><span class="risk-level" :class="risk.classificacao_fair.toLowerCase()">{{ risk.classificacao_fair }}</span></td>
                  </tr>
                  <tr v-if="!filteredRisks.length"><td colspan="7" class="empty-cell">Nenhum risco encontrado.</td></tr>
                </tbody>
              </table>
            </div>
            <footer class="table-footer"><span>Exibindo {{ filteredRisks.length }} de {{ analysis.riscos.length }} riscos</span><span>Valores estimados por ano · BRL</span></footer>
          </section>
        </template>

        <section v-else class="welcome-panel">
          <div class="welcome-copy"><p class="eyebrow">ANÁLISE QUANTITATIVA</p><h2>Entenda o risco.<br /><em>Antecipe o impacto.</em></h2><p>Execute uma simulação para visualizar a exposição da carteira, comparar controles e gerar relatórios FAIR.</p><button class="text-button" :disabled="loading" @click="executeAnalysis">Começar análise <span>→</span></button></div>
          <div class="welcome-visual"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div><div class="visual-core"><span>FAIR</span><small>10.000</small></div><span class="orbit-label label-top">EXPOSIÇÃO</span><span class="orbit-label label-bottom">CONTROLES</span></div>
        </section>

        <footer class="page-footer"><span>RISCO EM PERSPECTIVA <i>·</i> 4Ps</span><span>OPENFAIR · SIMULAÇÃO MONTE CARLO</span></footer>
      </section>
    </main>
  </div>
</template>