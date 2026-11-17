import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

import * as authApi from '@/features/auth/api/auth'
import { ApiError } from '@/shared/utils/http'

import PasswordView from '../PasswordView.vue'

vi.mock('@/features/auth/api/auth')

function mountView() {
  return mount(PasswordView, { global: { plugins: [PrimeVue, ToastService] } })
}

async function fill(
  wrapper: ReturnType<typeof mountView>,
  old: string,
  next: string,
  confirm: string,
) {
  await wrapper.get('#old-password').setValue(old)
  await wrapper.get('#new-password').setValue(next)
  await wrapper.get('#confirm-password').setValue(confirm)
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

describe('PasswordView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('blocks a mismatched confirmation before calling the API', async () => {
    const wrapper = mountView()

    await fill(wrapper, 'ancien', 'nouveau-1', 'nouveau-2')

    expect(authApi.changePassword).not.toHaveBeenCalled()
    expect(wrapper.get('[data-test="error-confirm"]').text()).toContain('ne correspondent pas')
  })

  it('shows API errors next to their fields', async () => {
    vi.mocked(authApi.changePassword).mockRejectedValue(
      new ApiError(400, 'invalide', {
        old_password: ['Le mot de passe actuel est incorrect.'],
        new_password: ['Ce mot de passe est trop courant.'],
      }),
    )
    const wrapper = mountView()

    await fill(wrapper, 'ancien', '12345678', '12345678')

    expect(wrapper.get('[data-test="error-old"]').text()).toBe(
      'Le mot de passe actuel est incorrect.',
    )
    expect(wrapper.get('[data-test="error-new"]').text()).toBe('Ce mot de passe est trop courant.')
  })

  it('sends the passwords and empties the form on success', async () => {
    vi.mocked(authApi.changePassword).mockResolvedValue()
    const wrapper = mountView()

    await fill(wrapper, 'ancien', 'nouveau-1', 'nouveau-1')

    expect(authApi.changePassword).toHaveBeenCalledWith('ancien', 'nouveau-1')
    expect((wrapper.get('#old-password').element as HTMLInputElement).value).toBe('')
    expect(wrapper.find('small').exists()).toBe(false)
  })

  it('reports a server failure', async () => {
    vi.mocked(authApi.changePassword).mockRejectedValue(new ApiError(500, 'panne'))
    const wrapper = mountView()

    await fill(wrapper, 'ancien', 'nouveau-1', 'nouveau-1')

    expect(wrapper.get('[data-test="form-error"]').text()).toContain('Enregistrement impossible')
  })
})
