import type { RouteRecordRaw } from 'vue-router'

import { LOGIN_PATH } from '@/router/guards'

/** Screens shown without the app shell, to anonymous visitors. */
export const publicRoutes: RouteRecordRaw[] = [
  {
    path: LOGIN_PATH,
    name: 'login',
    component: () => import('./views/LoginView.vue'),
    meta: { title: 'Connexion', public: true },
  },
]

/** Screens inside the app shell, for the signed-in user. */
export const routes: RouteRecordRaw[] = [
  {
    path: 'compte/mot-de-passe',
    name: 'password',
    component: () => import('./views/PasswordView.vue'),
    meta: { title: 'Mot de passe' },
  },
]
