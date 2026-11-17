<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="sy-card denied" data-test="access-denied">
    <span class="sy-icon big"><i class="pi pi-lock" aria-hidden="true" /></span>
    <h2>Accès refusé</h2>
    <p class="sy-muted">
      Votre profil ne donne pas accès à ce module. Si vous en avez besoin, adressez-vous à
      l'administrateur du système.
    </p>
    <RouterLink to="/" class="back">Retour au tableau de bord</RouterLink>
  </section>
</template>

<style scoped>
.denied {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sy-space-3);
  padding: 4rem var(--sy-space-5);
  text-align: center;
}

.denied p {
  max-width: 32rem;
}

.big {
  width: 3.5rem;
  height: 3.5rem;
  font-size: 1.3rem;
  background: var(--sy-danger-soft);
  color: var(--sy-danger);
}

.back {
  margin-top: var(--sy-space-2);
  padding: 0.6rem 1.1rem;
  border-radius: var(--sy-radius-pill);
  background: var(--sy-inverse);
  color: var(--sy-on-inverse);
  font-weight: 600;
  text-decoration: none;
}
</style>
