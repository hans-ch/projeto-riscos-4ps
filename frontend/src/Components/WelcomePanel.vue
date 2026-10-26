<script setup>
defineProps({
  loading: { type: Boolean, default: false },
});

defineEmits(["run-analysis"]);
</script>

<template>
  <section class="welcome-panel">
    <div class="welcome-copy">
      <p class="eyebrow">AVALIAÇÃO MATRICIAL 4Ps</p>
      <h2>Entenda as notas.<br /><em>Conheça as evidências.</em></h2>
      <p>Classifique severidade e probabilidade por dimensão, entenda a nota de cada P e gere justificativas com IA local.</p>
      <button class="text-button" :disabled="loading" @click="$emit('run-analysis')">
        {{ loading ? "Calculando..." : "Começar análise" }} <span>→</span>
      </button>
    </div>
    <div class="welcome-visual">
      <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div>
      <div class="visual-core"><span>4Ps</span><small>1–25</small></div>
      <span class="orbit-label label-top">NOTAS</span><span class="orbit-label label-bottom">EVIDÊNCIAS</span>
    </div>
  </section>
</template>
