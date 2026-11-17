import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

/**
 * PrimeVue preset for SyRH, aligned with src/assets/tokens.css.
 *
 * Lime is a fill colour, never a text colour: it does not have enough contrast
 * on white. Primary buttons are lime with dark text; for text, outlined or link
 * buttons use severity "secondary" or "contrast".
 */

// Warm neutral ramp shared by both schemes (50 = lightest, 950 = darkest).
const surface = {
  0: '#ffffff',
  50: '#f6f7f2',
  100: '#eeefe8',
  200: '#e2e4da',
  300: '#cfd2c5',
  400: '#a3a798',
  500: '#7b7f70',
  600: '#5d6154',
  700: '#45483e',
  800: '#2c2e28',
  900: '#1e1f1c',
  950: '#121311',
}

export const SyRHPreset = definePreset(Aura, {
  primitive: {
    borderRadius: {
      none: '0',
      xs: '6px',
      sm: '10px',
      md: '14px',
      lg: '18px',
      xl: '24px',
    },
  },
  semantic: {
    primary: {
      50: '#f8fde8',
      100: '#effbcb',
      200: '#e3f8a0',
      300: '#d2f65a',
      400: '#c6f04d',
      500: '#a8d42a',
      600: '#83a91c',
      700: '#63801a',
      800: '#4f651b',
      900: '#43561b',
      950: '#232f0a',
    },
    focusRing: {
      width: '2px',
      style: 'solid',
      color: '{text.color}',
      offset: '2px',
      shadow: 'none',
    },
    colorScheme: {
      light: {
        surface,
        primary: {
          color: '{primary.400}',
          contrastColor: '#14160f',
          hoverColor: '{primary.500}',
          activeColor: '{primary.600}',
        },
        highlight: {
          background: '{primary.100}',
          focusBackground: '{primary.200}',
          color: '{primary.950}',
          focusColor: '{primary.950}',
        },
        text: {
          color: '{surface.950}',
          hoverColor: '{surface.950}',
          mutedColor: '{surface.600}',
          hoverMutedColor: '{surface.700}',
        },
      },
      dark: {
        surface,
        primary: {
          color: '{primary.300}',
          contrastColor: '#14160f',
          hoverColor: '{primary.200}',
          activeColor: '{primary.100}',
        },
        highlight: {
          background: 'color-mix(in srgb, {primary.300}, transparent 82%)',
          focusBackground: 'color-mix(in srgb, {primary.300}, transparent 74%)',
          color: '{primary.100}',
          focusColor: '{primary.100}',
        },
        text: {
          color: '{surface.50}',
          hoverColor: '{surface.0}',
          mutedColor: '{surface.400}',
          hoverMutedColor: '{surface.300}',
        },
      },
    },
  },
  components: {
    button: {
      root: {
        borderRadius: '2rem',
      },
    },
    tag: {
      root: {
        borderRadius: '2rem',
      },
    },
    // The active tab keeps the text colour; lime only fills its underline.
    tabs: {
      tab: {
        activeColor: '{text.color}',
      },
    },
  },
})
