export function renderNodeToHtml(node: Node): string {
  const host = document.createElement("div");
  host.appendChild(node.cloneNode(true));
  return host.innerHTML;
}

export function renderFragmentToHtml(fragment: DocumentFragment): string {
  const host = document.createElement("div");
  host.appendChild(fragment.cloneNode(true));
  return host.innerHTML;
}

export function queryAllByComponent(root: ParentNode, component: string): Element[] {
  return Array.from(root.querySelectorAll(`[data-lia-component="${component}"]`));
}
