<script setup lang="ts">
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'

import ClassificationTree from '@/features/referentiels/components/ClassificationTree.vue'
import FonctionsTable from '@/features/referentiels/components/FonctionsTable.vue'
import OrganisationTree from '@/features/referentiels/components/OrganisationTree.vue'
import SitesTable from '@/features/referentiels/components/SitesTable.vue'
import { useReferentielsStore } from '@/features/referentiels/stores/referentiels'

// Read-only: reference data is edited in Django admin until roadmap 1.9 (D27).
const store = useReferentielsStore()
</script>

<template>
  <section class="sy-card">
    <div class="sy-card-header">
      <h2 class="sy-card-title">
        <span class="sy-icon"><i class="pi pi-sitemap" aria-hidden="true" /></span>
        Référentiels
      </h2>
    </div>

    <Tabs v-model:value="store.onglet" lazy>
      <TabList>
        <Tab value="organisation" data-test="tab-organisation">Organisation</Tab>
        <Tab value="sites" data-test="tab-sites">Sites</Tab>
        <Tab value="classification" data-test="tab-classification">Classification</Tab>
        <Tab value="fonctions" data-test="tab-fonctions">Fonctions</Tab>
      </TabList>
      <TabPanels class="panels">
        <TabPanel value="organisation">
          <OrganisationTree />
        </TabPanel>
        <TabPanel value="sites">
          <SitesTable />
        </TabPanel>
        <TabPanel value="classification">
          <ClassificationTree />
        </TabPanel>
        <TabPanel value="fonctions">
          <FonctionsTable />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </section>
</template>

<style scoped>
.panels {
  padding: var(--sy-space-4) 0 0;
}
</style>
