<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'

import { documentUrl, type Document } from '@/features/agents/api/documents'
import {
  attachDocument,
  detachDocument,
  listEvenements,
  type EvenementEtat,
  type PieceEvenement,
  type PieceExigee,
} from '@/features/agents/api/evenements'
import AddDocumentDialog from '@/features/agents/components/AddDocumentDialog.vue'
import AttachDocumentDialog from '@/features/agents/components/AttachDocumentDialog.vue'
import { useDocumentReferences } from '@/features/agents/composables/useDocumentReferences'
import { useAuthStore } from '@/features/auth/stores/auth'
import { formatDate } from '@/shared/utils/dates'

/**
 * An agent's events and the pieces they require (documents on events D23, D24): one card
 * per event, newest first, its status, each required piece ticked or missing with its
 * documents, and for editors "Joindre" and "Retirer le lien". Mounted by the "Pièces des
 * agents" page, then by the agent summary page of roadmap 2.10.
 */
const props = defineProps<{
  agentId: number
  /** Bumped by the page when the documents changed elsewhere: reload. */
  version?: number
}>()
const emit = defineEmits<{ change: [] }>()

const auth = useAuthStore()
const toast = useToast()
const peutJoindre = computed(() => auth.can('agents.add_piecejointe'))
const peutRetirer = computed(() => auth.can('agents.change_piecejointe'))
const peutDeposer = computed(() => peutJoindre.value && auth.can('agents.add_document'))

