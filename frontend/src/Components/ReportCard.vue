<script setup>
defineProps({
  downloadReport: { type: Function, required: true },
});
</script>

<template>
  <article class="panel report-panel">
    <div class="report-art"><span>FAIR</span><i>↗</i></div>
    <p class="eyebrow">RELATÓRIOS DA ANÁLISE</p>
    <h2>Leve os dados com você.</h2>
    <p>Exporte o relatório detalhado ou continue trabalhando com os resultados em uma planilha.</p>
    <button class="report-link" @click="downloadReport('html')">Abrir relatório completo <span>↗</span></button>
    <button class="report-link secondary" @click="downloadReport('excel')">Baixar planilha Excel <span>↓</span></button>
  </article>
</template>
