<script setup lang="ts">
import { reactive, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { useToast } from 'primevue/usetoast'

import { changePassword } from '@/api/auth'
import { ApiError, type FieldErrors } from '@/api/http'

const toast = useToast()

const form = reactive({ old: '', next: '', confirm: '' })
const errors = ref<FieldErrors>({})
const formError = ref<string | null>(null)
const saving = ref(false)

async function submit() {
  if (saving.value) return
  errors.value = {}
  formError.value = null

  if (form.next !== form.confirm) {
    errors.value = { confirm: ['Les deux mots de passe ne correspondent pas.'] }
    return
  }

  saving.value = true
  try {
    await changePassword(form.old, form.next)
    Object.assign(form, { old: '', next: '', confirm: '' })
    toast.add({
      severity: 'success',
      summary: 'Mot de passe modifié',
      detail: 'Vos autres sessions ont été fermées.',
      life: 4000,
    })
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      errors.value = e.fieldErrors
    } else if (!(e instanceof ApiError && e.status === 401)) {
      formError.value = 'Enregistrement impossible pour le moment. Réessayez dans un instant.'
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="sy-card panel">
    <div class="sy-card-header">
      <h2 class="sy-card-title">
        <span class="sy-icon"><i class="pi pi-lock" aria-hidden="true" /></span>
        Changer le mot de passe
      </h2>
    </div>

    <form novalidate @submit.prevent="submit">
      <Message v-if="formError" severity="error" :closable="false" data-test="form-error">
        {{ formError }}
      </Message>

      <div class="field">
        <label for="old-password">Mot de passe actuel</label>
        <Password
          v-model="form.old"
          input-id="old-password"
          :input-props="{ autocomplete: 'current-password' }"
          :invalid="!!errors.old_password"
          :feedback="false"
          toggle-mask
          fluid
        />
        <small v-for="message in errors.old_password" :key="message" data-test="error-old">
          {{ message }}
        </small>
      </div>

      <div class="field">
        <label for="new-password">Nouveau mot de passe</label>
        <Password
          v-model="form.next"
          input-id="new-password"
          :input-props="{ autocomplete: 'new-password' }"
          :invalid="!!errors.new_password"
          :feedback="false"
          toggle-mask
          fluid
        />
        <small v-for="message in errors.new_password" :key="message" data-test="error-new">
          {{ message }}
        </small>
      </div>

      <div class="field">
        <label for="confirm-password">Confirmer le nouveau mot de passe</label>
        <Password
          v-model="form.confirm"
          input-id="confirm-password"
          :input-props="{ autocomplete: 'new-password' }"
          :invalid="!!errors.confirm"
          :feedback="false"
          toggle-mask
          fluid
        />
        <small v-for="message in errors.confirm" :key="message" data-test="error-confirm">
          {{ message }}
        </small>
      </div>

      <div class="actions">
        <Button
          type="submit"
          label="Enregistrer"
          severity="contrast"
          :loading="saving"
          :disabled="saving || !form.old || !form.next || !form.confirm"
        />
      </div>
    </form>
  </section>
</template>

<style scoped>
.panel {
  max-width: 32rem;
}

form {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-4);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-2);
}

label {
  font-size: 0.9rem;
  font-weight: 600;
}

small {
  color: var(--sy-danger);
  font-size: 0.85rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
