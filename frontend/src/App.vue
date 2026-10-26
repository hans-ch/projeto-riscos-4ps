<script setup>
import { computed, onMounted, ref } from "vue";
import AppSidebar from "./Components/AppSidebar.vue";
import DimensionComparisonChart from "./Components/DimensionComparisonChart.vue";
import HistoryChart from "./Components/HistoryChart.vue";
import MetricCard from "./Components/MetricCard.vue";
import ReportCard from "./Components/ReportCard.vue";
import RiskMatrix from "./Components/RiskMatrix.vue";
import RiskRegistration from "./Components/RiskRegistration.vue";
import RiskVerdictPanel from "./Components/RiskVerdictPanel.vue";
import WelcomePanel from "./Components/WelcomePanel.vue";

const analysis = ref(null);
const registeredRisks = ref([]);
const history = ref([]);
const activeView = ref("Visão geral");
const loading = ref(false);
const analysisProgress = ref({
  percent: 0,
  message: "Preparando a análise...",
});
const error = ref("");
const success = ref("");

const viewDescription = computed(() => {
  if (activeView.value === "Cadastro de riscos") {
    return "Registre os perigos e parâmetros para incluir na próxima análise.";
  }
  if (activeView.value === "Histórico") {
    return "Acompanhe a evolução das notas e dos pareceres dos quatro P’s.";
  }
  return "Notas de severidade e probabilidade, matriz 4Ps e justificativas baseadas nas evidências.";
});

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
  const [risks, savedHistory] = await Promise.all([
    requestJson("/api/risks"),
    requestJson("/api/analysis/history"),
  ]);
  registeredRisks.value = risks;
  history.value = savedHistory;
}

async function pollAnalysisProgress() {
  let analysisStarted = false;
  while (loading.value) {
    try {
      const progress = await requestJson("/api/analysis/progress");
      if (progress.status === "running") {
        analysisStarted = true;
        analysisProgress.value = {
          percent: progress.percent,
          message: progress.message,
        };
      } else if (analysisStarted && progress.status === "completed") {
        analysisProgress.value = { percent: 100, message: progress.message };
        return null;
      } else if (analysisStarted && progress.status === "failed") {
        return new Error(progress.message);
      }
    } catch (cause) {
      return cause;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 400));
  }
  return null;
}

async function executeAnalysis() {
  loading.value = true;
  error.value = "";
  success.value = "";
  analysisProgress.value = {
    percent: 0,
    message: "Preparando a análise...",
  };
  const progressPolling = pollAnalysisProgress();
  try {
    analysis.value = await requestJson("/api/analysis", { method: "POST" });
    analysisProgress.value = {
      percent: 100,
      message: "Análise concluída.",
    };
    history.value = await requestJson("/api/analysis/history");
    registeredRisks.value = await requestJson("/api/risks");
    success.value = "Análise concluída e adicionada ao histórico do painel.";
  } catch (cause) {
    error.value = cause.message || "Não foi possível executar a análise.";
  } finally {
    loading.value = false;
    const progressError = await progressPolling;
    if (progressError && !error.value) {
      error.value = `Não foi possível atualizar o progresso: ${progressError.message}`;
    }
  }
}

function onRiskCreated(risk) {
  registeredRisks.value.unshift(risk);
  analysis.value = null;
  error.value = "";
  success.value = "Risco cadastrado. Execute uma nova análise para incluí-lo nos resultados.";
}

function onRiskUpdated(updatedRisk) {
  const index = registeredRisks.value.findIndex((risk) => risk.id === updatedRisk.id);
  if (index !== -1) registeredRisks.value[index] = updatedRisk;
  analysis.value = null;
  error.value = "";
  success.value = "As avaliações das quatro dimensões foram atualizadas.";
}

