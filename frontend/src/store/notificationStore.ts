import { create } from 'zustand'
import type { Notification } from '../types'

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  addNotification: (n: Notification) => void
  markRead: (id: number) => void
  markAllRead: () => void
  clear: () => void
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (n) => {
    const notifications = [n, ...get().notifications].slice(0, 100)
    set({ notifications, unreadCount: notifications.filter((x) => !x.read).length })
  },

  markRead: (id) => {
    const notifications = get().notifications.map((n) =>
      n.id === id ? { ...n, read: true } : n,
    )
    set({ notifications, unreadCount: notifications.filter((x) => !x.read).length })
  },

  markAllRead: () => {
    const notifications = get().notifications.map((n) => ({ ...n, read: true }))
    set({ notifications, unreadCount: 0 })
  },

  clear: () => set({ notifications: [], unreadCount: 0 }),
}))
