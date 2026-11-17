<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  /** Completion between 0 and 100. */
  percent: number
  tone?: 'lime' | 'violet' | 'orange'
}>()

const clamped = computed(() => Math.min(100, Math.max(0, props.percent)))
</script>

<template>
  <div class="progress" :class="tone ?? 'lime'">
    <div class="head">
      <span>{{ label }}</span>
      <strong class="sy-num">{{ clamped }} %</strong>
    </div>
    <div
      class="track sy-hatch"
      role="progressbar"
      :aria-label="label"
      :aria-valuenow="clamped"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div class="fill" :style="{ width: clamped + '%' }" />
    </div>
  </div>
</template>

<style scoped>
.progress {
  --tone: var(--sy-lime);
}

.progress.violet {
  --tone: var(--sy-violet);
}

.progress.orange {
  --tone: var(--sy-orange);
}

.head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.4rem;
  font-size: 0.85rem;
}

.track {
  height: 0.9rem;
  border-radius: var(--sy-radius-pill);
  background-color: var(--sy-surface-3);
  color: var(--sy-muted);
  overflow: hidden;
}

.fill {
  height: 100%;
  border-radius: var(--sy-radius-pill);
  background: var(--tone);
}
</style>
