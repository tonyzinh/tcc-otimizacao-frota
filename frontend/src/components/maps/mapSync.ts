import type { Map as MapLibreMap } from 'maplibre-gl'

/** Grupo de mapas com câmera compartilhada (centro, zoom, rotação e inclinação). */
export interface MapSync {
  register(map: MapLibreMap): () => void
}

export function createMapSync(): MapSync {
  const maps = new Set<MapLibreMap>()
  let syncing = false

  return {
    register(map) {
      const peer = [...maps][0]
      if (peer) {
        map.jumpTo({ center: peer.getCenter(), zoom: peer.getZoom(), bearing: peer.getBearing(), pitch: peer.getPitch() })
      }
      maps.add(map)
      const onMove = () => {
        if (syncing) return
        syncing = true
        try {
          const camera = { center: map.getCenter(), zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch() }
          for (const other of maps) if (other !== map) other.jumpTo(camera)
        } finally {
          syncing = false
        }
      }
      map.on('move', onMove)
      return () => {
        map.off('move', onMove)
        maps.delete(map)
      }
    },
  }
}
