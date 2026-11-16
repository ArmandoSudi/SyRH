<script setup lang="ts">
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'

import DonutChart, { type DonutSegment } from '@/components/ui/DonutChart.vue'
import PillBars, { type PillBar } from '@/components/ui/PillBars.vue'
import ProgressPill from '@/components/ui/ProgressPill.vue'
import StatCard from '@/components/ui/StatCard.vue'

// Demonstration data only: this screen showcases the design system.
// It is replaced by API data when the dashboard phase of the roadmap is built.

const effectifParDirection: PillBar[] = [
  { label: 'Technique', value: 96, extra: 8 },
  { label: 'Juridique', value: 41, extra: 3 },
  { label: 'Finances', value: 58 },
  { label: 'RH', value: 34, extra: 4 },
  { label: 'Marchés', value: 47 },
  { label: 'Informatique', value: 39, extra: 6, tone: 'violet' },
  { label: 'Provinces', value: 97, extra: 12, tone: 'violet' },
]

const categories: DonutSegment[] = [
  { label: 'Cadres supérieurs', value: 48, color: 'var(--sy-orange)' },
  { label: 'Cadres moyens', value: 131, color: 'var(--sy-lime)' },
  { label: 'Agents de maîtrise', value: 154, color: 'var(--sy-violet)' },
  { label: "Agents d'exécution", value: 79, color: 'var(--sy-muted)' },
]

const echeances = [
  { quand: 'Dans 12 jours', quoi: "Fin de période d'essai", qui: 'K. Ilunga', ton: 'warn' },
  { quand: 'Dans 3 semaines', quoi: 'Enfant atteignant 25 ans', qui: 'M. Kabeya', ton: 'info' },
  { quand: 'Dans 2 mois', quoi: 'Fin de mise en disponibilité', qui: 'J. Mbuyi', ton: 'warn' },
  { quand: 'Dans 3 mois', quoi: 'Retraite — 65 ans', qui: 'P. Lukusa', ton: 'danger' },
  {
    quand: 'Dans 6 mois',
    quoi: 'Retraite — 30 ans de carrière',
    qui: 'A. Tshibanda',
    ton: 'danger',
  },
]

const mouvements = [
  {
    matricule: 'AR/00412/26',
    agent: 'Nsimba Grâce',
    evenement: 'Engagement',
    date: '02/11/2026',
    statut: 'Validé',
  },
  {
    matricule: 'AR/00187/17',
    agent: 'Kalala Joseph',
    evenement: 'Promotion',
    date: '01/11/2026',
    statut: 'En attente',
  },
  {
    matricule: 'AR/00233/19',
    agent: 'Mwamba Esther',
    evenement: 'Congé de maternité',
    date: '28/10/2026',
    statut: 'Validé',
  },
  {
    matricule: 'AR/00098/12',
    agent: 'Banza Patrick',
    evenement: 'Intérim',
    date: '27/10/2026',
    statut: 'Rejeté',
  },
  {
    matricule: 'AR/00301/22',
    agent: 'Lumbala Sarah',
    evenement: 'Naissance',
    date: '21/10/2026',
    statut: 'En attente',
  },
]

const statutSeverity: Record<string, string> = {
  Validé: 'success',
  'En attente': 'warn',
  Rejeté: 'danger',
}

const sparkline = [38, 52, 44, 70, 58, 86, 64]
</script>

