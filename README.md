# Pour-it-out

## Vercel Deployment

The app uses Vercel's Python runtime. The journal keeps text entries and media in browser `localStorage`, separated by the signed-in username. This means entries are available only in the same browser and Vercel domain; they do not sync between devices, browsers, or preview and production deployments. Browser storage can be cleared and has limited capacity, so large video attachments may not fit.

Accounts still require a persistent hosted MySQL database. Vercel project storage is not used for database files or uploaded media.

1. Push this repository to GitHub, then import it at Vercel. Keep the project root set to the repository root.
2. Create a hosted MySQL database and set `DATABASE_URL` in Vercel's Production environment. Use a SQLAlchemy-compatible MySQL URL, for example `mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE?charset=utf8mb4`. URL-encode reserved characters in credentials.
3. Set `SECRET_KEY` in Vercel's Production environment to a private random value of at least 32 characters. Do not commit it or place it in `vercel.json`.
4. Initialize the hosted schema once, using the same environment values locally. Install dependencies with `pip install -e .`, then run `flask --app backend.app init-db`.
5. Deploy from the Vercel dashboard or run `npx vercel --prod` from the repository root.

For local Vercel-style testing, install the Vercel CLI and run `npx vercel dev`. The local `.env.local` file is ignored by Git and can hold development values. Existing accounts in a local database are not copied to the hosted database automatically.

The Vercel build copies assets from `backend/static` into `public/static`, excluding uploads, and `vercel.json` includes the Flask templates in the Python function bundle. The existing local uploaded media files are not part of the deployment.