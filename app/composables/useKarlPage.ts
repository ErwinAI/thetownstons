export type KarlPageRef = {
  title: string
  path: string
}

export function useKarlPage() {
  return useState<KarlPageRef | null>('karl-page', () => null)
}