<template>
  <div class="dashboard">
    <p class="demo">
      <Tag severity="secondary" value="Données de démonstration" />
    </p>

    <section class="stats" aria-label="Indicateurs clés">
      <StatCard
        featured
        label="Effectif total"
        value="412"
        icon="pi pi-users"
        :delta="2"
        caption="vs mois dernier"
      >
        <div class="spark">
          <span v-for="(h, i) in sparkline" :key="i" :style="{ height: h + '%' }" />
        </div>
      </StatCard>
      <StatCard
        label="Masse salariale"
        value="1 024 300 USD"
        icon="pi pi-wallet"
        :delta="1"
        caption="vs mois dernier"
      />
      <StatCard
        label="Taux de présence"
        value="94 %"
        icon="pi pi-calendar"
        :delta="-1"
        caption="vs mois dernier"
      />
      <StatCard label="Bons de soins émis" value="128" icon="pi pi-heart" caption="ce mois" />
    </section>

    <section class="grid two">
      <article class="sy-card">
        <div class="sy-card-header">
          <h2 class="sy-card-title">
            <span class="sy-icon"><i class="pi pi-sitemap" aria-hidden="true" /></span>
            Effectif par direction
          </h2>
          <div class="sy-legend">
            <span style="--dot: var(--sy-lime)">Siège</span>
            <span style="--dot: var(--sy-violet)">Multi-sites</span>
            <span>Postes vacants (hachuré)</span>
          </div>
        </div>
        <PillBars :bars="effectifParDirection" label="Effectif par direction" />
      </article>

      <article class="sy-card">
        <div class="sy-card-header">
          <h2 class="sy-card-title">
            <span class="sy-icon"><i class="pi pi-id-card" aria-hidden="true" /></span>
            Répartition par catégorie
          </h2>
        </div>
        <DonutChart :segments="categories" center-label="agents" center-value="412" />
      </article>
    </section>

    <section class="grid two">
      <article class="sy-card">
        <div class="sy-card-header">
          <h2 class="sy-card-title">
            <span class="sy-icon"><i class="pi pi-clock" aria-hidden="true" /></span>
            Échéances à venir
          </h2>
        </div>
        <ul class="deadlines">
          <li v-for="item in echeances" :key="item.quoi + item.qui">
            <div>
              <strong>{{ item.quoi }}</strong>
              <span class="sy-muted">{{ item.qui }}</span>
            </div>
            <Tag :severity="item.ton" :value="item.quand" />
          </li>
        </ul>
      </article>

      <article class="sy-card">
        <div class="sy-card-header">
          <h2 class="sy-card-title">
            <span class="sy-icon"><i class="pi pi-check-circle" aria-hidden="true" /></span>
            Clôture de la paie
          </h2>
          <span class="sy-muted">Novembre 2026</span>
        </div>
        <div class="progress-list">
          <ProgressPill label="Éléments variables validés" :percent="82" />
          <ProgressPill label="Écarts justifiés" :percent="64" tone="violet" />
          <ProgressPill label="Factures de soins contrôlées" :percent="35" tone="orange" />
        </div>
      </article>
    </section>

    <article class="sy-card">
      <div class="sy-card-header">
        <h2 class="sy-card-title">
          <span class="sy-icon"><i class="pi pi-file" aria-hidden="true" /></span>
          Derniers mouvements
        </h2>
      </div>
      <DataTable :value="mouvements" data-key="matricule">
        <Column field="matricule" header="Matricule" />
        <Column field="agent" header="Agent" />
        <Column field="evenement" header="Événement" />
        <Column field="date" header="Date d'effet" />
        <Column header="Statut">
          <template #body="{ data }">
            <Tag :severity="statutSeverity[data.statut]" :value="data.statut" />
          </template>
        </Column>
      </DataTable>
    </article>
  </div>
</template>

<style scoped>
.dashboard {
  display: grid;
  gap: var(--sy-space-4);
}

.demo {
  margin-top: calc(-1 * var(--sy-space-3));
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13.5rem, 1fr));
  gap: var(--sy-space-4);
}

.grid.two {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr));
  gap: var(--sy-space-4);
}

.spark {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 3.2rem;
}

.spark span {
  width: 0.45rem;
  border-radius: var(--sy-radius-pill);
  background: currentColor;
  opacity: 0.35;
}

.spark span:nth-last-child(2) {
  opacity: 1;
}

.deadlines {
  margin: 0;
  padding: 0;
  list-style: none;
}

.deadlines li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sy-space-3);
  padding: 0.7rem 0;
}

.deadlines li + li {
  border-top: 1px solid var(--sy-border);
}

.deadlines div {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.deadlines strong {
  font-weight: 600;
}

.deadlines span {
  font-size: 0.85rem;
}

.progress-list {
  display: grid;
  gap: var(--sy-space-5);
  padding-top: var(--sy-space-2);
}
</style>
