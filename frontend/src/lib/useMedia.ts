import { useEffect, useState } from 'react'

/** True while the media query matches; follows resizes and rotations. */
export function useMedia(q: string) {
  const [on, setOn] = useState(() => window.matchMedia(q).matches)
  useEffect(() => {
    const m = window.matchMedia(q)
    const change = () => setOn(m.matches)
    m.addEventListener('change', change)
    return () => m.removeEventListener('change', change)
  }, [q])
  return on
}
