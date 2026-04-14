const MOBILE_WIDTH_THRESHOLD = 768;

const MOBILE_UA_PATTERN =
  /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;

/**
 * Detect whether the current device should render the mobile shell.
 * Uses user-agent heuristic combined with viewport width.
 */
export function isMobile(): boolean {
  const uaMatch = MOBILE_UA_PATTERN.test(navigator.userAgent);
  const narrowViewport = window.innerWidth < MOBILE_WIDTH_THRESHOLD;
  return uaMatch || narrowViewport;
}
