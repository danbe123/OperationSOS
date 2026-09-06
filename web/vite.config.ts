import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const backend = 'http://127.0.0.1:8080';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // The dev stack puts Caddy on 8080 in front of this server and phones reach it by IP or sos.local.
    allowedHosts: true,
    proxy: {
      '/api': backend,
      '/kiwix': backend,
      '/maps': backend,
      '/docs': backend,
    },
  },
  preview: { port: 4173, strictPort: true },
  build: {
    target: 'es2022',
    sourcemap: false,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
        // The front door is the whole point of the box, and it was arriving as one 2.24 MB file
        // holding MapLibre, the EPUB reader and the on-screen keyboard — none of which Now uses.
        // The routes that need them are loaded on demand (`router.tsx`, `kiosk/KeyboardMount.tsx`);
        // naming the libraries here keeps each one in a chunk of its own, so opening the map does
        // not also fetch the reader, and a rebuilt guide never invalidates the map's cache entry.
        // Matched on the package's own directory, not on the name anywhere in the path: pnpm keeps
        // a package's dependencies under `.pnpm/<name>@<version>/node_modules/`, so a looser test
        // put epubjs's own dependencies in the epub chunk — and anything else that shared one then
        // imported the 240 kB reader on the front door.
        manualChunks(id) {
          const inPackage = (name: string) => id.includes(`/node_modules/${name}/`);
          if (!id.includes('node_modules')) return undefined;
          if (inPackage('maplibre-gl') || inPackage('pmtiles')) return 'maplibre';
          if (inPackage('epubjs') || inPackage('jszip')) return 'epub';
          if (inPackage('simple-keyboard')) return 'keyboard';
          if (inPackage('proj4')) return 'grid';
          if (inPackage('qrcode')) return 'qr';
          if (inPackage('react') || inPackage('react-dom') || inPackage('react-router') || inPackage('scheduler')) return 'react';
          // Everything else is left to Rollup, which puts a library used by one screen into that
          // screen's own chunk rather than on the front door.
          return undefined;
        },
      },
    },
  },
});
