import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import HomeView from '../HomeView.vue'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('HomeView', () => {
  it('shows the database reported by the API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          status: 'ok',
          database: { vendor: 'postgresql', name: 'syrh', version: '17.10' },
        }),
      }),
    )

    const wrapper = mount(HomeView)
    await flushPromises()

    expect(wrapper.get('[data-test="health"]').text()).toContain('postgresql 17.10')
  })

  it('shows an error when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502 }))

    const wrapper = mount(HomeView)
    await flushPromises()

    expect(wrapper.get('[data-test="error"]').text()).toContain('HTTP 502')
  })
})
