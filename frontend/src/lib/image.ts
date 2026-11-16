export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024
const MAX_EDGE = 1024
const ACCEPTED = ['image/jpeg', 'image/png']

/** Why a file can't be scanned, or null if it's fine (checked before any upload). */
export function rejectReason(f: File): string | null {
  if (!ACCEPTED.includes(f.type)) return 'Use a JPG or PNG image.'
  if (f.size > MAX_UPLOAD_BYTES) return 'That image is over 5 MB. Choose a smaller one.'
  return null
}

/** Downscale to ≤ 1024 px on the longest edge and re-encode as JPEG (q≈0.85). */
export async function shrinkForVision(blob: Blob): Promise<Blob> {
  const bmp = await createImageBitmap(blob)
  const scale = Math.min(1, MAX_EDGE / Math.max(bmp.width, bmp.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bmp.width * scale)
  canvas.height = Math.round(bmp.height * scale)
  canvas.getContext('2d')?.drawImage(bmp, 0, 0, canvas.width, canvas.height)
  bmp.close()
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('encode failed'))), 'image/jpeg', 0.85),
  )
}
