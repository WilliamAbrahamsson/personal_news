import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../pages/Dashboard.vue'),
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('../pages/About.vue'),
  },
  {
    path: '/sources',
    name: 'sources',
    component: () => import('../pages/Sources.vue'),
  },
  {
    path: '/add',
    name: 'add-source',
    component: () => import('../pages/AddSource.vue'),
  },
  {
    path: '/sources/:id',
    name: 'source-detail',
    component: () => import('../pages/SourceDetail.vue'),
  },
  {
    path: '/sources/:sourceId/videos/:videoId',
    name: 'video-detail',
    component: () => import('../pages/VideoDetail.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: {
      template: '<div style="padding:20px">Page not found.</div>',
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
