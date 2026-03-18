import { useState, useRef, useEffect, useLayoutEffect } from 'react'

/**
 * Enables Excel-style column resizing.
 *
 * Columns are stored as pixel widths.  On first paint the weights are scaled
 * to exactly fill the container so the table starts at 100 % width.  After
 * that each resize only changes the dragged column; the table grows / shrinks
 * accordingly and the container's overflow-x: auto provides the scroll.
 *
 * Usage:
 *   const { widths, sumPx, startResize, containerRef } = useColumnResize([90, 160, 80])
 *   <div ref={containerRef} className="overflow-x-auto ...">
 *     <Table style={{ tableLayout: 'fixed', width: sumPx }}>
 *       <th style={{ width: widths[0] }}>
 *         ...
 *         <ResizeHandle onMouseDown={e => startResize(0, e)} />
 *       </th>
 */
export function useColumnResize(initialWeights: number[]) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [widths, setWidths] = useState<number[]>(initialWeights)
  const drag = useRef<{ col: number; startX: number; startW: number } | null>(null)
  const initialized = useRef(false)

  // Scale the weights to fill the container on first paint (runs before browser paint).
  useLayoutEffect(() => {
    if (initialized.current || !containerRef.current) return
    initialized.current = true
    const containerW = containerRef.current.offsetWidth
    const totalWeight = initialWeights.reduce((a, b) => a + b, 0)
    setWidths(initialWeights.map(w => Math.round((w / totalWeight) * containerW)))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!drag.current) return
      const { col, startX, startW } = drag.current
      const delta = e.clientX - startX
      setWidths(prev => {
        const next = [...prev]
        next[col] = Math.max(48, startW + delta)
        return next
      })
    }

    function onMouseUp() {
      if (!drag.current) return
      drag.current = null
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    return () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  function startResize(col: number, e: React.MouseEvent) {
    e.preventDefault()
    e.stopPropagation()
    drag.current = { col, startX: e.clientX, startW: widths[col] }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  const sumPx = widths.reduce((a, b) => a + b, 0)

  return { widths, sumPx, startResize, containerRef }
}
