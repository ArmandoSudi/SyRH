<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <section class="sy-card empty">
    <span class="sy-icon big"><i class="pi pi-clock" aria-hidden="true" /></span>
    <h2>{{ route.meta.title }}</h2>
    <p class="sy-muted">Ce module n'est pas encore développé. Voir la feuille de route.</p>
  </section>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sy-space-3);
  padding: 4rem var(--sy-space-5);
  text-align: center;
}

.big {
  width: 3.5rem;
  height: 3.5rem;
  font-size: 1.3rem;
}
</style>
