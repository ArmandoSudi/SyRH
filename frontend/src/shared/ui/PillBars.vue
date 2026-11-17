<script setup lang="ts">
import { computed } from 'vue'

export interface PillBar {
  label: string
  value: number
  /** Accent used for the bar. Defaults to lime. */
  tone?: 'lime' | 'violet' | 'orange'
  /** Extra, hatched segment stacked above the bar (target, forecast, vacancy). */
  extra?: number
}

const props = defineProps<{
  bars: PillBar[]
  /** Accessible description of what the chart shows. */
  label: string
}>()

const max = computed(() => Math.max(1, ...props.bars.map((bar) => bar.value + (bar.extra ?? 0))))
</script>

<template>
  <ul class="bars" :aria-label="label">
    <li v-for="bar in bars" :key="bar.label" :class="bar.tone ?? 'lime'">
      <div class="track">
        <div
          v-if="bar.extra"
          class="extra sy-hatch"
          :style="{ height: (bar.extra / max) * 100 + '%' }"
        />
        <div class="fill" :style="{ height: (bar.value / max) * 100 + '%' }">
          <span class="value sy-num">{{ bar.value }}</span>
        </div>
      </div>
      <span class="name">{{ bar.label }}</span>
    </li>
  </ul>
</template>

<style scoped>
.bars {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: var(--sy-space-2);
  height: 14rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  display: flex;
  flex-direction: column;
  gap: var(--sy-space-2);
  min-width: 0;
  --tone: var(--sy-lime);
  --on-tone: var(--sy-on-lime);
}

li.violet {
  --tone: var(--sy-violet);
  --on-tone: var(--sy-on-violet);
}

li.orange {
  --tone: var(--sy-orange);
  --on-tone: var(--sy-on-orange);
}

.track {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 3px;
  min-height: 0;
}

.fill,
.extra {
  border-radius: var(--sy-radius-lg);
  min-height: 2.4rem;
}

.fill {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 0.3rem;
  background: var(--tone);
}

.extra {
  min-height: 0.75rem;
  color: var(--tone);
  border: 1px solid color-mix(in srgb, var(--tone) 45%, transparent);
}

.value {
  display: grid;
  place-items: center;
  min-width: 1.9rem;
  height: 1.9rem;
  padding: 0 0.3rem;
  border-radius: var(--sy-radius-pill);
  background: color-mix(in srgb, var(--on-tone) 88%, transparent);
  color: var(--tone);
  font-size: 0.75rem;
  font-weight: 600;
}

.name {
  font-size: 0.75rem;
  color: var(--sy-muted);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
