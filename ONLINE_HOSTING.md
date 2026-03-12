# Online Hosting (Shareable Links)

This app can be hosted online so participants use links from their own machines.

## Option A: Streamlit Community Cloud (fastest)

1. Push this project to a GitHub repository.
2. Go to Streamlit Community Cloud and deploy from that repo.
3. Set **Main file path** to `app.py`.
4. In app settings, add these secrets/environment values:

- `OPENAI_API_KEY`
- `PUBLIC_BASE_URL` (your deployed app URL, e.g. `https://your-app.streamlit.app`)
- `COORDINATOR_PASSCODE` (optional but recommended)

5. Redeploy/restart the app.

## Option B: Your own server (Render/Azure/AWS)

1. Deploy as a web service that runs:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

2. Configure environment variables:

- `OPENAI_API_KEY`
- `PUBLIC_BASE_URL=https://your-domain`
- `COORDINATOR_PASSCODE=your-code`

## Link Sharing Workflow

1. Open the deployed app URL.
2. In sidebar, use **Combination Links**.
3. Select `Group` + `Slot`.
4. Share:

- `Doctor Link` to participant doctor.
- `SP Link` only when assignment is SP.

Example:

- Doctor: `https://your-domain/?combo=A4&participant=doctor`
- SP: `https://your-domain/?participant=sp&session=study_a4`

## Important

- Do not use `localhost` for participants on other machines.
- Rotate any previously exposed OpenAI API keys.
