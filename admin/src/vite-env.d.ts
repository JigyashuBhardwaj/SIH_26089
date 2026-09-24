/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Karmanya backend. See `admin/.env.example`. */
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
