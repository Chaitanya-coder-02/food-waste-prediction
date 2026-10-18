/**
 * Food Waste Prediction – UI Scroll Animations & 3D Interactive Card System
 * Powered by GSAP ScrollTrigger & Vanilla CSS 3D
 */

(function () {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isPointerFine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  // Registry for Chart.js instances so ScrollTrigger can trigger progressive animations
  window.FoodWasteCharts = window.FoodWasteCharts || {};

  /**
   * Initialize 3D Card Tilt on Pointer Movement (Desktop only)
   */
  function init3DCardTilt() {
    if (prefersReducedMotion || !isPointerFine) return;

    const tiltCards = document.querySelectorAll('.card, .stat-card, .chart-card, .auth-card, .insight-card');

    tiltCards.forEach((card) => {
      // Create glare overlay if not already present
      if (!card.querySelector('.card-glare')) {
        const glare = document.createElement('div');
        glare.className = 'card-glare';
        card.appendChild(glare);
      }

      const glare = card.querySelector('.card-glare');

      let bounds = null;
      let rafId = null;

      function onMouseEnter() {
        bounds = card.getBoundingClientRect();
      }

      function onMouseMove(e) {
        if (!bounds) bounds = card.getBoundingClientRect();

        const x = e.clientX - bounds.left;
        const y = e.clientY - bounds.top;

        // Normalized from -1 to 1
        const normX = (x / bounds.width) * 2 - 1;
        const normY = (y / bounds.height) * 2 - 1;

        // Max tilt angles (in degrees)
        const maxRotX = card.classList.contains('auth-card') ? 4 : 7;
        const maxRotY = card.classList.contains('auth-card') ? 4 : 7;

        const rotX = -normY * maxRotX;
        const rotY = normX * maxRotY;

        if (rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
          card.style.transform = `perspective(1000px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) translateZ(8px)`;
          if (glare) {
            glare.style.background = `radial-gradient(circle at ${(normX * 40 + 50).toFixed(1)}% ${(normY * 40 + 50).toFixed(1)}%, rgba(255, 255, 255, 0.45) 0%, rgba(255, 255, 255, 0) 70%)`;
          }
        });
      }

      function onMouseLeave() {
        if (rafId) cancelAnimationFrame(rafId);
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
        bounds = null;
      }

      card.addEventListener('mouseenter', onMouseEnter);
      card.addEventListener('mousemove', onMouseMove);
      card.addEventListener('mouseleave', onMouseLeave);
    });
  }

  /**
   * Initializes GSAP ScrollTrigger entrance animations for UI components
   */
  function initScrollTriggers() {
    if (!window.gsap || !window.ScrollTrigger) return;
    gsap.registerPlugin(ScrollTrigger);

    if (prefersReducedMotion) return;

    // 1. Top Bar / Page Title 3D Perspective Entrance
    const pageTitle = document.querySelector('.page-title');
    if (pageTitle) {
      gsap.from(pageTitle, {
        duration: 0.85,
        opacity: 0,
        y: -18,
        rotateX: 18,
        transformOrigin: '50% 0%',
        ease: 'power3.out'
      });
    }

    // 2. Stat Cards 3D Perspective Forward Reveal
    const statCards = document.querySelectorAll('.stat-grid .stat-card');
    if (statCards.length > 0) {
      gsap.from(statCards, {
        duration: 0.75,
        opacity: 0,
        y: 35,
        scale: 0.94,
        rotateX: 12,
        stagger: 0.08,
        ease: 'power2.out',
        clearProps: 'scale,rotateX'
      });
    }

    // 3. Chart Cards Coordinated Staggered Reveal on Scroll
    const chartCards = document.querySelectorAll('.charts-grid .chart-card');
    chartCards.forEach((chartCard, idx) => {
      gsap.from(chartCard, {
        scrollTrigger: {
          trigger: chartCard,
          start: 'top 88%',
          toggleActions: 'play none none reverse'
        },
        duration: 0.75,
        opacity: 0,
        y: 40,
        rotateX: 8,
        ease: 'power2.out',
        clearProps: 'rotateX',
        onComplete: () => {
          // Trigger progressive chart animation if registered
          triggerChartAnimation(chartCard);
        }
      });
    });

    // 4. Data-Driven Operational Insights Cards Reveal
    const insightCards = document.querySelectorAll('.insights-grid .insight-card');
    if (insightCards.length > 0) {
      gsap.from(insightCards, {
        scrollTrigger: {
          trigger: '.insights-grid',
          start: 'top 85%',
          toggleActions: 'play none none reverse'
        },
        duration: 0.65,
        opacity: 0,
        x: -25,
        stagger: 0.1,
        ease: 'power2.out'
      });
    }

    // 5. Food Records Master Table Card Reveal
    const tableCards = document.querySelectorAll('.card:has(.data-table), .table-responsive');
    tableCards.forEach((tbl) => {
      gsap.from(tbl, {
        scrollTrigger: {
          trigger: tbl,
          start: 'top 88%',
          toggleActions: 'play none none reverse'
        },
        duration: 0.75,
        opacity: 0,
        y: 35,
        ease: 'power2.out'
      });
    });

    // 6. Auth Card Entrance (Login & Register)
    const authCard = document.querySelector('.auth-card');
    if (authCard) {
      gsap.from(authCard, {
        duration: 0.9,
        opacity: 0,
        y: 30,
        rotateY: -6,
        rotateX: 4,
        scale: 0.96,
        ease: 'power3.out',
        clearProps: 'scale,rotateX,rotateY'
      });
    }
  }

  /**
   * Triggers or replays smooth progressive drawing animation on Chart.js canvas
   * when its container scrolls into the viewport.
   */
  function triggerChartAnimation(cardElement) {
    const canvas = cardElement.querySelector('canvas');
    if (!canvas) return;

    const chartId = canvas.id;
    if (window.FoodWasteCharts && window.FoodWasteCharts[chartId]) {
      const chartInstance = window.FoodWasteCharts[chartId];
      if (typeof chartInstance.update === 'function') {
        chartInstance.update();
      }
    }
  }

  /**
   * Interactive Buttons Micro-interactions
   */
  function initButtonInteractions() {
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach((btn) => {
      btn.addEventListener('mousedown', () => {
        btn.style.transform = 'translateY(1px) scale(0.98)';
      });
      btn.addEventListener('mouseup', () => {
        btn.style.transform = '';
      });
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = '';
      });
    });
  }

  // Initialize once DOM is ready
  function init() {
    init3DCardTilt();
    initScrollTriggers();
    initButtonInteractions();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Re-run triggers on dynamically rendered changes
  window.FoodWasteAnimations = {
    refresh: () => {
      if (window.ScrollTrigger) ScrollTrigger.refresh();
      init3DCardTilt();
    },
    registerChart: (id, chartInstance) => {
      window.FoodWasteCharts[id] = chartInstance;
    }
  };

})();
