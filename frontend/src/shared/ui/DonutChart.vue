<script setup lang="ts">
import { computed } from 'vue'

export interface DonutSegment {
  label: string
  value: number
  /** Any CSS colour, normally a design token such as var(--sy-lime). */
  color: string
}

const props = defineProps<{
  segments: DonutSegment[]
  centerLabel: string
  centerValue: string
}>()

const RADIUS = 42
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const GAP = 5

const total = computed(() => props.segments.reduce((sum, segment) => sum + segment.value, 0))

const arcs = computed(() => {
  let offset = 0
  return props.segments.map((segment) => {
    const length = total.value ? (segment.value / total.value) * CIRCUMFERENCE : 0
    const arc = {
      ...segment,
      share: total.value ? Math.round((segment.value / total.value) * 100) : 0,
      dash: `${Math.max(length - GAP, 0)} ${CIRCUMFERENCE}`,
      offset: -offset,
    }
    offset += length
    return arc
  })
})
</script>

<template>
  <div class="donut">
    <div class="ring">
      <svg viewBox="0 0 100 100" role="img" :aria-label="`${centerLabel} : ${centerValue}`">
        <circle
          v-for="arc in arcs"
          :key="arc.label"
          cx="50"
          cy="50"
          :r="RADIUS"
          fill="none"
          :stroke="arc.color"
          stroke-width="13"
          stroke-linecap="round"
          :stroke-dasharray="arc.dash"
          :stroke-dashoffset="arc.offset"
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div class="center">
        <strong class="sy-num">{{ centerValue }}</strong>
        <span>{{ centerLabel }}</span>
      </div>
    </div>
    <ul>
      <li v-for="arc in arcs" :key="arc.label">
        <span class="dot" :style="{ background: arc.color }" />
        <span class="name">{{ arc.label }}</span>
        <span class="count sy-num">{{ arc.value }}</span>
        <span class="share sy-num">{{ arc.share }} %</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.donut {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sy-space-5);
}

.ring {
  position: relative;
  flex: none;
  width: 11rem;
  height: 11rem;
}

svg {
  width: 100%;
  height: 100%;
}

.center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.center strong {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.1;
}

.center span {
  font-size: 0.8rem;
  color: var(--sy-muted);
}

ul {
  flex: 1;
  min-width: 12rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  display: grid;
  grid-template-columns: auto 1fr auto 3.2rem;
  align-items: center;
  gap: var(--sy-space-3);
  padding: 0.45rem 0;
  font-size: 0.88rem;
}

li + li {
  border-top: 1px solid var(--sy-border);
}

.dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
}

.count {
  font-weight: 600;
}

.share {
  color: var(--sy-muted);
  text-align: right;
}
</style>
