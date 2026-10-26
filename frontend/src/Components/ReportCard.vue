<script setup>
defineProps({
  downloadReport: { type: Function, required: true },
});
</script>

<template>
  <article class="panel report-panel">
    <div class="report-art"><span>4Ps</span><i>↗</i></div>
    <p class="eyebrow">RELATÓRIOS DA ANÁLISE</p>
    <h2>Leve os dados com você.</h2>
    <p>Exporte as notas, classificações, evidências e justificativas da avaliação.</p>
    <button class="report-link" @click="downloadReport('html')">Abrir relatório completo <span>↗</span></button>
    <button class="report-link secondary" @click="downloadReport('excel')">Baixar planilha Excel <span>↓</span></button>
  </article>
</template>
