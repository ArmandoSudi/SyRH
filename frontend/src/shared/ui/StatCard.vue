<script setup lang="ts">
defineProps<{
  label: string
  value: string
  icon: string
  /** Signed change vs the previous period, in percent. */
  delta?: number
  caption?: string
  /** The one highlighted card of a row: solid lime. */
  featured?: boolean
}>()
</script>

<template>
  <article class="stat sy-card" :class="{ featured }">
    <header>
      <span class="sy-icon"><i :class="icon" aria-hidden="true" /></span>
      <h3>{{ label }}</h3>
    </header>
    <div class="body">
      <div>
        <p class="value sy-num">{{ value }}</p>
        <p class="caption">
          <span v-if="delta !== undefined" class="delta" :class="{ down: delta < 0 }">
            <i
              :class="delta < 0 ? 'pi pi-arrow-down-right' : 'pi pi-arrow-up-right'"
              aria-hidden="true"
            />
            {{ Math.abs(delta) }} %
          </span>
          {{ caption }}
        </p>
      </div>
      <div class="viz" aria-hidden="true"><slot /></div>
    </div>
  </article>
</template>

<style scoped>
.stat {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--sy-space-5);
  min-height: 9.5rem;
}

header {
  display: flex;
  align-items: center;
  gap: var(--sy-space-3);
}

h3 {
  font-size: 0.95rem;
  font-weight: 500;
}

.body {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sy-space-3);
}

.value {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.caption {
  margin-top: 0.35rem;
  font-size: 0.8rem;
  color: var(--sy-muted);
}

.delta {
  font-weight: 600;
  color: var(--sy-success);
  margin-right: 0.25rem;
}

.delta i {
  font-size: 0.65rem;
}

.delta.down {
  color: var(--sy-danger);
}

.viz {
  color: var(--sy-lime);
}

.featured {
  background: var(--sy-lime);
  border-color: transparent;
  color: var(--sy-on-lime);
}

.featured .sy-icon {
  background: var(--sy-on-lime);
  color: var(--sy-lime);
}

.featured .caption,
.featured .delta,
.featured .viz {
  color: var(--sy-on-lime);
}
</style>
