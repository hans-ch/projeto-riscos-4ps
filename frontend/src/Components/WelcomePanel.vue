<script setup>
defineProps({
  loading: { type: Boolean, default: false },
});

defineEmits(["run-analysis"]);
</script>

<template>
  <section class="welcome-panel">
    <div class="welcome-copy">
      <p class="eyebrow">ANÁLISE QUANTITATIVA</p>
      <h2>Entenda o risco.<br /><em>Antecipe o impacto.</em></h2>
      <p>Execute uma simulação para visualizar a exposição da carteira, comparar controles e gerar relatórios FAIR.</p>
      <button class="text-button" :disabled="loading" @click="$emit('run-analysis')">
        {{ loading ? "Calculando..." : "Começar análise" }} <span>→</span>
      </button>
    </div>
    <div class="welcome-visual">
      <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div>
      <div class="visual-core"><span>FAIR</span><small>10.000</small></div>
      <span class="orbit-label label-top">EXPOSIÇÃO</span><span class="orbit-label label-bottom">CONTROLES</span>
    </div>
  </section>
</template>
