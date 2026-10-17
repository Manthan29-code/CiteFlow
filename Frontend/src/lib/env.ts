import { z } from 'zod';

const envSchema = z.object({
  VITE_API_BASE_URL: z.string().default('/api/v1'),
  VITE_APP_NAME: z.string().default('CiteFlow'),
  VITE_MAX_UPLOAD_MB: z.coerce.number().int().positive().default(25),
  VITE_ALLOWED_EXTENSIONS: z
    .string()
    .default('pdf')
    .transform((s) =>
      s
        .split(',')
        .map((x) => x.trim().toLowerCase())
        .filter(Boolean)
    ),
  VITE_PAGE_SIZE: z.coerce.number().int().min(1).max(500).default(100),
  VITE_UPLOAD_CONCURRENCY: z.coerce.number().int().min(1).max(5).default(2),
  VITE_PASSWORD_MIN_LENGTH: z.coerce.number().int().min(1).default(6),
  VITE_JOB_POLL_INTERVAL_MS: z.coerce.number().int().positive().default(2000),
  VITE_JOB_POLL_MAX_INTERVAL_MS: z.coerce.number().int().positive().default(10000),
  VITE_ENABLE_SSE: z
    .string()
    .default('false')
    .transform((s) => s.toLowerCase() === 'true'),
});

let parsedEnv: z.infer<typeof envSchema>;

try {
  parsedEnv = envSchema.parse(import.meta.env);
} catch (error) {
  console.warn('Environment validation fallback to defaults:', error);
  parsedEnv = envSchema.parse({});
}

export const env = parsedEnv;
