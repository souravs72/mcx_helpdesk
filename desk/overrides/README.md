# MCX Helpdesk UI overrides

Place Vue/TS files here mirroring Helpdesk desk `@/` import paths.

Example: to override `@/pages/dashboard/Dashboard.vue`, add:

```
overrides/pages/dashboard/Dashboard.vue
```

These files are swapped in at compile time by `desk/vite.config.cjs` when you run:

```bash
bench build --app mcx_helpdesk
```

Do **not** copy files into `apps/helpdesk/desk/src`.

Use `@/` imports in override Vue files (never `./Sibling.vue`) — files are compiled from a temporary staging folder during build.
