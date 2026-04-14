export function mountTemplate(root: HTMLElement, html: string): void {
  root.innerHTML = html;
}

export function queryRequired<T extends Element>(scope: ParentNode, selector: string): T {
  const node = scope.querySelector<T>(selector);
  if (!node) {
    throw new Error(`Missing required node: ${selector}`);
  }
  return node;
}
