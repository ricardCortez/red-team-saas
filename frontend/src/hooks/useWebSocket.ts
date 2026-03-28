import { useEffect, useRef, useCallback, useState } from 'react'
import type { WSMessage } from '../types'
import { useNotificationStore } from '../store/notificationStore'

interface UseWebSocketOptions {
  url?: string
  onMessage?: (msg: WSMessage) => void
  reconnectInterval?: number
}

export function useWebSocket(options?: UseWebSocketOptions) {
  const {
    url = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`,
    onMessage,
    reconnectInterval = 3000,
  } = options ?? {}

  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const addNotification = useNotificationStore((s) => s.addNotification)

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    const wsUrl = `${url}?token=${token}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        onMessage?.(msg)

        if (msg.type === 'notification' || msg.type === 'alert') {
          addNotification({
            id: Date.now(),
            title: (msg.payload.title as string) || msg.type,
            message: (msg.payload.message as string) || '',
            severity: (msg.payload.severity as WSMessage['payload']['severity'] & string) || 'info',
            read: false,
            created_at: msg.timestamp,
          } as import('../types').Notification)
        }
      } catch { /* ignore malformed */ }
    }

    ws.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, reconnectInterval)
    }

    ws.onerror = () => ws.close()
  }, [url, onMessage, reconnectInterval, addNotification])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, send }
}
