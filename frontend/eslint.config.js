import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import boundaries from 'eslint-plugin-boundaries'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      boundaries,
    },
    settings: {
      'boundaries/elements': [
        {
          type: 'app',
          pattern: 'src/app/*',
        },
        {
          type: 'features',
          pattern: 'src/features/*',
          capture: ['featureName'],
        },
        {
          type: 'shared',
          pattern: 'src/(components|lib|utils)/*',
        },
        {
          type: 'types',
          pattern: 'src/types/*',
        },
        {
          type: 'config',
          pattern: 'src/config/*',
        },
      ],
    },
    rules: {
      // Prevent features from importing from other features
      'boundaries/element-types': [
        'error',
        {
          default: 'disallow',
          rules: [
            {
              from: 'features',
              allow: ['shared', 'types', 'config'],
            },
            {
              from: 'app',
              allow: ['features', 'shared', 'types', 'config'],
            },
            {
              from: 'shared',
              allow: ['types', 'config'],
            },
          ],
        },
      ],
    },
  },
])