const evenements = ref<EvenementEtat[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const joindre = ref(false)
const ajout = ref(false)
const cible = ref<EvenementEtat | null>(null)
const piece = ref<PieceExigee | null>(null)
const typeCode = ref<string | null>(null)
const { types, maxMo, load: loadReferences } = useDocumentReferences()

let latest = 0

async function load() {
  const call = ++latest
  loading.value = true
  error.value = null
  try {
    const rows = await listEvenements(props.agentId)
    if (call !== latest) return
    evenements.value = rows
  } catch (e) {
    if (call !== latest) return
    error.value = e instanceof Error ? e.message : String(e)
    evenements.value = []
  } finally {
    if (call === latest) loading.value = false
  }
}

watch(
  () => [props.agentId, props.version],
  () => void load(),
)
onMounted(() => {
  void load()
  if (peutDeposer.value) void loadReferences()
})

function remplace(etat: EvenementEtat) {
  evenements.value = evenements.value.map((e) => (e.cle === etat.cle ? etat : e))
}

function statut(e: EvenementEtat): string {
  if (e.complet) return 'Complet'
  const n = e.manquantes.length
  return n === 1 ? '1 pièce manquante' : `${n} pièces manquantes`
}

function ouvrirJoindre(e: EvenementEtat, p: PieceExigee | null) {
  cible.value = e
  piece.value = p
  joindre.value = true
}

function joint(etat: EvenementEtat) {
  remplace(etat)
  toast.add({ severity: 'success', summary: 'Pièce jointe', detail: etat.libelle, life: 3000 })
}

function deposer(code: string | null) {
  typeCode.value = code
  ajout.value = true
}

/** A new document was uploaded from an event: attach it straight away (D24). */
async function depose(document: Document) {
  emit('change')
  if (!cible.value) return
  try {
    joint(await attachDocument(props.agentId, cible.value, document.id))
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function detacher(e: EvenementEtat, document: PieceEvenement) {
  if (document.lien === null) return
  try {
    remplace(await detachDocument(props.agentId, e, document.lien))
    toast.add({
      severity: 'success',
      summary: 'Lien retiré',
      detail: document.nom_original,
      life: 3000,
    })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}
</script>

<template>
  <section class="evenements" aria-label="Événements et pièces exigées" data-test="evenements">
    <h3 class="titre">Événements et pièces exigées</h3>

    <Message v-if="error" severity="error" :closable="false" data-test="evenements-error">
      {{ error }}
    </Message>
    <p v-if="loading && evenements.length === 0" class="sy-muted">Chargement des événements…</p>
    <p
      v-else-if="!loading && !error && evenements.length === 0"
      class="sy-muted"
      data-test="evenements-vide"
    >
      Aucun événement : l'agent n'a pas encore de contrat.
    </p>

    <article
      v-for="e in evenements"
      :key="e.cle"
      class="carte"
      :class="{ incomplet: !e.complet }"
      data-test="evenement"
    >
      <header class="entete">
        <div>
          <strong>{{ e.evenement_libelle }}</strong>
          <span class="sy-muted sy-num"> — {{ formatDate(e.date) }}</span>
          <p class="sy-muted libelle">{{ e.libelle }}</p>
        </div>
        <Tag
          v-if="e.evenement"
          :value="statut(e)"
          :severity="e.complet ? 'success' : 'warn'"
          data-test="evenement-statut"
        />
      </header>

      <p v-if="!e.evenement" class="sy-muted note">
        Fait partie de l'engagement : ses pièces sont celles du contrat.
      </p>
      <p v-else-if="e.pieces.length === 0" class="sy-muted note">
        Aucune pièce exigée pour cet événement à cette date.
      </p>

      <ul class="pieces">
        <li v-for="p in e.pieces" :key="p.code" class="piece" data-test="piece">
          <i
            :class="p.satisfaite ? 'pi pi-check-circle ok' : 'pi pi-circle manque'"
            :aria-label="p.satisfaite ? 'Fournie' : 'Manquante'"
          />
          <div class="corps">
            <span>
              {{ p.nom }}
              <span class="sy-muted">{{ p.obligatoire ? 'obligatoire' : 'facultative' }}</span>
            </span>
            <span v-for="d in p.documents" :key="d.id" class="doc">
              <a :href="documentUrl(agentId, d.id)" target="_blank" rel="noopener">
                {{ d.nom_original }}
              </a>
              <Button
                v-if="peutRetirer"
                icon="pi pi-times"
                text
                size="small"
                severity="secondary"
                :aria-label="`Retirer le lien vers ${d.nom_original}`"
                :title="`Retirer le lien vers ${d.nom_original}`"
                data-test="piece-detacher"
                @click="detacher(e, d)"
              />
            </span>
            <span v-if="p.confidentielles > 0" class="sy-muted" data-test="piece-confidentielle">
              <i class="pi pi-lock" />
              {{
                p.confidentielles === 1
                  ? 'Pièce confidentielle fournie'
                  : `${p.confidentielles} pièces confidentielles fournies`
              }}
            </span>
          </div>
          <Button
            v-if="peutJoindre && !p.satisfaite"
            label="Joindre"
            icon="pi pi-link"
            size="small"
            severity="secondary"
            outlined
            data-test="piece-joindre"
            @click="ouvrirJoindre(e, p)"
          />
        </li>
      </ul>

      <div v-if="e.autres.length > 0 || e.autres_confidentielles > 0" class="autres">
        <span class="sy-muted">Autres pièces jointes :</span>
        <span v-for="d in e.autres" :key="d.id" class="doc">
          <a :href="documentUrl(agentId, d.id)" target="_blank" rel="noopener">
            {{ d.nom_original }}
          </a>
          <Button
            v-if="peutRetirer"
            icon="pi pi-times"
            text
            size="small"
            severity="secondary"
            :aria-label="`Retirer le lien vers ${d.nom_original}`"
            data-test="piece-detacher"
            @click="detacher(e, d)"
          />
        </span>
        <span v-if="e.autres_confidentielles > 0" class="sy-muted">
          <i class="pi pi-lock" /> {{ e.autres_confidentielles }} confidentielle(s)
        </span>
      </div>
      <Button
        v-if="peutJoindre && e.evenement"
        label="Joindre une autre pièce"
        icon="pi pi-plus"
        size="small"
        severity="secondary"
        text
        data-test="evenement-joindre"
        @click="ouvrirJoindre(e, null)"
      />
    </article>

    <AttachDocumentDialog
      v-if="peutJoindre"
      v-model:visible="joindre"
      :agent-id="agentId"
      :evenement="cible"
      :piece="piece"
      :peut-deposer="peutDeposer"
      @joint="joint"
      @deposer="deposer"
    />
    <AddDocumentDialog
      v-if="peutDeposer"
      v-model:visible="ajout"
      :agent-id="agentId"
      :types="types"
      :max-mo="maxMo"
      :type-code="typeCode"
      @depose="depose"
    />
  </section>
</template>

<style scoped>
.evenements {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-3);
  margin-top: var(--sy-space-5);
}

.titre {
  margin: 0;
  font-size: 1rem;
}

.carte {
  border: 1px solid var(--sy-border);
  border-radius: var(--sy-radius-md);
  padding: var(--sy-space-3) var(--sy-space-4);
  background: var(--sy-surface);
}

.carte.incomplet {
  border-left: 4px solid var(--sy-warning);
}

.entete {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--sy-space-3);
}

.libelle,
.note {
  margin: var(--sy-space-1) 0 0;
  font-size: 0.85rem;
}

.pieces {
  list-style: none;
  margin: var(--sy-space-3) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-2);
}

.piece {
  display: flex;
  align-items: flex-start;
  gap: var(--sy-space-2);
}

.piece .pi {
  margin-top: 0.2rem;
}

.ok {
  color: var(--sy-success);
}

.manque {
  color: var(--sy-warning);
}

.corps {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-1);
}

.doc {
  display: inline-flex;
  align-items: center;
  gap: var(--sy-space-1);
  font-size: 0.85rem;
}

.doc a {
  color: var(--sy-text);
}

.autres {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sy-space-2);
  margin-top: var(--sy-space-3);
  font-size: 0.85rem;
}
</style>
