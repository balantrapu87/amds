/**
 * SVGO Configuration for Autonomous Motion Design Studio.
 * Preserves XML element IDs, classes, and structure for GSAP timeline selectors.
 */
export default {
  multipass: true,
  plugins: [
    {
      name: 'preset-default',
      params: {
        overrides: {
          // CRITICAL: Preserve IDs and class names so GSAP selectors (#layer-accent, .cls-1) work
          cleanupIds: false,
          removeUnknownsAndDefaults: false,
          removeViewBox: false,
          collapseGroups: false,
          convertShapeToPath: false,
          mergePaths: false,
        },
      },
    },
    // Prevent stripping user data attributes used in kinetic animations
    {
      name: 'removeAttrs',
      params: {
        attrs: ['data-name'],
      },
    },
    // Ensure XML namespaces and xmlns attributes are maintained
    {
      name: 'removeXMLNS',
      active: false,
    },
  ],
};