function onRiskDeleted(riskId) {
  registeredRisks.value = registeredRisks.value.filter((risk) => risk.id !== riskId);
  analysis.value = null;
  error.value = "";
  success.value = "Risco excluído, incluindo controles, ocorrências e resultados associados.";
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
        <div class="breadcrumb">Painel <span>/</span> <strong>{{ activeView }}</strong></div>
        <div class="topbar-meta"><span class="live-dot"></span> Base local SQLite <i></i> Avaliação matricial 4Ps</div>
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
            {{ loading ? "Classificando notas..." : "Executar análise" }}
          </button>
        </div>

        <div v-if="error" class="notice error-notice" role="alert">
          <span>!</span><div><strong>Não foi possível concluir a operação</strong><p>{{ error }}</p></div>
        </div>
        <div v-if="success" class="notice success-notice" role="status">
          <span>✓</span><div><strong>Operação concluída</strong><p>{{ success }}</p></div>
        </div>
        <section v-if="loading" class="analysis-progress-panel" role="status">
          <div class="analysis-progress-heading">
            <strong>Executando análise 4Ps</strong>
            <span>{{ analysisProgress.percent }}%</span>
          </div>
          <div
            class="analysis-progress-track"
            role="progressbar"
            :aria-valuenow="analysisProgress.percent"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-label="Progresso da análise de risco"
          >
            <span :style="{ width: `${analysisProgress.percent}%` }"></span>
          </div>
          <p>{{ analysisProgress.message }}</p>
        </section>

        <RiskRegistration
          v-if="activeView === 'Cadastro de riscos'"
          :risks="registeredRisks"
          @created="onRiskCreated"
          @updated="onRiskUpdated"
          @deleted="onRiskDeleted"
        />

        <section v-else-if="activeView === 'Histórico'" class="rating-history-page">
          <HistoryChart :history="history" />
        </section>

        <template v-else-if="analysis">
          <div class="analysis-banner">
            <span class="check-mark">✓</span>
            <div><strong>Análise matricial 4Ps concluída</strong><p>Notas, classificações e justificativas salvas no SQLite.</p></div>
            <span class="sim-count">{{ analysis.resumo.quantidade_notas }} notas avaliadas</span>
          </div>
          <div v-if="analysis.resumo.herdados_pendentes_revisao || analysis.resumo.justificativas_pendentes" class="notice inherited-notice" role="note">
            <span>i</span>
            <div>
              <strong>Há notas ou justificativas que precisam de revisão</strong>
              <p>{{ analysis.resumo.herdados_pendentes_revisao }} notas herdadas e {{ analysis.resumo.justificativas_pendentes }} justificativas pendentes. Confira as evidências e revise os riscos em “Cadastro de riscos”.</p>
            </div>
          </div>

          <RiskVerdictPanel
            :risks="analysis.riscos"
            :portfolio-decision="analysis.resumo.parecer_carteira"
          />

          <section class="metric-grid" aria-label="Resumo das notas dos quatro P's">
            <MetricCard
              label="RISCOS AVALIADOS"
              :value="String(analysis.resumo.quantidade_riscos)"
              caption="Riscos com os quatro P’s"
              icon="◇"
            />
            <MetricCard
              label="FAVORÁVEIS"
              :value="String(analysis.resumo.riscos_favoraveis)"
              caption="Todos os P’s na faixa baixa"
              icon="✓"
            />
            <MetricCard
              label="NÃO FAVORÁVEIS"
              :value="String(analysis.resumo.riscos_nao_favoraveis)"
              caption="Ao menos um P médio ou alto"
              icon="!"
            />
            <MetricCard
              label="NOTAS DOS 4Ps"
              :value="String(analysis.resumo.quantidade_notas)"
              caption="Severidade × probabilidade"
              icon="4P"
            />
          </section>

          <section class="analytics-grid">
            <DimensionComparisonChart :dimensions="analysis.resumo.dimensoes" />
            <RiskMatrix :risks="analysis.riscos" />
          </section>

          <section class="content-grid">
            <article class="panel risks-panel">
              <div class="panel-heading table-heading">
                <div><p class="eyebrow">NOTAS E CLASSIFICAÇÕES</p><h2>Riscos analisados</h2></div>
                <span class="count-pill">{{ analysis.resumo.quantidade_riscos }} riscos</span>
              </div>
              <div class="table-scroll">
                <table>
                  <thead><tr><th>RISCO</th><th>CATEGORIA</th><th>NOTAS 4Ps</th><th>PARECER</th><th>JUSTIFICATIVA</th></tr></thead>
                  <tbody>
                    <tr v-for="risk in analysis.riscos" :key="risk.id">
                      <td><strong>{{ risk.risco }}</strong><small>{{ risk.descricao || "Sem descrição" }}</small></td>
                      <td><span class="category-tag">{{ risk.categoria }}</span></td>
                      <td class="dimension-summary">
                        <span v-for="dimension in risk.dimensoes" :key="dimension.dimension">
                          {{ dimension.dimension.replace("Políticas governamentais", "Políticas") }} {{ dimension.matrix_score }}/25 · {{ dimension.classification }}
                        </span>
                      </td>
                      <td><span class="risk-level" :class="risk.parecer_final.status === 'Favorável' ? 'baixo' : 'alto'">{{ risk.parecer_final.status }}</span></td>
                      <td>{{ risk.parecer_final.justificativa }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <footer class="table-footer"><span>{{ analysis.riscos.length }} riscos analisados</span><span>Notas da matriz de severidade × probabilidade</span></footer>
            </article>
            <ReportCard :download-report="downloadReport" />
          </section>
        </template>

        <WelcomePanel v-else :loading="loading" @run-analysis="executeAnalysis" />

        <footer class="page-footer"><span>RISCO EM PERSPECTIVA <i>·</i> 4Ps</span><span>MATRIZ DE SEVERIDADE × PROBABILIDADE</span></footer>
      </section>
    </main>
  </div>
</template>
