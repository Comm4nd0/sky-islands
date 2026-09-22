import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'uk.co.lumatechsolutions.skyislands',
  appName: 'Sky Islands',
  webDir: 'www',
  backgroundColor: '#12356b',
  ios: {
    // The Xcode target and shared scheme are both "Sky Islands"; the CLI defaults to "App".
    scheme: 'Sky Islands',
    contentInset: 'never',
    scrollEnabled: false,
    limitsNavigationsToAppBoundDomains: false,
  },
  plugins: {
    StatusBar: {
      overlaysWebView: true,
      style: 'DARK',
    },
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#12356b',
    },
  },
};

export default config;
