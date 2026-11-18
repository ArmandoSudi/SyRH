import type { TreeNode } from 'primevue/treenode'

import type { TypeUnite, Unite } from '@/features/referentiels/api/referentiels'

export const NIVEAUX: Record<TypeUnite, number> = {
  direction: 1,
  departement: 2,
  service: 3,
  bureau: 4,
}

export const TYPE_SEVERITY: Record<TypeUnite, 'primary' | 'info' | 'success' | 'secondary'> = {
  direction: 'primary',
  departement: 'info',
  service: 'success',
  bureau: 'secondary',
}

export interface UniteNode extends TreeNode {
  key: string
  data: Unite
  children: UniteNode[]
}

function bySiblingOrder(a: UniteNode, b: UniteNode): number {
  return NIVEAUX[a.data.type] - NIVEAUX[b.data.type] || a.data.code.localeCompare(b.data.code)
}

/**
 * The flat list from the API as a tree. A unit whose parent is not in the list
 * is shown at the root rather than lost.
 */
export function buildTree(unites: Unite[]): UniteNode[] {
  const nodes = new Map<number, UniteNode>(
    unites.map((unite) => [unite.id, { key: String(unite.id), data: unite, children: [] }]),
  )
  const roots: UniteNode[] = []
  for (const node of nodes.values()) {
    const parent = node.data.parent === null ? undefined : nodes.get(node.data.parent)
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  const sort = (list: UniteNode[]) => {
    list.sort(bySiblingOrder)
    list.forEach((node) => sort(node.children))
  }
  sort(roots)
  return roots
}

/** Lower case, without accents, so "departement" finds "Département". */
function normalise(text: string): string {
  return text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

/** A tree node the filter and "expand all" can walk: the organisation's or the grid's. */
export interface Branch<N extends TreeNode> extends TreeNode {
  key: string
  data: { code: string; nom: string }
  children: N[]
}

function codeAndName(node: Branch<TreeNode>): string {
  return `${node.data.code} ${node.data.nom}`
}

/**
 * Nodes whose search text contains the text, with their ancestors. The search
 * text is the code and name unless the caller says otherwise.
 */
export function filterTree<N extends Branch<N>>(
  nodes: N[],
  text: string,
  label: (node: N) => string = codeAndName,
): N[] {
  const wanted = normalise(text.trim())
  if (!wanted) return nodes
  const keep = (node: N): N | null => {
    const children = node.children.map(keep).filter((child): child is N => !!child)
    const matches = normalise(label(node)).includes(wanted)
    return matches || children.length ? { ...node, children } : null
  }
  return nodes.map(keep).filter((node): node is N => !!node)
}

/** Every key that has children, for "expand all". */
export function expandedKeys<N extends Branch<N>>(nodes: N[]): Record<string, boolean> {
  const keys: Record<string, boolean> = {}
  const walk = (list: N[]) => {
    for (const node of list) {
      if (node.children.length) {
        keys[node.key] = true
        walk(node.children)
      }
    }
  }
  walk(nodes)
  return keys
}
