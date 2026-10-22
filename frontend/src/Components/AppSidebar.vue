<script setup>
defineProps({
  activeView: { type: String, required: true },
});

defineEmits(["navigate"]);

const items = [
  { label: "Visão geral", icon: "◫" },
  { label: "Cadastro de riscos", icon: "◇" },
  { label: "Benchmark", icon: "⌁" },
];
</script>

<template>
  <aside class="sidebar">
    <a class="brand" href="#" aria-label="Risco em Perspectiva">
      <span class="brand-mark">4P</span>
      <span class="brand-copy"><strong>perspectiva</strong><small>GESTÃO DE RISCOS</small></span>
    </a>
    <div class="nav-label">ESPAÇO DE TRABALHO</div>
    <nav class="navigation" aria-label="Navegação principal">
      <button
        v-for="item in items"
        :key="item.label"
        :class="{ active: activeView === item.label }"
        @click="$emit('navigate', item.label)"
      >
        <span class="nav-icon">{{ item.icon }}</span>{{ item.label }}
      </button>
    </nav>
    <div class="sidebar-bottom">
      <span class="status-dot"></span>
      <div><strong>Modelo OpenFAIR</strong><small>10 mil simulações por risco</small></div>
    </div>
  </aside>
</template>
