<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'

import ProgressPill from '@/components/ui/ProgressPill.vue'

const surfaces = ['--sy-bg', '--sy-surface', '--sy-surface-2', '--sy-surface-3', '--sy-border']
const accents = ['--sy-lime', '--sy-violet', '--sy-orange', '--sy-inverse']
const statuses = ['--sy-success', '--sy-warning', '--sy-danger', '--sy-text', '--sy-muted']
</script>

<template>
  <div class="guide">
    <section class="sy-card">
      <h2>Couleurs</h2>
      <h3>Surfaces</h3>
      <ul class="swatches">
        <li v-for="token in surfaces" :key="token">
          <span :style="{ background: `var(${token})` }" /><code>{{ token }}</code>
        </li>
      </ul>
      <h3>Accents</h3>
      <ul class="swatches">
        <li v-for="token in accents" :key="token">
          <span :style="{ background: `var(${token})` }" /><code>{{ token }}</code>
        </li>
      </ul>
      <h3>Texte et statuts</h3>
      <ul class="swatches">
        <li v-for="token in statuses" :key="token">
          <span :style="{ background: `var(${token})` }" /><code>{{ token }}</code>
        </li>
      </ul>
    </section>

    <section class="sy-card">
      <h2>Typographie</h2>
      <p class="t-display">Titre de page — 412 agents</p>
      <p class="t-title">Titre de carte</p>
      <p>Texte courant. Le dossier de l'agent est la source unique de vérité.</p>
      <p class="sy-muted">Texte secondaire, légendes et libellés.</p>
      <p class="sy-num t-figure">1 024 300,00 USD</p>
    </section>

    <section class="sy-card">
      <h2>Boutons</h2>
      <div class="row">
        <Button label="Valider" icon="pi pi-check-circle" />
        <Button label="Enregistrer" severity="contrast" />
        <Button label="Annuler" severity="secondary" />
        <Button label="Exporter" severity="secondary" variant="outlined" icon="pi pi-file" />
        <Button label="Rejeter" severity="danger" variant="outlined" />
        <Button label="Indisponible" disabled />
      </div>
    </section>

    <section class="sy-card">
      <h2>Champs et statuts</h2>
      <div class="row">
        <InputText placeholder="Matricule" aria-label="Matricule" />
        <InputText model-value="Cadre moyen" aria-label="Classification" />
        <InputText placeholder="Champ invalide" invalid aria-label="Champ invalide" />
      </div>
      <div class="row">
        <Tag severity="success" value="Validé" />
        <Tag severity="warn" value="En attente" />
        <Tag severity="danger" value="Rejeté" />
        <Tag severity="info" value="Brouillon" />
        <Tag severity="secondary" value="Archivé" />
        <Tag severity="contrast" value="Actif" />
      </div>
    </section>

    <section class="sy-card">
      <h2>Progression et hachures</h2>
      <div class="stack">
        <ProgressPill label="Lime — avancement principal" :percent="72" />
        <ProgressPill label="Violet — série secondaire" :percent="48" tone="violet" />
        <ProgressPill label="Orange — attention" :percent="24" tone="orange" />
      </div>
      <p class="sy-muted note">
        La hachure représente ce qui reste, ce qui est prévu ou ce qui manque ; jamais une valeur
        réalisée.
      </p>
    </section>
  </div>
</template>

<style scoped>
.guide {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(24rem, 1fr));
  gap: var(--sy-space-4);
}

h2 {
  font-size: 1.05rem;
  margin-bottom: var(--sy-space-4);
}

h3 {
  margin: var(--sy-space-4) 0 var(--sy-space-2);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--sy-muted);
}

.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sy-space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.swatches li {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.swatches span {
  width: 5.5rem;
  height: 3.2rem;
  border-radius: var(--sy-radius-md);
  border: 1px solid var(--sy-border);
}

code {
  font-size: 0.72rem;
  color: var(--sy-muted);
}

.t-display {
  font-size: 1.6rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.t-title {
  font-size: 1.05rem;
  font-weight: 600;
  margin: var(--sy-space-2) 0;
}

.t-figure {
  margin-top: var(--sy-space-3);
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sy-space-3);
}

.row + .row {
  margin-top: var(--sy-space-4);
}

.stack {
  display: grid;
  gap: var(--sy-space-4);
}

.note {
  margin-top: var(--sy-space-4);
  font-size: 0.85rem;
}
</style>
