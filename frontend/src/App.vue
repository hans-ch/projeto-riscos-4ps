<script setup>
import { computed, onMounted, ref } from "vue";
import AppSidebar from "./Components/AppSidebar.vue";
import BenchmarkPanel from "./Components/BenchmarkPanel.vue";
import ExposureChart from "./Components/ExposureChart.vue";
import HistoryChart from "./Components/HistoryChart.vue";
import MetricCard from "./Components/MetricCard.vue";
import ReportCard from "./Components/ReportCard.vue";
import RiskMatrix from "./Components/RiskMatrix.vue";
import RiskRegistration from "./Components/RiskRegistration.vue";
import WelcomePanel from "./Components/WelcomePanel.vue";

const analysis = ref(null);
const registeredRisks = ref([]);
const history = ref([]);
const benchmark = ref(null);
const activeView = ref("Visão geral");
const loading = ref(false);
const savingBenchmark = ref(false);
const error = ref("");
const success = ref("");
const benchmarkError = ref("");

const viewDescription = computed(() => {
  if (activeView.value === "Cadastro de riscos") {
    return "Registre os perigos e parâmetros para incluir na próxima análise.";
  }
  if (activeView.value === "Benchmark") {
    return "Compare as execuções da carteira com suas referências configuradas.";
  }
  return "Uma leitura clara da exposição, dos controles e do impacto potencial.";
});
const latestHistorySummary = computed(() => {
  const latest = history.value.at(-1);
  if (!latest) return null;
  return {
    perda_inerente: latest.inherent_loss,
    perda_residual: latest.residual_loss,
    p95_total: latest.p95_total,
    reducao_geral: latest.control_reduction,
    quantidade_riscos: latest.risk_count,
    simulacoes_por_risco: latest.simulations_per_risk,
  };
});
const comparisonSummary = computed(() => analysis.value?.resumo ?? latestHistorySummary.value);
const comparisonSummaryLabel = computed(() => analysis.value ? "Análise atual" : "Última execução");

function formatCurrency(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value ?? 0);
}

function formatPercent(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value ?? 0);
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((item) => item.msg).join(" ")
      : payload.detail;
    throw new Error(detail || `A solicitação para ${url} falhou.`);
  }
  return payload;
}

async function loadDashboardData() {
  const [risks, savedHistory, savedBenchmark] = await Promise.all([
    requestJson("/api/risks"),
    requestJson("/api/analysis/history"),
    requestJson("/api/benchmark"),
  ]);
  registeredRisks.value = risks;
  history.value = savedHistory;
  benchmark.value = savedBenchmark;
}

async function executeAnalysis() {
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    analysis.value = await requestJson("/api/analysis", { method: "POST" });
    history.value = await requestJson("/api/analysis/history");
    registeredRisks.value = await requestJson("/api/risks");
    success.value = "Análise concluída e adicionada ao histórico da carteira.";
  } catch (cause) {
    error.value = cause.message || "Não foi possível executar a análise.";
  } finally {
    loading.value = false;
  }
}

function onRiskCreated(risk) {
  registeredRisks.value.unshift(risk);
  analysis.value = null;
  error.value = "";
  success.value = "Risco cadastrado. Execute uma nova análise para incluí-lo nos resultados.";
}

async function saveBenchmark(reference) {
  savingBenchmark.value = true;
  benchmarkError.value = "";
  try {
    benchmark.value = await requestJson("/api/benchmark", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(reference),
    });
    error.value = "";
    success.value = "Referência de benchmark salva e aplicada aos comparativos.";
  } catch (cause) {
    benchmarkError.value = cause.message || "Não foi possível salvar a referência.";
  } finally {
    savingBenchmark.value = false;
  }
}

function downloadReport(kind) {
  window.open(`/api/reports/${kind}`, "_blank", "noopener");
}

onMounted(async () => {
  try {
    await requestJson("/api/health");
    await loadDashboardData();
  } catch (cause) {
    error.value = cause.message || "Não foi possível conectar à API. Inicie o servidor Python para continuar.";
  }
});
</script>

