interface PoseEntry {
  src: string;
  phrase: string;
}

const LIA_POSES: PoseEntry[] = [
  { src: "/assets/poses/lia-pose-reading.png", phrase: "Entendiendo..." },
  { src: "/assets/poses/lia-pose-confused.png", phrase: "Confundiéndome..." },
  { src: "/assets/poses/lia-pose-calculator.png", phrase: "Revisando..." },
  { src: "/assets/poses/lia-pose-frustrated.png", phrase: "Frustrándome..." },
  { src: "/assets/poses/lia-pose-writing.png", phrase: "Mejorándome..." },
  { src: "/assets/poses/lia-pose-calculator.png", phrase: "Resolviendo!" },
  { src: "/assets/poses/lia-pose-trasnochando.png", phrase: "Trasnochando..." },
  { src: "/assets/poses/lia-pose-cuestionando.png", phrase: "Cuestionando..." },
  { src: "/assets/poses/lia-pose-revisando.png", phrase: "Revisando..." },
  { src: "/assets/poses/lia-pose-sopesando.png", phrase: "Sopesando..." },
];

export class LiaThinkingAnimation {
  private container: HTMLElement;
  private phraseNode: HTMLParagraphElement | null = null;
  private images: HTMLImageElement[] = [];
  private currentIndex: number = 0;
  private intervalId: number | null = null;
  private displayDuration: number;
  private reducedMotion: boolean;

  constructor(containerId: string, displayDurationMs: number = 2500) {
    const el = document.getElementById(containerId);
    if (!el) throw new Error(`Container #${containerId} not found`);
    this.container = el;
    this.displayDuration = displayDurationMs;
    this.reducedMotion =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  private getRandomIndex(excludeIndex: number): number {
    if (this.images.length <= 1) return 0;
    let newIndex: number;
    do {
      newIndex = Math.floor(Math.random() * this.images.length);
    } while (newIndex === excludeIndex);
    return newIndex;
  }

  private renderPhrase(): void {
    if (this.phraseNode) {
      this.phraseNode.textContent = LIA_POSES[this.currentIndex].phrase;
    }
  }

  public init(): void {
    this.container.innerHTML = "";
    this.container.classList.add("lia-thinking-container");
    this.currentIndex = Math.floor(Math.random() * LIA_POSES.length);

    // Image area — fixed height, images absolutely positioned inside
    const imageArea = document.createElement("div");
    imageArea.className = "lia-thinking-image-area";

    LIA_POSES.forEach((entry, index) => {
      const img = document.createElement("img");
      img.src = entry.src;
      img.className = "lia-pose";
      img.alt = "";
      if (index === this.currentIndex) img.classList.add("active");
      img.onerror = () => console.warn(`Failed to load LIA pose: ${entry.src}`);
      imageArea.appendChild(img);
      this.images.push(img);
    });

    this.container.appendChild(imageArea);

    // Phrase — sits below the image area in normal flow
    const p = document.createElement("p");
    p.className = "lia-thinking-phrase";
    this.container.appendChild(p);
    this.phraseNode = p;
    this.renderPhrase();
  }

  public start(): void {
    if (this.images.length <= 1 || this.reducedMotion) return;
    this.stop();
    this.intervalId = window.setInterval(() => {
      this.images[this.currentIndex].classList.remove("active");
      this.currentIndex = this.getRandomIndex(this.currentIndex);
      this.images[this.currentIndex].classList.add("active");
      this.renderPhrase();
    }, this.displayDuration);
  }

  public stop(): void {
    if (this.intervalId !== null) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
}
