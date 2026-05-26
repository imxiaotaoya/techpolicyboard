import { useEffect, useRef } from 'react';

export function useAutoScroll(
  speed: number = 0.3,
  enabled: boolean = true
) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let raf = 0;
    let pos = 0;
    const el = scrollRef.current;
    if (!el) return;

    const tick = () => {
      if (!enabled || el.matches(':hover')) {
        raf = requestAnimationFrame(tick);
        return;
      }
      pos += speed;
      if (pos >= el.scrollHeight / 2) pos = 0;
      el.scrollTop = pos;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [speed, enabled]);

  return scrollRef;
}
