<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  caption: { type: String, required: true },
  icon: { type: String, required: true },
  featured: { type: Boolean, default: false },
});
</script>

<template>
  <article class="metric-card" :class="{ featured }">
    <div class="metric-top"><span>{{ label }}</span><span class="metric-icon">{{ icon }}</span></div>
    <strong>{{ value }}</strong>
    <small>{{ caption }}</small>
  </article>
</template>
