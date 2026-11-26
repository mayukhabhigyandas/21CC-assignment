# SkillMatch Frontend

A small React UI for learner login, profile skill editing, and ranked opportunity matches with explanations.

## Run locally

Start the backend at `http://localhost:8000`, then run:

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. Set `VITE_API_BASE_URL` in a `.env.local` file if the API runs at another address. The backend allows both localhost Vite origins by default; set `FRONTEND_ORIGINS` to a comma-separated origin list to override them.

Seeded learner sign-in: `learner1@example.com` / `learner123`.
