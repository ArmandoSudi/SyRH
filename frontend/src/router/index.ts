import { createRouter, createWebHistory } from 'vue-router'

import AppShell from '@/layouts/AppShell.vue'

import { installAuthGuards, LOGIN_PATH } from './guards'

// Screens are lazy-loaded so the first load stays small as modules are added.
const placeholder = () => import('@/views/PlaceholderView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: LOGIN_PATH,
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: 'Connexion', public: true },
    },
    {
      path: '/',
      component: AppShell,
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: 'Tableau de bord' },
        },
        { path: 'agents', name: 'agents', component: placeholder, meta: { title: 'Agents' } },
        { path: 'carriere', name: 'carriere', component: placeholder, meta: { title: 'Carrière' } },
        {
          path: 'personnel',
          name: 'personnel',
          component: placeholder,
          meta: { title: 'Présences et absences' },
        },
        { path: 'paie', name: 'paie', component: placeholder, meta: { title: 'Paie' } },
        { path: 'social', name: 'social', component: placeholder, meta: { title: 'Social' } },
        {
          path: 'formation',
          name: 'formation',
          component: placeholder,
          meta: { title: 'Formation' },
        },
        {
          path: 'referentiels',
          name: 'referentiels',
          component: placeholder,
          meta: { title: 'Référentiels' },
        },
        {
          path: 'systeme',
          name: 'systeme',
          component: () => import('@/views/SystemView.vue'),
          meta: { title: 'Système' },
        },
        {
          path: 'design',
          name: 'design',
          component: () => import('@/views/DesignView.vue'),
          meta: { title: 'Système de design' },
        },
        {
          path: 'compte/mot-de-passe',
          name: 'password',
          component: () => import('@/views/PasswordView.vue'),
          meta: { title: 'Mot de passe' },
        },
      ],
    },
  ],
})

installAuthGuards(router)

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} · SyRH` : 'SyRH'
})

export default router
