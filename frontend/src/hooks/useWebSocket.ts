import { useEffect, useRef, useCallback, useState } from 'react'
import type { WSMessage } from '../types'
import { useNotificationStore } from '../store/notificationStore'

interface UseWebSocketOptions {
  url?: string
  onMessage?: (msg: WSMessage) => void
  reconnectInterval?: number
  maxRetries?: number
}

export function useWebSocket(options?: UseWebSocketOptions) {
  const {
    url = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`,
    onMessage,
    reconnectInterval = 5000,
    maxRetries = 3,
  } = options ?? {}

  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const retriesRef = useRef(0)
  const stoppedRef = useRef(false)
  const addNotification = useNotificationStore((s) => s.addNotification)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (stoppedRef.current) return
    const token = localStorage.getItem('access_token')
    if (!token) return
    if (retriesRef.current >= maxRetries) return

    // Close previous connection if any
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      wsRef.current.close()
    }

    const ws = new WebSocket(`${url}?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => {
      retriesRef.current = 0
      setConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        onMessageRef.current?.(msg)
        if (msg.type === 'notification' || msg.type === 'alert') {
          addNotification({
            id: Date.now(),
            title: (msg.payload.title as string) || msg.type,
            message: (msg.payload.message as string) || '',
            severity: (msg.payload.severity as string) || 'info',
            read: false,
            created_at: msg.timestamp,
          } as import('../types').Notification)
        }
      } catch { /* ignore malformed */ }
    }

    ws.onclose = (e) => {
      setConnected(false)
      if (stoppedRef.current) return
      // Don't reconnect on auth failure
      if (e.code === 4001) return
      retriesRef.current += 1
      if (retriesRef.current < maxRetries) {
        reconnectTimer.current = setTimeout(connect, reconnectInterval * retriesRef.current)
      }
    }

    ws.onerror = () => {
      ws.onclose = null
      ws.close()
      setConnected(false)
      if (stoppedRef.current) return
      retriesRef.current += 1
      if (retriesRef.current < maxRetries) {
        reconnectTimer.current = setTimeout(connect, reconnectInterval * retriesRef.current)
      }
    }
  }, [url, maxRetries, reconnectInterval, addNotification])

  useEffect(() => {
    stoppedRef.current = false
    retriesRef.current = 0
    // Delay initial connect to let the page settle
    reconnectTimer.current = setTimeout(connect, 1000)

    return () => {
      stoppedRef.current = true
      clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, send }
}