<template>
  <div class="app-shell">
    <AppSidebar :active-view="activeView" @navigate="activeView = $event" />

    <main class="main-content">
      <header class="topbar">
        <div class="breadcrumb">Carteira <span>/</span> <strong>{{ activeView }}</strong></div>
        <div class="topbar-meta"><span class="live-dot"></span> Base local SQLite <i></i> Análise quantitativa</div>
      </header>

      <section class="page">
        <div class="page-heading">
          <div>
            <p class="eyebrow">SEGURANÇA OPERACIONAL · 4Ps</p>
            <h1>{{ activeView === "Visão geral" ? "Risco em perspectiva" : activeView }}<span>.</span></h1>
            <p class="intro">{{ viewDescription }}</p>
          </div>
          <button
            v-if="activeView === 'Visão geral'"
            class="run-button"
            :disabled="loading"
            @click="executeAnalysis"
          >
            <span v-if="loading" class="spinner"></span><span v-else>↗</span>
            {{ loading ? "Calculando riscos..." : "Executar análise" }}
          </button>
        </div>

        <div v-if="error" class="notice error-notice" role="alert">
          <span>!</span><div><strong>Não foi possível concluir a operação</strong><p>{{ error }}</p></div>
        </div>
        <div v-if="success" class="notice success-notice" role="status">
          <span>✓</span><div><strong>Operação concluída</strong><p>{{ success }}</p></div>
        </div>

        <RiskRegistration
          v-if="activeView === 'Cadastro de riscos'"
          :risks="registeredRisks"
          @created="onRiskCreated"
        />

        <template v-else-if="activeView === 'Benchmark'">
          <section class="benchmark-page-grid">
            <HistoryChart
              :history="history"
              :reference="benchmark"
              :format-currency="formatCurrency"
              :format-percent="formatPercent"
            />
            <BenchmarkPanel
              :reference="benchmark"
              :summary="comparisonSummary"
              :summary-label="comparisonSummaryLabel"
              :format-currency="formatCurrency"
              :format-percent="formatPercent"
              :saving="savingBenchmark"
              :error="benchmarkError"
              @save="saveBenchmark"
            />
          </section>
          <p class="benchmark-disclaimer">
            As referências são definidas por você e não representam médias de mercado. O histórico começa a ser registrado a cada nova execução.
          </p>
        </template>

        <template v-else-if="analysis">
          <div class="analysis-banner">
            <span class="check-mark">✓</span>
            <div><strong>Análise OpenFAIR concluída</strong><p>Resultados salvos no SQLite e adicionados ao histórico.</p></div>
            <span class="sim-count">{{ analysis.resumo.simulacoes_por_risco.toLocaleString("pt-BR") }} simulações / risco</span>
          </div>

          <section class="metric-grid" aria-label="Resumo da exposição">
            <MetricCard
              label="PERDA INERENTE"
              :value="formatCurrency(analysis.resumo.perda_inerente)"
              caption="Exposição anual estimada"
              icon="$"
            />
            <MetricCard
              label="PERDA RESIDUAL"
              :value="formatCurrency(analysis.resumo.perda_residual)"
              caption="Após aplicação dos controles"
              icon="↘"
              featured
            />
            <MetricCard
              label="CENÁRIO P95"
              :value="formatCurrency(analysis.resumo.p95_total)"
              caption="Percentil 95 de perda residual"
              icon="⌁"
            />
            <MetricCard
              label="REDUÇÃO DOS CONTROLES"
              :value="formatPercent(analysis.resumo.reducao_geral)"
              caption="Redução frente à exposição inerente"
              icon="◎"
            />
          </section>

          <section class="analytics-grid">
            <ExposureChart :risks="analysis.riscos" :format-currency="formatCurrency" />
            <RiskMatrix :risks="analysis.riscos" />
          </section>

          <section class="comparison-grid">
            <HistoryChart
              :history="history"
              :reference="benchmark"
              :format-currency="formatCurrency"
              :format-percent="formatPercent"
            />
            <BenchmarkPanel
              :reference="benchmark"
              :summary="analysis.resumo"
              summary-label="Execução atual"
              :format-currency="formatCurrency"
              :format-percent="formatPercent"
              :saving="savingBenchmark"
              :error="benchmarkError"
              compact
              @save="saveBenchmark"
            />
          </section>

          <section class="content-grid">
            <article class="panel risks-panel">
              <div class="panel-heading table-heading">
                <div><p class="eyebrow">INVENTÁRIO DE EXPOSIÇÃO</p><h2>Riscos analisados</h2></div>
                <span class="count-pill">{{ analysis.resumo.quantidade_riscos }} riscos</span>
              </div>
              <div class="table-scroll">
                <table>
                  <thead><tr><th>RISCO</th><th>CATEGORIA</th><th>MATRIZ</th><th>REDUÇÃO</th><th>PERDA RESIDUAL</th><th>P95</th><th>CLASSIFICAÇÃO</th></tr></thead>
                  <tbody>
                    <tr v-for="risk in analysis.riscos" :key="risk.id">
                      <td><strong>{{ risk.risco }}</strong><small>{{ risk.pessoa_afetada }} · {{ risk.data_ocorrencia }}</small></td>
                      <td><span class="category-tag">{{ risk.categoria }}</span></td>
                      <td>{{ risk.matriz }}</td>
                      <td>{{ formatPercent(risk.reducao_controles) }}</td>
                      <td class="money-cell">{{ formatCurrency(risk.perda_residual) }}</td>
                      <td>{{ formatCurrency(risk.p95_residual) }}</td>
                      <td><span class="risk-level" :class="risk.classificacao_fair.toLowerCase()">{{ risk.classificacao_fair }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <footer class="table-footer"><span>{{ analysis.riscos.length }} riscos analisados</span><span>Valores estimados por ano · BRL</span></footer>
            </article>
            <ReportCard :download-report="downloadReport" />
          </section>
        </template>

        <WelcomePanel v-else :loading="loading" @run-analysis="executeAnalysis" />

        <footer class="page-footer"><span>RISCO EM PERSPECTIVA <i>·</i> 4Ps</span><span>OPENFAIR · SIMULAÇÃO MONTE CARLO</span></footer>
      </section>
    </main>
  </div>
</template>
